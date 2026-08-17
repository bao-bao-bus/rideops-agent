# RideOps 当前链路

下面的流程图对应当前仓库已经实现的代码。虚线部分是后续增强，不代表当前已经接入。

```mermaid
flowchart TD
    U[用户请求] --> S{业务场景}

    S -->|出行前| P1[POST /api/pretrip/plan]
    P1 --> P2[普通只读工具：查询附近可用车辆]
    P1 --> P3[普通只读工具：路线与费用合成预估]
    P2 --> P4[返回候选车辆与预估]
    P3 --> P4
    P4 --> P5[POST /api/pretrip/reserve]
    P5 --> P6[预约写工具 + idempotency_key]
    P6 --> DB[(SQLite：车辆与预约状态)]

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

    DONE --> F[Next.js 工作台：普通 HTTP 展示真实状态]
    SAFE --> F
    ASK --> F
    REF --> F

    API[外部 Embedding API] -.后续启用.-> R3
    MCP[FastMCP] -.后续封装普通工具.-> W1
    SSE[SSE 事件流] -.后续替换普通 HTTP.-> F
    PG[PostgreSQL] -.后续可选.-> DB2
    REDIS[Redis] -.后续可靠性扩展.-> DB2
```

## 当前边界

- 当前默认使用 Mock Embedding，不调用外部模型 API。
- 当前 RAG 使用 BM25 + Mock Vector + RRF，向量索引持久化在 SQLite。
- 当前 Reranker 接口存在但默认关闭，没有用简单排序冒充真实 Reranker。
- 当前业务工具是 Python 服务内普通工具，不是 MCP。
- 当前前端使用普通 HTTP 请求，不是 SSE。
- 当前业务数据和 Run 状态使用 SQLite，不需要 PostgreSQL、Redis 或 Docker。
