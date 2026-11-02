-- V5__baseline_advisor.sql - Auto-Baseline Advisor Schema (§10.4 / Workstream 12)

CREATE TABLE IF NOT EXISTS baseline_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    enpi_id VARCHAR(64) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'proposed', -- 'proposed', 'accepted', 'modified', 'rejected'
    fit_window_start TIMESTAMPTZ NOT NULL,
    fit_window_end TIMESTAMPTZ NOT NULL,
    cv_mape DOUBLE PRECISION NOT NULL,
    aic DOUBLE PRECISION,
    bic DOUBLE PRECISION,
    fsu_pct DOUBLE PRECISION NOT NULL,
    dsl_formula TEXT NOT NULL,
    coefficients JSONB NOT NULL,
    diagnostics_summary JSONB NOT NULL,
    reproducibility_manifest VARCHAR(64) NOT NULL,
    proposal_snapshot JSONB,
    modification_delta JSONB,
    rejection_reason TEXT,
    accepted_by VARCHAR(128),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS baseline_diagnostics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES baseline_candidates(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    test_type VARCHAR(64) NOT NULL,
    test_name VARCHAR(64) NOT NULL,
    test_statistic DOUBLE PRECISION,
    p_value DOUBLE PRECISION,
    passed BOOLEAN NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Immutability Enforcement Trigger for Accepted Baselines
CREATE OR REPLACE FUNCTION enforce_baseline_immutability()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'accepted' THEN
        RAISE EXCEPTION 'BASELINE_IMMUTABLE: Accepted baseline records are permanently immutable for ISO 50001 auditability';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_baseline_immutability ON baseline_candidates;
CREATE TRIGGER trg_baseline_immutability
BEFORE UPDATE OR DELETE ON baseline_candidates
FOR EACH ROW EXECUTE FUNCTION enforce_baseline_immutability();

-- RLS Enforcement
ALTER TABLE baseline_candidates ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_baseline_candidates ON baseline_candidates
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);

ALTER TABLE baseline_diagnostics ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_baseline_diagnostics ON baseline_diagnostics
    USING (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid);
