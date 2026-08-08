"use client";

import { useState } from "react";

const steps = [
  ["意图识别", "事故处理", "done"],
  ["Skill 加载", "accident-handling", "done"],
  ["RAG 检索", "命中 3 条事故政策", "done"],
  ["业务查询", "订单与车辆状态已核验", "done"],
  ["人工审批", "等待运营人员确认", "active"],
  ["可靠执行", "审批后执行 3 个写工具", "pending"],
];

const tools = [
  ["suspend_order_billing", "暂停订单计费", "O-83921"],
  ["mark_vehicle_unavailable", "车辆标记为不可用", "B-1047"],
  ["create_incident_ticket", "创建事故工单", "深圳科技园南门"],
];

export default function Home() {
  const [status, setStatus] = useState<"waiting" | "approved" | "rejected">("waiting");
  const [tab, setTab] = useState<"plan" | "evidence">("plan");

  const approve = () => setStatus("approved");
  const reject = () => setStatus("rejected");

  return (
    <main>
      <header className="topbar">
        <div className="brand"><span className="logo">R</span><div><b>RideOps Agent</b><small>共享出行业务智能体</small></div></div>
        <div className="status"><span /> SYSTEM ONLINE</div>
      </header>

      <section className="hero">
        <div><p className="eyebrow">AGENT OPERATIONS WORKBENCH</p><h1>让客服 Agent 不只回答，<br />还能安全地完成业务。</h1></div>
        <div className="heroMeta"><span>RUN ID</span><b>run-20260808-042</b><span>THREAD</span><b>user-U-10086</b></div>
      </section>

      <section className="workspace">
        <div className="chat panel">
          <div className="panelTitle"><span>01</span><div><b>用户会话</b><small>事故处理 · 高风险流程</small></div></div>
          <div className="message user">我刚才在深圳科技园骑车摔倒了，手臂有擦伤，车锁也坏了。订单还在计费，怎么办？</div>
          <div className="message agent"><b>已进入事故处理流程</b><p>我已核验你的进行中订单和车辆状态，并根据事故处理政策生成处置计划。涉及暂停计费、停用车辆和创建工单的操作，需要运营人员批准后执行。</p></div>
          <div className="facts"><div><span>订单</span><b>O-83921</b></div><div><span>车辆</span><b>B-1047</b></div><div><span>伤情</span><b>轻微擦伤</b></div></div>
        </div>

        <div className="trace panel">
          <div className="panelTitle"><span>02</span><div><b>执行轨迹</b><small>LangGraph durable workflow</small></div></div>
          <div className="timeline">
            {steps.map(([name, desc, originalState], index) => {
              const state = status === "approved" && index >= 4 ? "done" : status === "rejected" && index >= 4 ? "rejected" : originalState;
              return <div className={`step ${state}`} key={name}><i>{state === "done" ? "✓" : index + 1}</i><div><b>{name}</b><small>{status === "approved" && index === 5 ? "3 个工具执行成功，结果已回读" : desc}</small></div></div>;
            })}
          </div>
        </div>
      </section>

      <section className="decision panel">
        <div className="decisionHead"><div><p className="eyebrow">HUMAN-IN-THE-LOOP</p><h2>{status === "waiting" ? "需要人工批准" : status === "approved" ? "执行已完成" : "执行已拒绝"}</h2></div><span className={`pill ${status}`}>{status === "waiting" ? "WAITING" : status.toUpperCase()}</span></div>
        <div className="tabs"><button className={tab === "plan" ? "selected" : ""} onClick={() => setTab("plan")}>执行计划</button><button className={tab === "evidence" ? "selected" : ""} onClick={() => setTab("evidence")}>证据与引用</button></div>
        {tab === "plan" ? <div className="toolGrid">{tools.map(([name, label, value]) => <article key={name}><code>{name}</code><b>{label}</b><p>{value}</p><span>WRITE · APPROVAL REQUIRED</span></article>)}</div> : <div className="evidence"><article><b>《共享电单车事故处理规范》§ 3.2</b><p>事故订单可在核验后暂停计费；车辆需立即进入不可用状态，等待运维复检。</p></article><article><b>订单系统回读</b><p>订单 O-83921 处于 ACTIVE，车辆 B-1047 当前为 IN_SERVICE。</p></article></div>}
        {status === "waiting" && <div className="actions"><button className="secondary" onClick={reject}>拒绝执行</button><button className="primary" onClick={approve}>批准并执行</button></div>}
        {status === "approved" && <div className="result">✓ 幂等写入成功 · 事故工单 INC-20260808-042 已创建 · 最终状态已核验</div>}
        {status === "rejected" && <div className="result rejectedResult">流程已安全终止，未调用任何写工具。</div>}
      </section>

      <footer><span>RAG EVIDENCE</span><span>MCP TOOLS</span><span>LANGGRAPH</span><span>HITL</span><span>IDEMPOTENCY</span></footer>
    </main>
  );
}
