# Flood Response System

A full-stack starter for flood risk assessment and emergency response planning.

## Run & Operate

- `cd backend && uvicorn app.main:app --reload --port 8000` — run the FastAPI service locally
- `cd frontend && npm run dev` — run the React frontend locally (port 5173)
- `docker compose up --build` — run frontend, backend, and PostgreSQL together
- Replit workflow `Flood Response Dashboard` — starts FastAPI on port 8000 and the Vite dashboard on port 5173
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: FastAPI, Pydantic, SQLAlchemy
- DB: PostgreSQL in Compose, SQLite by default for local backend development
- Frontend: React, Vite, Tailwind CSS, Leaflet, Recharts
- Data: JSON fixtures in `data/`
- ML: Python starter entry points in `ml/`

## Where things live

- `backend/` — FastAPI app, SQLAlchemy engine, Dockerfile, and Python dependencies
- `frontend/` — React + Vite + Tailwind app, Dockerfile, and Nginx proxy
- `data/` — sample villages, roads, hospitals, and shelters JSON datasets
- `ml/` — placeholder risk prediction and response optimization scripts
- `docker-compose.yml` — local three-service stack

## Architecture decisions

- The backend defaults to SQLite when `DATABASE_URL` is not set, making local development lightweight.
- Docker Compose switches the backend to PostgreSQL and waits for the database health check.
- The frontend uses `/health` as a same-origin request; Vite proxies it locally and Nginx proxies it in Compose.
- Raw risk and response priority are separate rankings; priority adds impact, access, vulnerability, and hospital proximity.

## Product

The app provides sample-data risk and response-priority rankings through the
FastAPI backend, plus a non-persistent what-if simulator at `POST /api/simulate`
for rainfall scaling and road closures. The React dashboard compares baseline
and simulated priority order and evacuation route side by side.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
