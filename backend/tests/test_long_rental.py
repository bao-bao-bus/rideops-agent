def test_long_rental_plan_returns_inventory_and_price_breakdown(client):
    response = client.post(
        "/api/long-rental/plan",
        json={"city": "上海", "duration_days": 45, "vehicle_type": "电单车", "daily_budget": 40},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is True
    assert body["candidates"][0]["billing_basis"] == "monthly_plus_daily"
    assert body["candidates"][0]["rental_fee"] == 1284.0
    assert body["candidates"][0]["within_budget"] is True


def test_long_rental_plan_reports_empty_city_inventory(client):
    response = client.post("/api/long-rental/plan", json={"city": "成都", "duration_days": 30})
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is False
    assert body["candidates"] == []
    assert "没有找到" in body["message"]


def test_long_rental_lead_requires_confirmation_and_is_idempotent(client):
    payload = {
        "listing_id": "rent_sh_e1",
        "duration_days": 45,
        "start_date": "2026-09-01",
        "idempotency_key": "lead-001",
        "approval_reference": "user-confirmed-001",
    }
    first = client.post("/api/long-rental/leads", json=payload)
    second = client.post("/api/long-rental/leads", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "pending_follow_up"


def test_long_rental_lead_rejects_unknown_listing(client):
    response = client.post(
        "/api/long-rental/leads",
        json={
            "listing_id": "missing-listing",
            "duration_days": 45,
            "idempotency_key": "lead-002",
            "approval_reference": "user-confirmed-002",
        },
    )
    assert response.status_code == 404


def test_long_rental_lead_rejects_blank_confirmation(client):
    response = client.post(
        "/api/long-rental/leads",
        json={
            "listing_id": "rent_sh_e1",
            "duration_days": 45,
            "idempotency_key": "lead-003",
            "approval_reference": "   ",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
