-- V7__action_pdca_and_building_analytics.sql - Action/PDCA & Building Analytics at Scale (§5.1 & §5.9 / W5 & W6)

-- 1. Extend action_items with enpi_id linkage
ALTER TABLE action_items 
ADD COLUMN IF NOT EXISTS enpi_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_action_items_enpi_id ON action_items(enpi_id);

-- 2. PDCA Action Transition History
CREATE TABLE IF NOT EXISTS action_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_id UUID NOT NULL REFERENCES action_items(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    old_status VARCHAR(32),
    new_status VARCHAR(32) NOT NULL,
    transition_reason TEXT,
    transitioned_by UUID NOT NULL,
    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_history_action_id ON action_history(action_id, transitioned_at);

-- 3. Building Analytics Results & Metadata Table
CREATE TABLE IF NOT EXISTS building_analytics_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    building_id VARCHAR(64) NOT NULL,
    analytic_type VARCHAR(64) NOT NULL, -- 'HVAC_RUNTIME', 'SIMULTANEOUS_HC', 'OCCUPANCY_WASTE', 'DR_READINESS'
    assumption TEXT NOT NULL,
    computed_value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(32) NOT NULL,
    details JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE action_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_action_history ON action_history
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE building_analytics_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_building_analytics_results ON building_analytics_results
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);
