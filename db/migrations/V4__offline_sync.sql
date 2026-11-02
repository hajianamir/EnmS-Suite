-- V4__offline_sync.sql - Offline Capabilities & Reconciliation Schema (§10.3 / ADR-008)

CREATE TABLE offline_sync_state (
    edge_node_id VARCHAR(64) NOT NULL,
    stream_key VARCHAR(255) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    last_synced_sequence BIGINT NOT NULL DEFAULT 0,
    last_synced_timestamp TIMESTAMPTZ,
    synced_digest VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'IN_SYNC', -- 'IN_SYNC', 'PARTITIONED', 'RECONCILING', 'DIGEST_MISMATCH'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (edge_node_id, stream_key)
);

CREATE INDEX idx_offline_sync_tenant ON offline_sync_state(tenant_id);

CREATE TABLE sync_conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    edge_node_id VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    conflict_type VARCHAR(32) NOT NULL, -- 'TELEMETRY_OVERWRITE', 'CONFIG_DRIFT', 'TIMESTAMP_COLLISION'
    edge_value JSONB NOT NULL,
    cloud_value JSONB NOT NULL,
    resolution VARCHAR(32) NOT NULL, -- 'EDGE_PRECEDENCE', 'CLOUD_PRECEDENCE', 'MANUAL_REVIEW'
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sync_conflicts_tenant ON sync_conflicts(tenant_id, edge_node_id);

-- Enable Row-Level Security
ALTER TABLE offline_sync_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_offline_sync ON offline_sync_state
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE sync_conflicts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_sync_conflicts ON sync_conflicts
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);
