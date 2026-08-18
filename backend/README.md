# Flood Response System backend

FastAPI service with Pydantic, SQLAlchemy, and PostgreSQL support.

## Local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Without `DATABASE_URL`, SQLAlchemy uses a local SQLite file at
`backend/flood_response.db`. Set `DATABASE_URL` to a PostgreSQL connection
string when using the Compose stack.

Endpoints:

- `GET /health` — service health
- `GET /health/database` — database connectivity check