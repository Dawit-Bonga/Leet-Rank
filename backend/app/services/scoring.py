from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


REVIEW_COOLDOWN = timedelta(days=7)
FIRST_SOLVE_POINTS = {"EASY": 10, "MEDIUM": 20, "HARD": 30}
REVIEW_POINTS = {"EASY": 3, "MEDIUM": 6, "HARD": 10}


class ScoreReason(StrEnum):
    FIRST_SOLVE = "FIRST_SOLVE"
    REVIEW = "REVIEW"
    COOLDOWN = "COOLDOWN"


@dataclass(frozen=True)
class ProblemStatsSnapshot:
    first_solved_at: datetime
    last_solved_at: datetime
    last_rewarded_at: datetime
    rewarded_solve_count: int


@dataclass(frozen=True)
class ScoreDecision:
    points: int
    reason: ScoreReason
    stats: ProblemStatsSnapshot


def calculate_score(
    difficulty: str,
    submitted_at: datetime,
    current_stats: ProblemStatsSnapshot | None,
) -> ScoreDecision:
    normalized_difficulty = difficulty.upper()
    if normalized_difficulty not in FIRST_SOLVE_POINTS:
        raise ValueError(f"Unsupported difficulty: {difficulty}")

    if current_stats is None:
        return ScoreDecision(
            points=FIRST_SOLVE_POINTS[normalized_difficulty],
            reason=ScoreReason.FIRST_SOLVE,
            stats=ProblemStatsSnapshot(
                first_solved_at=submitted_at,
                last_solved_at=submitted_at,
                last_rewarded_at=submitted_at,
                rewarded_solve_count=1,
            ),
        )

    if submitted_at < current_stats.last_solved_at:
        raise ValueError("Submissions must be ingested in chronological order.")

    if submitted_at >= current_stats.last_rewarded_at + REVIEW_COOLDOWN:
        return ScoreDecision(
            points=REVIEW_POINTS[normalized_difficulty],
            reason=ScoreReason.REVIEW,
            stats=ProblemStatsSnapshot(
                first_solved_at=current_stats.first_solved_at,
                last_solved_at=submitted_at,
                last_rewarded_at=submitted_at,
                rewarded_solve_count=current_stats.rewarded_solve_count + 1,
            ),
        )

    return ScoreDecision(
        points=0,
        reason=ScoreReason.COOLDOWN,
        stats=ProblemStatsSnapshot(
            first_solved_at=current_stats.first_solved_at,
            last_solved_at=submitted_at,
            last_rewarded_at=current_stats.last_rewarded_at,
            rewarded_solve_count=current_stats.rewarded_solve_count,
        ),
    )
