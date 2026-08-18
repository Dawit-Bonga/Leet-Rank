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
- Personal score responses return all three totals with a server-generated
  `as_of` timestamp and the start of each period.
- Activity is read from `score_events` newest-first. Zero-point cooldown events
  remain visible so users can understand why a submission earned no points.
- A friends leaderboard contains the requesting user and every accepted friend,
  including participants with zero points.
- Ties share competition rank (`1, 1, 3`) and username provides stable display
  ordering within a tie.
- The response uses one `as_of` timestamp for every participant. It is computed
  from stored score events and is not persisted separately.

## V1 infrastructure

- FastAPI and the synchronization process share one application codebase.
- PostgreSQL is the application source of truth.
- No Redis, task queue, or precomputed leaderboard is needed for V1.
- Direct LeetCode GraphQL responses are normalized behind the LeetCode service
  so upstream query changes do not affect scoring code.
- Public synchronization requests at most the latest 20 accepted submissions
  and uses their real LeetCode submission IDs for deduplication.

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

## V1 friendships

- Every user chooses a unique LeetRank username during onboarding. Usernames
  are case-insensitive and stored in lowercase.
- Friend requests use exact LeetRank usernames, not LeetCode or LinkedIn names.
- A friendship exists only after the recipient accepts the request.
- Accepted friendships are stored in both directions to keep friend and future
  friends-only leaderboard reads simple.
- Either participant can remove an accepted friendship. The sender can cancel
  a pending request and the recipient can decline it.
- Each account can have at most 20 accepted friends. Pending requests do not
  count toward the limit; acceptance fails if either participant is full.
- V1 development endpoints still identify the acting user by URL ID. Supabase
  authentication must replace that trust boundary before public deployment.

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
