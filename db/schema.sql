CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    status job_status NOT NULL DEFAULT 'pending',
    row_count_raw INTEGER NOT NULL DEFAULT 0,
    row_count_clean INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    txn_id VARCHAR(128),
    date DATE,
    merchant VARCHAR(255) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    category VARCHAR(80) NOT NULL,
    account_id VARCHAR(128) NOT NULL,
    notes TEXT,
    is_anomaly BOOLEAN NOT NULL DEFAULT false,
    anomaly_reason TEXT,
    llm_category VARCHAR(80),
    llm_raw_response JSONB,
    llm_failed BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE job_summaries (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    total_spend_inr NUMERIC(14, 2) NOT NULL DEFAULT 0,
    total_spend_usd NUMERIC(14, 2) NOT NULL DEFAULT 0,
    top_merchants JSONB NOT NULL DEFAULT '[]',
    spend_by_category JSONB NOT NULL DEFAULT '{}',
    anomaly_count INTEGER NOT NULL DEFAULT 0,
    narrative TEXT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    llm_raw_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_jobs_status ON jobs(status);
CREATE INDEX ix_transactions_job_id ON transactions(job_id);
CREATE INDEX ix_transactions_job_category ON transactions(job_id, category);
CREATE INDEX ix_transactions_account_id ON transactions(account_id);
CREATE INDEX ix_transactions_is_anomaly ON transactions(is_anomaly);
