"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_RIDEOPS_API_URL ?? "http://127.0.0.1:8000";

type UiStatus = "loading" | "waiting" | "approved" | "rejected";

type Evidence = {
  document_id: string;
  title: string;
  section: string;
  content: string;
  score: number;
  source: string;
};

type PlannedAction = {
  action_id: string;
  tool: string;
  requires_approval: boolean;
  arguments: Record<string, string>;
};

type RunData = {
  run_id: string;
  workflow_status: string;
  selected_skill: string | null;
  collected_fields: Record<string, string | null>;
  missing_fields: string[];
  evidence: Evidence[];
  planned_actions: PlannedAction[];
  approval: string;
  action_results: Array<{ action_id: string; tool: string; status: string; result?: Record<string, string> }>;
  final_state: {
    order?: { order_id: string; billing_status: string; status: string } | null;
    vehicle?: { vehicle_id: string; status: string } | null;
    ticket?: { ticket_id: string; status: string } | null;
  };
  message: string;
};

const demoRequest = {
  user_id: "usr_demo_001",
  message: "我在上海静安区骑车发生碰撞，手臂有轻微擦伤，车锁损坏，订单仍在计费，怎么办？",
  order_id: "ord_demo_001",
  vehicle_id: "veh_demo_001",
  location: "上海市静安区",
  description: "车辆碰撞，用户手臂有轻微擦伤，车锁损坏",
};

const toolLabels: Record<string, string> = {
  suspend_order_billing: "暂停订单计费",
  mark_vehicle_unavailable: "车辆标记为不可用",
  create_incident_ticket: "创建事故工单",
};

function uiStatus(run: RunData | null): UiStatus {
  if (!run) return "loading";
  if (run.workflow_status === "completed") return "approved";
  if (run.workflow_status === "safe_terminated" || run.workflow_status === "failed") return "rejected";
  return "waiting";
}

function stepState(run: RunData | null, index: number) {
  if (!run) return "pending";
  if (run.workflow_status === "completed") return "done";
  if (run.workflow_status === "safe_terminated" || run.workflow_status === "failed") return index < 4 ? "done" : "rejected";
  if (run.workflow_status === "waiting_for_input") return index < 2 ? "done" : index === 2 ? "active" : "pending";
  return index < 4 ? "done" : index === 4 ? "active" : "pending";
}

