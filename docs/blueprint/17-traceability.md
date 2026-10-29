# 17. ISO 50001:2018 Traceability Matrix

## 17.1 Traceability Overview & Compliance Mapping
This document provides full traceability between ISO 50001:2018 standard clauses, VerdantOS platform modules, API endpoints, database entities, acceptance criteria, and audit evidence artifacts.

Validation Regular Expressions:
- **Clause Regex**: `^ISO-50001:(4\.[1-4]|5\.[1-3]|6\.[1-3]|7\.[1-5]|8\.[1-3]|9\.[1-3]|10\.[1-2])$`
- **AC ID Regex**: `^AC-[0-9]{2}[a-z]$`

---

## 17.2 ISO 50001:2018 Clause Mapping Matrix

| ISO Clause | Requirement Description | Satisfying Module | API Operation(s) | Data Entity / Table | Acceptance Criterion ID | Status / Target Phase | Evidence Artifact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ISO-50001:4.1** | Context of the organization | Tenant & Asset Management | `GET /api/v1/tenants/context` | `tenants`, `organization_units` | AC-01a | MVP (Phase 1) | `docs/blueprint/01-vision.md`, Tenant Boundary Config |
| **ISO-50001:4.2** | Needs and expectations of interested parties | User & IAM Management | `GET /api/v1/users/roles` | `users`, `roles` | AC-01b | MVP (Phase 1) | RBAC Matrix, User Role Assignment Log |
| **ISO-50001:4.3** | Determining the scope of the EnMS | Semantic Asset Layer | `GET /api/v1/assets/tree` | `assets` (ltree path) | AC-01b | MVP (Phase 1) | Site Boundary Map, Asset Tree Export |
| **ISO-50001:4.4** | Energy management system | Core EnMS Engine | `GET /api/v1/enms/status` | `tenants`, `enpi_baselines` | AC-01c | MVP (Phase 1) | System Architecture & PDCA Workflow Log |
| **ISO-50001:5.1** | Leadership and commitment | Action & Policy Management | `GET /api/v1/policy` | `energy_policies` | AC-01b | MVP (Phase 1) | Published Energy Policy Document |
| **ISO-50001:5.2** | Energy policy | Policy Management | `POST /api/v1/policy` | `energy_policies` | AC-01b | MVP (Phase 1) | Cryptographically Hashed Policy Sign-off |
| **ISO-50001:5.3** | Organization roles, responsibilities, authorities | IAM & Keycloak | `GET /api/v1/users/permissions` | `user_roles`, `audit_trail` | AC-01b | MVP (Phase 1) | Keycloak Role Definition & Governance Log |
| **ISO-50001:6.1** | Actions to address risks and opportunities | Action Management & Risk | `POST /api/v1/actions` | `action_items`, `risks` | AC-01b | MVP (Phase 1) | Risk Register & Action Item Exports |
| **ISO-50001:6.2** | Objectives, energy targets and planning | Action & Target Management | `POST /api/v1/targets` | `energy_targets` | AC-01b | MVP (Phase 1) | Target Tracking Dashboard & Report |
| **ISO-50001:6.3** | Energy review (SEUs, consumption, variables) | EnPI & SEU Engine | `POST /api/v1/seu/analyze` | `seu_definitions`, `measurement_points` | AC-01b | MVP (Phase 1) | SEU Analysis Pareto & Consumption Breakdown |
| **ISO-50001:7.1** | Resources | Platform Infrastructure | `GET /api/v1/system/health` | `system_nodes` | AC-01c | MVP (Phase 1) | Infrastructure Provisioning & Health Log |
| **ISO-50001:7.2** | Competence | Action & User Governance | `GET /api/v1/users/competence` | `user_competencies` | AC-01b | MVP (Phase 1) | Training Certification & Skill Matrix |
| **ISO-50001:7.3** | Awareness | Dashboard & Notifications | `GET /api/v1/dashboards/public` | `dashboards` | AC-01c | MVP (Phase 1) | Public Kiosk Dashboard & News Bulletin |
| **ISO-50001:7.4** | Communication | Alert & Notification Engine | `POST /api/v1/notifications/broadcast` | `notifications` | AC-01b | MVP (Phase 1) | Broadcast Log & Alert Dispatch History |
| **ISO-50001:7.5** | Documented information | ISO Audit Evidence Engine | `GET /api/v1/audit/pack` | `audit_trail`, `documents` | AC-01b | MVP (Phase 1) | SHA-256 Verified Immutable Audit Pack PDF |
| **ISO-50001:8.1** | Operational planning and control | Constraint Optimization | `POST /api/v1/control/setpoints` | `control_schedules` | AC-01d | DEFERRED (Phase 2) | Control Schedule & BMS Interlock Logs |
| **ISO-50001:8.2** | Design (energy performance in facility design) | Energy Digital Twin | `POST /api/v1/simulation/what-if` | `digital_twins` | AC-01d | DEFERRED (Phase 2) | Simulation Comparison & Design Evaluation Report |
| **ISO-50001:8.3** | Procurement of energy services, products, equipment | Sustainability & Energy Procurement | `GET /api/v1/procurement/tariffs` | `energy_tariffs` | AC-01d | DEFERRED (Phase 2) | Supplier Energy Intensity & Tariff Evaluation |
| **ISO-50001:9.1** | Monitoring, measurement, analysis and evaluation | Data Ingestion & EnPI Engine | `POST /api/v1/telemetry/query` | `telemetry_time_series`, `enpi_baselines` | AC-01b | MVP (Phase 1) | Calibrated Meter Telemetry & EnPI Trends |
| **ISO-50001:9.2** | Internal audit | Action Management & Audit | `POST /api/v1/audit/internal` | `internal_audits` | AC-01b | MVP (Phase 1) | Internal Audit Report & Checklist Results |
| **ISO-50001:9.3** | Management review | Executive Reporting Engine | `GET /api/v1/reports/executive-review` | `reports` | AC-01b | MVP (Phase 1) | Signed Executive Management Review Minutes |
| **ISO-50001:10.1** | Nonconformity and corrective action | Action Management & PDCA | `POST /api/v1/actions/nonconformity` | `action_items` | AC-01b | MVP (Phase 1) | Nonconformity Closure Log & M&V Proof |
| **ISO-50001:10.2** | Continual improvement | Baseline & CUSUM Engine | `GET /api/v1/enpi/cusum` | `enpi_baselines` | AC-01b | MVP (Phase 1) | CUSUM Savings Curve showing multi-year trend |
| **ISO-50001:10.3** | Continual improvement | Baseline & CUSUM Engine | `GET /api/v1/enpi/cusum` | `enpi_baselines`, `action_items` | AC-01b | MVP (Phase 1) | Multi-year CUSUM savings curve verifying PDCA actions |
