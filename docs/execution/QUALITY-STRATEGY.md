# Phase 2 — Quality & Testing Strategy

## 1. Test Pyramid Targets

| Layer / Test Type | Target Coverage | Tooling & Harness | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | >= 80% line coverage | Go test, PyTest, Jest | Block PR merge in GitHub Actions |
| **Contract / Schema Tests** | 100% API & Event schemas | Spectral, Schema Registry | Block PR if contract breaks |
| **Integration Tests** | All API Endpoints & DDL | Testcontainers (Postgres, Kafka) | CI nightly test runner |
| **Security / RLS Tests** | 100% Tenant isolation | Custom RLS negative test suite | CI required security check |
| **Performance / Load Tests**| 500k points/sec target | k6 / Locust streaming harness | Staging release gate |
