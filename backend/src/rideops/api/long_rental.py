from fastapi import APIRouter

from rideops.domain.models import LongRentalPlanRequest, LongRentalPlanResponse
from rideops.services import LongRentalService


def create_long_rental_router(service: LongRentalService) -> APIRouter:
    api = APIRouter(prefix="/api/long-rental", tags=["long-rental"])

    @api.post("/plan", response_model=LongRentalPlanResponse)
    def plan(request: LongRentalPlanRequest):
        return service.plan(request)

    return api
