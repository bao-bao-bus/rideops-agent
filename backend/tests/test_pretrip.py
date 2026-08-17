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
