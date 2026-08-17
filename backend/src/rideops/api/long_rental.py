from fastapi import APIRouter, HTTPException

from rideops.domain.models import LongRentalLead, LongRentalLeadRequest, LongRentalPlanRequest, LongRentalPlanResponse
from rideops.repositories import BusinessToolError
from rideops.services import LongRentalService


def create_long_rental_router(service: LongRentalService) -> APIRouter:
    api = APIRouter(prefix="/api/long-rental", tags=["long-rental"])

    @api.post("/plan", response_model=LongRentalPlanResponse)
    def plan(request: LongRentalPlanRequest):
        return service.plan(request)

    @api.post("/leads", response_model=LongRentalLead)
    def create_lead(request: LongRentalLeadRequest):
        try:
            return service.create_lead(request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": str(exc)}) from exc
        except BusinessToolError as exc:
            status_code = 404 if exc.code == "NOT_FOUND" else 409 if exc.code == "CONFLICT" else 422
            raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message}) from exc

    return api
