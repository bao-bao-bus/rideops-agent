# RideOps Agent

面向共享出行业务的 Agent 应用开发实习项目。当前仓库保留原有 Next.js 前端交互原型，并新增了第一轮 Python 后端基础与 Agent Skills 能力。

## 当前完成状态

本轮已完成阶段一和阶段二：

- FastAPI 应用骨架与 `GET /health`
- Pydantic v2 领域模型：订单、车辆、库存、事故工单
- 本地合成业务数据仓库，不连接真实企业数据库
- 三个 Skill：`accident-handling`、`long-rental-planning`、`pretrip-support`
- Skill Registry：启动时只扫描名称和描述
- Skill Router：基于业务关键词路由，命中后再加载完整 `SKILL.md`
- references 和 templates 按需读取
- 10 条以上 Skill 路由测试用例
- 原有 Next.js 前端原型未改动

阶段三与 RAG 第一轮升级已完成：

- 合成事故处理与长租政策文档
- Markdown 文档解析与按章节 Chunk 切分
- 统一 Embedding Provider 接口
- 本地 Mock Embedding Provider
- OpenAI-compatible Embedding Adapter（配置 API Key 后启用）
- 中文分词与 BM25
- SQLite 持久化向量索引
- BM25 + Vector + RRF Hybrid Search
- 可选 Reranker 接口（当前默认关闭）
- `document_id`、标题、章节、内容、分数和来源引用
- 无足够证据时拒答
- `POST /api/rag/search` 检索接口

## RAG 评估集与当前基线

评估集位于 `evals/rag_eval.jsonl`，当前包含 37 条带标注问题，覆盖事故计费、车辆损坏、人员受伤、事故工单、长租需求、库存、续租/退租、无关问题和知识库外问题。评估脚本位于 `evals/run_rag_eval.py`。

运行命令：

```bash
python evals/run_rag_eval.py --output evals/mock-baseline.json
```

当前本地 `BM25 + Mock Vector + RRF` 基线（`min_score=0.18`，实际运行结果）：

| 指标 | 结果 |
| --- | ---: |
| Hit@1 | 0.8750 |
| Hit@3 | 0.9167 |
| Hit@5 | 0.9167 |
| MRR | 0.8958 |
| 拒答正确率 | 0.8919 |
| Skill Routing Accuracy | 0.8378 |

这些数字仅用于后续比较真实 Embedding、BM25、Vector、Hybrid+RRF 和 Reranker 版本，不代表生产能力，也不作为简历指标。

当前已增加事故处理 MVP 和出行前场景边界：SQLite 持久化、普通业务工具、简单 LangGraph 准备/执行图、审批前暂停、批准后写入、结果回读、附近车辆查询、路线/费用预估、长租库存/价格规划和幂等预约。事故流程现在支持缺失信息补交后继续运行，并持久化记录路由、检索、追问、审批、工具执行和最终完成等运行事件，方便前端展示审计轨迹。出行前路线已经支持通过 MCP Client 调用高德官方远程 MCP；没有配置 Provider 或 API Key 时自动使用合成路线。费用仍由 RideOps 自己计算，不把地图路线费用冒充共享出行最终价格。新增统一只读客服查询接口，能够根据用户问题查询路线、费用、附近车辆和本地政策，并返回来源、证据和缺失字段。长租规划支持查询库存和价格；用户确认后可带确认引用和幂等键创建后续跟进线索，但不会直接创建租赁订单。当前尚未实现：LangGraph Checkpoint、复杂可靠性策略、SSE，以及真实模型或企业系统连接。RAG 默认仍使用 Mock Embedding，但已经具备真实 Embedding Adapter 接口。

## 目录结构

```text
app/                         # 原有 Next.js 前端
backend/
  src/rideops/
    api/                     # FastAPI 接口
    domain/                  # Pydantic 领域模型
    repositories/            # 合成数据仓库
    services/                # 普通业务工具
    agents/                  # 简单 LangGraph 事故流程
    skills/                  # Registry 与 Router
    rag/                     # 文档、Chunk、Embedding、BM25、RRF、持久化索引
skills/                     # 可按需加载的 SKILL.md
docs/policies/               # 合成政策文档
```

## 启动后端

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
uvicorn rideops.api.app:app --reload
```

访问 `http://127.0.0.1:8000/health`。默认是 mock 模式，不需要 API Key。

### 高德 MCP（可选）

