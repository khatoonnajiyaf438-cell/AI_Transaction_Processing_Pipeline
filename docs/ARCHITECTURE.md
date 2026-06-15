# Architecture

## Components

- `FastAPI` serves the REST API and the browser UI.
- `PostgreSQL` stores jobs, cleaned transactions, anomaly flags, and summaries.
- `Redis` acts as the Celery broker and result backend.
- `Celery worker` runs the CSV pipeline outside the request path.
- `LLMClient` supports Gemini, OpenAI, Ollama, and a deterministic heuristic fallback for no-key local runs.

## Data Flow

1. User uploads a CSV with `POST /api/v1/jobs/upload`.
2. API validates the extension and size, stores the file, inserts a `pending` job, and enqueues Celery.
3. Worker marks the job `processing`, validates the CSV schema, and removes exact duplicate rows.
4. Worker normalises dates, amounts, statuses, currencies, and missing categories.
5. Worker detects statistical and currency/merchant anomalies.
6. Worker classifies missing categories in a batch through `LLMClient`.
7. Worker creates one narrative summary call, persists results, and marks the job `completed`.
8. UI or API clients poll `/status` and fetch `/results`.

## Scaling Notes

At 100x traffic, the first pressure points are upload disk I/O, API database pool size, worker concurrency, Redis queue memory, and LLM provider rate limits. A production-scale version should use object storage for uploads, database migrations and tuned pools, horizontally scaled workers on dedicated queues, request idempotency keys, backpressure, structured observability, and provider-specific LLM rate limiting.
