def test_pretrip_plan_returns_available_vehicle_and_synthetic_estimate(client):
    response = client.post("/api/pretrip/plan", json={"origin": "上海市静安区", "destination": "上海市人民广场"})
    assert response.status_code == 200
    body = response.json()
    assert body["nearby_vehicles"][0]["vehicle_id"] == "veh_demo_002"
    assert body["estimate"]["source"] == "synthetic_estimator"


def test_synthetic_map_provider_is_used_when_amap_key_is_missing(client):
    response = client.post("/api/pretrip/plan", json={"origin": "上海市静安区", "destination": "上海市人民广场"})
    assert response.status_code == 200
    assert response.json()["estimate"]["pricing_source"] == "synthetic_pricing"


def test_map_provider_failure_falls_back_to_synthetic_estimate():
    from rideops.integrations.maps import MapProviderError
    from rideops.repositories import SQLiteBusinessRepository
    from rideops.services import BusinessTools

    class FailingProvider:
        def estimate_trip(self, origin, destination):
            raise MapProviderError("upstream unavailable")

    tools = BusinessTools(SQLiteBusinessRepository(":memory:"), map_provider=FailingProvider())
    estimate = tools.estimate_trip("起点", "终点")
    assert estimate["source"] == "synthetic_fallback"
    assert estimate["fallback_reason"] == "upstream unavailable"


def test_pretrip_reservation_is_idempotent(client):
    payload = {"vehicle_id": "veh_demo_002", "idempotency_key": "pretrip-001:reserve"}
    first = client.post("/api/pretrip/reserve", json=payload)
    second = client.post("/api/pretrip/reserve", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_pretrip_reservation_conflict_is_explicit(client):
    first = client.post("/api/pretrip/reserve", json={"vehicle_id": "veh_demo_002", "idempotency_key": "pretrip-002:reserve"})
    second = client.post("/api/pretrip/reserve", json={"vehicle_id": "veh_demo_002", "idempotency_key": "pretrip-003:reserve"})
    assert first.status_code == 200
    assert second.status_code == 409


def test_pretrip_reservation_can_be_cancelled_idempotently_and_releases_vehicle(client):
    reservation = client.post("/api/pretrip/reserve", json={"vehicle_id": "veh_demo_002", "idempotency_key": "pretrip-004:reserve"}).json()
    payload = {
        "idempotency_key": "pretrip-004:cancel",
        "approval_reference": "user-confirmed-cancel-004",
    }
    first = client.post(f"/api/pretrip/reservations/{reservation['reservation_id']}/cancel", json=payload)
    second = client.post(f"/api/pretrip/reservations/{reservation['reservation_id']}/cancel", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "cancelled"
    assert first.json()["vehicle_status"] == "available"
    snapshot = client.get("/api/demo-data").json()
    assert snapshot["reservations"][0]["status"] == "cancelled"
    assert next(vehicle for vehicle in snapshot["vehicles"] if vehicle["vehicle_id"] == "veh_demo_002")["status"] == "available"


def test_pretrip_reservation_cancellation_checks_owner_and_key_scope(client):
    reservation = client.post("/api/pretrip/reserve", json={"vehicle_id": "veh_demo_002", "idempotency_key": "pretrip-005:reserve"}).json()
    forbidden = client.post(
        f"/api/pretrip/reservations/{reservation['reservation_id']}/cancel",
        json={"user_id": "usr_other", "idempotency_key": "pretrip-005:forbidden", "approval_reference": "user-confirmed"},
    )
    reused_key = client.post(
        f"/api/pretrip/reservations/{reservation['reservation_id']}/cancel",
        json={"idempotency_key": "pretrip-005:reserve", "approval_reference": "user-confirmed"},
    )
    assert forbidden.status_code == 403
    assert reused_key.status_code == 409
