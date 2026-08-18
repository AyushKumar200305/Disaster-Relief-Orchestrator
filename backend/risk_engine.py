"""Transparent, dataset-relative flood risk scoring."""

import json
from pathlib import Path
from typing import Literal, TypedDict

from pydantic import BaseModel, Field


Elevation = Literal["low", "medium", "high"]
RoadStatus = Literal["open", "blocked", "slow"]

WEIGHTS = {
    "rainfall": 0.25,
    "river_level": 0.25,
    "elevation": 0.15,
    "river_proximity": 0.15,
    "population_density": 0.10,
    "road_accessibility": 0.10,
}

ELEVATION_RISK = {"low": 100.0, "medium": 50.0, "high": 0.0}
ROAD_ACCESS_RISK = {"open": 0.0, "slow": 50.0, "blocked": 100.0}
VILLAGES_PATH = Path(__file__).resolve().parents[1] / "data" / "villages.json"


class VillageRecord(BaseModel):
    """Input shape for a village in the sample dataset."""

    id: str
    name: str
    district: str
    population: int = Field(gt=0)
    area_km2: float = Field(gt=0)
    rainfall_mm: float = Field(ge=0)
    river_level: float = Field(ge=0)
    river_distance_km: float = Field(ge=0)
    elevation: Elevation
    road_status: RoadStatus
    latitude: float | None = None
    longitude: float | None = None


class NormalizedFactors(BaseModel):
    """All scoring inputs after conversion to a 0–100 risk scale."""

    rainfall: float
    river_level: float
    elevation: float
    river_proximity: float
    population_density: float
    road_accessibility: float


class VillageRisk(VillageRecord):
    """Village data enriched with its score and severity bucket."""

    population_density: float
    normalized_factors: NormalizedFactors
    risk_score: float
    risk_bucket: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class _ScoringRecord(TypedDict):
    village: VillageRecord
    population_density: float


def _normalize(value: float, minimum: float, maximum: float, *, inverse: bool = False) -> float:
    """Normalize a value to 0–100, optionally reversing its direction."""

    if maximum == minimum:
        return 0.0
    normalized = (value - minimum) / (maximum - minimum) * 100
    if inverse:
        normalized = 100 - normalized
    return max(0.0, min(100.0, normalized))


def _bucket_for_score(score: float) -> Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    """Apply the documented inclusive lower-bucket boundaries."""

    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


def load_villages(path: Path = VILLAGES_PATH) -> list[VillageRecord]:
    """Load and validate village records from JSON."""

    with path.open(encoding="utf-8") as dataset_file:
        raw_villages = json.load(dataset_file)
    return [VillageRecord.model_validate(village) for village in raw_villages]


def score_villages(villages: list[VillageRecord | dict]) -> list[VillageRisk]:
    """Score and rank villages using relative normalization across the input set."""

    records = [
        village if isinstance(village, VillageRecord) else VillageRecord.model_validate(village)
        for village in villages
    ]
    if not records:
        return []

    densities = [village.population / village.area_km2 for village in records]
    scoring_records = [
        {"village": village, "population_density": density}
        for village, density in zip(records, densities, strict=True)
    ]

    rainfall_values = [record["village"].rainfall_mm for record in scoring_records]
    river_level_values = [record["village"].river_level for record in scoring_records]
    river_distance_values = [record["village"].river_distance_km for record in scoring_records]

    results: list[VillageRisk] = []
    for record in scoring_records:
        village = record["village"]
        density = record["population_density"]
        factors = NormalizedFactors(
            rainfall=_normalize(village.rainfall_mm, min(rainfall_values), max(rainfall_values)),
            river_level=_normalize(village.river_level, min(river_level_values), max(river_level_values)),
            elevation=ELEVATION_RISK[village.elevation],
            river_proximity=_normalize(
                village.river_distance_km,
                min(river_distance_values),
                max(river_distance_values),
                inverse=True,
            ),
            population_density=_normalize(density, min(densities), max(densities)),
            road_accessibility=ROAD_ACCESS_RISK[village.road_status],
        )
        score = sum(
            (
                factors.rainfall * WEIGHTS["rainfall"],
                factors.river_level * WEIGHTS["river_level"],
                factors.elevation * WEIGHTS["elevation"],
                factors.river_proximity * WEIGHTS["river_proximity"],
                factors.population_density * WEIGHTS["population_density"],
                factors.road_accessibility * WEIGHTS["road_accessibility"],
            )
        )
        results.append(
            VillageRisk(
                **village.model_dump(),
                population_density=round(density, 2),
                normalized_factors=factors,
                risk_score=round(score, 2),
                risk_bucket=_bucket_for_score(score),
            )
        )

    return sorted(results, key=lambda village: (-village.risk_score, village.id))