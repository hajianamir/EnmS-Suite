# 15. Risk Register Hardening (R-16) & Operational Assumptions

## 15.1 Hardened Risk Register Matrix

| Risk ID | Risk Description & Impact Area | Severity | Trigger Condition | Leading Indicator | Mitigation Strategy | Mitigation Owner | Residual Risk | Verification Method & Backlog Link |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | OT Protocol Diversity / Field Bus Failures | High | Packet loss > 5% on RS485 bus | Rising retry count on BACnet/Modbus polling | Deploy modular driver architecture with fallback polling and edge buffer | Edge Lead | Intermittent legacy device drops | Integration Test (`Story 1.1`) |
| **RSK-02** | Operator Alert Fatigue from False Positives | High | Operator dismiss rate > 40% | Elevated 1-interval baseline spike counts | Enforce Tri-State classification and requiring 3 consecutive anomalous intervals | Lead Data Scientist | Delayed operator response to minor leaks | Evaluation Protocol Test (`Story 3.1`) |
| **RSK-03** | Extended WAN WAN Outage > Store Capacity | Medium | Local SQLite disk usage > 85% | Edge disk usage warning event | Compress telemetry payloads with Zstd; drop low-priority diagnostics | Infrastructure Lead | Loss of non-critical high-frequency diagnostic data | Edge Buffer Test (`Story 1.2`) |
| **RSK-04** | LLM Prompt Injection in AI Assistant | High | Retrieval of non-tenant document chunks | Vector similarity anomaly on user prompt | Strict RAG tenant isolation, input guardrail classifier, citation checking | AI Security Lead | Refusal response on edge-case queries | RAG Security Suite (`Story 4.2`) |

---

## 15.2 Operational Assumptions
1. Edge gateways have access to local OT networks (VLAN isolation) with outbound mTLS access to cloud API gateway over port 8883 / 443.
2. Tenant facilities have at least 12 months of historical interval meter data available for baseline training during initial onboarding.
| **RSK-05** | Gradual Baseload Drift Un-detected by Single-Interval Cutoff | High | Sustained baseload leak +15% to +25% over 14+ days | Rising 14-day cumulative energy variance | Implement `PHASE-5-ANOM-001` CUSUM cumulative drift model | ML Lead | Minor delayed detection for low-leak events | Integration Test (`STORY-3.1 / PHASE-5-ANOM-001`) |
