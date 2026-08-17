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
    assert body["delegated_agents"] == ["pretrip-agent"]


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
    assert body["delegated_agents"] == ["policy-agent"]


def test_customer_service_returns_nearby_vehicles(client):
    response = client.post("/api/customer-service/query", json={"message": "附近有没有可用车辆？", "location": "上海市静安区"})
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "nearby_vehicles"
    assert body["answerable"] is True
    assert body["nearby_vehicles"][0]["vehicle_id"] == "veh_demo_002"


def test_supervisor_can_delegate_one_query_to_pretrip_and_policy_agents(client):
    response = client.post(
        "/api/customer-service/query",
        json={
            "message": "从静安区到人民广场怎么走，附近有车吗，停车有什么规定？",
            "origin": "上海市静安区",
            "destination": "上海市人民广场",
            "location": "上海市静安区",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "mixed"
    assert body["delegated_agents"] == ["pretrip-agent", "policy-agent"]
    assert body["estimate"]
    assert body["evidence"]


def test_supervisor_delegates_long_rental_planning_to_specialist(client):
    response = client.post(
        "/api/customer-service/query",
        json={"message": "我想在上海长租电单车", "city": "上海", "duration_days": 45, "daily_budget": 40},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "long_rental"
    assert body["delegated_agents"] == ["long-rental-agent"]
    assert body["long_rental_plan"]["candidates"]


def test_supervisor_hands_incident_to_existing_approval_workflow_without_writing(client):
    response = client.post(
        "/api/customer-service/query",
        json={"message": "车辆发生碰撞，订单还在扣费", "order_id": "ord_demo_001", "location": "上海市静安区"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "incident"
    assert body["delegated_agents"] == ["incident-triage-agent"]
    assert body["next_action"]["endpoint"] == "/api/runs"
    snapshot = client.get("/api/demo-data").json()
    assert snapshot["orders"][0]["billing_status"] == "active"


def test_customer_session_continues_long_rental_follow_up_with_extracted_context(client):
    session = client.post("/api/customer-service/sessions", json={"user_id": "usr_demo_001"})
    assert session.status_code == 200
    session_id = session.json()["session_id"]
    first = client.post(
        "/api/customer-service/query",
        json={"session_id": session_id, "message": "我想在上海长租电单车"},
    )
    assert first.status_code == 200
    assert first.json()["missing_fields"] == ["duration_days"]
    second = client.post(
        "/api/customer-service/query",
        json={"session_id": session_id, "message": "45天，日预算40元"},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["session_id"] == session_id
    assert body["scenario"] == "long_rental"
    assert body["long_rental_plan"]["candidates"]


def test_customer_session_checks_user_ownership(client):
    session = client.post("/api/customer-service/sessions", json={"user_id": "usr_demo_001"}).json()
    response = client.post(
        "/api/customer-service/query",
        json={"session_id": session["session_id"], "user_id": "usr_other", "message": "附近有车吗？"},
    )
    assert response.status_code == 403
