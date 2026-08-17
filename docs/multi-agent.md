# RideOps 客服多 Agent 设计

当前多 Agent 不是让多个模型自由讨论，而是一个可测试、可审计的客服 Supervisor 加四个职责明确的专职 Agent。外部模型 API 尚未接入；因此分派规则目前是确定性的，后续替换为模型路由时不会改变工具和写入边界。

## 分工

| 组件 | 负责 | 可调用能力 | 禁止事项 |
| --- | --- | --- | --- |
| Customer Service Supervisor | 识别可并行的客服意图、分派、汇总 | 专职 Agent | 直接写业务数据库 |
| PreTrip Agent | 路线、费用、附近车辆 | 高德 MCP、RideOps 计价、SQLite 车辆查询 | 预约或修改车辆状态 |
| Policy Agent | 当地政策问答 | RAG 检索与证据 | 编造知识库外结论 |
| LongRental Agent | 长租库存、价格、预算 | LongRentalService | 创建租赁订单或支付 |
| Incident Triage Agent | 事故信息分诊与交接 | 生成 `/api/runs` 建议载荷 | 执行事故写工具 |
| IncidentWorkflow | 事故处理写入闭环 | 既有 LangGraph、Service、Repository | 绕过人工审批 |

## 分派与安全边界

```text
用户问题
  → Customer Service Supervisor
  → 一个或多个只读专职 Agent
  → 汇总 evidence / estimate / missing_fields / delegated_agents

事故问题
  → Incident Triage Agent
  → 返回 POST /api/runs 的 next_action（不写入）
  → 既有 IncidentWorkflow
  → 人工审批
  → 现有 Service / Repository 幂等写入与状态回读
```

同一个“路线 + 附近车辆 + 停车规则”问题会同时委派给出行前 Agent 和政策 Agent；响应中的 `delegated_agents` 可作为审计和前端展示依据。

## API 变化

`POST /api/customer-service/query` 在保留原有字段的基础上新增可选输入：

- `duration_days`、`daily_budget`：用于长租 Agent
- `order_id`、`vehicle_id`、`description`：用于事故分诊 Agent

新增响应字段：

- `delegated_agents`
- `long_rental_plan`
- `next_action`

`next_action` 只是安全的下一步建议，不代表操作已执行；所有写入仍通过对应的确认、审批和幂等机制进行。
