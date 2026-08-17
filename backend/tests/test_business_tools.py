from rideops.repositories import SQLiteBusinessRepository
from rideops.services import BusinessTools


def test_business_tool_write_is_idempotent(tmp_path):
    repository = SQLiteBusinessRepository(tmp_path / "tools.db")
    tools = BusinessTools(repository)
    first = tools.create_incident_ticket("ord_demo_001", "usr_demo_001", "车锁损坏", "run-1:create-ticket")
    second = tools.create_incident_ticket("ord_demo_001", "usr_demo_001", "车锁损坏", "run-1:create-ticket")
    assert first == second
    assert len(repository.snapshot()["tickets"]) == 1


def test_business_tool_rejects_missing_idempotency_key(tmp_path):
    tools = BusinessTools(SQLiteBusinessRepository(tmp_path / "tools.db"))
    try:
        tools.suspend_order_billing("ord_demo_001", "")
    except ValueError as error:
        assert "idempotency_key" in str(error)
    else:
        raise AssertionError("missing idempotency key should fail")


def test_sqlite_state_survives_repository_recreation(tmp_path):
    database_path = tmp_path / "persistent.db"
    first = SQLiteBusinessRepository(database_path)
    BusinessTools(first).suspend_order_billing("ord_demo_001", "run-2:suspend")
    second = SQLiteBusinessRepository(database_path)
    assert second.get_order("ord_demo_001").billing_status == "suspended"
