from app.core.celery_app import celery_app
from app.core.database import SessionLocal, init_db
from app.services.pipeline import process_job_pipeline


@celery_app.task(name="process_job")
def process_job(job_id: str) -> None:
    init_db()
    db = SessionLocal()
    try:
        process_job_pipeline(job_id, db)
    finally:
        db.close()
