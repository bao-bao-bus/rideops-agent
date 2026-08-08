from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class VehicleStatus(StrEnum):
    available = "available"
    in_use = "in_use"
    maintenance = "maintenance"
    unavailable = "unavailable"


class OrderStatus(StrEnum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class TicketStatus(StrEnum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Order(DomainModel):
    order_id: str
    user_id: str
    vehicle_id: str
    status: OrderStatus
    started_at: datetime
    pickup_location: str


class Vehicle(DomainModel):
    vehicle_id: str
    plate_number: str
    model: str
    status: VehicleStatus
    battery_percent: int = Field(ge=0, le=100)
    current_location: str


class InventoryItem(DomainModel):
    item_id: str
    item_name: str
    quantity: int = Field(ge=0)
    warehouse: str


class IncidentTicket(DomainModel):
    ticket_id: str
    order_id: str
    user_id: str
    category: str
    description: str
    status: TicketStatus
    created_at: datetime
