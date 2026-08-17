def test_customer_service_returns_route_and_fare_estimate(client):
    response = client.post(
        "/api/customer-service/query",
        json={
            "message": "从静安区到人民广场怎么走，大概要多少钱？",
            "origin": "上海市静安区",
            "destination": "上海市人民广场",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "mixed"
    assert body["answerable"] is True
    assert body["estimate"]["source"] == "synthetic_estimator"
    assert body["estimate"]["pricing_source"] == "synthetic_pricing"


def test_customer_service_asks_for_missing_route_fields(client):
    response = client.post("/api/customer-service/query", json={"message": "怎么去火车站？"})
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is False
    assert body["missing_fields"] == ["origin", "destination"]
    assert "出发地" in body["message"]


def test_customer_service_returns_policy_evidence(client):
    response = client.post("/api/customer-service/query", json={"message": "共享电单车应该在哪里停车？", "city": "上海"})
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "policy"
    assert body["answerable"] is True
    assert body["evidence"]


def test_customer_service_returns_nearby_vehicles(client):
    response = client.post("/api/customer-service/query", json={"message": "附近有没有可用车辆？", "location": "上海市静安区"})
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "nearby_vehicles"
    assert body["answerable"] is True
    assert body["nearby_vehicles"][0]["vehicle_id"] == "veh_demo_002"
