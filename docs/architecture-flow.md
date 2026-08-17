# RideOps 当前链路

下面的流程图对应当前仓库已经实现的代码。虚线部分是后续增强，不代表当前已经接入。

```mermaid
flowchart TD
    U[用户请求] --> S{业务场景}

    S -->|客服查询| C0[Customer Service Supervisor]
    C0 --> C1[出行前 Agent：路线/费用/车辆]
    C0 --> C2[政策 Agent：RAG 证据]
    C0 --> C3[长租 Agent：库存/价格规划]
    C0 --> C4[事故分诊 Agent：交接事故 Run]
    C1 --> C5[高德官方 MCP + RideOps 计价 + SQLite 车辆]
    C2 --> C6[RAG：本地政策证据]
    C3 --> C7[SQLite：长租库存与价格]
    C4 -.不写入.-> A1
    C5 --> C8[汇总回复、来源与缺失字段]
    C6 --> C8
    C7 --> C8

    S -->|出行前预约| P1[POST /api/pretrip/plan]
    P1 --> P2[普通只读工具：查询附近可用车辆]
    P1 --> P3[路线与费用预估]
    P2 --> P4[返回候选车辆与预估]
    P3 --> P4
    P4 --> P5[POST /api/pretrip/reserve]
    P5 --> P6[预约写工具 + idempotency_key]
    P6 --> DB[(SQLite：车辆与预约状态)]
    DB --> P7{用户取消预约?}
    P7 -->|是| P8[POST /api/pretrip/reservations/{id}/cancel]
    P8 --> P9[归属校验 + 确认引用 + 幂等键]
    P9 --> DB

    S -->|长租规划| L1[POST /api/long-rental/plan]
    L1 --> L2[SQLite：长租库存与价格]
    L2 --> L3[返回候选方案、预算判断和假设]
    L3 --> L4{用户确认?}
    L4 -->|是| L5[POST /api/long-rental/leads]
    L5 --> L6[确认引用 + 幂等键]
    L6 --> L7[(SQLite：长租跟进线索)]

    S -->|事故中| A1[POST /api/runs]
    A1 --> A2[Skill Router：accident-handling]
    A2 --> R1[政策文档解析与 Chunk]
    R1 --> R2[BM25 Top20]
    R1 --> R3[SQLite 持久化 Vector Top20]
    R2 --> R4[RRF 融合]
    R3 --> R4
    R4 --> R5[可选 Reranker：当前 disabled]
    R5 --> A3{证据足够?}
    A3 -->|否| REF[拒答]
    A3 -->|是| A4{信息完整?}
    A4 -->|否| ASK[返回缺失字段并追问]
    A4 -->|是| A5[普通只读工具：查询活动订单]
    A5 --> A6[生成待执行动作]
    A6 --> HITL{人工审批}
    HITL -->|拒绝| SAFE[安全结束：不执行写工具]
    HITL -->|批准| W1[普通写工具：暂停计费]
    W1 --> W2[普通写工具：车辆不可用]
    W2 --> W3[普通写工具：创建事故工单]
    W3 --> DB2[(SQLite：订单、车辆、工单、Run)]
    DB2 --> V1[只读工具回读最终状态]
    V1 --> DONE[Run completed]

    DONE --> F[Next.js 客服对话：按需展示确认结果]
    SAFE --> F
    ASK --> F
    REF --> F

    API[外部 Embedding API] -.后续启用.-> R3
    MCP[RideOps 自有 FastMCP Server] --> W1
    SSE[SSE 事件流] -.后续替换普通 HTTP.-> F
    PG[PostgreSQL] -.后续可选.-> DB2
    REDIS[Redis] -.后续可靠性扩展.-> DB2
```

## 当前边界

- 当前默认使用 Mock Embedding，不调用外部模型 API。
- 当前 RAG 使用 BM25 + Mock Vector + RRF，向量索引持久化在 SQLite。
- 当前 Reranker 接口存在但默认关闭，没有用简单排序冒充真实 Reranker。
- 当前已实现确定性的 Customer Service Supervisor：可将一个客服问题分派给出行前、政策、长租或事故分诊 Agent，并在响应中返回 `delegated_agents`。它不依赖模型 API，也不让 Agent 直接写数据库。
- 当前路线查询已通过 MCP Client 调用高德官方 MCP；订单、预约、事故工单等 RideOps 私有业务仍是 Python 服务内普通工具。预约取消会校验预约归属，并只在车辆仍是预约占用状态时恢复可用。
- RideOps 私有业务工具已通过 stdio 暴露为 FastMCP Server。事故 HTTP 主流程目前仍直接调用 Service / Repository，以保持可恢复、可审计的闭环；后续若改为 MCP Client 调用，也会复用同一套 Service / Repository，而不是再造一套写入逻辑。
- 当前前端使用普通 HTTP 请求，不是 SSE。
- 当前业务数据和 Run 状态使用 SQLite，不需要 PostgreSQL、Redis 或 Docker。
