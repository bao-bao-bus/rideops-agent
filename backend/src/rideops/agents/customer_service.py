from dataclasses import dataclass, field

from rideops.domain.models import CustomerServiceQueryRequest, CustomerServiceResponse, LongRentalPlanRequest
from rideops.rag import RAGService
from rideops.services.business_tools import BusinessTools
from rideops.services.long_rental import LongRentalService
from rideops.skills import SkillRouter


@dataclass
class AgentResult:
    name: str
    scenario: str
    answerable: bool
    messages: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    nearby_vehicles: list[dict] = field(default_factory=list)
    estimate: dict | None = None
    long_rental_plan: dict | None = None
    next_action: dict | None = None


class PreTripAgent:
    ROUTE_TERMS = ("怎么去", "怎么走", "路线", "导航", "骑行", "多久", "时间")
    FARE_TERMS = ("费用", "多少钱", "价格", "收费", "贵不贵")
    VEHICLE_TERMS = ("附近", "可用车辆", "有没有车", "找车", "车辆")

    def __init__(self, tools: BusinessTools) -> None:
        self.tools = tools

    def handles(self, message: str) -> bool:
        return any(term in message for term in (*self.ROUTE_TERMS, *self.FARE_TERMS, *self.VEHICLE_TERMS))

    def run(self, request: CustomerServiceQueryRequest) -> AgentResult:
        route_requested = any(term in request.message for term in self.ROUTE_TERMS)
        fare_requested = any(term in request.message for term in self.FARE_TERMS)
        vehicle_requested = any(term in request.message for term in self.VEHICLE_TERMS)
        missing_fields: list[str] = []
        messages: list[str] = []
        estimate: dict | None = None
        nearby_vehicles: list[dict] = []

        if route_requested or fare_requested:
            if not request.origin:
                missing_fields.append("origin")
            if not request.destination:
                missing_fields.append("destination")
            if not missing_fields:
                estimate = self.tools.estimate_trip(request.origin, request.destination)
                messages.append(f"路线约 {estimate['distance_km']} 公里，预计 {estimate['estimated_minutes']} 分钟，费用约 {estimate['estimated_fee']} 元。")
                messages.append(f"路线来源：{estimate.get('source', 'unknown')}；费用来源：{estimate.get('pricing_source', 'unknown')}。")

        if vehicle_requested:
            location = request.location or request.origin
            if not location:
                missing_fields.append("location")
            else:
                nearby_vehicles = [vehicle.model_dump(mode="json") for vehicle in self.tools.get_nearby_vehicles(location, request.vehicle_type)]
                messages.append(f"{location} 当前找到 {len(nearby_vehicles)} 辆可用车辆。")

        if missing_fields:
            labels = {"origin": "出发地", "destination": "目的地", "location": "当前位置"}
            messages.append("请补充：" + "、".join(labels[item] for item in dict.fromkeys(missing_fields)))
        scenario = "mixed" if sum((route_requested, fare_requested, vehicle_requested)) > 1 else next(
            name
            for name, enabled in (("route", route_requested), ("fare", fare_requested), ("nearby_vehicles", vehicle_requested))
            if enabled
        )
        return AgentResult(
            name="pretrip-agent",
            scenario=scenario,
            answerable=bool(estimate or nearby_vehicles),
            messages=messages,
            missing_fields=list(dict.fromkeys(missing_fields)),
            nearby_vehicles=nearby_vehicles,
            estimate=estimate,
        )


class PolicyAgent:
    TERMS = ("政策", "规定", "停车", "禁停", "电子围栏", "还车", "能不能")

    def __init__(self, rag_service: RAGService) -> None:
        self.rag_service = rag_service

    def handles(self, message: str) -> bool:
        return any(term in message for term in self.TERMS)

    def run(self, request: CustomerServiceQueryRequest) -> AgentResult:
        response = self.rag_service.query(request.message)
        evidence = [item.model_dump(mode="json") for item in response.evidence]
        message = f"已检索到 {len(evidence)} 条政策证据，请结合来源和适用条件查看。" if evidence else "当前知识库没有足够的政策证据，不能给出确定结论。"
        return AgentResult(name="policy-agent", scenario="policy", answerable=bool(evidence), messages=[message], evidence=evidence)


