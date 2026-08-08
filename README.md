# RideOps Agent

> 面向共享出行业务的 Agent 应用原型：RAG 证据、MCP 业务工具计划、LangGraph 长任务、HITL 审批与可靠执行。

[在线体验原型](https://rideops-agent.mikelcarus6908.chatgpt.site)

## 为什么做这个项目

传统 RAG 客服通常只能回答知识问题，无法安全完成暂停计费、停用故障车辆、创建事故工单等业务动作。RideOps Agent 将事故处理建模为一个受约束的长任务：先识别意图并加载 Skill，再检索政策证据、查询业务状态、生成执行计划，最后在人类审批后执行写操作并回读验证结果。

## 当前初版

当前仓库包含可运行的 Next.js 交互原型，用合成数据演示完整事故处理链路：

- Skill 路由与渐进式加载状态
- RAG 政策证据和订单状态展示
- 三个 MCP 写工具的结构化执行计划
- HITL 批准 / 拒绝交互
- 幂等写入、结果回读和安全终止状态
- 桌面端与移动端响应式界面

> 当前按钮驱动的是确定性前端状态机，不会调用真实业务系统。后端能力将在后续里程碑逐步接入，并以测试和评估结果为准更新项目描述。

## 本地运行

```bash
npm install
npm run dev
```

访问 `http://localhost:3000`。

生产构建：

```bash
npm run build
npm start
```

## 计划中的工程化升级

- [x] 可交互 Agent 工作台与 HITL 原型
- [ ] Agent Skills 注册、渐进加载与路由评估
- [ ] 带引用和拒答策略的 RAG 检索
- [ ] FastMCP 读写工具及 Pydantic 契约
- [ ] LangGraph checkpoint、interrupt 与恢复执行
- [ ] FastAPI + SSE 运行状态接口
- [ ] 幂等键、超时重试、错误分类与执行回读
- [ ] 端到端评估集和可复现实验报告

## 简历使用原则

只把已完成并能在仓库中验证的能力写进简历。当前可以描述“完成交互式 Agent 工作台和 HITL 流程原型”；MCP、LangGraph、RAG 后端和量化指标应在对应代码与评估完成后再写。
