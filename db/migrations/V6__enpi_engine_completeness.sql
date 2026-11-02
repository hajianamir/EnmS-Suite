-- V6__enpi_engine_completeness.sql - EnPI Engine Completeness Schema (§5.1 / Workstream 3)

CREATE TABLE IF NOT EXISTS enpi_definitions (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    target_unit VARCHAR(32) NOT NULL,
    current_baseline_id UUID,
    current_baseline_version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enpi_baseline_dependencies (
    enpi_id VARCHAR(64) NOT NULL REFERENCES enpi_definitions(id) ON DELETE CASCADE,
    baseline_id VARCHAR(64) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (enpi_id, baseline_id)
);

CREATE TABLE IF NOT EXISTS enpi_state (
    enpi_id VARCHAR(64) PRIMARY KEY REFERENCES enpi_definitions(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    baseline_id VARCHAR(64) NOT NULL,
    baseline_version INT NOT NULL DEFAULT 1,
    latest_value DOUBLE PRECISION,
    coverage_ratio DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enpi_recomputation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL, -- 'ENPI_RECOMPUTED'
    reason VARCHAR(64) NOT NULL,     -- 'LATE_DATA', 'BASELINE_UPDATE'
    point_id VARCHAR(64),
    point_recorded_at TIMESTAMPTZ,
    arrived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    affected_enpi_ids JSONB NOT NULL,
    old_value DOUBLE PRECISION,
    new_value DOUBLE PRECISION,
    delta_pct DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE enpi_definitions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_enpi_definitions ON enpi_definitions
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE enpi_baseline_dependencies ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_enpi_baseline_dependencies ON enpi_baseline_dependencies
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE enpi_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_enpi_state ON enpi_state
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE enpi_recomputation_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_enpi_recomputation_log ON enpi_recomputation_log
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);
