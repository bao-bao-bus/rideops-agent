# RideOps Agent

面向共享出行业务的 Agent 应用开发实习项目。当前仓库保留原有 Next.js 前端交互原型，并新增了第一轮 Python 后端基础与 Agent Skills 能力。

## 当前完成状态

本轮已完成阶段一和阶段二：

- FastAPI 应用骨架与 `GET /health`
- Pydantic v2 领域模型：订单、车辆、库存、事故工单
- 本地合成业务数据仓库，不连接真实企业数据库
- 两个 Skill：`accident-handling`、`long-rental-planning`
- Skill Registry：启动时只扫描名称和描述
- Skill Router：基于业务关键词路由，命中后再加载完整 `SKILL.md`
- references 和 templates 按需读取
- 10 条以上 Skill 路由测试用例
- 原有 Next.js 前端原型未改动

阶段三已完成：

- 合成事故处理与长租政策文档
- Markdown 文档解析与按章节 Chunk 切分
- 可替换的 Embedding 接口与本地确定性 Mock Embedding
- 关键词检索、向量检索和 Hybrid Search
- 可选本地 Rerank
- `document_id`、标题、章节、内容、分数和来源引用
- 无足够证据时拒答
- `POST /api/rag/search` 检索接口

当前尚未实现：MCP、LangGraph、HITL checkpoint、可靠执行、SSE，以及真实模型或企业系统连接。RAG 当前使用本地 Mock 模式；前端中的相关流程仍是确定性演示状态机。

## 目录结构

```text
app/                         # 原有 Next.js 前端
backend/
  src/rideops/
    api/                     # FastAPI 接口
    domain/                  # Pydantic 领域模型
    repositories/            # 合成数据仓库
    skills/                  # Registry 与 Router
    rag/                     # 文档、Chunk、Embedding、Hybrid Search
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

## 下一阶段

下一轮实现 MCP 业务工具：只读/写入工具契约、审批约束、合成数据、错误分类和幂等键。只有实际运行评估后，才会把指标写入 README 或简历。

## 简历表述（基于当前代码）

搭建 RideOps Agent 的 FastAPI 后端基础，使用 Pydantic 建模订单、车辆、库存和事故工单等业务实体；设计可扩展的 Skill Registry 与关键词路由器，实现 Skill 元数据启动扫描、命中后的渐进式 `SKILL.md` 加载；进一步实现本地 Mock 优先的 RAG 检索链路，支持 Markdown 政策解析、Hybrid Search、可替换 Embedding 接口、证据引用和无证据拒答，并使用 pytest 覆盖 26 个测试场景。
