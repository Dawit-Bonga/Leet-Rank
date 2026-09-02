# LeetClimb

LeetClimb turns accepted LeetCode submissions into points on a private friends
leaderboard.

## Local development

Start the FastAPI backend:

```bash
set -a
source backend/.env
set +a

backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload
```

In a second terminal, start the React frontend:

```bash
cd frontend
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

The backend exposes an unauthenticated liveness check at
`GET http://127.0.0.1:8000/health` for local and production monitoring.

Run all accounts that are due for automatic LeetCode synchronization:

```bash
set -a
source backend/.env
set +a

cd backend
.venv/bin/python -m app.jobs.sync_due_users
```

New accounts are due immediately. After a run, an account is not selected again
for 15 minutes. Production scheduling will invoke the same command every 15
minutes; users do not trigger synchronization from the application.

Users may optionally connect a NeetCode auto-commit GitHub repository from
settings. The scheduler reads `GITHUB_TOKEN` from the cron job environment.
The token stays on the backend and needs read access to connected repositories.
Public repositories are recommended for V1; private repositories must be
explicitly accessible to the token. After the initial scan, synchronization
requests only commits newer than the latest stored or queued GitHub event.

NeetCode sometimes uses a different problem slug than LeetCode. Confirmed
differences are mapped in `backend/app/services/problem_resolution.py`.
Unrecognized slugs remain safely queued in `unmapped_submissions` and are
retried by later synchronization runs. Review unresolved slugs with:

```sql
SELECT
    problem_slug,
    COUNT(*) AS submission_count,
    COUNT(DISTINCT user_id) AS affected_users,
    MIN(submitted_at) AS first_seen_at,
    MAX(submitted_at) AS last_seen_at,
    MAX(last_error) AS latest_error
FROM unmapped_submissions
WHERE resolved_at IS NULL
GROUP BY problem_slug
ORDER BY affected_users DESC, submission_count DESC;
```

The frontend requires `frontend/.env.local`. Copy `frontend/.env.example` and
set the Supabase project URL and publishable key. Never place a Supabase secret
key or database password in a `VITE_` environment variable.

## Supabase Auth URLs

In Supabase, open **Authentication → URL Configuration**. For local
development, add this exact Redirect URL:

```text
http://localhost:5173/reset-password
```

Set the production Site URL to the deployed frontend origin and add the
equivalent production reset URL, for example:

```text
https://app.example.com/reset-password
```

For shared profiles and authentication return routes, also allow the deployed
frontend wildcard, for example `https://app.example.com/**`.

Password recovery emails redirect to this public frontend route. Production
deployments must also serve the Vite application for direct requests to
`/reset-password`.

## Verification

```bash
backend/.venv/bin/pytest backend/tests -q
cd frontend && npm run build
```
