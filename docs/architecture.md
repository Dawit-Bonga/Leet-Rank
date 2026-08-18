# V1 Architecture

Normal reads use the application database:

```text
React -> FastAPI -> PostgreSQL / Supabase
```

LeetCode synchronization is a separate write path:

```text
manual refresh / scheduler
    -> submission sync service
    -> Alfa LeetCode API
    -> PostgreSQL
```

The API returns stored data without waiting for LeetCode. A new accepted
submission is normalized, checked against the user's scoring start, and then
stored and scored in one database transaction. Unique database constraints
make ingestion safe to retry.

The V1 backend remains a single FastAPI application with a simple scheduled
entry point added after manual synchronization is proven. Redis, distributed
queues, microservices, and leaderboard caches are intentionally excluded.
