from datetime import UTC, datetime, timedelta

import pytest

from app.services.scoring import ProblemStatsSnapshot, ScoreReason, calculate_score


SOLVE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("difficulty", "points"),
    [("EASY", 10), ("MEDIUM", 20), ("HARD", 30)],
)
def test_first_solve_points(difficulty, points):
    decision = calculate_score(difficulty, SOLVE_TIME, None)

    assert decision.points == points
    assert decision.reason is ScoreReason.FIRST_SOLVE
    assert decision.stats.rewarded_solve_count == 1


def test_repeat_inside_cooldown_is_recorded_without_points():
    stats = ProblemStatsSnapshot(SOLVE_TIME, SOLVE_TIME, SOLVE_TIME, 1)

    decision = calculate_score("MEDIUM", SOLVE_TIME + timedelta(days=6), stats)

    assert decision.points == 0
    assert decision.reason is ScoreReason.COOLDOWN
    assert decision.stats.last_rewarded_at == SOLVE_TIME


def test_repeat_at_cooldown_boundary_receives_review_points():
    stats = ProblemStatsSnapshot(SOLVE_TIME, SOLVE_TIME, SOLVE_TIME, 1)

    decision = calculate_score("MEDIUM", SOLVE_TIME + timedelta(days=7), stats)

    assert decision.points == 6
    assert decision.reason is ScoreReason.REVIEW
    assert decision.stats.rewarded_solve_count == 2


def test_out_of_order_submission_is_rejected():
    stats = ProblemStatsSnapshot(SOLVE_TIME, SOLVE_TIME, SOLVE_TIME, 1)

    with pytest.raises(ValueError, match="chronological"):
        calculate_score("EASY", SOLVE_TIME - timedelta(seconds=1), stats)


def test_unknown_difficulty_is_rejected():
    with pytest.raises(ValueError, match="Unsupported difficulty"):
        calculate_score("UNKNOWN", SOLVE_TIME, None)
