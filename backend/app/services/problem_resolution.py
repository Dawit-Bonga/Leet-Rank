from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Problem, UnmappedSubmission
from app.services.leetcode import AcceptedSubmission, ProblemDetails
from app.services.submission_sync import ingest_submission


_SLUG_SANITIZER = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class ProblemLookupResult:
    normalized_slug: str
    problem: Problem | None


def normalize_problem_slug(value: str) -> str:
    lowered = value.strip().lower().replace("_", "-").replace(" ", "-")
    collapsed = re.sub(r"-{2,}", "-", lowered)
    return _SLUG_SANITIZER.sub("", collapsed).strip("-")


def resolve_problem_by_slug(session: Session, raw_slug: str) -> ProblemLookupResult:
    normalized_slug = normalize_problem_slug(raw_slug)
    problem = None
    if normalized_slug:
        problem = session.scalar(select(Problem).where(Problem.leetcode_slug == normalized_slug))
    return ProblemLookupResult(normalized_slug=normalized_slug, problem=problem)


def queue_unmapped_submission(
    session: Session,
    *,
    user_id: uuid.UUID,
    provider: str,
    provider_submission_id: str,
    problem_slug: str,
    problem_title: str,
    submitted_at: datetime,
    metadata: dict[str, str] | None = None,
) -> bool:
    existing = session.scalar(
        select(UnmappedSubmission.id).where(
            UnmappedSubmission.provider == provider,
            UnmappedSubmission.provider_submission_id == provider_submission_id,
        )
    )
    if existing is not None:
        return False

    payload = None if metadata is None else json.dumps(metadata, sort_keys=True)
    session.add(
        UnmappedSubmission(
            user_id=user_id,
            provider=provider,
            provider_submission_id=provider_submission_id,
            problem_slug=problem_slug,
            problem_title=problem_title,
            submitted_at=submitted_at,
            metadata_json=payload,
        )
    )
    session.commit()
    return True


def retry_unmapped_submissions(session: Session, *, limit: int = 100) -> int:
    pending = list(
        session.scalars(
            select(UnmappedSubmission)
            .where(UnmappedSubmission.resolved_at.is_(None))
            .order_by(UnmappedSubmission.created_at.asc())
            .limit(limit)
        )
    )
    resolved_count = 0
    for item in pending:
        lookup = resolve_problem_by_slug(session, item.problem_slug)
        if lookup.problem is None:
            continue

        submission = AcceptedSubmission(
            external_id=item.provider_submission_id,
            problem_slug=lookup.problem.leetcode_slug,
            problem_title=lookup.problem.title,
            submitted_at=item.submitted_at.astimezone(UTC),
        )
        details = ProblemDetails(
            slug=lookup.problem.leetcode_slug,
            title=lookup.problem.title,
            difficulty=lookup.problem.difficulty,
        )
        ingest_submission(
            session,
            user_id=item.user_id,
            submission=submission,
            problem_details=details,
            provider=item.provider,
            provider_submission_id=item.provider_submission_id,
        )
        item.resolved_at = datetime.now(UTC)
        item.last_error = None
        session.commit()
        resolved_count += 1
    return resolved_count
