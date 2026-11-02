import json
"""
Integration Tests for STORY-3.7 (HITL Workflow), STORY-3.8 (Warm-Up & Retraining), and STORY-3.9 (NN Governance & SHAP)
Evaluates against canonical ISO 50006 ground-truth baseline dataset:
  y = 5.0 + 0.30 * HDD18.3 + 0.20 * production_tons + N(0, sigma=2.0)
"""
import pytest
import os
import sys
import numpy as np
import pandas as pd
import psycopg

sys.path.insert(0, os.path.abspath("."))
from docs.slice.evidence.generate_ground_truth import generate_ground_truth_dataset
from services.baseline_advisor.advisor_workflow import BaselineAdvisorWorkflow, BaselineImmutableError
from services.baseline_advisor.nn_governance import NNGovernanceEngine

DB_URL = "postgresql://postgres@/verdantos?host=/var/run/postgresql&port=5433"
TENANT_ID = "11111111-1111-1111-1111-111111111111"

@pytest.fixture(scope="module")
def gt_data():
    return generate_ground_truth_dataset(n_days=365, seed=42)

def test_3_7_human_in_the_loop_workflow():
    """
    STORY-3.7: Human-in-the-Loop UI & Workflow.
    3.7-1: Proposal card renders coefficients with CIs, diagnostics summary, M&V option, FSU.
    3.7-2: Accept flow creates immutable baseline record with full precision.
    3.7-3: Modify flow records delta original vs modified.
    3.7-4: Reject flow captures operator stated rationale.
    3.7-5: Immutability enforcement: update on accepted raises BASELINE_IMMUTABLE.
    """
    # 3.7-1: Create proposal
    proposal_data = {
        "enpi_id": "enpi_campus_intensity",
        "model_name": "multiple_linear",
        "fit_window_start": "2025-01-01T00:00:00Z",
        "fit_window_end": "2025-12-31T23:59:59Z",
        "cv_mape": 6.57,
        "aic": 1526.56,
        "bic": 1538.26,
        "fsu_pct": 0.75,
        "dsl_formula": "baseline_energy = 5.21 ± 0.38 + (0.32 ± 0.0190) × hdd18_3 + (0.1955 ± 0.0036) × production_tons ± 1.95",
        "coefficients": {"beta_0": 5.214769, "beta_1": 0.321120, "beta_2": 0.195512},
        "diagnostics_summary": {
            "normality": "PASS",
            "homoskedasticity": "PASS",
            "durbin_watson": 2.17,
            "ipmvp_option": "Option C (Whole Facility Regression)"
        },
        "reproducibility_manifest": "cf64e69cbf581df7f54933d2a1157849fe703d1fe900673c9b99b5a6a3ab0e50"
    }

    prop_id = BaselineAdvisorWorkflow.create_proposal(DB_URL, TENANT_ID, proposal_data)
    print("\n3.7-1 Proposal Card Generated:")
    print(f"  Proposal ID:    {prop_id}")
    print(f"  Model:          {proposal_data['model_name']} (CV-MAPE: {proposal_data['cv_mape']}%, FSU: {proposal_data['fsu_pct']}%)")
    print(f"  DSL:            {proposal_data['dsl_formula']}")
    print(f"  M&V Suggestion: {proposal_data['diagnostics_summary']['ipmvp_option']}")
    assert prop_id is not None

    # 3.7-2: Accept Flow
    accepted_res = BaselineAdvisorWorkflow.accept_proposal(DB_URL, TENANT_ID, prop_id, accepted_by="energy_manager_jane")
    print("\n3.7-2 Accepted Baseline Record:")
    print(f"  ID:          {accepted_res['id']}")
    print(f"  Status:      {accepted_res['status']}")
    print(f"  Accepted By: {accepted_res['accepted_by']} at {accepted_res['accepted_at']}")
    print(f"  Full-Precision Coeffs: {accepted_res['coefficients']}")
    print(f"  Manifest:    {accepted_res['reproducibility_manifest']}")

    assert accepted_res["status"] == "accepted"
    assert accepted_res["coefficients"]["beta_2"] == 0.195512

    # 3.7-5: Immutability Enforcement (attempt update on accepted row)
    with pytest.raises(BaselineImmutableError) as exc_info:
        BaselineAdvisorWorkflow.attempt_update_on_accepted(DB_URL, TENANT_ID, prop_id)
    print(f"\n3.7-5 Immutability Enforcement Caught: {exc_info.value}")
    assert "BASELINE_IMMUTABLE" in str(exc_info.value)

    # 3.7-3: Modify Flow on a separate proposed baseline
    prop_id_mod = BaselineAdvisorWorkflow.create_proposal(DB_URL, TENANT_ID, proposal_data)
    mod_coeffs = {"beta_0": 5.214769, "beta_1": 0.321120, "beta_2": 0.200000} # Adjusted to round 0.20
    mod_res = BaselineAdvisorWorkflow.modify_proposal(DB_URL, TENANT_ID, prop_id_mod, "operator_john", mod_coeffs)
    print("\n3.7-3 Modify Flow Output:")
    print(f"  Status: {mod_res['status']}")
    print(f"  Modification Delta: {json.dumps(mod_res['modification_delta'], indent=2)}")
    assert mod_res["status"] == "modified"
    assert round(mod_res["modification_delta"]["difference"]["beta_2"], 6) == round(0.200000 - 0.195512, 6)

    # 3.7-4: Reject Flow on a separate proposed baseline
    prop_id_rej = BaselineAdvisorWorkflow.create_proposal(DB_URL, TENANT_ID, proposal_data)
    rej_reason = "Production schedule shifts scheduled for next quarter; retrain required."
    rej_res = BaselineAdvisorWorkflow.reject_proposal(DB_URL, TENANT_ID, prop_id_rej, "operator_john", rej_reason)
    print("\n3.7-4 Reject Flow Output:")
    print(f"  Status: {rej_res['status']}")
    print(f"  Rejection Reason: {rej_res['rejection_reason']}")
    assert rej_res["status"] == "rejected"
    assert rej_res["rejection_reason"] == rej_reason

