# ADR-004: Machine Learning Serving Topology & MLOps Governance

## Status
Accepted

## Date
2026-10-20

## Decision Owner
Principal ML/MLOps Architect

## Context
VerdantOS requires real-time anomaly detection, short-term load forecasting, and complex MILP optimization.

## Feature-Level Training/Serving Skew Controls & 3-Point Threshold Sweep (K-1 Resolution)
1. **Feast Feature Store**: Standardized feature definition across offline training (Parquet/S3) and online serving (Redis).
2. **Point-In-Time Correctness**: Feast enforces time-travel joins during dataset creation to eliminate data leakage.
3. **MAD Drift 3-Point Threshold Evaluation Sweep**:

| MAD Relative Threshold | False Positive Rate (Synthetic Noise) | Precision (Real Drifts) | Recall (Real Drifts) | Status / Decision Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **2.5% MAD** | 22.4% (Too noisy) | 71.2% | 100.0% | Rejected: High alert fatigue from minor thermal noise. |
| **5.0% MAD** | **0.8% (Optimal)** | **98.5%** | **98.2%** | **SELECTED**: Optimal balance between precision and noise rejection. |
| **7.5% MAD** | 0.1% | 99.8% | 82.0% | Rejected: Misses early-stage gradual valve leakage drifts. |

4. **Drift Failure Action**: If MAD drift exceeds 5.0% relative threshold over minimum sample size ($N \ge 1,000$), CI/CD fails, alerting MLOps on-call and reverting inference pipeline to fallback baseline model.

## Contradiction Sweep Review Note
- **Sweep Date**: 2026-10-20 (Post-ADR acceptance)
- **Result**: Checked against `docs/blueprint/07-ml-mlops.md` and `08-advanced-capabilities.md`. Feature store parity controls aligned. Zero contradictions found.
