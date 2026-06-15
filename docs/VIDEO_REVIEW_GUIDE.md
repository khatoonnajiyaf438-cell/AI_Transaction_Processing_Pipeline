# 3-Minute Technical Review Guide

## 0:00-1:00 System Design and Data Flow

Show a simple diagram with: Browser/API client -> FastAPI -> PostgreSQL job row -> Redis queue -> Celery worker -> PostgreSQL results -> polling endpoints.

Explain that the request path stays short because the heavy CSV, anomaly, and LLM work runs asynchronously.

## 1:00-2:15 Bottlenecks

Call out disk I/O for uploads, database connection limits, worker CPU/memory for large CSVs, Redis queue depth, and external LLM rate limits.

## 2:15-3:00 Production Iteration

Recommend S3-compatible object storage, Alembic migrations, worker autoscaling, chunked CSV streaming, queue partitioning, idempotency keys, OpenTelemetry, LLM caching, and stricter auth/rate limiting.
