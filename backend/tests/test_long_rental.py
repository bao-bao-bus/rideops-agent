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
