def run_request():
    return {
        "user_id": "usr_demo_001",
        "message": "车辆发生碰撞，订单仍在计费，需要处理事故",
        "order_id": "ord_demo_001",
        "vehicle_id": "veh_demo_001",
        "location": "上海市静安区",
        "description": "车辆碰撞，用户手臂有轻微擦伤，车锁损坏",
    }


def test_incident_run_waits_for_approval_without_writing(client):
    response = client.post("/api/runs", json=run_request())
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_status"] == "awaiting_approval"
    assert body["approval"] == "pending"
    assert len(body["evidence"]) > 0
    assert len(body["planned_actions"]) == 3
    assert body["planned_actions"][0]["reason"]
    assert body["planned_actions"][0]["risk"]
    assert body["action_results"] == []
    assert body["final_state"]["order"]["billing_status"] == "active"


def test_missing_fields_are_returned_as_follow_up_request(client):
    response = client.post("/api/runs", json={"message": "车辆发生事故了"})
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_status"] == "waiting_for_input"
    assert set(body["missing_fields"]) == {"order_id", "location", "description"}
    assert body["planned_actions"] == []


def test_providing_missing_information_continues_to_approval(client):
    created = client.post("/api/runs", json={"message": "车辆发生事故了"}).json()
    continued = client.post(f"/api/runs/{created['run_id']}/provide-info", json={"order_id": "ord_demo_001", "location": "上海市静安区", "description": "车辆碰撞并且车锁损坏"})
    assert continued.status_code == 200
    body = continued.json()
    assert body["workflow_status"] == "awaiting_approval"
    assert body["missing_fields"] == []


def test_run_events_record_decisions_and_tool_trace(client):
    created = client.post("/api/runs", json=run_request()).json()
    run_id = created["run_id"]
    pending_events = [event["event_type"] for event in created["events"]]
    assert pending_events[:4] == ["run.created", "skill.selected", "evidence.retrieved", "business.state.queried"]
    assert "approval.required" in pending_events
    completed = client.post(f"/api/runs/{run_id}/resume", json={"approved": True}).json()
    event_types = [event["event_type"] for event in completed["events"]]
    assert "run.resumed" in event_types
    assert event_types.count("tool.started") == 3
    assert event_types.count("tool.completed") == 3
    assert event_types[-1] == "run.completed"
    fetched = client.get(f"/api/runs/{run_id}/events")
    assert fetched.status_code == 200
    assert len(fetched.json()["events"]) == len(completed["events"])


def test_incident_run_creation_is_idempotent_when_client_provides_key(client):
    payload = run_request() | {"idempotency_key": "incident-create-001"}
    first = client.post("/api/runs", json=payload)
    second = client.post("/api/runs", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]
    assert [event["event_type"] for event in second.json()["events"]].count("run.created") == 1


def test_approval_executes_writes_and_reads_back_sqlite_state(client):
    created = client.post("/api/runs", json=run_request()).json()
    run_id = created["run_id"]
    completed = client.post(f"/api/runs/{run_id}/resume", json={"approved": True})
    assert completed.status_code == 200
    body = completed.json()
    assert body["workflow_status"] == "completed"
    assert all(item["status"] == "completed" for item in body["action_results"])
    assert body["final_state"]["order"]["billing_status"] == "suspended"
    assert body["final_state"]["vehicle"]["status"] == "unavailable"
    assert body["final_state"]["ticket"]["status"] == "open"


def test_rejected_approval_does_not_write(client):
    created = client.post("/api/runs", json=run_request()).json()
    rejected = client.post(f"/api/runs/{created['run_id']}/resume", json={"approved": False})
    assert rejected.status_code == 200
    body = rejected.json()
    assert body["workflow_status"] == "safe_terminated"
    assert body["action_results"] == []


def test_repeated_resume_is_idempotent(client):
    created = client.post("/api/runs", json=run_request()).json()
    first = client.post(f"/api/runs/{created['run_id']}/resume", json={"approved": True}).json()
    second = client.post(f"/api/runs/{created['run_id']}/resume", json={"approved": True}).json()
    assert second["workflow_status"] == "completed"
    assert second["final_state"] == first["final_state"]
    assert len(second["action_results"]) == 3
