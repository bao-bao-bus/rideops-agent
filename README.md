# RideOps Agent

> Skill-driven shared-mobility support agent with RAG evidence, MCP business tools, LangGraph durable workflows, human approval, and reliable execution.

RideOps is a portfolio project for AI Agent application engineering internships. It upgrades a conventional RAG support bot into a bounded business agent that can investigate an incident, propose actions, pause for operator approval, execute typed tools, and verify the result.

## What the demo proves

| Workflow | Skill | RAG | MCP | HITL | Reliable writes |
|---|---:|---:|---:|---:|---:|
| FAQ and policy Q&A | — | Yes | — | — | — |
| Long-rental planning | Yes | Yes | Read + confirmed lead | Confirmation | Idempotent lead |
| Accident handling | Yes | Yes | Read + write | Operator approval | Idempotency + verification |

## Current milestone

- Interactive agent workbench showing the complete accident-handling trace.
- Typed contracts for eight business tools.
- Deterministic mock order, vehicle, ticket, and rental data.
- Two Agent Skills with references and output templates.
- Seed routing dataset for Skill selection evaluation.
- Unit tests proving seeded reads and idempotent writes.

The web workbench is currently a deterministic UI prototype. The following milestones connect it to the FastAPI, MCP, LangGraph, and RAG runtime.

## Repository map

```text
rideops-agent/
├── app/                    # React workbench
├── backend/                # FastAPI, LangGraph, MCP, and domain code
├── skills/                 # Agent Skills bundles
├── evals/                  # Routing and workflow evaluation datasets
├── docs/                   # Architecture and design notes
└── tests/                  # Web artifact tests
```

## Local checks

Frontend:

```bash
npm run lint
npm test
```

Backend after installing the development dependencies:

```bash
cd backend
python -m pip install -e '.[dev]'
pytest
```

## Design decisions

- Skills describe reusable business procedures; they do not grant permission.
- LangGraph will enforce state transitions and resumable approval boundaries.
- MCP write tools require explicit approval and stable idempotency keys.
- Retrieved documents are evidence, never authorization for a business action.
- The repository contains only synthetic users, orders, policies, and metrics.

See [the architecture notes](docs/architecture.md) for component boundaries and the staged implementation plan.

## Roadmap

- [x] Product workbench and interaction prototype
- [x] Skills, tool contracts, mock data, and initial tests
- [ ] Skill registry with progressive loading and routing evals
- [ ] RAG policy retrieval with citations and refusal
- [ ] FastMCP server with read/write annotations
- [ ] LangGraph checkpoints and `interrupt` approval flow
- [ ] FastAPI run, event-stream, state, and resume endpoints
- [ ] End-to-end eval report and recorded demo
