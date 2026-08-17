from rideops.domain.models import LongRentalCandidate, LongRentalPlanRequest, LongRentalPlanResponse
from rideops.repositories import SQLiteBusinessRepository


class LongRentalService:
    """Plans synthetic long-rental options without creating a reservation."""

    def __init__(self, repository: SQLiteBusinessRepository) -> None:
        self.repository = repository

    def plan(self, request: LongRentalPlanRequest) -> LongRentalPlanResponse:
        listings = self.repository.get_rental_inventory(request.city, request.vehicle_type)
        if not listings:
            return LongRentalPlanResponse(
                city=request.city,
                duration_days=request.duration_days,
                answerable=False,
                message=f"当前没有找到 {request.city} 的可用长租库存，请更换城市或车型。",
            )

        candidates: list[LongRentalCandidate] = []
        for listing in listings:
            months, remaining_days = divmod(request.duration_days, 30)
            monthly_part = months * listing.monthly_rate
            daily_part = remaining_days * listing.daily_rate
            rental_fee = round(monthly_part + daily_part, 2)
            if months and remaining_days:
                billing_basis = "monthly_plus_daily"
            elif months:
                billing_basis = "monthly"
            else:
                billing_basis = "daily"
            daily_budget_total = request.daily_budget * request.duration_days if request.daily_budget is not None else None
            candidates.append(
                LongRentalCandidate(
                    listing_id=listing.listing_id,
                    city=listing.city,
                    vehicle_type=listing.vehicle_type,
                    model=listing.model,
                    available_units=listing.available_units,
                    duration_days=request.duration_days,
                    billing_basis=billing_basis,
                    rental_fee=rental_fee,
                    deposit=listing.deposit,
                    estimated_total=round(rental_fee + listing.deposit, 2),
                    within_budget=None if daily_budget_total is None else rental_fee <= daily_budget_total,
                    assumptions=[
                        "月租按 30 天折算",
                        "预估总额包含押金，不包含优惠和超时费用",
                        "库存和价格为合成业务数据",
                    ],
                )
            )
        candidates.sort(key=lambda item: (item.within_budget is False, item.estimated_total))
        budget_note = "，已优先展示预算内方案" if request.daily_budget is not None else ""
        return LongRentalPlanResponse(
            city=request.city,
            duration_days=request.duration_days,
            answerable=True,
            message=f"已找到 {len(candidates)} 个长租方案{budget_note}。结果仅用于方案比较，实际库存和价格需在确认时再次核验。",
            candidates=candidates,
        )
