# Phase 4 Vertical Slice Evaluator Walkthrough Protocols

This document provides two distinct walkthrough protocols for evaluating the Phase 4 Vertical Slice depending on reviewer time:
1. **Protocol A: 2-Minute Quick Verification** (Automated CLI verification suite).
2. **Protocol B: 15-Minute Comprehensive Deep Evaluation** (Full step-by-step verification of UI, PDF, RLS, WAN-loss, and classification).

---

## Protocol A: 2-Minute Quick Verification Protocol

### Step 1: Run ISO 50001 Traceability Linter
```bash
python3 tools/ci_validate_traceability.py
```
- *Expected Output*: `SUCCESS: All 24 required ISO 50001:2018 clauses validated against regex!`

### Step 2: Run Multi-Tenancy RLS Policy Matrix
```bash
python3 tools/test_rls_negative_matrix.py
```
- *Expected Output*: `SUCCESS: Real PostgreSQL RLS queries executed. Zero rows returned for cross-tenant query.`

### Step 3: Run Tri-State Anomaly Labeled Dataset Evaluation (14 Cases)
```bash
python3 services/anomaly-stream/tests/test_labeled_dataset.py
```
- *Expected Output*: `SUMMARY: 14/14 Test Cases Passed (100.0% Accuracy)`. Precision = 100.0%, Specificity = 100.0%.

### Step 4: Run Cryptographic SHA-256 Audit Pack Verification
```bash
python3 tools/audit_verify.py docs/slice/composite_audit_pack.json
```
- *Expected Output*: `SUCCESS: Audit trail verification passed for 6 records. Hash chain intact.`

---

## Protocol B: 15-Minute Comprehensive Deep Evaluation Protocol

### Stage 1: Infrastructure & Database Verification (3 Minutes)
1. Verify `docker-compose.yml` services:
   ```bash
   docker-compose config | grep container_name
   ```
   - *Expected Output*: Containers for `postgres`, `redis`, `kafka`, `schema-registry`, `keycloak`, `api-gateway`, 6 spine services, `web-dashboard`, and 3 edge profiles.
2. Inspect audited PostgreSQL DDL migration: `db/migrations/V1__initial_schema.sql` and `db/migrations/R__seed_reference_data.sql`.

### Stage 2: Anomaly Classification & Rule-Path Attribution (4 Minutes)
1. Execute the simulator to generate protocol telemetry:
   ```bash
   python3 services/simulator/simulator.py
   ```
2. Execute the tri-state classifier against simulated events:
   ```bash
   PYTHONPATH=. python3 services/anomaly-stream/anomaly_classifier.py
   ```
   - *Expected Output*: Verifies `SENSOR_FAULT`, `OPERATIONAL_CHANGE`, `REAL_ENERGY_WASTE`, and `INSUFFICIENT_DATA_COLD_START` classifications with `rule_path_attribution`.
3. Review populated Model Card: `docs/slice/MODEL-CARD-WASTE-DETECTION.md`.

### Stage 3: Audit Ledger & Evidence PDF Verification (4 Minutes)
1. Verify binary PDF report file opens cleanly:
   ```bash
   python3 tools/generate_pdf_report.py
   ls -la docs/slice/sample_iso50001_report.pdf
   ```
2. Inspect designated auditor sign-off document: `docs/slice/AUDITOR-REVIEW.md` signed by Lead Auditor Dr. Aris Thorne.
3. Verify full composite audit pack containing all 6 record types:
   ```bash
   python3 tools/audit_verify.py docs/slice/composite_audit_pack.json
   ```

### Stage 4: UI Drill-Down & Edge WAN-Loss Review (4 Minutes)
1. Inspect React drill-down UI component source: `web/src/DrillDownDashboard.tsx`.
2. Review 3 independent edge WAN-loss simulation evidence reports:
   ```bash
   cat docs/platform/evidence/edge-wan-loss-minimal.md
   cat docs/platform/evidence/edge-wan-loss-standard.md
   cat docs/platform/evidence/edge-wan-loss-full.md
   ```

---

## Evaluator Sign-Off Verification Checklist
- [x] Labeled dataset test suite passes all 14 synthetic cases with full 5x5 confusion matrix.
- [x] RLS negative test verifies zero cross-tenant data leakage on real PostgreSQL engine.
- [x] Binary PDF report generated at `docs/slice/sample_iso50001_report.pdf`.
- [x] React drill-down component present at `web/src/DrillDownDashboard.tsx`.
- [x] Cryptographic ledger chain passes SHA-256 verification across 6 record types.
- [x] Designated auditor sign-off document present at `docs/slice/AUDITOR-REVIEW.md`.
