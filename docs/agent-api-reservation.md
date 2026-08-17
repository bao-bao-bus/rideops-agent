# Agent 模型 API 与客服会话预留

当前项目已预留 OpenAI-compatible Agent 模型适配层，但默认关闭，不会因为环境中存在 Key 而自动调用外部模型。

## 当前可用的会话 API

- POST /api/customer-service/sessions：创建一条 SQLite 持久化客服会话。
- GET /api/customer-service/sessions/{session_id}：按用户归属读取已保存的上下文和对话记录，用于页面刷新恢复。
- POST /api/customer-service/query：传入 session_id 后，服务端会合并前文已确认的行程信息，并在没有新意图关键词时延续当前场景。
- GET /api/agent-model/status：查看模型适配器是否仅预留、已配置或未来可启用；响应不包含 Key。

例如，用户先问“我想在上海长租电单车”，系统会追问租期；同一会话的下一句“45 天，日预算 40 元”会由长租 Agent 继续处理。

## 未来配置方式

需要实际接入模型时，在本地 .env 中配置以下变量：

- RIDEOPS_AGENT_MODEL_PROVIDER=openai_compatible
- AGENT_MODEL_BASE_URL=兼容服务的基础地址
- AGENT_MODEL_API_KEY=本地保存的密钥
- AGENT_MODEL=模型名称

本轮不会启用这些变量，也不会提交密钥。即使后续启用，模型只能用于意图识别、字段抽取、查询改写和回复润色；它不能创建幂等键、决定审批、修改数据库或宣称写入成功。

## 写操作保护

前端为一次事故启动、预约、取消预约和长租意向确认固定生成并复用同一个幂等键，同时在提交中禁用对应按钮。后端仍以 Repository 的幂等记录、预约归属和事故审批流程作为最终保护。
