# AgentOS Architecture

AgentOS is a web application: a Next.js frontend talking to a FastAPI backend that runs a
LangGraph multi-agent workflow. Product scope is in [AgentOS_README.md](../AgentOS_README.md);
this document covers how the code is organised and why.

## Status

A walking skeleton is in place: the web UI starts a run, the API executes the LangGraph
workflow and streams each agent's result back, and the UI renders the execution trace and
report. **All seven agents are stubs** that return placeholder data. No LLM, retrieval, MCP,
database tables or auth exist yet. See [Build order](#build-order).

## System overview

```text
 Browser
    │  HTTPS (REST + Server-Sent Events)
    ▼
┌──────────────┐        ┌───────────────────────────────────────────┐
│  apps/web    │        │  apps/api                                 │
│  Next.js     │ ─────► │  FastAPI  ──►  LangGraph workflow         │
│  (UI only)   │        │     │            planner → rag ─────────┐ │
└──────────────┘        │     │                    → github →     │ │
                        │     │                      code_analysis┤ │
                        │     │            analyst ◄──────────────┘ │
                        │     │            → verifier → report      │
                        │     ▼                                     │
                        │  Celery tasks (ingestion, indexing, evals)│
                        └──────┬───────────────┬──────────────┬─────┘
                               ▼               ▼              ▼
                          PostgreSQL        Qdrant          Redis
                        (app data, run    (embeddings)   (Celery broker)
                         checkpoints)
                                                    GitHub MCP server
                                                    LLM provider
```

## Repository layout

```text
apps/
  web/                    Next.js 16 (App Router, TypeScript, Tailwind 4), pnpm
    src/app/              routes: / (AgentLens landing page), /console (run UI)
    src/app/layout.tsx    Google Fonts, one per role (heading, subheading, body, mono)
    src/components/       landing/ sections; run-console.tsx = query box, trace, report
    src/lib/api.ts        the only place that calls the backend
    src/lib/types.ts      API event types shared across the UI
  api/                    Python 3.12, uv-managed, package name `agentos`
    src/agentos/
      main.py             FastAPI app factory
      core/config.py      settings from AGENTOS_* env vars
      api/                HTTP layer: router.py + routes/ (health, runs)
      agents/             LangGraph: state.py, graph.py, nodes/<agent>.py
      rag/                ingestion, embeddings, hybrid retrieval, reranking   (empty)
      mcp/                GitHub MCP client + custom MCP servers               (empty)
      llm/                provider-agnostic model factories                    (empty)
      db/                 SQLAlchemy async engine/session, models
      workers/            Celery app and tasks
    tests/
infra/
  docker-compose.yml      Postgres, Redis, Qdrant for local development
docs/
```

Dependency direction inside `agentos`: `api` → `agents` → `rag` / `mcp` / `llm` → `db` / `core`.
Routes stay thin; agents never import from `api`.

## Key decisions

**Two apps, not one.** The frontend is Next.js and the AI stack (LangChain, LangGraph, Ragas)
is Python, so the backend is a separate FastAPI service rather than Next.js route handlers.
Next.js is UI only and holds no business logic.

**Browser calls the API directly.** `apps/web` reads `NEXT_PUBLIC_API_URL` and the API allows
that origin through CORS (`AGENTOS_CORS_ORIGINS`). This avoids proxying long-lived streams
through the Next.js server.

**Runs stream over Server-Sent Events.** `POST /api/v1/runs/stream` returns a
`text/event-stream`; each frame is one JSON event:

| Event | Meaning |
|---|---|
| `{"type": "node", "node": "<agent>", "update": {...}}` | an agent finished; `update` is its state change |
| `{"type": "done"}` | the workflow completed |
| `{"type": "error", "message": "..."}` | the workflow failed mid-stream |

SSE fits because the flow is one-way (server → browser) and it works over plain HTTP. The
contract is defined in `api/routes/runs.py` and mirrored in `web/src/lib/types.ts`; change
both together.

**One LangGraph graph with shared state.** `agents/state.py` defines `AgentState`; each agent
is a module in `agents/nodes/` exposing `async def run(state)` and returning a partial update.
`agents/graph.py` is the only place that knows the wiring. RAG and GitHub branches run in
parallel, and the analyst waits for both.

**Agent runs in the API process, heavy jobs in Celery.** Agent runs are I/O-bound and need to
stream, so they run as async tasks inside FastAPI. Repository ingestion, embedding and
evaluation are slow batch jobs and go to Celery workers via Redis.

## Planned, not built

- **Persistence and resumable runs.** Runs currently live only for the duration of the HTTP
  request. Next step is `runs` tables in Postgres plus LangGraph's Postgres checkpointer, so a
  run has an ID, survives a dropped connection, and can be resumed.
- **Human-in-the-loop.** Built on the checkpointer: write-capable tools call LangGraph
  `interrupt()`, the stream emits an approval event, and a `POST /runs/{id}/resume` endpoint
  continues the run.
- **Data model.** Workspace → repositories and documents → runs → run events. Qdrant payloads
  carry `workspace`, `repository`, `file`, `language`, `branch` for filtered retrieval.
- **Auth.** Undecided. Every table and Qdrant filter should be workspace-scoped from the start
  so auth can be added without a data migration.
- **Observability and evaluation.** Langfuse callbacks on the graph; Ragas runs as Celery tasks.
- **Deployment.** Dockerfiles for `web` and `api` and a production compose file are not written.

## Build order

1. Database models + Alembic migrations; persist runs and events.
2. `llm/` factory (Gemini by default) and a real planner agent.
3. `rag/`: ingestion task → Qdrant → hybrid retrieval → RAG agent.
4. `mcp/`: GitHub MCP client → GitHub and code-analysis agents.
5. Analyst, verifier and report agents with citations.
6. Checkpointer, resumable runs, human approval.
7. Auth and workspaces, Langfuse, Ragas, Dockerfiles.

## Running locally

```sh
# backing services (not needed for the current stub pipeline)
docker compose -f infra/docker-compose.yml up -d

# API — http://localhost:8000/docs
cd apps/api
uv sync
uv run fastapi dev src/agentos/main.py

# Web — http://localhost:3000
cd apps/web
pnpm install
pnpm dev
```

Checks: `uv run pytest` and `uv run ruff check .` in `apps/api`; `pnpm lint` and `pnpm build`
in `apps/web`.
