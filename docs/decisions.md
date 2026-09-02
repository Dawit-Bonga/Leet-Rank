# Decisions

## V1 scoring eligibility

- A user's scoring window starts when their LeetCode username is successfully
  connected to LeetClimb.
- Accepted submissions before `scoring_started_at` are ignored and are not
  stored.
- Previous LeetCode solves do not affect LeetClimb. The first eligible solve of
  a problem is the user's first LeetClimb solve.
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
- LeetCode and GitHub/NeetCode submissions share the same per-user/problem
  scoring history. A provider does not create a second first-solve opportunity.
- Activity retains the submission provider so users can see where each scored
  event originated.
- If a provider discovers an older submission after a newer event was ingested,
  the affected user/problem ledger is rebuilt from stored submissions in
  timestamp order so cooldown decisions remain deterministic.

## V1 leaderboard periods

- `week` is a rolling seven-day window.
- `month` is a rolling thirty-day window.
- `all` contains every LeetClimb score event since signup.
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
- Synchronization is backend-controlled; users cannot manually trigger it.
- A scheduled command processes accounts due for synchronization in batches.
  New accounts are immediately due, then each account becomes due 15 minutes
  after its last attempt.
- Each synchronization requests at most the latest 20 accepted submissions and
  uses their real LeetCode submission IDs for deduplication.
- Optional NeetCode synchronization reads GitHub auto-commit repositories with
  a backend-only token. After the initial scan, it uses the newest stored or
  queued GitHub event as an incremental timestamp with a small overlap.
- One user's failure does not stop the remaining batch. A `RUNNING` state older
  than 30 minutes is treated as abandoned and recovered by the next job.
- LeetClimb tables are not a browser-facing Supabase Data API. Row Level
  Security is enabled without client policies, and the `anon` and
  `authenticated` roles have no direct table privileges. All application data
  access goes through FastAPI.

## V1 authentication

- Supabase Auth owns signup, login, email confirmation, sessions, and access
  tokens. LeetClimb does not store passwords.
- Password recovery stays entirely within Supabase Auth. Reset links return to
  the public frontend `/reset-password` route, and the recovery session is
  signed out after the password is changed.
- FastAPI validates each bearer token with the Supabase Auth user endpoint
  before trusting its user ID.
- The verified Supabase user ID maps to the unique `users.auth_user_id` column.
- User-owned operations use `/users/me`; the caller cannot choose the acting
  user by putting a LeetClimb user ID in the URL.
- An authenticated account without a linked profile may only complete
  onboarding. Other private endpoints return `onboarding_required`.
- `GET /users/me` is the frontend session-bootstrap endpoint. It returns
  `profile: null` with HTTP 200 when the authenticated account still needs
  onboarding, and the full LeetClimb profile after onboarding.
- The public LeetCode submissions lookup remains independent of LeetClimb
  identity because it only reads public LeetCode data.

## V1 onboarding

- Scoring starts only after the submitted LeetCode username is validated.
- Onboarding records one primary goal, experience level, and weekly problem
  goal. These fields personalize the product but do not change scoring.
- A validated username is normalized to lowercase and can belong to only one
  LeetClimb user.
- Username validation proves that the LeetCode account exists, not that the
  LeetClimb user owns it. Ownership verification is deferred beyond V1.
- Onboarding uses authenticated `POST /users/me/onboarding` and permanently
  links the new profile to that Supabase Auth account.

## V1 friendships

- Every user chooses a unique LeetClimb username during onboarding. Usernames
  are case-insensitive and stored in lowercase.
- Friend requests use exact LeetClimb usernames, not LeetCode or LinkedIn names.
- Authenticated users can search by LeetClimb username prefix. Results are
  limited to ten public summaries and include relationship state so the
  frontend never needs to guess whether a request can be sent.
- A friendship exists only after the recipient accepts the request.
- Accepted friendships are stored in both directions to keep friend and future
  friends-only leaderboard reads simple.
- Either participant can remove an accepted friendship. The sender can cancel
  a pending request and the recipient can decline it.
- Each account can have at most 20 accepted friends. Pending requests do not
  count toward the limit; acceptance fails if either participant is full.
- Accepted friends can open a limited performance profile containing public
  identity, scoring totals, weekly goal progress data, and recent activity.
  Authentication details, onboarding answers, sync errors, and the user's
  broader friends list are not exposed.
- Removing a friendship immediately removes profile access in both directions.

## V1 profile settings

- Users can update their display name, primary goal, experience level, and
  weekly problem goal.
- LeetClimb usernames remain stable because friends use them for discovery.
- Connected LeetCode usernames remain stable because they define scoring
  identity and history. Reconnection requires a separate future workflow.
- Email and password changes remain owned by Supabase Auth.

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
Easy: 10, 3 on review
Medium: 20, 6 on review
Hard: 30, 10 on review
