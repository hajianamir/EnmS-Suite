-- V4_2__edge_timescaledb_telemetry.sql - Edge Embedded Telemetry Schema & Continuous Downsampling (§10.3 / STORY-2.13)

-- 1. Raw Telemetry Table partitioned by month (or Timescale hypertable in prod)
CREATE TABLE IF NOT EXISTS edge_telemetry_raw (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    point_id VARCHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    val DOUBLE PRECISION NOT NULL,
    quality_flag VARCHAR(32) NOT NULL DEFAULT 'GOOD',
    PRIMARY KEY (tenant_id, point_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_edge_telemetry_raw_lookup 
ON edge_telemetry_raw (tenant_id, point_id, recorded_at DESC);

-- 2. Hourly Downsampled Continuous Aggregate Table
CREATE TABLE IF NOT EXISTS edge_telemetry_hourly (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    point_id VARCHAR(64) NOT NULL,
    bucket_at TIMESTAMPTZ NOT NULL,
    val_avg DOUBLE PRECISION NOT NULL,
    val_min DOUBLE PRECISION NOT NULL,
    val_max DOUBLE PRECISION NOT NULL,
    sample_count INT NOT NULL,
    PRIMARY KEY (tenant_id, point_id, bucket_at)
);

CREATE INDEX IF NOT EXISTS idx_edge_telemetry_hourly_lookup 
ON edge_telemetry_hourly (tenant_id, point_id, bucket_at DESC);

-- Enable RLS
ALTER TABLE edge_telemetry_raw ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_edge_telemetry_raw ON edge_telemetry_raw
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE edge_telemetry_hourly ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_edge_telemetry_hourly ON edge_telemetry_hourly
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);
