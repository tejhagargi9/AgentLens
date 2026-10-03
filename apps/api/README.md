# AgentOS API

FastAPI backend, LangGraph agent workflow and Celery workers. See [docs/architecture.md](../../docs/architecture.md).

```sh
uv sync
uv run fastapi dev src/agentos/main.py   # http://localhost:8000/docs
uv run pytest
uv run celery -A agentos.workers.celery_app worker --pool=solo   # needs Redis
```
