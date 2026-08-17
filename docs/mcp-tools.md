# RideOps MCP 工具

RideOps 自有 MCP Server 位于 `backend/src/rideops/mcp/server.py`，复用现有 Service 和 Repository，不允许工具直接执行 SQL。

## 启动

```bash
cd backend
pip install -e ".[test]"
rideops-mcp
```

默认使用 stdio 传输，适合接入支持 MCP 的本地客户端。外部路线能力仍通过配置的高德官方 MCP Provider 获取；RideOps 自有 MCP 只负责统一暴露业务语义。

## 工具边界

只读工具：

- `get_active_order`
- `get_vehicle_status`
- `search_nearby_vehicles`
- `estimate_route_and_fare`
- `search_local_policy`

写工具：

- `reserve_vehicle`
- `suspend_order_billing`
- `mark_vehicle_unavailable`
- `create_incident_ticket`

每个写工具都要求：

```json
{
  "idempotency_key": "run-001:reserve",
  "approval_reference": "operator-approved-001"
}
```

`idempotency_key` 防止重复写入，`approval_reference` 防止模型或客户端绕过人工确认直接执行状态变更。真正的审批状态仍由上层 LangGraph/业务流程负责，本 MCP Server 不把模型输出当作审批凭证。
