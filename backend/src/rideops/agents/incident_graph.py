from collections.abc import Callable
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
    def __init__(self, rag: RAGService, repository: SQLiteBusinessRepository, router: SkillRouter, tools: BusinessTools | None = None, event_sink: Callable[[str, str, dict], dict] | None = None) -> None:
        self.rag = rag
        self.repository = repository
        self.tools = tools or BusinessTools(repository)
        self.router = router
        self.event_sink = event_sink
        self.prepare_graph = self._build_prepare_graph()
        self.execute_graph = self._build_execute_graph()

    def _emit(self, state: IncidentState, event_type: str, payload: dict | None = None) -> None:
        if self.event_sink:
            self.event_sink(state["run_id"], event_type, payload or {})

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
            self._emit(state, "run.failed", {"code": "UNSUPPORTED_SKILL"})
            return {"selected_skill": selected.name if selected else None, "workflow_status": "failed", "error_history": [{"code": "UNSUPPORTED_SKILL", "message": "当前 MVP 只处理事故场景"}]}
        self._emit(state, "skill.selected", {"skill": selected.name})
        return {"selected_skill": selected.name}

    def retrieve_policy(self, state: IncidentState) -> dict[str, Any]:
        if state.get("workflow_status") == "failed":
            return {}
        result = self.rag.query(state["message"], top_k=3)
        if not result.answerable:
            self._emit(state, "run.failed", {"code": "NO_EVIDENCE", "reason": result.refusal_reason})
            return {"workflow_status": "failed", "evidence": [], "error_history": [{"code": "NO_EVIDENCE", "message": result.refusal_reason}]}
        evidence = [item.model_dump(mode="json") for item in result.evidence]
        self._emit(state, "evidence.retrieved", {"count": len(evidence), "strategy": result.retrieval_strategy})
        return {"evidence": evidence}

    def _continue_after_retrieval(self, state: IncidentState) -> str:
        return "end" if state.get("workflow_status") == "failed" else "query_order"

    def query_order(self, state: IncidentState) -> dict[str, Any]:
        fields = state.get("collected_fields", {})
        missing = [field for field in ("order_id", "location", "description") if not fields.get(field)]
        if missing:
            self._emit(state, "input.required", {"fields": missing})
            return {"missing_fields": missing, "workflow_status": "waiting_for_input"}
        order = self.tools.get_active_order(fields["order_id"])
        if order is None:
            self._emit(state, "run.failed", {"code": "NOT_FOUND", "order_id": fields["order_id"]})
            return {"workflow_status": "failed", "error_history": [{"code": "NOT_FOUND", "message": f"找不到进行中的订单: {fields['order_id']}"}]}
        fields.setdefault("vehicle_id", order.vehicle_id)
        self._emit(state, "business.state.queried", {"order_id": order.order_id, "vehicle_id": order.vehicle_id})
        return {"collected_fields": fields, "final_state": {"order": order.model_dump(mode="json")}}

    def _continue_after_order(self, state: IncidentState) -> str:
        return "end" if state.get("workflow_status") in {"waiting_for_input", "failed"} else "plan_actions"

    def plan_actions(self, state: IncidentState) -> dict[str, Any]:
        fields = state["collected_fields"]
        run_id = state["run_id"]
        actions = [
            {"action_id": "suspend-billing", "tool": "suspend_order_billing", "title": "暂停订单计费", "reason": "用户报告事故且订单仍在计费", "risk": "影响当前订单计费状态", "requires_approval": True, "arguments": {"order_id": fields["order_id"], "idempotency_key": f"{run_id}:suspend-billing"}},
            {"action_id": "disable-vehicle", "tool": "mark_vehicle_unavailable", "title": "车辆标记为不可用", "reason": "车辆存在碰撞或安全风险", "risk": "车辆暂时无法被其他用户使用", "requires_approval": True, "arguments": {"vehicle_id": fields["vehicle_id"], "idempotency_key": f"{run_id}:disable-vehicle"}},
            {"action_id": "create-ticket", "tool": "create_incident_ticket", "title": "创建事故工单", "reason": "保留事故记录并交给后续运营处理", "risk": "新增一条事故工单记录", "requires_approval": True, "arguments": {"order_id": fields["order_id"], "user_id": state["user_id"], "description": fields["description"], "idempotency_key": f"{run_id}:create-ticket"}},
        ]
        self._emit(state, "approval.required", {"action_count": len(actions), "actions": [action["tool"] for action in actions]})
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
                self._emit(state, "tool.started", {"action_id": action["action_id"], "tool": action["tool"]})
                if action["tool"] == "suspend_order_billing":
                    result = self.tools.suspend_order_billing(**arguments)
                elif action["tool"] == "mark_vehicle_unavailable":
                    result = self.tools.mark_vehicle_unavailable(**arguments)
                else:
                    result = self.tools.create_incident_ticket(**arguments)
                    ticket_id = result["ticket_id"]
                results.append({"action_id": action["action_id"], "tool": action["tool"], "status": "completed", "result": result})
                self._emit(state, "tool.completed", {"action_id": action["action_id"], "tool": action["tool"]})
            except BusinessToolError as exc:
                results.append({"action_id": action["action_id"], "tool": action["tool"], "status": "failed", "error_code": exc.code, "error": exc.message})
                self._emit(state, "tool.failed", {"action_id": action["action_id"], "tool": action["tool"], "code": exc.code})
                return {"action_results": results, "workflow_status": "failed", "error_history": [{"code": exc.code, "message": exc.message}]}
        return {"action_results": results, "ticket_id": ticket_id}

    def verify_results(self, state: IncidentState) -> dict[str, Any]:
        if state.get("workflow_status") in {"failed", "safe_terminated"}:
            return {}
        fields = state["collected_fields"]
        order = self.tools.get_order(fields["order_id"])
        vehicle = self.tools.get_vehicle_status(fields["vehicle_id"])
        ticket = self.tools.get_incident_ticket(state.get("ticket_id")) if state.get("ticket_id") else None
        self._emit(state, "run.completed", {"ticket_id": ticket.ticket_id if ticket else None})
        return {"final_state": {"order": order.model_dump(mode="json") if order else None, "vehicle": vehicle.model_dump(mode="json") if vehicle else None, "ticket": ticket.model_dump(mode="json") if ticket else None}, "workflow_status": "completed"}

    def prepare(self, state: IncidentState) -> IncidentState:
        return self.prepare_graph.invoke(state)

    def execute(self, state: IncidentState) -> IncidentState:
        return self.execute_graph.invoke(state)