开发阶段默认不调用外部地图服务。需要真实路线时，在项目根目录 `.env` 或 `backend/.env` 中配置：

```env
RIDEOPS_MAP_PROVIDER=amap_mcp
AMAP_API_KEY=你的高德Web服务Key
```

高德 MCP 返回真实路线距离和时间，RideOps 仍使用自己的计价规则计算费用，并在响应中区分 `source` 与 `pricing_source`。Key 只放在本地 `.env`，不提交到仓库。调用失败时可以回退到合成路线，避免演示流程被外部服务中断。

## 运行测试

```bash
cd backend
pytest
```

## 前端

```bash
npm install
npm run dev
```

## RAG 检索示例

```bash
curl -X POST http://127.0.0.1:8000/api/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query":"车辆发生碰撞后应该怎么处理"}'
```

返回的每条证据包含 `document_id`、`title`、`section`、`content`、`score` 和 `source`。没有足够证据时返回 `answerable: false`，不会强行生成答案。

## 事故 MVP 闭环

前端默认创建一条合成事故 Run，后端执行：

```text
用户报事故
→ Skill 路由
→ BM25 + Mock Vector + RRF 返回政策证据
→ SQLite 查询活动订单
→ 缺字段时返回追问
→ 生成三个待审批写动作
→ 人工批准或拒绝
→ 普通业务工具写入 SQLite
→ 只读工具回读订单、车辆和工单状态
```

当前 Run 接口：

```text
POST /api/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events
POST /api/runs/{run_id}/provide-info
POST /api/runs/{run_id}/resume
```

统一客服查询接口：

```text
POST /api/customer-service/query
```

只读查询不触发审批；路线结果标注 `amap_mcp` 或合成回退来源，费用结果标注 RideOps 计价来源，政策结果返回 RAG 证据。出发地、目的地或当前位置缺失时返回 `missing_fields`，不会猜测用户条件。

当事故信息不完整时，`provide-info` 会将用户补充的信息写回当前 Run，并重新进入准备阶段；只有进入人工审批后，`resume` 才会执行写操作。Run 事件保存在 SQLite 的 `run_events` 表中，当前以 JSON 接口提供，后续可在不改变业务事件模型的情况下接入 SSE。

当前出行前接口：

```text
POST /api/pretrip/plan
POST /api/pretrip/reserve
```

当前长租接口：

```text
POST /api/long-rental/plan
POST /api/long-rental/leads
```

长租方案会返回城市、车型、可用库存、日租/月租计价方式、租金、押金、预算判断和计算假设；库存不足时明确返回不可回答，不虚构方案。创建跟进线索必须带 `approval_reference` 和 `idempotency_key`，重复提交不会重复创建。

当前 MVP 使用普通 HTTP 请求，不使用 SSE；使用 SQLite 保存业务状态和 Run 状态，不引入 Redis。高德路线调用通过 MCP Client 访问官方地图 MCP，订单、预约、事故工单等 RideOps 私有业务仍由本项目自己的 Service 和 Repository 负责。

## RideOps 自有 MCP

自有 MCP Server 已提供 11 个共享出行客服工具，包含订单、车辆、路线/费用、政策检索和事故、预约、长租留资写操作。启动方式：

```bash
cd backend
pip install -e ".[test]"
rideops-mcp
```

读工具可以直接查询；写工具必须携带 `idempotency_key` 和 `approval_reference`，不能绕过人工确认。详细工具边界见 [docs/mcp-tools.md](docs/mcp-tools.md)。

## 下一阶段

下一轮使用 OpenAI-compatible API 实际运行真实 Embedding，并重新跑评估对比；确认 RAG 稳定后，再进入 FastMCP、PostgreSQL、SSE 断线恢复等加分项。

## 简历表述（基于当前代码）

搭建 RideOps Agent 的 FastAPI 后端基础，使用 Pydantic 建模订单、车辆、库存和事故工单等业务实体；实现 Skill Registry 渐进式加载、中文 BM25、Mock Vector、RRF 融合和可选 Embedding Adapter，并基于 SQLite、普通业务工具和 LangGraph 构建事故处理 MVP，实现缺失信息补交、审批前禁止写入、批准后幂等执行、运行事件审计及订单/车辆/工单状态回读，同时补充出行前车辆查询、MCP 路线查询、统一客服查询、长租库存/价格规划与确认线索、费用预估和幂等预约接口；使用 pytest 覆盖 56 个测试场景。
