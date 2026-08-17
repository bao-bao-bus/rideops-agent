from uuid import uuid4

from fastapi import APIRouter, HTTPException

from rideops.agents import IncidentWorkflow
from rideops.domain.models import IncidentRunRequest, ProvideInfoRequest, ResumeRequest, RunResponse


def _message(state: dict) -> str:
    status = state.get("workflow_status")
    if status == "waiting_for_input":
        return f"请补充信息：{', '.join(state.get('missing_fields', []))}。"
    if status == "awaiting_approval":
        return "已检索事故处理规则并核验订单，写入动作等待人工审批。"
    if status == "completed":
        return "事故工单已创建，订单、车辆和工单最终状态已回读验证。"
    if status == "safe_terminated":
        return "审批被拒绝，流程已安全终止，未产生写入副作用。"
    if status == "failed":
        errors = state.get("error_history", [])
        return errors[-1].get("message", "流程执行失败。") if errors else "流程执行失败。"
    return "事故流程已创建。"


def state_to_response(state: dict, events: list[dict] | None = None) -> RunResponse:
    return RunResponse(
        run_id=state["run_id"],
        workflow_status=state.get("workflow_status", "created"),
        selected_skill=state.get("selected_skill"),
        collected_fields=state.get("collected_fields", {}),
        missing_fields=state.get("missing_fields", []),
        evidence=state.get("evidence", []),
        planned_actions=state.get("planned_actions", []),
        approval=state.get("approval", "not_required"),
        action_results=state.get("action_results", []),
        final_state=state.get("final_state", {}),
        events=events or [],
        message=_message(state),
    )


def create_runs_router(workflow: IncidentWorkflow, repository) -> APIRouter:
    api = APIRouter(prefix="/api/runs", tags=["runs"])

    @api.post("", response_model=RunResponse)
    def create_run(request: IncidentRunRequest):
        run_id = f"run_{uuid4().hex[:12]}"
        fields = {"order_id": request.order_id, "vehicle_id": request.vehicle_id, "location": request.location, "description": request.description}
        state = {
            "run_id": run_id,
            "user_id": request.user_id,
            "message": request.message,
            "collected_fields": fields,
            "approval": "not_required",
            "action_results": [],
            "error_history": [],
            "workflow_status": "created",
        }
        persisted_run_id = repository.create_run(run_id, state, request.idempotency_key)
        if persisted_run_id != run_id:
            existing_state = repository.get_run(persisted_run_id)
            if existing_state is None:
                raise HTTPException(status_code=409, detail="Run initialization is in progress; retry with the same idempotency key")
            return state_to_response(existing_state, repository.list_events(persisted_run_id))
        repository.append_event(run_id, "run.created", {"user_id": request.user_id})
        state = workflow.prepare(state)
        repository.save_run(run_id, state)
        return state_to_response(state, repository.list_events(run_id))

    @api.get("/{run_id}", response_model=RunResponse)
    def get_run(run_id: str):
        state = repository.get_run(run_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return state_to_response(state, repository.list_events(run_id))

    @api.get("/{run_id}/events")
    def list_run_events(run_id: str):
        if repository.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"run_id": run_id, "events": repository.list_events(run_id)}

    @api.post("/{run_id}/provide-info", response_model=RunResponse)
    def provide_info(run_id: str, request: ProvideInfoRequest):
        state = repository.get_run(run_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if state.get("workflow_status") != "waiting_for_input":
            return state_to_response(state, repository.list_events(run_id))
        fields = dict(state.get("collected_fields", {}))
        fields.update({key: value for key, value in request.model_dump().items() if value is not None})
        state["collected_fields"] = fields
        state["missing_fields"] = []
        state["error_history"] = []
        state["workflow_status"] = "created"
        repository.append_event(run_id, "input.received", {"fields": list(request.model_dump(exclude_none=True))})
        state = workflow.prepare(state)
        repository.save_run(run_id, state)
        return state_to_response(state, repository.list_events(run_id))

    @api.post("/{run_id}/resume", response_model=RunResponse)
    def resume_run(run_id: str, request: ResumeRequest):
        state = repository.get_run(run_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if state.get("workflow_status") != "awaiting_approval":
            return state_to_response(state, repository.list_events(run_id))
        state["approval"] = "approved" if request.approved else "rejected"
        if request.approved:
            repository.append_event(run_id, "run.resumed", {"approval": "approved"})
            state = workflow.execute(state)
        else:
            repository.append_event(run_id, "approval.rejected", {})
            state["workflow_status"] = "safe_terminated"
            repository.append_event(run_id, "run.safe_terminated", {})
        repository.save_run(run_id, state)
        return state_to_response(state, repository.list_events(run_id))

    return api
