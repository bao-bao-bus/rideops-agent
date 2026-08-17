from pydantic import BaseModel, ConfigDict, Field

from rideops.domain.models import IncidentTicket, Order, Vehicle
from rideops.repositories import SQLiteBusinessRepository


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrderLookupInput(ToolInput):
    order_id: str = Field(min_length=1)


class VehicleLookupInput(ToolInput):
    vehicle_id: str = Field(min_length=1)


class WriteInput(ToolInput):
    idempotency_key: str = Field(min_length=1)


class BusinessTools:
    """Ordinary in-process tools. FastMCP can wrap these contracts later."""

    def __init__(self, repository: SQLiteBusinessRepository) -> None:
        self.repository = repository

    def get_active_order(self, order_id: str) -> Order | None:
        OrderLookupInput(order_id=order_id)
        return self.repository.get_active_order(order_id)

    def get_order(self, order_id: str) -> Order | None:
        OrderLookupInput(order_id=order_id)
        return self.repository.get_order(order_id)

    def get_vehicle_status(self, vehicle_id: str) -> Vehicle | None:
        VehicleLookupInput(vehicle_id=vehicle_id)
        return self.repository.get_vehicle(vehicle_id)

    def get_incident_ticket(self, ticket_id: str) -> IncidentTicket | None:
        if not ticket_id:
            raise ValueError("ticket_id cannot be empty")
        return self.repository.get_ticket(ticket_id)

    def get_nearby_vehicles(self, location: str, vehicle_type: str | None = None) -> list[Vehicle]:
        if not location:
            raise ValueError("location cannot be empty")
        return self.repository.get_available_vehicles(location, vehicle_type)

    def estimate_trip(self, origin: str, destination: str) -> dict:
        if not origin or not destination:
            raise ValueError("origin and destination are required")
        # Synthetic estimate; no map or payment provider is called in the MVP.
        return {"distance_km": 4.2, "estimated_minutes": 18, "estimated_fee": 8.5, "currency": "CNY", "source": "synthetic_estimator"}

    def reserve_vehicle(self, vehicle_id: str, user_id: str, idempotency_key: str) -> dict:
        VehicleLookupInput(vehicle_id=vehicle_id)
        WriteInput(idempotency_key=idempotency_key)
        return self.repository.reserve_vehicle(vehicle_id, user_id, idempotency_key)

    def suspend_order_billing(self, order_id: str, idempotency_key: str) -> dict:
        OrderLookupInput(order_id=order_id)
        WriteInput(idempotency_key=idempotency_key)
        return self.repository.suspend_order_billing(order_id, idempotency_key)

    def mark_vehicle_unavailable(self, vehicle_id: str, idempotency_key: str) -> dict:
        VehicleLookupInput(vehicle_id=vehicle_id)
        WriteInput(idempotency_key=idempotency_key)
        return self.repository.mark_vehicle_unavailable(vehicle_id, idempotency_key)

    def create_incident_ticket(self, order_id: str, user_id: str, description: str, idempotency_key: str) -> dict:
        OrderLookupInput(order_id=order_id)
        WriteInput(idempotency_key=idempotency_key)
        if not description:
            raise ValueError("description cannot be empty")
        return self.repository.create_incident_ticket(order_id, user_id, description, idempotency_key)
