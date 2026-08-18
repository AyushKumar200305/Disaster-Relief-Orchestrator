"""FastAPI application entry point for the Flood Response System."""

import os
from collections.abc import Generator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.risk_engine import VillageRisk, load_villages, score_villages


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