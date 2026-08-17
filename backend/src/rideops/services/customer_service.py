from rideops.domain.models import CustomerServiceQueryRequest, CustomerServiceResponse
from rideops.rag import RAGService
from rideops.services.business_tools import BusinessTools
from rideops.skills import SkillRouter


class CustomerService:
    """Deterministic read-only customer service flow before external LLM integration."""

    ROUTE_TERMS = ("怎么去", "怎么走", "路线", "导航", "骑行", "多久", "时间")
    FARE_TERMS = ("费用", "多少钱", "价格", "收费", "贵不贵")
    VEHICLE_TERMS = ("附近", "可用车辆", "有没有车", "找车", "车辆")
    POLICY_TERMS = ("政策", "规定", "停车", "禁停", "电子围栏", "还车", "能不能")

    def __init__(self, router: SkillRouter, rag_service: RAGService, business_tools: BusinessTools) -> None:
        self.router = router
        self.rag_service = rag_service
        self.business_tools = business_tools

    def query(self, request: CustomerServiceQueryRequest) -> CustomerServiceResponse:
        route = self.router.route(request.message)
        message = request.message
        route_requested = any(term in message for term in self.ROUTE_TERMS)
        fare_requested = any(term in message for term in self.FARE_TERMS)
        vehicle_requested = any(term in message for term in self.VEHICLE_TERMS)
        policy_requested = any(term in message for term in self.POLICY_TERMS)
        missing_fields: list[str] = []
        evidence: list[dict] = []
        nearby_vehicles: list[dict] = []
        estimate: dict | None = None

        if route_requested or fare_requested:
            if not request.origin:
                missing_fields.append("origin")
            if not request.destination:
                missing_fields.append("destination")
            if not missing_fields:
                estimate = self.business_tools.estimate_trip(request.origin, request.destination)

        if vehicle_requested:
            location = request.location or request.origin
            if not location:
                missing_fields.append("location")
            else:
                nearby_vehicles = [vehicle.model_dump(mode="json") for vehicle in self.business_tools.get_nearby_vehicles(location, request.vehicle_type)]

        if policy_requested:
            policy = self.rag_service.query(message)
            evidence = [item.model_dump(mode="json") for item in policy.evidence]

        requested = route_requested or fare_requested or vehicle_requested or policy_requested
        if not requested:
            return CustomerServiceResponse(
                scenario="unsupported",
                selected_skill=route.skill.name if route.skill else None,
                matched_terms=route.matched_terms,
                message="当前客服查询支持路线、费用、附近车辆和当地出行政策。请补充你想查询的具体内容。",
            )

        parts: list[str] = []
        if estimate:
            parts.append(f"路线约 {estimate['distance_km']} 公里，预计 {estimate['estimated_minutes']} 分钟，费用约 {estimate['estimated_fee']} 元。")
            parts.append(f"路线来源：{estimate.get('source', 'unknown')}；费用来源：{estimate.get('pricing_source', 'unknown')}。")
        if vehicle_requested:
            parts.append(f"{request.location or request.origin} 当前找到 {len(nearby_vehicles)} 辆可用车辆。")
        if policy_requested:
            parts.append(f"已检索到 {len(evidence)} 条政策证据，请结合来源和适用条件查看。" if evidence else "当前知识库没有足够的政策证据，不能给出确定结论。")
        if missing_fields:
            labels = {"origin": "出发地", "destination": "目的地", "location": "当前位置"}
            parts.append("请补充：" + "、".join(labels[field] for field in dict.fromkeys(missing_fields)))

        answerable = bool(estimate or nearby_vehicles or evidence)
        if missing_fields and not (nearby_vehicles or evidence):
            answerable = False
        scenario = "mixed" if sum(bool(value) for value in (route_requested, fare_requested, vehicle_requested, policy_requested)) > 1 else next((name for name, enabled in (("route", route_requested), ("fare", fare_requested), ("nearby_vehicles", vehicle_requested), ("policy", policy_requested)) if enabled), "unknown")
        return CustomerServiceResponse(
            scenario=scenario,
            selected_skill=route.skill.name if route.skill else None,
            matched_terms=route.matched_terms,
            answerable=answerable,
            missing_fields=list(dict.fromkeys(missing_fields)),
            message="".join(parts),
            evidence=evidence,
            nearby_vehicles=nearby_vehicles,
            estimate=estimate,
        )
