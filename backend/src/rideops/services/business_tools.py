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
