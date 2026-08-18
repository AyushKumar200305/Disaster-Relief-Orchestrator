# Flood Response System backend

FastAPI service with Pydantic, SQLAlchemy, and PostgreSQL support.

## Local development

```bash
cd flood-response-system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Without `DATABASE_URL`, SQLAlchemy uses a local SQLite file at
`backend/flood_response.db`. Set `DATABASE_URL` to a PostgreSQL connection
string when using the Compose stack.

Endpoints:

- `GET /health` — service health
- `GET /health/database` — database connectivity check
- `GET /api/risk` — all sample villages ranked by flood risk
- `GET /api/priority` — all sample villages ranked by impact-aware response priority

Run the scoring tests from the project root with `pytest backend/tests`.