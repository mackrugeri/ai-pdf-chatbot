-- Durable workflow state. Queue messages carry identifiers, never document content.
CREATE TABLE jobs (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES users(id),
    document_id uuid,
    job_type text NOT NULL CHECK (job_type IN ('ingestion', 'answer', 'cleanup')),
    state text NOT NULL CHECK (state IN ('queued', 'running', 'retrying', 'succeeded', 'failed', 'cancelling', 'cancelled', 'expired')),
    payload_key text,
    result_key text,
    error_code text,
    progress_current integer NOT NULL DEFAULT 0 CHECK (progress_current >= 0),
    progress_total integer CHECK (progress_total IS NULL OR progress_total >= 0),
    lease_token uuid,
    lease_expires_at timestamptz,
    heartbeat_at timestamptz,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 20),
    available_at timestamptz NOT NULL DEFAULT now(),
    deadline_at timestamptz,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fk_jobs_owner_document FOREIGN KEY (owner_id, document_id) REFERENCES documents (owner_id, id),
    CONSTRAINT ck_jobs_lease_state CHECK (
        (state IN ('running', 'cancelling')) = (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)
    ),
    CONSTRAINT ck_jobs_lease_pair CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL)),
    CONSTRAINT ck_jobs_progress CHECK (progress_total IS NULL OR progress_current <= progress_total)
);
CREATE INDEX ix_jobs_owner_created_id ON jobs (owner_id, created_at DESC, id DESC);
CREATE INDEX ix_jobs_owner_state_created ON jobs (owner_id, state, created_at DESC, id DESC);
CREATE INDEX ix_jobs_dispatch ON jobs (available_at, created_at, id) WHERE state IN ('queued', 'retrying');
CREATE INDEX ix_jobs_expired_lease ON jobs (lease_expires_at) WHERE state IN ('running', 'cancelling');
CREATE INDEX ix_jobs_document ON jobs (owner_id, document_id, created_at DESC) WHERE document_id IS NOT NULL;

CREATE TABLE outbox_events (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES jobs(id),
    event_type text NOT NULL CHECK (event_type IN ('job.queued', 'job.cancelled', 'document.deleted')),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    available_at timestamptz NOT NULL DEFAULT now(),
    lease_token uuid,
    lease_expires_at timestamptz,
    published_at timestamptz,
    last_error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_outbox_lease_pair CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL))
);
CREATE INDEX ix_outbox_dispatch ON outbox_events (available_at, created_at, id) WHERE published_at IS NULL;
CREATE INDEX ix_outbox_job ON outbox_events (job_id, created_at);

CREATE TABLE idempotency_receipts (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES users(id),
    operation text NOT NULL CHECK (length(operation) BETWEEN 1 AND 128),
    key_digest char(64) NOT NULL CHECK (key_digest ~ '^[0-9a-f]{64}$'),
    request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    resource_type text NOT NULL CHECK (resource_type IN ('document', 'job', 'deletion')),
    resource_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    CONSTRAINT uq_idempotency_owner_operation_key UNIQUE (owner_id, operation, key_digest)
);
CREATE INDEX ix_idempotency_expiry ON idempotency_receipts (expires_at) WHERE expires_at IS NOT NULL;

CREATE TABLE deletion_tombstones (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES users(id),
    document_id uuid NOT NULL,
    operation_id uuid NOT NULL UNIQUE,
    journal_entry_id text NOT NULL CHECK (length(journal_entry_id) BETWEEN 1 AND 512),
    state text NOT NULL CHECK (state IN ('accepted', 'cleaning', 'complete', 'blocked')),
    requested_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CONSTRAINT uq_deletion_tombstones_document UNIQUE (document_id),
    CONSTRAINT fk_deletion_owner_document FOREIGN KEY (owner_id, document_id) REFERENCES documents (owner_id, id),
    CONSTRAINT ck_deletion_completed_timestamp CHECK ((state = 'complete') = (completed_at IS NOT NULL))
);
CREATE INDEX ix_deletion_tombstones_pending ON deletion_tombstones (requested_at, id) WHERE state <> 'complete';

CREATE TABLE audit_events (
    id uuid PRIMARY KEY,
    owner_id uuid REFERENCES users(id),
    actor_subject text,
    action text NOT NULL CHECK (length(action) BETWEEN 1 AND 128),
    target_type text NOT NULL CHECK (length(target_type) BETWEEN 1 AND 64),
    target_id uuid,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_owner_created ON audit_events (owner_id, created_at DESC, id DESC);
