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
    billing_status: str = "active"


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


class IncidentRunRequest(DomainModel):
    user_id: str = "usr_demo_001"
    message: str = Field(min_length=1)
    order_id: str | None = None
    vehicle_id: str | None = None
    location: str | None = None
    description: str | None = None


class ResumeRequest(DomainModel):
    approved: bool


class RunResponse(DomainModel):
    run_id: str
    workflow_status: str
    selected_skill: str | None = None
    collected_fields: dict[str, str | None] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    planned_actions: list[dict] = Field(default_factory=list)
    approval: str = "not_required"
    action_results: list[dict] = Field(default_factory=list)
    final_state: dict = Field(default_factory=dict)
    message: str
