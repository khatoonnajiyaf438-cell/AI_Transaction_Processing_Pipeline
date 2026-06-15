# API Documentation

Base URL: `http://localhost:8000/api/v1`

Interactive OpenAPI docs are available at `http://localhost:8000/docs`.

## POST `/jobs/upload`

Uploads a CSV and enqueues asynchronous processing.

```bash
curl -F "file=@sample_data/transactions.csv" http://localhost:8000/api/v1/jobs/upload
```

Response:

```json
{
  "job_id": "3fe17e57-c223-4386-a7b7-8bfc509879f1",
  "status": "pending",
  "message": "Job accepted for processing."
}
```

## GET `/jobs/{job_id}/status`

Returns current job state. Completed jobs include a high-level summary.

```bash
curl http://localhost:8000/api/v1/jobs/<job_id>/status
```

## GET `/jobs/{job_id}/results`

Returns cleaned transactions, anomalies, spend-by-category totals, and the narrative summary.

```bash
curl http://localhost:8000/api/v1/jobs/<job_id>/results
```

If the job is not complete, the API returns `409 Conflict`.

## GET `/jobs`

Lists jobs. Optional filter: `?status=pending|processing|completed|failed`.

```bash
curl "http://localhost:8000/api/v1/jobs?status=completed"
```
