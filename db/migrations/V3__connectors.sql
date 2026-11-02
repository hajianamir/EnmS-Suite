-- V3__connectors.sql - Data Connectors Schema (§10.2 / ADR-007)
-- Supports external relational databases, local stores, and flat-file connectors

CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(64) NOT NULL, -- 'postgresql', 'mysql', 'sqlserver', 'sqlite', 'oracle', 'xlsx', 'csv'
    runtime_placement VARCHAR(32) NOT NULL DEFAULT 'cloud', -- 'cloud', 'edge'
    secret_ref VARCHAR(512) NOT NULL, -- Pointer URI into secrets manager; never cleartext credentials
    connection_config JSONB NOT NULL DEFAULT '{}'::jsonb, -- Host, port, dbname, max_qps, timeout_seconds
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL
);

CREATE INDEX idx_data_sources_tenant ON data_sources(tenant_id);

CREATE TABLE source_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    source_table VARCHAR(255) NOT NULL,
    source_column VARCHAR(255) NOT NULL,
    point_id UUID NOT NULL REFERENCES measurement_points(id) ON DELETE CASCADE,
    transform_expression TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_source_mappings_source ON source_mappings(tenant_id, source_id);

CREATE TABLE sync_watermarks (
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    stream_key VARCHAR(255) NOT NULL, -- Table or file identifier
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    watermark_timestamp TIMESTAMPTZ,
    watermark_sequence BIGINT,
    last_committed_row INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_id, stream_key)
);

CREATE TABLE connector_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    run_type VARCHAR(32) NOT NULL, -- 'scheduled', 'manual', 'incremental', 'preview'
    status VARCHAR(32) NOT NULL, -- 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL'
    rows_read INT NOT NULL DEFAULT 0,
    rows_committed INT NOT NULL DEFAULT 0,
    rows_rejected INT NOT NULL DEFAULT 0,
    error_summary JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INT
);

CREATE INDEX idx_connector_runs_source ON connector_runs(tenant_id, source_id, started_at DESC);

-- Enable Row-Level Security on connector tables
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_data_sources ON data_sources
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE source_mappings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_source_mappings ON source_mappings
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE sync_watermarks ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_sync_watermarks ON sync_watermarks
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE connector_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_connector_runs ON connector_runs
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);
