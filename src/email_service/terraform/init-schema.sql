-- Create RUNS table
CREATE TABLE IF NOT EXISTS RUNS (
    run_id VARCHAR(255) PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL DEFAULT 'DIRECT', -- DIRECT or SPREADSHEET or WEBHOOK
    attachment_file_ids JSONB NOT NULL DEFAULT '[]',
    attachment_files JSONB NOT NULL DEFAULT '[]',
    bcc JSONB NOT NULL DEFAULT '[]',
    cc JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_year VARCHAR(4) NOT NULL,
    created_year_month VARCHAR(7) NOT NULL,
    created_year_month_day VARCHAR(10) NOT NULL,
    display_name VARCHAR(255),
    expected_email_send_count INTEGER NOT NULL DEFAULT 0,
    is_generate_certificate BOOLEAN NOT NULL DEFAULT FALSE,
    recipients JSONB NOT NULL DEFAULT '[]',
    recipient_source VARCHAR(255), -- Source of the recipient list DIRECT, SPREADSHEET
    reply_to VARCHAR(255),
    sender JSONB,
    sender_id VARCHAR(255),
    sender_local_part VARCHAR(255),
    spreadsheet_file JSONB,
    spreadsheet_file_id VARCHAR(255),
    subject VARCHAR(255) NOT NULL,
    success_email_count INTEGER NOT NULL DEFAULT 0,
    failed_email_count INTEGER NOT NULL DEFAULT 0,
    template_file JSONB NOT NULL,
    template_file_id VARCHAR(255) NOT NULL
);

-- Create EMAILS table with foreign key reference to RUNS
CREATE TABLE IF NOT EXISTS EMAILS (
    email_id VARCHAR(255) PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL,
    attachment_file_ids JSONB NOT NULL DEFAULT '[]',
    bcc JSONB NOT NULL DEFAULT '[]',
    cc JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    display_name VARCHAR(255),
    is_generate_certificate BOOLEAN NOT NULL DEFAULT FALSE,
    recipient_email VARCHAR(255) NOT NULL,
    reply_to VARCHAR(255),
    row_data JSONB,
    sender_id VARCHAR(255),
    sender_local_part VARCHAR(255),
    sender_username VARCHAR(255),
    sent_at TIMESTAMP WITH TIME ZONE,
    spreadsheet_file_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    subject VARCHAR(255) NOT NULL,
    template_file_id VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,

    CONSTRAINT fk_run FOREIGN KEY (run_id) REFERENCES RUNS(run_id) ON DELETE CASCADE
);

-- Create index on run_id in EMAILS table for faster joins
CREATE INDEX IF NOT EXISTS idx_emails_run_id ON EMAILS(run_id);

-- Create index on status in EMAILS table for faster filtering
CREATE INDEX IF NOT EXISTS idx_emails_status ON EMAILS(status);

-- Create index on created_at in EMAILS table for faster sorting
CREATE INDEX IF NOT EXISTS idx_emails_created_at ON EMAILS(created_at);

-- Create index on created_at in RUNS table for faster sorting
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON RUNS(created_at);

-- Create index on sender_id in RUNS table for faster filtering
CREATE INDEX IF NOT EXISTS idx_runs_sender_id ON RUNS(sender_id);

-- Create index on created_year in RUNS table for faster filtering
CREATE INDEX IF NOT EXISTS idx_runs_created_year ON RUNS(created_year);

-- Create combined index on sender_id and created_year for common query pattern
CREATE INDEX IF NOT EXISTS idx_runs_sender_id_created_year ON RUNS(sender_id, created_year);

-- Create combined index on run_id and status for email status queries
CREATE INDEX IF NOT EXISTS idx_emails_run_id_status ON EMAILS(run_id, status);
