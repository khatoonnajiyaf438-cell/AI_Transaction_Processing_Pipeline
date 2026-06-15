import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending, index=True)
    row_count_raw: Mapped[int] = mapped_column(Integer, default=0)
    row_count_clean: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    summary: Mapped["JobSummary | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), index=True)
    txn_id: Mapped[str | None] = mapped_column(String(128), index=True)
    date: Mapped[date | None] = mapped_column(Date)
    merchant: Mapped[str] = mapped_column(String(255), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    category: Mapped[str] = mapped_column(String(80), default="Uncategorised")
    account_id: Mapped[str] = mapped_column(String(128), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    anomaly_reason: Mapped[str | None] = mapped_column(Text)
    llm_category: Mapped[str | None] = mapped_column(String(80))
    llm_raw_response: Mapped[dict | None] = mapped_column(JSONB)
    llm_failed: Mapped[bool] = mapped_column(Boolean, default=False)

    job: Mapped[Job] = relationship(back_populates="transactions")


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), unique=True)
    total_spend_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    total_spend_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    top_merchants: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    spend_by_category: Mapped[dict] = mapped_column(JSONB, default=dict)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0)
    narrative: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    llm_raw_response: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[Job] = relationship(back_populates="summary")


Index("ix_transactions_job_category", Transaction.job_id, Transaction.category)
