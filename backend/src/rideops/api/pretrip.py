from fastapi import APIRouter, HTTPException

from rideops.domain.models import PreTripPlanResponse, PreTripRequest, PreTripReservationCancellationRequest, PreTripReservationRequest
from rideops.repositories import BusinessToolError
from rideops.services import BusinessTools


def create_pretrip_router(tools: BusinessTools) -> APIRouter:
    api = APIRouter(prefix="/api/pretrip", tags=["pretrip"])

    @api.post("/plan", response_model=PreTripPlanResponse)
    def plan(request: PreTripRequest):
        vehicles = tools.get_nearby_vehicles(request.origin, request.vehicle_type)
        estimate = tools.estimate_trip(request.origin, request.destination)
        return PreTripPlanResponse(origin=request.origin, destination=request.destination, nearby_vehicles=[vehicle.model_dump(mode="json") for vehicle in vehicles], estimate=estimate)

    @api.post("/reserve", response_model=dict)
    def reserve(request: PreTripReservationRequest):
        try:
            return tools.reserve_vehicle(request.vehicle_id, request.user_id, request.idempotency_key)
        except BusinessToolError as exc:
            status_code = 404 if exc.code == "NOT_FOUND" else 409 if exc.code == "CONFLICT" else 422
            raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message}) from exc

    @api.post("/reservations/{reservation_id}/cancel", response_model=dict)
    def cancel_reservation(reservation_id: str, request: PreTripReservationCancellationRequest):
        if not request.approval_reference.strip():
            raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "approval_reference is required"})
        try:
            return tools.cancel_reservation(reservation_id, request.user_id, request.idempotency_key)
        except BusinessToolError as exc:
            status_code = 404 if exc.code == "NOT_FOUND" else 403 if exc.code == "FORBIDDEN" else 409 if exc.code == "CONFLICT" else 422
            raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message}) from exc

    return api
