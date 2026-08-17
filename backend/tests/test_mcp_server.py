from rideops.mcp.server import _require_approval, build_server


def test_rideops_mcp_server_exposes_customer_service_tools():
    server = build_server()
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert names == {
        "get_active_order",
        "get_vehicle_status",
        "search_nearby_vehicles",
        "estimate_route_and_fare",
        "search_local_policy",
        "plan_long_rental",
        "create_long_rental_lead",
        "reserve_vehicle",
        "cancel_reservation",
        "suspend_order_billing",
        "mark_vehicle_unavailable",
        "create_incident_ticket",
    }


def test_mcp_write_tools_require_approval_reference():
    try:
        _require_approval("")
    except ValueError as exc:
        assert "approval_reference" in str(exc)
    else:
        raise AssertionError("write tools must require approval_reference")
