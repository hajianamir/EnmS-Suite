# Phase 2 — Decomposed Execution Backlog

## Epic 1: Core Platform & Protocol Ingestion Spine
- **STORY-1.1**: Deploy PostgreSQL + TimescaleDB Migration Pipeline (`AC-03a`)
  - *Context*: Execute audited DDL SQL schema from Section 5.
  - *DoR*: Schema reviewed; migration tool selected (Golang-migrate/Flyway).
  - *DoD*: Migration runs clean in CI; RLS negative test passes (`AC-03d`).
- **STORY-1.2**: Go Edge Gateway BACnet/IP Adapter (`AC-01b`)
  - *Context*: Implement BACnet polling loop with store-and-forward SQLite buffer.
  - *DoR*: BACnet point schema defined.
  - *DoD*: Polling loop reads 1,000 points/min; store-and-forward queues during WAN offline simulation.

- **STORY-1.3 / PHASE-5-DISC-001**: BACnet/IP Broadcast WHO-IS & OPC UA Endpoint Auto-Discovery (`AC-01b`)
  - *Target Phase*: Phase 5 Workstream 2
  - *Status*: **`DEFERRED`** — see Target Phase.
  - *AC Checklist*:
    - [ ] Implement BACnet WHO-IS/I-AM broadcast listener
    - [ ] Implement OPC UA GetEndpoints/FindServers discovery
    - [ ] Auto-populate discovered field devices into staging asset graph
    - [ ] $> 95\%$ discovery rate on local subnet without operator manual entry

- **STORY-1.4 / PHASE-5-CMD-001**: Tridium Niagara Command Path with Safety Interlocks & Audit Logging (`AC-01b`)
  - *Target Phase*: Phase 5 Workstream 5
  - *Status*: **`DEFERRED`** — see Target Phase.
  - *AC Checklist*:
    - [ ] Implement Niagara control write endpoint (`POST /ord/setpoint`)
    - [ ] Enforce safety interlock check rules (temperature/pressure bounds)
    - [ ] SHA-256 cryptographic audit logging for setpoint change attempts
    - [ ] Block out-of-bounds command attempts with audited nonconformity record

- **STORY-1.5 / PHASE-5-BAC-001**: Standalone Native Go BACnet/IP ReadProperty Driver (`AC-01b`)
  - *Target Phase*: Phase 5 Workstream 2
  - *Status*: **`DEFERRED`** — see Target Phase.
  - *AC Checklist*:
    - [ ] Integrate Go `gobacnet` native protocol stack
    - [ ] Implement ReadProperty/ReadPropertyMultiple polling loops
    - [ ] Device-level connection error handling & socket reconnect
    - [ ] Poll 1,000 BACnet/IP points/min with $< 1\%$ drop rate on non-Niagara sites

## Epic 2: Semantic Asset Graph & EnPI Engine
- **STORY-2.1**: Asset Tree Graph API with ltree Index (`AC-01b`)
  - *Context*: REST/GraphQL endpoints for traversing asset trees.
  - *DoR*: Asset schema and OpenAPI spec defined.
  - *DoD*: Subtree query latency < 10ms for 10,000 assets.
- **STORY-2.2**: EnPI Formula DSL Evaluator (`AC-07a`)
  - *Context*: Python EBNF parser and unit dimensional checker.
  - *DoR*: EBNF grammar specification completed.
  - *DoD*: Evaluator parses valid formulas and rejects unit mismatches.

## Epic 3: Phase 5 Advanced Anomaly Engine & Cumulative CUSUM Drift
- **STORY-3.1 / PHASE-5-ANOM-001**: Cumulative CUSUM Drift Detection for Gradual Valve Degradation (`AC-08a`)
  - *Target Phase*: Phase 5 Workstream 4
  - *Status*: **`IN_PROGRESS`** — see Target Phase.
  - *AC Checklist*:
    - [x] Implement CUSUM drift calculation module (`services/anomaly-stream/cusum_drift.py`)
    - [x] Magnitude sweep testing (+10%, +15%, +20%, +25%)
    - [x] 30-day baseline noise 10-seed false-positive evaluation ($\le 5\%$ target; achieved $0.00\%$)
    - [x] 14-day linear and exponential ramp duration tests
    - [x] Document calibration parameters $k=0.12$ and $h=4.5\sigma$

- **STORY-1.6 / PHASE-5-ADP-001**: Mid-Flight TCP Socket Termination Adapter Resilience (`AC-01b`)
  - *Target Phase*: Phase 5 Workstream 1.2
  - *Status*: **`DEFERRED`** — see Target Phase.
  - *AC Checklist*:
    - [ ] Establish active streaming session
    - [ ] Simulate mid-flight TCP socket termination (kill active connection socket mid-request)
    - [ ] Catch `ConnectionResetError` / `RemoteDisconnected` exception
    - [ ] Verify zero data loss via sequence counter buffer replay
