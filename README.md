# VerdantOS: Enterprise Energy Management & Building Management System

[![Contract CI Pipeline](https://github.com/hajianamir/EnmS-Suite/actions/workflows/ci.yml/badge.svg)](https://github.com/hajianamir/EnmS-Suite/actions/workflows/ci.yml)
[![ISO 50001:2018 Traceability](https://img.shields.io/badge/ISO%2050001%3A2018-Aligned-blue.svg)](docs/blueprint/17-traceability.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

*Repository Relationship Note*: **VerdantOS** is the official product platform name; the repository is maintained under `EnmS-Suite` for historical continuity.

**VerdantOS** is an open-architecture, cloud-native, and edge-deployable Energy Management System (EnMS) and Building Management System (BMS) platform aligned with **ISO 50001:2018**, **ISO 50006**, **ISO 50015**, **IPMVP**, and **IEC 62443**.

---

## Honest Project Status & Maturity Breakdown

- **Phases 1–4 (Master Blueprint, Architecture & Vertical Slice)**: **CLOSED**
  - Complete master architectural blueprint across 17 modular sections (`docs/blueprint/`).
  - Audited PostgreSQL DDL SQL schema with Row-Level Security (RLS) policies and `ltree` asset hierarchies.
  - Executable OpenAPI 3.0 specification (`contracts/openapi/`) and Kafka event envelope schemas.
  - Validated vertical slice pipeline from protocol simulation through EnPI baseline evaluation, tri-state anomaly classification, and cryptographic audit evidence pack generation (`docs/slice/`).
- **Phase 5 (MVP Completion & Hardening)**: **IN PROGRESS**
  - **Workstream 1 (Protocol Adapters)**: **IN PROGRESS** (Contract-tested error-wrapper and reconnect adapters for AVEVA PI System, Tridium Niagara BMS, and OPC UA; standalone BACnet driver deferred to `STORY-1.5`).
  - **Workstream 2 (Semantic Model at Scale)**: **AUTHORIZED / IN KICKOFF**
  - **Workstreams 3–9**: **PLANNED** (EnPI Engine completeness, Anomaly CUSUM drift engine `PHASE-5-ANOM-001`, Action PDCA, Building Analytics, Multi-Tenancy, Operability DR drills, Security pentest).

---

## Known Gaps

### Not Covered:
- **Protocol Adapter Handling of Mid-Flight TCP Socket Death**: Connection reset or abrupt socket termination while an HTTP/streaming request is in flight. The current adapter test suite covers connect-refused and error-wrapper handling. Mid-flight socket death at the adapter layer is tracked as **`STORY-1.6 / PHASE-5-ADP-001`**.

### Covered at a Different Layer:
- **Edge Gateway Store-and-Forward Under Full WAN Loss**: Verified via `tools/test_edge_wan_loss.py`. This validates local edge gateway buffer resilience, not protocol adapter layer resilience.

---

## Strategic License Rationale
VerdantOS is released under the **Apache 2.0 License** to promote open-architecture enterprise adoption, vendor neutrality, and community contributions. The Apache 2.0 license permits any commercial use, including proprietary forks and white-label enterprise deployments.

---

## Core Platform Capabilities

1. **English-First Standard**: 100% of user interfaces, API contracts, logs, and generated reports natively created in English.
2. **Extended Brick Schema & Project Haystack Asset Graph**: Hybrid semantic asset graph storing physical equipment relationships, ltree path hierarchies, and JSONB tag sets.
3. **Tri-State Anomaly Detection**: Rule-path decision tree distinguishing `SENSOR_FAULT` (out-of-bounds/hardware errors), `OPERATIONAL_CHANGE` (scheduled overrides), and `REAL_ENERGY_WASTE` (>30% baseline deviation).
4. **Cryptographic SHA-256 ISO 50001 Audit Trail**: Immutable ledger tracking energy policy approvals, SEU registrations, baseline changes, and PDCA action items with standalone verification CLI (`tools/audit_verify.py`).
5. **Tiered Edge Memory Profiles**: Go-based edge store-and-forward gateway supporting `minimal` (~50MB RAM limit), `standard` (~150MB RAM limit), and `full` (~300MB RAM limit) Docker Compose container overlays.

---

## Quickstart & Local Bring-Up

### Prerequisites
- Docker Engine 24.0+ & Docker Compose 2.20+
- Python 3.11+

### Single-Command Local Full Stack Bring-Up
```bash
# Clone repository
git clone https://github.com/hajianamir/EnmS-Suite.git
cd EnmS-Suite

# Copy development environment variables template
cp .env.example .env

# Bring up Postgres, Redis, Kafka, Schema Registry, Keycloak OIDC, 6 Spine Services, Web Dashboard, and Edge Profile Overlays
docker-compose up -d
```

### Verification & Automated Test Runners
```bash
# Validate ISO 50001 Traceability Matrix
python3 tools/ci_validate_traceability.py

# Verify Multi-Tenant PostgreSQL RLS Policy Negative Matrix
python3 tools/test_rls_negative_matrix.py

# Verify Edge Gateway WAN-Loss Store-and-Forward Reconnection (3 Profiles)
python3 tools/test_edge_wan_loss.py

# Verify Cryptographic SHA-256 Audit Trail Hash Chain
python3 tools/audit_verify.py docs/slice/composite_audit_pack.json

# Run Labeled Anomaly Dataset Classifier Evaluation Suite (14 Cases)
python3 services/anomaly-stream/tests/test_labeled_dataset.py

# Run CUSUM Cumulative Drift Evaluation Suite (432,000 Points across 10 Random Seeds)
python3 services/anomaly-stream/tests/test_cusum_drift.py
```

---

## Security & Governance
- Security Vulnerability Reporting Policy: See [SECURITY.md](SECURITY.md)
- Contribution Guidelines: See [CONTRIBUTING.md](CONTRIBUTING.md)
- Open Source License: Apache 2.0 License. See [LICENSE](LICENSE)
