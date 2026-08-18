# LeetRank

LeetRank turns accepted LeetCode submissions into points on a private friends
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

The frontend requires `frontend/.env.local`. Copy `frontend/.env.example` and
set the Supabase project URL and publishable key. Never place a Supabase secret
key or database password in a `VITE_` environment variable.

## Verification

```bash
backend/.venv/bin/pytest backend/tests -q
cd frontend && npm run build
```
