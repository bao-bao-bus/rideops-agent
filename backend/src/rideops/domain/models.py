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


class RentalInventory(DomainModel):
    listing_id: str
    city: str
    vehicle_type: str
    model: str
    available_units: int = Field(ge=0)
    daily_rate: float = Field(ge=0)
    monthly_rate: float = Field(ge=0)
    deposit: float = Field(ge=0)
    min_days: int = Field(ge=1)


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


class ProvideInfoRequest(DomainModel):
    order_id: str | None = None
    vehicle_id: str | None = None
    location: str | None = None
    description: str | None = None


class PreTripRequest(DomainModel):
    user_id: str = "usr_demo_001"
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    vehicle_type: str | None = None


class PreTripReservationRequest(DomainModel):
    user_id: str = "usr_demo_001"
    vehicle_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class PreTripPlanResponse(DomainModel):
    origin: str
    destination: str
    nearby_vehicles: list[dict] = Field(default_factory=list)
    estimate: dict
    reservation: dict | None = None


class LongRentalPlanRequest(DomainModel):
    user_id: str = "usr_demo_001"
    city: str = Field(min_length=1)
    duration_days: int = Field(ge=1, le=365)
    start_date: str | None = None
    vehicle_type: str | None = None
    daily_budget: float | None = Field(default=None, ge=0)


class LongRentalCandidate(DomainModel):
    listing_id: str
    city: str
    vehicle_type: str
    model: str
    available_units: int
    duration_days: int
    billing_basis: str
    rental_fee: float
    deposit: float
    estimated_total: float
    within_budget: bool | None = None
    assumptions: list[str] = Field(default_factory=list)


class LongRentalPlanResponse(DomainModel):
    city: str
    duration_days: int
    answerable: bool
    message: str
    candidates: list[LongRentalCandidate] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class CustomerServiceQueryRequest(DomainModel):
    user_id: str = "usr_demo_001"
    message: str = Field(min_length=1)
    origin: str | None = None
    destination: str | None = None
    location: str | None = None
    city: str | None = None
    vehicle_type: str | None = None


class CustomerServiceResponse(DomainModel):
    scenario: str
    selected_skill: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    answerable: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    message: str
    evidence: list[dict] = Field(default_factory=list)
    nearby_vehicles: list[dict] = Field(default_factory=list)
    estimate: dict | None = None


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
    events: list[dict] = Field(default_factory=list)
    message: str
