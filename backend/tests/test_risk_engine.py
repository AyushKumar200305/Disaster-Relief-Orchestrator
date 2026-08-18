import pytest

from backend.risk_engine import load_villages, score_villages


@pytest.fixture()
def sample_scores():
    return {village.id: village for village in score_villages(load_villages())}


def test_riverbend_hand_calculated_score(sample_scores):
    village = sample_scores["village-001"]

    # Rain 100, river level 100, elevation 100, proximity 100,
    # population density 2250/2950*100, road access 100.
    expected_score = 25 + 25 + 15 + 15 + (2250 / 2950 * 10) + 10

    assert village.risk_score == pytest.approx(expected_score, abs=0.01)
    assert village.risk_bucket == "CRITICAL"


def test_mangalpur_hand_calculated_score(sample_scores):
    village = sample_scores["village-002"]

    # Rain 60, river level 60, elevation 50, proximity 9/11*100,
    # population density 650/2950*100, road access 50.
    expected_score = (
        60 * 0.25
        + 60 * 0.25
        + 50 * 0.15
        + (9 / 11 * 100) * 0.15
        + (650 / 2950 * 100) * 0.10
        + 50 * 0.10
    )

    assert village.risk_score == pytest.approx(expected_score, abs=0.01)
    assert village.risk_bucket == "MEDIUM"


def test_low_risk_village_scores_zero(sample_scores):
    village = sample_scores["village-007"]

    assert village.risk_score == 0
    assert village.risk_bucket == "LOW"


def test_results_are_ranked_highest_first():
    scores = score_villages(load_villages())

    assert len(scores) == 10
    assert scores == sorted(scores, key=lambda village: village.risk_score, reverse=True)
    assert scores[0].id == "village-001"