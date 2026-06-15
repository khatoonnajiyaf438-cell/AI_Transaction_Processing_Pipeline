from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Job, JobStatus, JobSummary, Transaction
from app.services.anomaly import detect_anomalies
from app.services.cleaner import clean_transactions
from app.services.csv_parser import read_transactions
from app.services.llm import LLMClient


def process_job_pipeline(job_id: str, db: Session) -> None:
    job = db.scalar(select(Job).where(Job.id == UUID(job_id)))
    if not job:
        return

    try:
        job.status = JobStatus.processing
        db.commit()

        raw_rows = read_transactions(job.stored_path)
        cleaned = clean_transactions(raw_rows)
        anomaly_map = detect_anomalies(cleaned)
        llm = LLMClient()
        category_map = llm.classify_missing_categories(cleaned)

        db.execute(delete(Transaction).where(Transaction.job_id == job.id))
        transactions_payload: list[dict] = []
        for index, item in enumerate(cleaned):
            llm_item = category_map.get(index, {})
            category = llm_item.get("category") or item.category
            anomaly_reasons = anomaly_map.get(index, [])
            transaction = Transaction(
                job_id=job.id,
                txn_id=item.txn_id,
                date=item.date,
                merchant=item.merchant,
                amount=item.amount,
                currency=item.currency,
                status=item.status,
                category=category,
                account_id=item.account_id,
                notes=item.notes,
                is_anomaly=bool(anomaly_reasons),
                anomaly_reason="; ".join(anomaly_reasons) or None,
                llm_category=llm_item.get("category") if item.original_category_missing else None,
                llm_raw_response=llm_item.get("raw"),
                llm_failed=bool(llm_item.get("failed")),
            )
            db.add(transaction)
            transactions_payload.append(
                {
                    "merchant": item.merchant,
                    "amount": str(item.amount),
                    "currency": item.currency,
                    "category": category,
                    "is_anomaly": bool(anomaly_reasons),
                }
            )

        spend_by_category = _spend_by_category(transactions_payload)
        anomaly_count = sum(1 for transaction in transactions_payload if transaction["is_anomaly"])
        summary_payload = llm.build_summary(transactions_payload, anomaly_count, spend_by_category)

        db.query(JobSummary).filter(JobSummary.job_id == job.id).delete()
        db.add(
            JobSummary(
                job_id=job.id,
                total_spend_inr=Decimal(summary_payload["total_spend_inr"]),
                total_spend_usd=Decimal(summary_payload["total_spend_usd"]),
                top_merchants=summary_payload["top_merchants"],
                spend_by_category=spend_by_category,
                anomaly_count=summary_payload["anomaly_count"],
                narrative=summary_payload["narrative"],
                risk_level=summary_payload["risk_level"],
                llm_raw_response=summary_payload["llm_raw_response"],
            )
        )

        job.row_count_raw = len(raw_rows)
        job.row_count_clean = len(cleaned)
        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = None
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.scalar(select(Job).where(Job.id == UUID(job_id)))
        if job:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            db.commit()
        raise


def _spend_by_category(transactions: list[dict]) -> dict[str, dict[str, str]]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for transaction in transactions:
        totals[transaction["category"]][transaction["currency"]] += Decimal(str(transaction["amount"]))
    return {
        category: {currency: str(amount.quantize(Decimal("0.01"))) for currency, amount in currency_totals.items()}
        for category, currency_totals in sorted(totals.items())
    }
