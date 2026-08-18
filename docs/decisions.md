# Decisions

## V1 scoring eligibility

- A user's scoring window starts when their LeetCode username is successfully
  connected to LeetRank.
- Accepted submissions before `scoring_started_at` are ignored and are not
  stored.
- Previous LeetCode solves do not affect LeetRank. The first eligible solve of
  a problem is the user's first LeetRank solve.
- Submission time, rather than synchronization time, determines when points
  were earned.
- All timestamps are stored and compared in UTC.

## V1 scoring policy

| Difficulty | First solve | Eligible review |
| --- | ---: | ---: |
| Easy | 10 | 3 |
| Medium | 20 | 6 |
| Hard | 30 | 10 |

- Reviews become eligible seven days after the last rewarded submission.
- A submission exactly at the cooldown boundary is eligible.
- Repeats inside the cooldown create a zero-point `COOLDOWN` score event so
  scoring decisions remain auditable.
- Scoring occurs once, transactionally, when an eligible accepted submission
  is first ingested.

## V1 leaderboard periods

- `week` is a rolling seven-day window.
- `month` is a rolling thirty-day window.
- `all` contains every LeetRank score event since signup.
- Leaderboards aggregate stored score events and never recalculate scores.

## V1 infrastructure

- FastAPI and the synchronization process share one application codebase.
- PostgreSQL is the application source of truth.
- No Redis, task queue, or precomputed leaderboard is needed for V1.
- Alfa LeetCode API responses are normalized behind the LeetCode service so
  the provider can be replaced without changing scoring code.

## V1 onboarding

- Scoring starts only after the submitted LeetCode username is validated.
- Onboarding records one primary goal, experience level, and weekly problem
  goal. These fields personalize the product but do not change scoring.
- A validated username is normalized to lowercase and can belong to only one
  LeetRank user.
- Username validation proves that the LeetCode account exists, not that the
  LeetRank user owns it. Ownership verification is deferred beyond V1.
- Until Supabase authentication is connected, development uses `POST /users`.
  It will later become the authenticated `POST /users/me/onboarding` flow.

# Product Rules
Scoring begins when a LeetCode username is successfully connected.
Previous LeetCode activity is ignored.
Only accepted submissions count.
Submission time determines leaderboard placement.
The first post-connection solve of a problem receives full points.
Repeats inside the cooldown receive zero points.
Eligible repeats receive reduced review points.
Past week means a rolling 7-day window.
Past month means a rolling 30-day window.
All time means since connecting LeetCode.
All timestamps use UTC.

# Scoring Defaults
Easy : 5, 3 on review
Medium: 10, 6 on review
Hard: 20, 10 on Review
