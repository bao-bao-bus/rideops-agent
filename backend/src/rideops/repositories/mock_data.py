from datetime import datetime, timezone

from rideops.domain.models import IncidentTicket, InventoryItem, Order, Vehicle


class MockBusinessRepository:
    """Deterministic synthetic business data for local development and demos."""

    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.orders = {
            "ord_demo_001": Order(order_id="ord_demo_001", user_id="usr_demo_001", vehicle_id="veh_demo_001", status="active", started_at=now, pickup_location="上海市静安区")
        }
        self.vehicles = {
            "veh_demo_001": Vehicle(vehicle_id="veh_demo_001", plate_number="沪A·MOCK01", model="RideOps E-bike", status="in_use", battery_percent=72, current_location="上海市静安区")
        }
        self.inventory = [InventoryItem(item_id="inv_lock_001", item_name="智能锁组件", quantity=18, warehouse="上海一号仓")]
        self.tickets = {
            "ticket_demo_001": IncidentTicket(ticket_id="ticket_demo_001", order_id="ord_demo_001", user_id="usr_demo_001", category="vehicle_damage", description="车辆外观疑似损坏", status="open", created_at=now)
        }

    def snapshot(self) -> dict[str, list | dict]:
        return {"orders": list(self.orders.values()), "vehicles": list(self.vehicles.values()), "inventory": self.inventory, "tickets": list(self.tickets.values())}
