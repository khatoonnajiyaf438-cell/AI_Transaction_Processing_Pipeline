import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Job, JobStatus, Transaction
from app.schemas import JobCreated, JobListItem, JobResults, JobStatusResponse
from app.tasks import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


@router.post("/upload", response_model=JobCreated, status_code=status.HTTP_202_ACCEPTED)
def upload_job(file: UploadFile = File(...), db: Session = Depends(get_db)) -> JobCreated:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv uploads are supported.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    job_id = uuid.uuid4()
    safe_name = Path(file.filename).name
    stored_path = settings.upload_dir / f"{job_id}_{safe_name}"

    bytes_written = 0
    with stored_path.open("wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > max_bytes:
                buffer.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB.")
            buffer.write(chunk)

    job = Job(id=job_id, file_name=safe_name, stored_path=str(stored_path), status=JobStatus.pending)
    db.add(job)
    db.commit()

    process_job.delay(str(job.id))
    return JobCreated(job_id=job.id, status=job.status, message="Job accepted for processing.")


@router.get("", response_model=list[JobListItem])
def list_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Job]:
    query = select(Job).order_by(Job.created_at.desc())
    if status_filter:
        query = query.where(Job.status == status_filter)
    return list(db.scalars(query).all())


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_status(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = db.scalar(select(Job).options(selectinload(Job.summary)).where(Job.id == job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        file_name=job.file_name,
        row_count_raw=job.row_count_raw,
        row_count_clean=job.row_count_clean,
        error_message=job.error_message,
        summary=job.summary,
    )


@router.get("/{job_id}/results", response_model=JobResults)
def get_results(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobResults:
    job = db.scalar(select(Job).options(selectinload(Job.summary)).where(Job.id == job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=409, detail=f"Job is {job.status.value}; results are not ready.")

    transactions = list(
        db.scalars(select(Transaction).where(Transaction.job_id == job_id).order_by(Transaction.id)).all()
    )
    anomalies = [transaction for transaction in transactions if transaction.is_anomaly]
    spend_by_category = job.summary.spend_by_category if job.summary else {}

    return JobResults(
        job_id=job.id,
        status=job.status,
        cleaned_transactions=transactions,
        flagged_anomalies=anomalies,
        spend_by_category=spend_by_category,
        summary=job.summary,
    )
