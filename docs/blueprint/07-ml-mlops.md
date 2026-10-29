# 7. ML and MLOps Capabilities

## 7.1 Machine Learning Engines
1. **Load Forecasting Engine**:
   - Short-term (1-24 hours): XGBoost + LSTM / Temporal Fusion Transformer (TFT) for day-ahead peak demand prediction.
   - Medium/Long-term (1-12 months): Prophet / N-BEATS with weather climate scenario projections.
2. **Anomaly Detection & Root Cause Analysis (RCA)**:
   - Isolation Forest / Autoencoder neural networks trained on multi-parameter operating states.
   - SHAP (SHapley Additive exPlanations) values to highlight the top 3 contributing factors to an anomaly (e.g., "High kW caused by: Chiller #1 Condenser Water Temp (+45%), Outdoor RH (+30%)").
3. **Predictive Maintenance**:
   - Remaining Useful Life (RUL) estimation for major rotary equipment (compressors, pumps, fans) using vibration and thermal degradation curves.
4. **Constraint-Aware Optimization**:
   - Mixed-Integer Linear Programming (MILP) / Bayesian Optimization to determine optimal equipment setpoints (e.g., Chilled Water Setpoint) without violating thermal comfort or pressure boundaries.

## 7.2 MLOps Architecture & Governance
- **Feature Store**: Feast / Hopsworks for centralized, leak-free feature engineering across training and real-time inference.
- **Model Registry & Versioning**: MLflow integration tracking model weights, hyperparameter configs, and training datasets.
- **Drift Monitoring Engine**:
  - Data Drift: Kolmogorov-Smirnov (KS) test and Population Stability Index (PSI) on input telemetry distributions.
  - Concept Drift: Continuous tracking of Mean Absolute Percentage Error (MAPE) against ground-truth meter data.
  - Automated Retraining: Automated trigger fires when PSI > 0.25 or MAPE degrades beyond 15% threshold.
- **Model Cards**: Auto-generated documentation for every active ML model detailing training dataset date ranges, accuracy metrics, operational constraints, and failure modes.

---

## 7.3 Model Governance Card Skeleton (R-09)

Every machine learning model deployed in VerdantOS maintains a structured **Model Card** artifact in MLflow:

```yaml
model_card:
  model_id: "ml-load-forecast-xgboost-v1.2"
  model_name: "Short-Term Day-Ahead Load Forecasting Engine"
  owner: "MLOps Architecture Team <mlops@verdantos.com>"
  intended_use: "Predicts 15-minute electrical demand (kW) 24 hours ahead for peak shaving."
  out_of_scope_use: "Not to be used for safety-critical electrical tripping or life-safety controls."
  training_data:
    time_range: "2024-01-01T00:00:00Z to 2026-06-30T23:59:59Z"
    features: ["outdoor_temp_c", "outdoor_humidity_pct", "building_occupancy_ratio", "hour_of_day", "day_of_week"]
    target_variable: "active_power_kw"
  performance_metrics:
    mape: 4.2%
    rmse_kw: 12.8
    r_squared: 0.94
  operational_constraints:
    max_inference_latency_ms: 250
    edge_artifact_size_limit_mb: 50
  drift_triggers:
    psi_threshold: 0.25
    mape_degradation_limit: 15.0%
  rollback_procedure:
    automated_rollback_to: "ml-load-forecast-xgboost-v1.1"
    decision_authority: "Lead ML Engineer"

---

## 7.3 Model Governance Card Skeleton (R-09)

Every machine learning model deployed in VerdantOS maintains a structured **Model Card** artifact in MLflow:

```yaml
model_card:
  model_id: "ml-load-forecast-xgboost-v1.2"
  model_name: "Short-Term Day-Ahead Load Forecasting Engine"
  owner: "MLOps Architecture Team <mlops@verdantos.com>"
  intended_use: "Predicts 15-minute electrical demand (kW) 24 hours ahead for peak shaving."
  out_of_scope_use: "Not to be used for safety-critical electrical tripping or life-safety controls."
  training_data:
    time_range: "2024-01-01T00:00:00Z to 2026-06-30T23:59:59Z"
    features: ["outdoor_temp_c", "outdoor_humidity_pct", "building_occupancy_ratio", "hour_of_day", "day_of_week"]
    target_variable: "active_power_kw"
  performance_metrics:
    mape: 4.2%
    rmse_kw: 12.8
    r_squared: 0.94
  operational_constraints:
    max_inference_latency_ms: 250
    edge_artifact_size_limit_mb: 50
  drift_triggers:
    psi_threshold: 0.25
    mape_degradation_limit: 15.0%
  rollback_procedure:
    automated_rollback_to: "ml-load-forecast-xgboost-v1.1"
    decision_authority: "Lead ML Engineer"
```
