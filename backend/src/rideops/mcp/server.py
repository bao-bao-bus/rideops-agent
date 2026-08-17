from typing import Any

from mcp.server.fastmcp import FastMCP

from rideops.config import settings
from rideops.integrations import build_map_provider
from rideops.rag import build_default_service
from rideops.rag.embeddings import build_embedding_provider
from rideops.repositories import SQLiteBusinessRepository
from rideops.services import BusinessTools, LongRentalService


def _model(value: Any) -> dict | None:
    return value.model_dump(mode="json") if value is not None else None


def _require_approval(approval_reference: str) -> None:
    if not approval_reference.strip():
        raise ValueError("approval_reference is required for write tools")


def build_server() -> FastMCP:
    server = FastMCP("rideops-customer-service")
    repository = SQLiteBusinessRepository(settings.database_path)
    tools = BusinessTools(repository, map_provider=build_map_provider(settings.map_provider, settings.amap_api_key))
    long_rental_service = LongRentalService(repository)
    rag_service = build_default_service(settings.policies_dir, settings.rag_index_path, build_embedding_provider(settings))

    @server.tool()
    def get_active_order(order_id: str) -> dict | None:
        """查询活动订单及当前计费状态。只读。"""
        return _model(tools.get_active_order(order_id))

    @server.tool()
    def get_vehicle_status(vehicle_id: str) -> dict | None:
        """查询车辆状态、电量和当前位置。只读。"""
        return _model(tools.get_vehicle_status(vehicle_id))

    @server.tool()
    def search_nearby_vehicles(location: str, vehicle_type: str | None = None) -> list[dict]:
        """查询指定位置的可用合成车辆。只读。"""
        return [_model(vehicle) for vehicle in tools.get_nearby_vehicles(location, vehicle_type)]

    @server.tool()
    def estimate_route_and_fare(origin: str, destination: str) -> dict:
        """查询路线时间并返回 RideOps 费用预估，标注地图和计价来源。只读。"""
        return tools.estimate_trip(origin, destination)

    @server.tool()
    def search_local_policy(query: str, top_k: int = 3) -> dict:
        """检索本地出行政策并返回可引用证据。只读。"""
        response = rag_service.query(query, top_k=top_k)
        return response.model_dump(mode="json")

    @server.tool()
    def plan_long_rental(city: str, duration_days: int, vehicle_type: str | None = None, daily_budget: float | None = None, start_date: str | None = None) -> dict:
        """查询长租库存和价格方案。只读，不会创建租赁订单。"""
        from rideops.domain.models import LongRentalPlanRequest

        return long_rental_service.plan(
            LongRentalPlanRequest(
                city=city,
                duration_days=duration_days,
                vehicle_type=vehicle_type,
                daily_budget=daily_budget,
                start_date=start_date,
            )
        ).model_dump(mode="json")

    @server.tool()
    def create_long_rental_lead(listing_id: str, user_id: str, duration_days: int, idempotency_key: str, approval_reference: str, start_date: str | None = None) -> dict:
        """创建长租跟进线索。必须提供人工确认引用和幂等键。"""
        from rideops.domain.models import LongRentalLeadRequest

        _require_approval(approval_reference)
        return long_rental_service.create_lead(
            LongRentalLeadRequest(
                listing_id=listing_id,
                user_id=user_id,
                duration_days=duration_days,
                start_date=start_date,
                idempotency_key=idempotency_key,
                approval_reference=approval_reference,
            )
        ).model_dump(mode="json")

    @server.tool()
    def reserve_vehicle(vehicle_id: str, user_id: str, idempotency_key: str, approval_reference: str) -> dict:
        """预约车辆。必须提供人工确认引用和幂等键。"""
        _require_approval(approval_reference)
        return tools.reserve_vehicle(vehicle_id, user_id, idempotency_key)

    @server.tool()
    def cancel_reservation(reservation_id: str, user_id: str, idempotency_key: str, approval_reference: str) -> dict:
        """取消本人尚未使用的预约，并回读车辆可用状态。必须提供确认引用和幂等键。"""
        _require_approval(approval_reference)
        return tools.cancel_reservation(reservation_id, user_id, idempotency_key)

    @server.tool()
    def suspend_order_billing(order_id: str, idempotency_key: str, approval_reference: str) -> dict:
        """暂停订单计费。必须提供人工确认引用和幂等键。"""
        _require_approval(approval_reference)
        return tools.suspend_order_billing(order_id, idempotency_key)

    @server.tool()
    def mark_vehicle_unavailable(vehicle_id: str, idempotency_key: str, approval_reference: str) -> dict:
        """将车辆标记为不可用。必须提供人工确认引用和幂等键。"""
        _require_approval(approval_reference)
        return tools.mark_vehicle_unavailable(vehicle_id, idempotency_key)

    @server.tool()
    def create_incident_ticket(order_id: str, user_id: str, description: str, idempotency_key: str, approval_reference: str) -> dict:
        """创建事故工单。必须提供人工确认引用和幂等键。"""
        _require_approval(approval_reference)
        return tools.create_incident_ticket(order_id, user_id, description, idempotency_key)

    return server


mcp = build_server()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