export default function Home() {
  const [run, setRun] = useState<RunData | null>(null);
  const [tab, setTab] = useState<"plan" | "evidence">("plan");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(demoRequest),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`后端返回 ${response.status}`);
        return response.json() as Promise<RunData>;
      })
      .then((data) => {
        if (!cancelled) setRun(data);
      })
      .catch((reason: Error) => {
        if (!cancelled) setError(`无法连接后端：${reason.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const status = uiStatus(run);
  const actionTitle = status === "waiting" ? (run?.workflow_status === "waiting_for_input" ? "需要补充信息" : "需要人工批准") : status === "approved" ? "执行已完成" : status === "rejected" ? "流程已终止" : "正在连接后端";
  const ticketId = run?.final_state.ticket?.ticket_id;
  const steps = useMemo(() => [
    ["意图识别", run?.selected_skill ?? "等待后端路由"],
    ["Skill 加载", run?.selected_skill ?? "等待 Skill"],
    ["RAG 检索", run?.evidence.length ? `命中 ${run.evidence.length} 条事故政策` : "等待证据"],
    ["业务查询", run?.final_state.order ? `订单 ${run.final_state.order.order_id} 已核验` : "等待订单信息"],
    ["人工审批", run?.approval === "pending" ? "等待运营人员确认" : run?.approval === "approved" ? "已批准" : run?.approval === "rejected" ? "已拒绝" : "未进入审批"],
    ["可靠执行", run?.workflow_status === "completed" ? "工具执行成功，结果已回读" : "审批后执行写操作"],
  ], [run]);

  async function resume(approved: boolean) {
    if (!run) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/runs/${run.run_id}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      if (!response.ok) throw new Error(`后端返回 ${response.status}`);
      setRun(await response.json());
    } catch (reason) {
      setError(`操作失败：${reason instanceof Error ? reason.message : "未知错误"}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand"><span className="logo">R</span><div><b>RideOps Agent</b><small>共享出行业务智能体</small></div></div>
        <div className="status"><span /> {error ? "BACKEND ERROR" : "LIVE BACKEND"}</div>
      </header>

      <section className="hero">
        <div><p className="eyebrow">AGENT OPERATIONS WORKBENCH</p><h1>让客服 Agent 不只回答，<br />还能安全地完成业务。</h1></div>
        <div className="heroMeta"><span>RUN ID</span><b>{run?.run_id ?? "creating..."}</b><span>API</span><b>{API_BASE}</b></div>
      </section>

      {error && <div className="result rejectedResult">{error}。请确认后端已启动：<code>uvicorn rideops.api.app:app --reload</code></div>}

      <section className="workspace">
        <div className="chat panel">
          <div className="panelTitle"><span>01</span><div><b>用户会话</b><small>事故处理 · SQLite + LangGraph MVP</small></div></div>
          <div className="message user">{demoRequest.message}</div>
          <div className="message agent"><b>{run?.message ?? "正在创建真实 Run..."}</b><p>{run?.workflow_status === "waiting_for_input" ? "后端已识别到信息缺口，暂不执行任何写操作。" : "当前内容来自后端 Run、RAG 证据和 SQLite 回读，不再使用前端固定执行结果。"}</p></div>
          <div className="facts"><div><span>订单</span><b>{run?.collected_fields.order_id ?? "待补充"}</b></div><div><span>车辆</span><b>{run?.collected_fields.vehicle_id ?? "待查询"}</b></div><div><span>地点</span><b>{run?.collected_fields.location ?? "待补充"}</b></div></div>
        </div>

        <div className="trace panel">
          <div className="panelTitle"><span>02</span><div><b>执行轨迹</b><small>真实 Run 状态 · 暂不使用 SSE</small></div></div>
          <div className="timeline">
            {steps.map(([name, desc], index) => {
              const current = stepState(run, index);
              return <div className={`step ${current}`} key={name}><i>{current === "done" ? "✓" : index + 1}</i><div><b>{name}</b><small>{desc}</small></div></div>;
            })}
          </div>
        </div>
      </section>

      <section className="decision panel">
        <div className="decisionHead"><div><p className="eyebrow">HUMAN-IN-THE-LOOP</p><h2>{actionTitle}</h2></div><span className={`pill ${status}`}>{status === "loading" ? "CONNECTING" : run?.workflow_status.toUpperCase()}</span></div>
        <div className="tabs"><button className={tab === "plan" ? "selected" : ""} onClick={() => setTab("plan")}>执行计划</button><button className={tab === "evidence" ? "selected" : ""} onClick={() => setTab("evidence")}>证据与回读</button></div>
        {tab === "plan" ? <div className="toolGrid">{run?.planned_actions.length ? run.planned_actions.map((action) => <article key={action.action_id}><code>{action.tool}</code><b>{toolLabels[action.tool] ?? action.tool}</b><p>{Object.values(action.arguments).filter(Boolean).join(" · ")}</p><span>{action.requires_approval ? "WRITE · APPROVAL REQUIRED" : "READ ONLY"}</span></article>) : <article><b>{run?.message ?? "正在读取后端计划"}</b><p>{run?.missing_fields.join("、") || "暂无可执行动作"}</p></article>}</div> : <div className="evidence">{run?.evidence.map((item) => <article key={`${item.document_id}-${item.section}`}><b>{item.title} · {item.section}</b><p>{item.content}</p><small>score {item.score} · {item.source}</small></article>)}{run?.final_state.order && <article><b>SQLite 业务状态回读</b><p>订单计费：{run.final_state.order.billing_status}；车辆状态：{run.final_state.vehicle?.status ?? "未回读"}；工单：{run.final_state.ticket?.status ?? "尚未创建"}</p></article>}</div>}
        {run?.workflow_status === "awaiting_approval" && <div className="actions"><button className="secondary" disabled={submitting} onClick={() => resume(false)}>拒绝执行</button><button className="primary" disabled={submitting} onClick={() => resume(true)}>{submitting ? "处理中..." : "批准并执行"}</button></div>}
        {run?.workflow_status === "completed" && <div className="result">✓ SQLite 持久化写入成功 · 事故工单 {ticketId ?? "已创建"} · 订单、车辆和工单状态已回读</div>}
        {run?.workflow_status === "safe_terminated" && <div className="result rejectedResult">流程已安全终止，未调用任何写工具。</div>}
      </section>

      <footer><span>REAL RAG EVIDENCE</span><span>SQLITE TOOLS</span><span>LANGGRAPH MVP</span><span>HITL</span><span>IDEMPOTENCY</span></footer>
    </main>
  );
}
