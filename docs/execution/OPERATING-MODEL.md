# Phase 2 — Engineering Operating Model & SLOs

## 1. Service Level Objectives (SLOs) & Error Budgets
- **Telemetry Ingestion**: 99.95% success rate; error budget = 0.05% per month.
- **API Availability**: 99.9% uptime; error budget = 43.8 minutes downtime per month.
- **Incident Severity**:
  - `SEV-1` (Critical): Ingestion halted or cross-tenant data leak -> 15 min response target.
  - `SEV-2` (Major): Dashboard unavailable or anomaly engine delayed -> 1 hour response target.
