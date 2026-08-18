"""Transparent flood risk and emergency priority scoring."""

import json
import math
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

PRIORITY_WEIGHTS = {
    "risk_score": 0.40,
    "population_risk": 0.25,
    "vulnerability": 0.15,
    "road_difficulty": 0.10,
    "medical_need": 0.10,
}

ELEVATION_RISK = {"low": 100.0, "medium": 50.0, "high": 0.0}
ROAD_ACCESS_RISK = {"open": 0.0, "slow": 50.0, "blocked": 100.0}
VILLAGES_PATH = Path(__file__).resolve().parents[1] / "data" / "villages.json"
HOSPITALS_PATH = Path(__file__).resolve().parents[1] / "data" / "hospitals.json"


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
    elderly_pct: float | None = Field(default=None, ge=0, le=100)
    children_pct: float | None = Field(default=None, ge=0, le=100)


class HospitalRecord(BaseModel):
    """Hospital location and capacity used by the priority model."""

    id: str
    name: str
    lat: float
    lng: float
    bed_capacity: int = Field(gt=0)


class NormalizedFactors(BaseModel):
    """All raw risk inputs after conversion to a 0–100 risk scale."""

    rainfall: float
    river_level: float
    elevation: float
    river_proximity: float
    population_density: float
    road_accessibility: float


class PriorityFactors(BaseModel):
    """All impact and response inputs after conversion to a 0–100 scale."""

    population_risk: float
    vulnerability: float
    road_difficulty: float
    medical_need: float


class VillageRisk(VillageRecord):
    """Village data enriched with its raw hazard score and severity bucket."""

    population_density: float
    normalized_factors: NormalizedFactors
    risk_score: float
    risk_bucket: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class VillagePriority(VillageRisk):
    """Village data enriched with impact-aware response priority."""

    nearest_hospital_name: str
    nearest_hospital_distance_km: float
    priority_factors: PriorityFactors
    priority_score: float


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


def load_hospitals(path: Path = HOSPITALS_PATH) -> list[HospitalRecord]:
    """Load and validate hospital records from JSON."""

    with path.open(encoding="utf-8") as dataset_file:
        raw_hospitals = json.load(dataset_file)
    return [HospitalRecord.model_validate(hospital) for hospital in raw_hospitals]


def score_villages(villages: list[VillageRecord | dict]) -> list[VillageRisk]:
    """Score and rank villages using relative normalization across the input set."""

    records = [
        village if isinstance(village, VillageRecord) else VillageRecord.model_validate(village)
        for village in villages
    ]
    if not records:
        return []

    densities = [village.population / village.area_km2 for village in records]
    scoring_records: list[_ScoringRecord] = [
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


def _haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two latitude/longitude pairs."""

    earth_radius_km = 6371.0
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    return earth_radius_km * 2 * math.asin(math.sqrt(haversine))


def score_priority(
    villages: list[VillageRecord | dict],
    hospitals: list[HospitalRecord | dict],
) -> list[VillagePriority]:
    """Rank villages by hazard, population impact, vulnerability, access, and care need."""

    risk_scores = score_villages(villages)
    hospital_records = [
        hospital if isinstance(hospital, HospitalRecord) else HospitalRecord.model_validate(hospital)
        for hospital in hospitals
    ]
    if not hospital_records:
        raise ValueError("At least one hospital is required to calculate priority.")

    populations = [village.population for village in risk_scores]
    density_values = [village.population_density for village in risk_scores]
    nearest_distances: dict[str, tuple[HospitalRecord, float]] = {}
    for village in risk_scores:
        if village.latitude is None or village.longitude is None:
            raise ValueError(f"Village {village.id} is missing coordinates.")
        nearest_distances[village.id] = min(
            (
                (
                    hospital,
                    _haversine_distance_km(
                        village.latitude,
                        village.longitude,
                        hospital.lat,
                        hospital.lng,
                    ),
                )
                for hospital in hospital_records
            ),
            key=lambda item: item[1],
        )

    distance_values = [distance for _, distance in nearest_distances.values()]
    results: list[VillagePriority] = []
    for village in risk_scores:
        nearest_hospital, nearest_distance = nearest_distances[village.id]
        population_normalized = _normalize(village.population, min(populations), max(populations))
        population_risk = population_normalized * (village.risk_score / 100)
        if village.elderly_pct is not None or village.children_pct is not None:
            vulnerability = min(100.0, (village.elderly_pct or 0) + (village.children_pct or 0))
        else:
            vulnerability = _normalize(village.population_density, min(density_values), max(density_values))
        priority_factors = PriorityFactors(
            population_risk=population_risk,
            vulnerability=vulnerability,
            road_difficulty=ROAD_ACCESS_RISK[village.road_status],
            medical_need=_normalize(
                nearest_distance,
                min(distance_values),
                max(distance_values),
            ),
        )
        # Risk ranking measures hazard severity; priority can differ because response
        # planning also favors larger, more vulnerable, less accessible populations.
        priority_score = sum(
            (
                village.risk_score * PRIORITY_WEIGHTS["risk_score"],
                priority_factors.population_risk * PRIORITY_WEIGHTS["population_risk"],
                priority_factors.vulnerability * PRIORITY_WEIGHTS["vulnerability"],
                priority_factors.road_difficulty * PRIORITY_WEIGHTS["road_difficulty"],
                priority_factors.medical_need * PRIORITY_WEIGHTS["medical_need"],
            )
        )
        results.append(
            VillagePriority(
                **village.model_dump(),
                nearest_hospital_name=nearest_hospital.name,
                nearest_hospital_distance_km=round(nearest_distance, 2),
                priority_factors=priority_factors,
                priority_score=round(priority_score, 2),
            )
        )

    return sorted(results, key=lambda village: (-village.priority_score, village.id))