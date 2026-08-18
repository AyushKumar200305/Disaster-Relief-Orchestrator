"""FastAPI application entry point for the Flood Response System."""

import os
from collections.abc import Generator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.risk_engine import (
    RouteSummary,
    VillagePriority,
    VillageRisk,
    load_hospitals,
    load_roads,
    load_villages,
    plan_route,
    score_priority,
    score_villages,
)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./flood_response.db")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

engine_kwargs: dict[str, Any] = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({"pool_pre_ping": True, "pool_recycle": 300})

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(
    title="Flood Response System API",
    version="0.1.0",
    description="Starter API for flood risk and emergency response planning.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    """Scenario overrides accepted by the what-if dashboard."""

    rainfall_percent: float = Field(default=100, ge=0, le=300)
    blocked_road_id: str | None = None


class SimulationSnapshot(BaseModel):
    """One side of a before/after simulation response."""

    priority: list[VillagePriority]
    route: RouteSummary


class SimulationChanges(BaseModel):
    """Small summary used to highlight meaningful scenario differences."""

    priority_order_changed: bool
    route_changed: bool
    rainfall_percent: float
    blocked_road_id: str | None


class SimulationResponse(BaseModel):
    """Baseline and simulated decision outputs."""

    baseline: SimulationSnapshot
    simulated: SimulationSnapshot
    changes: SimulationChanges


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for future route handlers."""

    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight service health response."""

    return {"status": "ok", "service": "flood-response-backend"}


@app.get("/health/database")
def database_health() -> dict[str, str]:
    """Check that SQLAlchemy can reach the configured database."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/api/risk", response_model=list[VillageRisk])
def risk_scores() -> list[VillageRisk]:
    """Return all sample villages ranked from highest to lowest flood risk."""

    return score_villages(load_villages())


@app.get("/api/priority", response_model=list[VillagePriority])
def priority_scores() -> list[VillagePriority]:
    """Return all sample villages ranked by response priority."""

    return score_priority(load_villages(), load_hospitals())


@app.get("/api/roads")
def roads() -> list[dict[str, object]]:
    """Return roads available for scenario closures."""

    return [road.model_dump() for road in load_roads()]


@app.post("/api/simulate", response_model=SimulationResponse)
def simulate(request: SimulationRequest) -> SimulationResponse:
    """Re-run risk, priority, and route planning against non-persistent overrides."""

    original_villages = load_villages()
    hospitals = load_hospitals()
    roads = load_roads()

    baseline_priority = score_priority(original_villages, hospitals)
    baseline_route = plan_route(original_villages, hospitals, roads)

    known_road_ids = {road.id for road in roads}
    if request.blocked_road_id is not None and request.blocked_road_id not in known_road_ids:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Unknown road_id")

    rainfall_multiplier = request.rainfall_percent / 100
    impacted_village_ids = {
        endpoint
        for road in roads
        if road.id == request.blocked_road_id
        for endpoint in road.connects
    }
    simulated_villages = []
    for village in original_villages:
        updates: dict[str, object] = {
            "rainfall_mm": village.rainfall_mm * rainfall_multiplier,
        }
        if village.id in impacted_village_ids:
            updates["road_status"] = "blocked"
        simulated_villages.append(village.model_copy(update=updates))

    simulated_priority = score_priority(simulated_villages, hospitals)
    simulated_route = plan_route(
        simulated_villages,
        hospitals,
        roads,
        blocked_road_id=request.blocked_road_id,
    )
    baseline_order = [village.id for village in baseline_priority]
    simulated_order = [village.id for village in simulated_priority]

    def route_signature(route: RouteSummary) -> tuple[object, ...]:
        return (
            route.status,
            tuple((road.id, road.blocked) for road in route.roads),
            route.total_distance_km,
        )

    return SimulationResponse(
        baseline=SimulationSnapshot(priority=baseline_priority, route=baseline_route),
        simulated=SimulationSnapshot(priority=simulated_priority, route=simulated_route),
        changes=SimulationChanges(
            priority_order_changed=baseline_order != simulated_order,
            route_changed=route_signature(baseline_route) != route_signature(simulated_route),
            rainfall_percent=request.rainfall_percent,
            blocked_road_id=request.blocked_road_id,
        ),
    )