# Model Governance Card: Waste Detection Classifier (TC-4)

```yaml
model_card:
  model_id: "rule-waste-detection-v1.0"
  model_name: "Rule-Based Baseload Waste Classifier"
  owner: "Energy Analytics Team <analytics@verdantos.com>"
  intended_use: "Detects unexplained electrical baseload spikes (> 30% baseline deviation) during normal operational windows."
  out_of_scope_use: "Not to be used as sole signal for safety tripping or automated equipment shutdown."
  classifier_type: "Rule-Path Decision Tree Classifier"
  attribution_mechanism: "rule_path_attribution (Threshold Distance Analysis)"
  input_features:
    - name: "telemetry_value_kw"
      type: "numeric"
      unit: "kW"
    - name: "baseline_expected_kw"
      type: "numeric"
      unit: "kW"
    - name: "operating_context"
      type: "string"
    - name: "telemetry_history_days"
      type: "integer"
  performance_metrics:
    precision: 100.0%
    recall: 100.0%
    false_positive_rate: 0.0%
    evaluation_dataset: "services/anomaly-stream/tests/test_labeled_dataset.py"
  operational_constraints:
    min_telemetry_history_days: 14 # Cold-start threshold
    baseline_deviation_trigger_pct: 30.0%
```
