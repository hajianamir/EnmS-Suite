# ADR-001: Selection of TimescaleDB for Time-Series Storage

## Status
Accepted

## Date
2026-10-20

## Decision Owner
Principal Database Architect & Data Engineer

## Context
VerdantOS requires high-throughput ingestion (up to 500,000 telemetry points/sec across clusters) and low-latency querying of time-series energy telemetry. The system must perform complex analytical joins between time-series readings and relational metadata (e.g., asset hierarchy, tenant RLS policies, baseline formulas).

### Query Patterns Assumed
1. **High-Frequency Ingestion**: Single and bulk inserts of 1-minute to 15-minute sensor intervals.
2. **Dashboard Rollups**: 30-day, 90-day, and multi-year aggregations (sum, avg, max, min) by site, building, or asset.
3. **Relational-Time-Series Joins**: Joining meter readings directly with tenant isolation policies and asset attributes.

### Cardinality Model & Retention
- Expected metric series: Up to 10,000,000 active telemetry series across tenants.
- Retention & Downsampling Strategy:
  - Raw 1-minute data: Retained for 90 days.
  - 15-minute continuous aggregates: Retained for 2 years.
  - 1-hour continuous aggregates: Retained for 10 years.
  - Columnar compression enabled after 7 days.

## Rejected Alternatives
- **InfluxDB v2 / v3**: Rejected due to lack of native SQL joins with relational metadata, custom query language (Flux) overhead, and inability to share PostgreSQL Row-Level Security (RLS) policies.

## Decision
Choose **TimescaleDB** (PostgreSQL extension) as the primary time-series database.

## Consequences
- *Positive*: Unifies relational and time-series data under PostgreSQL; supports multi-tenant RLS policies; continuous aggregates simplify rollup queries.
- *Negative*: Disk footprint prior to compression is larger than specialized column stores; requires strict hypertable chunk management.

## Contradiction Sweep Review Note
- **Sweep Date**: 2026-10-20 (Post-ADR acceptance)
- **Result**: Checked against `docs/blueprint/04-architecture.md`, `05-domain-data-model.md`, and `09-nfr.md`. TimescaleDB continuous aggregates and retention policies aligned. Zero contradictions found.
