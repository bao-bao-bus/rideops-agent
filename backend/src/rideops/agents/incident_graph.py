from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from rideops.rag.service import RAGService
from rideops.repositories import BusinessToolError, SQLiteBusinessRepository
from rideops.services import BusinessTools
from rideops.skills.router import SkillRouter


class IncidentState(TypedDict, total=False):
    run_id: str
    user_id: str
    message: str
    selected_skill: str | None
    collected_fields: dict[str, str | None]
    missing_fields: list[str]
    evidence: list[dict]
    planned_actions: list[dict]
    approval: str
    action_results: list[dict]
    final_state: dict
    workflow_status: str
    error_history: list[dict]
    ticket_id: str | None


class IncidentWorkflow:
    def __init__(self, rag: RAGService, repository: SQLiteBusinessRepository, router: SkillRouter, tools: BusinessTools | None = None) -> None:
        self.rag = rag
        self.repository = repository
        self.tools = tools or BusinessTools(repository)
        self.router = router
        self.prepare_graph = self._build_prepare_graph()
        self.execute_graph = self._build_execute_graph()

    def _build_prepare_graph(self):
        graph = StateGraph(IncidentState)
        graph.add_node("route", self.route)
        graph.add_node("retrieve_policy", self.retrieve_policy)
        graph.add_node("query_order", self.query_order)
        graph.add_node("plan_actions", self.plan_actions)
        graph.add_edge(START, "route")
        graph.add_edge("route", "retrieve_policy")
        graph.add_conditional_edges("retrieve_policy", self._continue_after_retrieval, {"query_order": "query_order", "end": END})
        graph.add_conditional_edges("query_order", self._continue_after_order, {"plan_actions": "plan_actions", "end": END})
        graph.add_edge("plan_actions", END)
        return graph.compile()

    def _build_execute_graph(self):
        graph = StateGraph(IncidentState)
        graph.add_node("execute_actions", self.execute_actions)
        graph.add_node("verify_results", self.verify_results)
        graph.add_edge(START, "execute_actions")
        graph.add_edge("execute_actions", "verify_results")
        graph.add_edge("verify_results", END)
        return graph.compile()

    def route(self, state: IncidentState) -> dict[str, Any]:
        selected = self.router.route(state["message"]).skill
        if selected is None or selected.name != "accident-handling":
            return {"selected_skill": selected.name if selected else None, "workflow_status": "failed", "error_history": [{"code": "UNSUPPORTED_SKILL", "message": "当前 MVP 只处理事故场景"}]}
        return {"selected_skill": selected.name}

    def retrieve_policy(self, state: IncidentState) -> dict[str, Any]:
        if state.get("workflow_status") == "failed":
            return {}
        result = self.rag.query(state["message"], top_k=3)
        if not result.answerable:
            return {"workflow_status": "failed", "evidence": [], "error_history": [{"code": "NO_EVIDENCE", "message": result.refusal_reason}]}
        return {"evidence": [item.model_dump(mode="json") for item in result.evidence]}

    def _continue_after_retrieval(self, state: IncidentState) -> str:
        return "end" if state.get("workflow_status") == "failed" else "query_order"

    def query_order(self, state: IncidentState) -> dict[str, Any]:
        fields = state.get("collected_fields", {})
        missing = [field for field in ("order_id", "location", "description") if not fields.get(field)]
        if missing:
            return {"missing_fields": missing, "workflow_status": "waiting_for_input"}
        order = self.tools.get_active_order(fields["order_id"])
        if order is None:
            return {"workflow_status": "failed", "error_history": [{"code": "NOT_FOUND", "message": f"找不到进行中的订单: {fields['order_id']}"}]}
        fields.setdefault("vehicle_id", order.vehicle_id)
        return {"collected_fields": fields, "final_state": {"order": order.model_dump(mode="json")}}

    def _continue_after_order(self, state: IncidentState) -> str:
        return "end" if state.get("workflow_status") in {"waiting_for_input", "failed"} else "plan_actions"

    def plan_actions(self, state: IncidentState) -> dict[str, Any]:
        fields = state["collected_fields"]
        run_id = state["run_id"]
        actions = [
            {"action_id": "suspend-billing", "tool": "suspend_order_billing", "requires_approval": True, "arguments": {"order_id": fields["order_id"], "idempotency_key": f"{run_id}:suspend-billing"}},
            {"action_id": "disable-vehicle", "tool": "mark_vehicle_unavailable", "requires_approval": True, "arguments": {"vehicle_id": fields["vehicle_id"], "idempotency_key": f"{run_id}:disable-vehicle"}},
            {"action_id": "create-ticket", "tool": "create_incident_ticket", "requires_approval": True, "arguments": {"order_id": fields["order_id"], "user_id": state["user_id"], "description": fields["description"], "idempotency_key": f"{run_id}:create-ticket"}},
        ]
        return {"planned_actions": actions, "approval": "pending", "workflow_status": "awaiting_approval"}

    def execute_actions(self, state: IncidentState) -> dict[str, Any]:
        if state.get("approval") != "approved":
            return {"workflow_status": "safe_terminated", "action_results": []}
        results = list(state.get("action_results", []))
        ticket_id = state.get("ticket_id")
        for action in state.get("planned_actions", []):
            if any(result.get("action_id") == action["action_id"] for result in results):
                continue
            try:
                arguments = action["arguments"]
                if action["tool"] == "suspend_order_billing":
                    result = self.tools.suspend_order_billing(**arguments)
                elif action["tool"] == "mark_vehicle_unavailable":
                    result = self.tools.mark_vehicle_unavailable(**arguments)
                else:
                    result = self.tools.create_incident_ticket(**arguments)
                    ticket_id = result["ticket_id"]
                results.append({"action_id": action["action_id"], "tool": action["tool"], "status": "completed", "result": result})
            except BusinessToolError as exc:
                results.append({"action_id": action["action_id"], "tool": action["tool"], "status": "failed", "error_code": exc.code, "error": exc.message})
                return {"action_results": results, "workflow_status": "failed", "error_history": [{"code": exc.code, "message": exc.message}]}
        return {"action_results": results, "ticket_id": ticket_id}

    def verify_results(self, state: IncidentState) -> dict[str, Any]:
        if state.get("workflow_status") in {"failed", "safe_terminated"}:
            return {}
        fields = state["collected_fields"]
        order = self.tools.get_order(fields["order_id"])
        vehicle = self.tools.get_vehicle_status(fields["vehicle_id"])
        ticket = self.tools.get_incident_ticket(state.get("ticket_id")) if state.get("ticket_id") else None
        return {"final_state": {"order": order.model_dump(mode="json") if order else None, "vehicle": vehicle.model_dump(mode="json") if vehicle else None, "ticket": ticket.model_dump(mode="json") if ticket else None}, "workflow_status": "completed"}

    def prepare(self, state: IncidentState) -> IncidentState:
        return self.prepare_graph.invoke(state)

    def execute(self, state: IncidentState) -> IncidentState:
        return self.execute_graph.invoke(state)
