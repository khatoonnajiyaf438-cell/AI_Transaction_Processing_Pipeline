import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import JobStatus


class JobCreated(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    message: str


class SummaryBrief(BaseModel):
    total_spend_inr: Decimal
    total_spend_usd: Decimal
    anomaly_count: int
    risk_level: str

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    file_name: str
    row_count_raw: int
    row_count_clean: int
    error_message: str | None = None
    summary: SummaryBrief | None = None


class JobListItem(BaseModel):
    id: uuid.UUID
    file_name: str
    status: JobStatus
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionOut(BaseModel):
    id: int
    txn_id: str | None
    date: date | None
    merchant: str
    amount: Decimal
    currency: str
    status: str
    category: str
    account_id: str
    notes: str | None
    is_anomaly: bool
    anomaly_reason: str | None
    llm_category: str | None
    llm_raw_response: dict[str, Any] | None
    llm_failed: bool

    model_config = ConfigDict(from_attributes=True)


class JobSummaryOut(BaseModel):
    total_spend_inr: Decimal
    total_spend_usd: Decimal
    top_merchants: list[dict[str, Any]]
    spend_by_category: dict[str, Any]
    anomaly_count: int
    narrative: str
    risk_level: str
    llm_raw_response: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class JobResults(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    cleaned_transactions: list[TransactionOut]
    flagged_anomalies: list[TransactionOut]
    spend_by_category: dict[str, Any]
    summary: JobSummaryOut | None
