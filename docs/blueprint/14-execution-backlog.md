# 14. Execution Backlog (Epics & User Stories)

## Epic 1: Edge Gateway & Protocol Ingestion
- **Story 1.1**: *As a Systems Engineer, I want the edge gateway to collect BACnet/IP points every 60 seconds so that telemetry is captured accurately.*
  - *Acceptance Criteria*: Gateway polls up to 1,000 BACnet points with $< 1\%$ drop rate; caches locally if offline.
- **Story 1.2**: *As an Operator, I want store-and-forward disk queueing so that no telemetry is lost during WAN outages.*
  - *Acceptance Criteria*: Gateway writes to local SQLite buffer when internet connection drops; back-fills cloud TSDB upon reconnection without duplicating timestamps.

## Epic 2: Semantic Asset Layer & EnPI Engine
- **Story 2.1**: *As an Energy Manager, I want to create a multi-variable regression baseline model so that I can calculate weather-adjusted savings.*
  - *Acceptance Criteria*: System computes $R^2$, $p\text{-value}$, and regression coefficients for energy vs HDD/CDD; saves versioned baseline model.
- **Story 2.2**: *As an ISO Auditor, I want an automated audit pack generation button so that I can review immutable evidence.*
  - *Acceptance Criteria*: One-click PDF generation containing SEU analysis, baseline equations, CUSUM graphs, and SHA-256 cryptographic verification hashes.