class LongRentalAgent:
    TERMS = ("长租", "租期", "月租", "长期租赁", "续租", "租车计划")

    def __init__(self, service: LongRentalService) -> None:
        self.service = service

    def handles(self, message: str) -> bool:
        return any(term in message for term in self.TERMS)

    def run(self, request: CustomerServiceQueryRequest) -> AgentResult:
        missing_fields = [name for name, value in (("city", request.city), ("duration_days", request.duration_days)) if value is None]
        if missing_fields:
            labels = {"city": "城市", "duration_days": "租期天数"}
            return AgentResult(
                name="long-rental-agent",
                scenario="long_rental",
                answerable=False,
                messages=["请补充：" + "、".join(labels[field] for field in missing_fields)],
                missing_fields=missing_fields,
            )
        plan = self.service.plan(
            LongRentalPlanRequest(
                user_id=request.user_id,
                city=request.city,
                duration_days=request.duration_days,
                vehicle_type=request.vehicle_type,
                daily_budget=request.daily_budget,
            )
        )
        return AgentResult(
            name="long-rental-agent",
            scenario="long_rental",
            answerable=plan.answerable,
            messages=[plan.message],
            long_rental_plan=plan.model_dump(mode="json"),
        )


class IncidentTriageAgent:
    TERMS = ("事故", "故障", "损坏", "碰撞", "受伤", "车辆问题")

    def handles(self, message: str) -> bool:
        return any(term in message for term in self.TERMS)

    def run(self, request: CustomerServiceQueryRequest) -> AgentResult:
        description = request.description or request.message
        payload = {
            "user_id": request.user_id,
            "message": request.message,
            "order_id": request.order_id,
            "vehicle_id": request.vehicle_id,
            "location": request.location,
            "description": description,
        }
        missing_fields = [field for field in ("order_id", "location") if not payload[field]]
        if missing_fields:
            labels = {"order_id": "订单号", "location": "事故地点"}
            message = "事故分诊已完成。进入处理流程前请补充：" + "、".join(labels[field] for field in missing_fields)
        else:
            message = "事故分诊已完成。可进入事故工作流检索规则、生成待审批动作并回读执行结果。"
        return AgentResult(
            name="incident-triage-agent",
            scenario="incident",
            answerable=not missing_fields,
            messages=[message],
            missing_fields=missing_fields,
            next_action={"method": "POST", "endpoint": "/api/runs", "payload": payload},
        )


class CustomerServiceSupervisor:
    """Deterministic supervisor that delegates to bounded customer-service agents before LLM integration."""

    def __init__(self, router: SkillRouter, rag_service: RAGService, tools: BusinessTools, long_rental_service: LongRentalService) -> None:
        self.router = router
        self.pretrip_agent = PreTripAgent(tools)
        self.policy_agent = PolicyAgent(rag_service)
        self.long_rental_agent = LongRentalAgent(long_rental_service)
        self.incident_agent = IncidentTriageAgent()

    def query(self, request: CustomerServiceQueryRequest) -> CustomerServiceResponse:
        route = self.router.route(request.message)
        if self.incident_agent.handles(request.message):
            results = [self.incident_agent.run(request)]
        else:
            results = []
            for agent in (self.pretrip_agent, self.policy_agent, self.long_rental_agent):
                if agent.handles(request.message):
                    results.append(agent.run(request))
        if not results:
            return CustomerServiceResponse(
                scenario="unsupported",
                selected_skill=route.skill.name if route.skill else None,
                matched_terms=route.matched_terms,
                message="当前客服支持路线、费用、附近车辆、当地政策、长租咨询和事故报备。请补充你想查询的具体内容。",
            )

        missing_fields = list(dict.fromkeys(field for result in results for field in result.missing_fields))
        evidence = [item for result in results for item in result.evidence]
        nearby_vehicles = [item for result in results for item in result.nearby_vehicles]
        estimate = next((result.estimate for result in results if result.estimate is not None), None)
        long_rental_plan = next((result.long_rental_plan for result in results if result.long_rental_plan is not None), None)
        next_action = next((result.next_action for result in results if result.next_action is not None), None)
        scenario = results[0].scenario if len(results) == 1 else "mixed"
        return CustomerServiceResponse(
            scenario=scenario,
            selected_skill=route.skill.name if route.skill else None,
            matched_terms=route.matched_terms,
            answerable=any(result.answerable for result in results),
            missing_fields=missing_fields,
            message="".join(message for result in results for message in result.messages),
            evidence=evidence,
            nearby_vehicles=nearby_vehicles,
            estimate=estimate,
            long_rental_plan=long_rental_plan,
            next_action=next_action,
            delegated_agents=[result.name for result in results],
        )
