import re

from rideops.agents.customer_service import CustomerServiceSupervisor
from rideops.domain.models import CustomerServiceQueryRequest, CustomerServiceResponse
from rideops.rag import RAGService
from rideops.repositories import BusinessToolError, SQLiteBusinessRepository
from rideops.services.business_tools import BusinessTools
from rideops.services.long_rental import LongRentalService
from rideops.skills import SkillRouter


class CustomerService:
    """Compatibility facade for the deterministic multi-agent customer-service supervisor."""

    CONTEXT_FIELDS = ("origin", "destination", "location", "city", "vehicle_type", "duration_days", "daily_budget", "order_id", "vehicle_id", "description")

    def __init__(self, router: SkillRouter, rag_service: RAGService, business_tools: BusinessTools, long_rental_service: LongRentalService, repository: SQLiteBusinessRepository) -> None:
        self.supervisor = CustomerServiceSupervisor(router, rag_service, business_tools, long_rental_service)
        self.repository = repository

    def query(self, request: CustomerServiceQueryRequest) -> CustomerServiceResponse:
        if not request.session_id:
            return self.supervisor.query(request)
        session = self.repository.get_customer_session(request.session_id)
        if session is None:
            raise BusinessToolError("NOT_FOUND", f"客服会话不存在: {request.session_id}")
        if session["user_id"] != request.user_id:
            raise BusinessToolError("FORBIDDEN", "无权访问其他用户的客服会话")
        context = dict(session["context"])
        context.update(self._extract_context(request.message))
        for field in self.CONTEXT_FIELDS:
            value = getattr(request, field)
            if value is not None:
                context[field] = value
        merged_request = CustomerServiceQueryRequest(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message,
            **{field: context.get(field) for field in self.CONTEXT_FIELDS},
        )
        response = self.supervisor.query(merged_request, active_scenario=session["active_scenario"])
        response.session_id = request.session_id
        active_scenario = self._active_scenario(response.scenario, session["active_scenario"])
        self.repository.update_customer_session(request.session_id, context, active_scenario)
        self.repository.append_customer_message(request.session_id, "user", request.message)
        self.repository.append_customer_message(request.session_id, "assistant", response.message, response.model_dump(mode="json"))
        return response

    def create_session(self, user_id: str) -> dict:
        return self.repository.create_customer_session(user_id)

    def get_session(self, session_id: str, user_id: str) -> dict:
        session = self.repository.get_customer_session(session_id)
        if session is None:
            raise BusinessToolError("NOT_FOUND", f"客服会话不存在: {session_id}")
        if session["user_id"] != user_id:
            raise BusinessToolError("FORBIDDEN", "无权访问其他用户的客服会话")
        return {
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "active_scenario": session["active_scenario"],
            "created_at": session["created_at"],
            "context": session["context"],
            "messages": self.repository.list_customer_messages(session_id),
        }

    @staticmethod
    def _active_scenario(scenario: str, previous: str | None) -> str | None:
        if scenario in {"route", "fare", "nearby_vehicles", "mixed"}:
            return "pretrip"
        if scenario in {"long_rental", "incident"}:
            return scenario
        return previous if scenario == "unsupported" else None

    @staticmethod
    def _extract_context(message: str) -> dict:
        extracted: dict[str, str | int | float] = {}
        if "上海" in message:
            extracted["city"] = "上海"
        elif "杭州" in message:
            extracted["city"] = "杭州"
        duration = re.search(r"(\d{1,3})\s*(?:天|日)", message)
        if duration:
            extracted["duration_days"] = int(duration.group(1))
        budget = re.search(r"(?:日预算|每天|预算)\D{0,6}(\d{1,4}(?:\.\d+)?)", message)
        if budget:
            extracted["daily_budget"] = float(budget.group(1))
        order = re.search(r"\b(ord_[A-Za-z0-9_]+)\b", message)
        if order:
            extracted["order_id"] = order.group(1)
        route = re.search(r"从([^，。？?]+?)到([^，。？?]+?)(?:怎么|要|大概|多少钱|，|。|？|\?|$)", message)
        if route:
            extracted["origin"] = route.group(1).strip()
            extracted["destination"] = route.group(2).strip()
        if "静安" in message and ("事故" in message or "碰撞" in message or "受伤" in message):
            extracted["location"] = "上海市静安区"
        if any(term in message for term in ("事故", "碰撞", "受伤", "损坏")):
            extracted["description"] = message
        return extracted
