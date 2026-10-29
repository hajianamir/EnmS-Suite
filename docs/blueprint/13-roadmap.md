# 13. Product Roadmap (MoSCoW Prioritization)

## 13.1 Phase 1: MVP Release (Commercial Campus Anchor)
- **Must Have**:
  - Ingestion via Modbus TCP/RTU, BACnet/IP, and MQTT.
  - Edge Gateway store-and-forward engine with SQLite disk buffer.
  - Semantic Asset Graph (PostgreSQL `ltree` schema with Brick/Haystack tags).
  - EnPI & Baseline Engine (MLR regression, HDD/CDD normalization).
  - Anomaly Detection (Statistical thresholds + rule-based sensor fault separation).
  - Closed-loop Action Items & PDCA workflow.
  - Basic ISO 50001 Audit Pack PDF export.
  - English-first Web Dashboard in React.
- **Should Have**:
  - Auto-discovery for BACnet IP network devices.
  - High-resolution CSV/XLSX custom reports exporter.
- **Could Have**:
  - Simple single-variable XGBoost load forecasting.
- **Won't Have (Phase 1)**:
  - Federated learning, OPC UA industrial protocol suite, CBAM export.

## 13.2 Phase 2: Industrial Expansion & Operational ML
- **Must Have**:
  - OPC UA, DL/T645, and IEC 61850 protocol adapters.
  - Production-normalized EnPI (consumption per product, shift, batch, order).
  - Full MLOps engine (MLflow, Feast Feature Store, PSI/KS drift monitoring).
  - AVEVA PI System & SAP PM CMMS integrations.
  - Constraint-Aware Setpoint Optimization Engine (MILP).
- **Should Have**:
  - Energy Digital Twin scenario simulation.
  - RAG-based AI Assistant over asset manuals and ISO documentation.

## 13.3 Phase 3: Global Enterprise & Smart Grid Integration
- **Must Have**:
  - Privacy-preserving Federated Learning for multi-site deployments.
  - DER (Distributed Energy Resources) & Battery Storage Demand Response dispatch.
  - Full CBAM (Carbon Border Adjustment Mechanism) embedded carbon calculations.
- **Should Have**:
  - Automated tariff optimization and spot market bidding integrations.