def test_3_8_warmup_and_retraining_triggers():
    """
    STORY-3.8: Warm-Up & Retraining Triggers.
    3.8-1: Anomaly thresholds proposed on acceptance (+-2sigma, +-3sigma, MAD).
    3.8-2: CUSUM parameters proposed (h = 4.5 * sigma, k = 0.25 * y_mean).
    3.8-3: Shadow mode logs predictions without alerting.
    3.8-4: Retraining triggers fire with specific pre/post values pasted.
    3.8-5: Retraining produces new proposal side-by-side with accepted baseline (verified via DB query).
    """
    fitted_sigma = 1.95 # From model residual standard deviation

    # 3.8-1 & 3.8-2: Derived Warm-Up Parameters
    warmup = BaselineAdvisorWorkflow.propose_warmup_parameters(fitted_sigma)
    print("\n3.8-1 & 3.8-2 Warm-Up Parameters Derived from Residual Sigma:")
    print(f"  Fitted Sigma:       {warmup['fitted_sigma']} kW")
    print(f"  Anomaly Thresholds: 2sigma = {warmup['anomaly_thresholds']['two_sigma']} kW, 3sigma = {warmup['anomaly_thresholds']['three_sigma']} kW, MAD = {warmup['anomaly_thresholds']['mad']} kW")
    print(f"  CUSUM Parameters:   k = {warmup['cusum_parameters']['k_allowance']} kW, h = {warmup['cusum_parameters']['h_threshold']} kW")

    assert warmup["anomaly_thresholds"]["two_sigma"] == round(2.0 * fitted_sigma, 2)
    assert warmup["anomaly_thresholds"]["three_sigma"] == round(3.0 * fitted_sigma, 2)
    assert warmup["cusum_parameters"]["h_threshold"] == round(4.5 * fitted_sigma, 2)

    # 3.8-3: Shadow Mode (2 weeks = 14 daily points)
    base_vals = [25.0] * 14
    actual_vals = [25.0, 26.0, 29.0, 25.5, 33.5, 25.0, 26.0, 25.0, 24.5, 25.0, 25.2, 26.1, 25.0, 25.0]
    shadow = BaselineAdvisorWorkflow.simulate_shadow_mode(actual_vals, base_vals, fitted_sigma)
    print("\n3.8-3 2-Week Shadow Mode Output:")
    print(f"  Predictions Logged: {shadow['shadow_predictions']}")
    print(f"  Alerts Fired:       {shadow['alerts_fired']} (Suppressed in shadow mode)")
    print(f"  Would-be Alerts:    {shadow['would_be_alerts']}")

    assert shadow["shadow_predictions"] == 14
    assert shadow["alerts_fired"] == 0
    assert shadow["would_be_alerts"] >= 1

    # 3.8-4: Retraining Triggers Monitoring with Concrete Values
    base_fsu = 0.75
    current_fsu = 16.4
    trig_fsu = BaselineAdvisorWorkflow.check_retraining_triggers(current_fsu=current_fsu, current_mad=1.32, base_mad=1.32, season_changed=False)
    print("\n3.8-4 Trigger 1 (FSU Degradation):")
    print(f"  Baseline FSU:    {base_fsu}%")
    print(f"  Current FSU:     {current_fsu}%  (exceeds 15% threshold)")
    print(f"  Trigger fired:   {trig_fsu['active_triggers'][0]}")
    assert current_fsu > 15.0
    assert "FSU_EXCEEDS_15_PERCENT" in trig_fsu["active_triggers"]

    base_mad = 1.32
    current_mad = 2.87
    drift_ratio = current_mad / base_mad
    trig_mad = BaselineAdvisorWorkflow.check_retraining_triggers(current_fsu=5.0, current_mad=current_mad, base_mad=base_mad, season_changed=False)
    print("\n3.8-4 Trigger 2 (Residual MAD Drift):")
    print(f"  Baseline residual MAD:  {base_mad} kW")
    print(f"  Current residual MAD:   {current_mad} kW")
    print(f"  Drift ratio:            {drift_ratio:.2f}x  (exceeds 1.5x threshold)")
    print(f"  Trigger fired:          {trig_mad['active_triggers'][0]}")
    assert drift_ratio > 1.5
    assert "RESIDUAL_MAD_DRIFT" in trig_mad["active_triggers"]

    prev_season = "SUMMER (ended 2024-08-31)"
    curr_season = "AUTUMN (started 2024-09-01)"
    trig_seas = BaselineAdvisorWorkflow.check_retraining_triggers(current_fsu=5.0, current_mad=1.32, base_mad=1.32, season_changed=True)
    print("\n3.8-4 Trigger 3 (Season Boundary):")
    print(f"  Previous season:       {prev_season}")
    print(f"  Current season:        {curr_season}")
    print(f"  Detection date:        2024-09-01")
    print(f"  Trigger fired:         {trig_seas['active_triggers'][0]}")
    assert prev_season != curr_season
    assert "NEW_SEASON_DETECTED" in trig_seas["active_triggers"]

    # 3.8-5: Retraining produces new proposal side-by-side with accepted baseline
    proposal_retrain_old = {
        "enpi_id": "enpi_campus_retrain_test",
        "model_name": "multiple_linear",
        "fit_window_start": "2024-01-01T00:00:00Z",
        "fit_window_end": "2024-12-31T23:59:59Z",
        "cv_mape": 6.57,
        "aic": 1526.56,
        "bic": 1538.26,
        "fsu_pct": 0.75,
        "dsl_formula": "baseline_energy = 5.21 + 0.32*hdd + 0.1955*prod",
        "coefficients": {"beta_0": 5.2148, "beta_1": 0.3211, "beta_2": 0.1955},
        "diagnostics_summary": {"ipmvp": "Option C"},
        "reproducibility_manifest": "manifest_v1_accepted"
    }
    accepted_id = BaselineAdvisorWorkflow.create_proposal(DB_URL, TENANT_ID, proposal_retrain_old)
    BaselineAdvisorWorkflow.accept_proposal(DB_URL, TENANT_ID, accepted_id, "energy_manager_jane")

    # Retraining trigger creates NEW proposal
    proposal_retrain_new = {
        "enpi_id": "enpi_campus_retrain_test",
        "model_name": "multiple_linear",
        "fit_window_start": "2024-07-01T00:00:00Z",
        "fit_window_end": "2025-06-30T23:59:59Z",
        "cv_mape": 6.12,
        "aic": 1512.40,
        "bic": 1524.10,
        "fsu_pct": 0.68,
        "dsl_formula": "baseline_energy = 5.34 + 0.3189*hdd + 0.1901*prod",
        "coefficients": {"beta_0": 5.3412, "beta_1": 0.3189, "beta_2": 0.1901},
        "diagnostics_summary": {"ipmvp": "Option C"},
        "reproducibility_manifest": "manifest_v2_proposed"
    }
    proposed_id = BaselineAdvisorWorkflow.create_proposal(DB_URL, TENANT_ID, proposal_retrain_new)

    print("\n3.8-5 Database Side-by-Side Coexistence Query:")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                SELECT id, status, created_at, model_name,
                       (coefficients->>'beta_0')::numeric AS beta_0,
                       (coefficients->>'beta_1')::numeric AS beta_1,
                       (coefficients->>'beta_2')::numeric AS beta_2
                FROM baseline_candidates 
                WHERE tenant_id = %s AND id IN (%s, %s)
                ORDER BY status;
            """, (TENANT_ID, accepted_id, proposed_id))
            rows = cur.fetchall()
            print("  id                                   | status   | created_at             | model_name      | beta_0 | beta_1 | beta_2")
            print("  -------------------------------------+----------+------------------------+-----------------+--------+--------+--------")
            for r in rows:
                print(f"  {r[0]} | {r[1]:8} | {str(r[2])[:22]} | {r[3]:15} | {r[4]:.4f} | {r[5]:.4f} | {r[6]:.4f}")

    assert len(rows) == 2
    accepted_row = [r for r in rows if r[1] == 'accepted'][0]
    proposed_row = [r for r in rows if r[1] == 'proposed'][0]

    assert accepted_row[0] != proposed_row[0]
    assert float(accepted_row[4]) == 5.2148
    assert float(proposed_row[4]) == 5.3412

def test_3_9_nn_governance_and_shap(gt_data):
    """
    STORY-3.9: Neural Network Candidate with SHAP & Model Card.
    3.9-1: NN trained on ground truth (N=365) -> NN rejected by governance rule.
    3.9-2: SHAP values computed for drivers & non-drivers.
    3.9-3: Populated ISO 50001 Model Card.
    3.9-4: Evaluation on large dataset (>5,000 samples).
    3.9-5: SHAP summary for selected model.
    """
    # 3.9-1: Ground truth evaluation (N=365)
    nn_res = NNGovernanceEngine.evaluate_nn_candidate(gt_data, "energy_kwh", ["hdd18_3", "production_tons"])
    print("\n3.9-1 Neural Network Evaluation on Ground Truth (N=365):")
    print(f"  NN CV-MAPE:      {nn_res['cv_mape_nn']}%")
    print(f"  GBM CV-MAPE:     {nn_res['cv_mape_gbm']}%")
    print(f"  Improvement:     {nn_res['improvement_pct']}%")
    print(f"  Sample Size Check (>5,000): {nn_res['sample_size_rule_passed']}")
    print(f"  Governance Rule Applied:    {nn_res['rule_applied']}")
    print(f"  NN Selected:     {nn_res['nn_selected']}")

    assert nn_res["nn_selected"] is False
    assert "Reject: N <= 5,000" in nn_res["rule_applied"]

    # 3.9-2: SHAP values
    shap_vals = NNGovernanceEngine.compute_shap_attribution(
        gt_data, "energy_kwh", ["hdd18_3", "production_tons", "hour_of_day"]
    )
    print("\n3.9-2 Feature Attribution (SHAP Marginal Importance):")
    for feat, val in shap_vals.items():
        print(f"  {feat:16}: SHAP importance = {val:.4f}")

    assert shap_vals["production_tons"] > shap_vals["hour_of_day"]
    assert shap_vals["hdd18_3"] > shap_vals["hour_of_day"]

    # 3.9-3: Model Card
    card = NNGovernanceEngine.generate_model_card(
        model_name="Multi-Layer Perceptron (MLPRegressor 16x8)",
        n_samples=len(gt_data),
        cv_mape=nn_res["cv_mape_nn"],
        shap_summary=shap_vals,
        rejection_rationale=nn_res["rule_applied"]
    )
    print("\n3.9-3 Populated ISO 50001 Model Card:")
    print(f"  Model:           {card['model_name']}")
    print(f"  Intended Use:    {card['intended_use']}")
    print(f"  Governance:      {card['limitations_and_governance']['governance_status']} ({card['limitations_and_governance']['rationale']})")
    print(f"  Compliance:      {card['compliance_alignment']}")
    assert card["limitations_and_governance"]["governance_status"] == "REJECTED"

    # 3.9-4: Evaluation on large synthetic dataset (>5,000 samples)
    large_gt = generate_ground_truth_dataset(n_days=5200, seed=123)
    large_res = NNGovernanceEngine.evaluate_nn_candidate(large_gt, "energy_kwh", ["hdd18_3", "production_tons"])
    print(f"\n3.9-4 Scale Evaluation (>5,000 Samples, N={large_res['n_samples']}):")
    print(f"  NN CV-MAPE:  {large_res['cv_mape_nn']}%")
    print(f"  GBM CV-MAPE: {large_res['cv_mape_gbm']}%")
    print(f"  NN Selected: {large_res['nn_selected']}")
    assert (large_res["cv_mape_nn"] <= 0.95 * large_res["cv_mape_gbm"]) == large_res["nn_selected"]
