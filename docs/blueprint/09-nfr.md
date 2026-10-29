# 9. Quantified Non-Functional Requirements (NFR) & Multi-Tenancy Matrix

## 9.1 Quantified Performance Benchmarks (R-12)

| Category | Quantified Target | Measurement Method | Test Type / Load Profile |
| :--- | :--- | :--- | :--- |
| **Ingestion Throughput** | 500,000 datapoints/sec sustained; 750,000 peak | Kafka Consumer lag & TSDB write rate gauge | Load Test (Locust / k6 streaming) |
| **Telemetry Write Latency** | p50 < 100 ms, p95 < 350 ms, p99 < 500 ms | OpenTelemetry trace span `ingestion.tsdb_write` | Integration & Load Test |
| **Dashboard Read Latency** | p50 < 200 ms, p95 < 800 ms, p99 < 1500 ms | API Gateway HTTP response time metric | Performance Test (30-day query) |
| **System Availability** | 99.95% uptime (SaaS tier) | Synthetic HTTP ping monitor | Reliability / Chaos Engineering |
| **Disaster Recovery RPO** | RPO < 1 minute (streaming WAL replication) | Database replication lag metric | DR Failure Injection Test |
| **Disaster Recovery RTO** | RTO < 1 hour (multi-region failover) | Failover dry-run execution timer | DR Failover Simulation |
| **Edge Gateway Autonomy** | Minimum 30 days offline local store-and-forward | Simulated WAN link disconnection | Edge Resilience Hardware Test |
| **Data Retention Tiers** | Raw: 90 days; 15m aggregates: 2 yrs; 1h: 10 yrs | TimescaleDB hypertable retention policy | Automated Compression Audit |

---

## 9.2 Multi-Tenancy Isolation Matrix (R-13)

| Plan Tier | Compute Isolation | Data Isolation Strategy | Encryption Key Scope | Noisy-Neighbor Controls | Migration Path Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard SaaS (SME)** | Shared Kubernetes pods | Shared DB with PostgreSQL RLS (`tenant_id`) | Shared KMS Key | Per-tenant API rate limits (100 req/min) | Baseline default tier. |
| **Enterprise Cloud** | Dedicated service namespace | Schema-per-tenant on shared DB cluster | Per-tenant KMS Key | Isolated compute resources & memory limits | Live schema export & RLS migration script. |
| **Dedicated / Air-Gapped** | Fully isolated K8s cluster | Dedicated Database instance | Customer-managed KMS (BYOK) | Physical hardware / VPC isolation | Backup & restore to dedicated PostgreSQL. |
