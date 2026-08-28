# Project

LeetClimb is a competitive LeetCode accountability app where users
earn points from accepted LeetCode submissions and compete with friends.

## Stack

Frontend:
- React
- TypeScript
- Vite
- Tailwind

Backend:
- Python
- FastAPI

Database:
- PostgreSQL through Supabase

## Architecture

The application database is the source of truth for reads.

Normal application reads should follow:

React -> FastAPI -> PostgreSQL

LeetCode synchronization is separate from normal application reads:

Scheduler / refresh request -> submission sync service -> LeetCode -> PostgreSQL

Do not make frontend/profile requests depend directly on LeetCode being available.

### Core backend concepts

- `users` stores application users.
- `friendships` stores friendships as two directed rows.
- `problems` stores LeetCode problem metadata.
- `submissions` stores raw LeetCode submissions.
- `user_problem_stats` stores per-user/per-problem state used by scoring.
- `score_events` is the points ledger.
- `user_sync_state` tracks LeetCode synchronization state.

See `architecture.md` for detailed system design.

## Scoring Rules

Scoring happens when a new submission is ingested.

Do not recalculate submission scores when reading the leaderboard.

The scoring service should determine whether a submission is:
- a first solve
- an eligible review
- a repeat within the cooldown period

Score changes should be represented through `score_events`.

Keep scoring rules centralized so they can be changed without modifying
API routes or LeetCode integration code.

## Leaderboard

The V1 leaderboard is calculated from PostgreSQL when requested.

Use database aggregation and ordering rather than sorting leaderboard
data in application code.

Do not introduce Redis, leaderboard caches, or precomputed leaderboard
tables unless there is a demonstrated need.

## LeetCode Synchronization

LeetCode calls must live behind a dedicated service.

Users may be refreshed through:
- periodic polling
- a stale-data refresh triggered when a user opens their own profile

Opening a profile should return database data without waiting for
LeetCode.

Avoid starting multiple simultaneous syncs for the same user.

Use LeetCode submission IDs for submission deduplication.

## Database Rules

- Prefer PostgreSQL constraints over application-only guarantees.
- Foreign keys should be used for relationships.
- Use unique constraints where duplicate records would be invalid.
- Add indexes based on actual query access patterns.
- Avoid denormalization unless there is a demonstrated performance need.
- Database migrations should be explicit and reviewable.

## Engineering Rules

- Do not introduce new dependencies without explaining why.
- Prefer simple implementations over premature abstractions.
- Backend business logic should not live in API route handlers.
- External LeetCode calls should live behind a dedicated service.
- Keep scoring logic separate from submission fetching.
- Add tests for backend business logic.
- Do not modify unrelated files.
- Avoid speculative infrastructure such as Redis, Kafka, or additional
  services unless the current requirements justify them.
- Explain architectural decisions before making large changes.

## Learning Rule

When implementing something nontrivial:

1. Explain the proposed approach.
2. Identify the files that need changing.
3. Explain relevant database/schema changes.
4. Let me approve or understand the architecture.
5. Then implement.

Do not skip directly to implementation for significant architectural
changes.