# 16. Final Acceptance Criteria & Design Validation Checklist (R-15)

## 16.1 Key Product Performance Indicators (KPIs)
- **Energy Waste Reduction**: Deliver demonstrable average 8-15% energy cost reduction within 6 months of deployment.
- **Audit Compliance Rate**: 100% zero-nonconformity pass rate for ISO 50001 audits using generated audit packs.
- **Mean Time to Detect Anomaly (MTTD)**: < 5 minutes from event occurrence to operator notification.
- **System Ingestion Scalability**: Support >= 500,000 points/sec ingestion at < 500 ms write latency.

---

## 16.2 Refined Binary Acceptance Criteria (R-15)

| AC ID | Capability Area | Binary Testable Criterion | Test Type |
| :--- | :--- | :--- | :--- |
| **AC-01a** | ISO Traceability | Traceability matrix covers all ISO 50001:2018 clauses 4.1 to 10.2 without gaps. | Automated Lint Check |
| **AC-01b** | ISO Traceability | Every matrix row maps to an existing OpenAPI endpoint and DDL table column. | Integration Test |
| **AC-02a** | Signed ADRs | All 4 ADRs have Status = Accepted with owner, date, and consequences section. | Documentation Audit |
| **AC-03a** | PostgreSQL DDL | Schema executes in clean PostgreSQL container with zero warnings or errors. | Migration Test |
| **AC-03d** | Multi-Tenant RLS | Query with invalid `app.current_tenant_id` returns 0 rows from `assets` table. | Security Test |
| **AC-04a** | OpenAPI Contract | Spectral linter returns 0 errors against OpenAPI 3.0 specification. | API Linter Check |
| **AC-04c** | Idempotency | Duplicate POST request with identical `Idempotency-Key` returns cached 201 response. | Integration Test |
| **AC-05b** | Event Schemas | Schema Registry rejects incompatible field deletion on `telemetry.raw.v1` topic. | Schema Compatibility Test |
| **AC-07a** | EnPI DSL Engine | Grammar parser accepts all valid EnPI expressions and rejects unit mismatch expressions. | Unit Test |
| **AC-08a** | Tri-State Anomaly | Decision logic correctly classifies 3 positive test cases for sensor fault, change, and waste. | Integration Test |
| **AC-10a** | RAG Isolation | Vector similarity query for Tenant A returns zero results when executed in Tenant B scope. | Security Test |
| **AC-11b** | Audit Hash Chain | Modifying a single record in `audit_trail` table causes verification tool to report TAMPER_DETECTED. | Cryptographic Test |

---

## 16.3 Design Validation Checklist

| Requested Capability | Design Section Reference | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **English-First Language Standard** | Section 1, Section 12 | ✅ Verified | All specifications, logs, APIs, reports, and UI copy mandated in English. |
| **Competitor Gap Solutions** | Section 2 | ✅ Verified | Matrix addresses raw data, closed APIs, black-box ML, and OT/IT disconnects. |
| **Target Personas & Journeys** | Section 3 | ✅ Verified | Personas mapped to ISO 50001 PDCA journey with acceptance criteria. |
| **Edge-Cloud Topology & Store-Forward** | Section 4, Section 6 | ✅ Verified | Docker edge on industrial Linux with SQLite/RocksDB buffer and PTP time sync. |
| **Domain Data Model & Executable DDL** | Section 5 | ✅ Verified | Executable PostgreSQL DDL schema with RLS policies, `ltree`, and audit tables. |
| **Protocol Support (Modbus, OPC UA, BACnet, etc.)** | Section 6.1 | ✅ Verified | Comprehensive protocol adapter list and quality tagging rules specified. |
| **Semantic Asset Layer (Brick/Haystack)** | Section 5, Section 6.2 | ✅ Verified | Extended taxonomy with GraphQL/REST graph navigation API. |
| **EnPI & Baseline Regression Engine** | Section 6.4 | ✅ Verified | Formula DSL, MLR regression, R^2 validation, and IPMVP M&V rules. |
| **Tri-State Anomaly Detection** | Section 6.5 | ✅ Verified | Separation of Sensor Fault, Operational Change, and Real Energy Waste. |
| **Action Management & ISO Audit Trail** | Section 5, Section 6.6 | ✅ Verified | PDCA tracking with cryptographically hashed audit trail. |
| **Operational MLOps & Explainable AI** | Section 7 | ✅ Verified | XGBoost/TFT load forecasting, SHAP factor attribution, PSI drift monitoring. |
| **Constraint-Aware Optimization** | Section 7.1, Section 8.2 | ✅ Verified | MILP setpoint optimizer bounded by hard thermal/pressure safety limits. |
| **Energy Digital Twin & What-If Engine** | Section 8.1 | ✅ Verified | Scenario simulation for setpoint changes and tariff structures. |
| **Guardrailed RAG AI Assistant** | Section 8.3 | ✅ Verified | Vector search over asset manuals with hallucination-free citation bounds. |
| **Non-Functional Requirements & Security** | Section 9 | ✅ Verified | IEC 62443 compliance, mTLS encryption, Keycloak IAM, 99.95% SLA. |
| **Tech Stack Rationale & ADRs** | Section 10 | ✅ Verified | Detailed tech matrix + ADRs for TimescaleDB and Go edge runtime. |
| **Executable OpenAPI 3.0 Contract** | Section 11 | ✅ Verified | OpenAPI 3.0 YAML specification provided. |
| **UX/UI Wireframes & Copy Guidelines** | Section 12 | ✅ Verified | Textual wireframe, dark-mode design rules, and English terminology standards. |
| **MoSCoW Roadmap & Execution Backlog** | Section 13, Section 14 | ✅ Verified | MVP vs Phase 2/3 roadmap and detailed user stories with acceptance criteria. |
| **ISO 50001 Traceability Matrix** | Section 17 | ✅ Verified | Complete clause mapping matrix across ISO 50001:2018 standard clauses. |
