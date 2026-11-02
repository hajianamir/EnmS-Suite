"""
Integration Tests for STORY-3.4 (Selection & Diagnostics) & STORY-3.6 (EnPI DSL Formula Synthesis)
Evaluates against canonical ISO 50006 ground-truth baseline dataset:
  y = 5.0 + 0.30 * HDD18.3 + 0.20 * production_tons + N(0, sigma=2.0)
"""
import pytest
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))
from docs.slice.evidence.generate_ground_truth import generate_ground_truth_dataset
from services.baseline_advisor.model_battery import ModelCandidateBattery
from services.baseline_advisor.selection_diagnostics import SelectionDiagnosticsEngine
from services.baseline_advisor.formula_synthesis import FormulaSynthesisEngine, UnitDimensionalError

@pytest.fixture(scope="module")
def gt_data():
    return generate_ground_truth_dataset(n_days=365, seed=42)

def test_3_4_selection_and_diagnostics(gt_data):
    """
    STORY-3.4: Selection & Diagnostics Battery.
    3.4-1: Fold-by-fold walk-forward cross validation.
    3.4-3: IPMVP Fractional Savings Uncertainty (FSU < 15%).
    3.4-4: Residual diagnostics (Normality, Heteroskedasticity, Autocorrelation, Cook's distance).
    3.4-5: Multi-seed model comparison stability.
    """
    # 3.4-1: Fold-by-fold CV
    cv_res = SelectionDiagnosticsEngine.evaluate_walk_forward_folds(
        gt_data, "energy_kwh", ["hdd18_3", "production_tons"], n_splits=5
    )
    print("\n3.4-1 Fold-by-Fold Walk-Forward Cross Validation:")
    for f in cv_res["folds"]:
        print(f"  Fold {f['fold']}: MAPE = {f['mape']:>5.2f}%, RMSE = {f['rmse']:>5.2f}")
    print(f"  Mean CV-MAPE:        {cv_res['mean_cv_mape']:.2f}%")
    print(f"  Std dev across folds: {cv_res['std_dev_cv_mape']:.2f}")

    assert cv_res["std_dev_cv_mape"] < 2.0, "Model unstable across walk-forward folds"

    # 3.4-3: IPMVP FSU
    fsu_res = SelectionDiagnosticsEngine.calculate_ipmvp_fsu(
        gt_data, "energy_kwh", ["hdd18_3", "production_tons"]
    )
    print(f"\n3.4-3 IPMVP Fractional Savings Uncertainty (FSU):")
    print(f"  t critical value: {fsu_res['t_stat_crit']}")
    print(f"  MSE:              {fsu_res['mse']}")
    print(f"  y mean:           {fsu_res['y_mean']}")
    print(f"  Computed FSU:     {fsu_res['fsu_pct']}% (Target: < 15.0%)")

    assert fsu_res["fsu_pct"] < 15.0

    # 3.4-4: Residual diagnostics
    diag = SelectionDiagnosticsEngine.run_residual_diagnostics(
        gt_data, "energy_kwh", ["hdd18_3", "production_tons"]
    )
    print("\n3.4-4 Residual Diagnostics Battery:")
    print(f"  Normality (Shapiro-Wilk):       W = {diag['shapiro_w']}, p = {diag['shapiro_p']} (Pass: {diag['normality_pass']})")
    print(f"  Heteroskedasticity (Breusch-Pagan): LM = {diag['breusch_pagan_lm']}, p = {diag['breusch_pagan_p']} (Pass: {diag['homoskedasticity_pass']})")
    print(f"  Autocorrelation (Durbin-Watson): DW = {diag['durbin_watson']} (Pass: {diag['dw_pass']})")
    print(f"  Autocorrelation (Ljung-Box lag10): p = {diag['ljung_box_lag10_p']} (Pass: {diag['ljung_box_pass']})")
    print(f"  Max Cook's D: {diag['max_cooks_d']}")
    print(f"  4/n threshold (n=365): {diag['cooks_threshold_4_n']} - observation crosses mild warning")
    print(f"  D=1.0 threshold (concern): {diag['cooks_threshold_concern']} - observation is far below concern")
    print(f"  Influence Pass: {diag['influence_pass']}")

    assert diag["normality_pass"] is True
    assert diag["homoskedasticity_pass"] is True
    assert diag["dw_pass"] is True
    assert diag["ljung_box_pass"] is True
    assert diag["influence_pass"] is True
    assert diag["max_cooks_d"] < 1.0

    # 3.4-5: Multi-seed model comparison stability
    print("\n3.4-5 Multi-Seed Model Selection Stability:")
    for seed in [42, 137, 2023]:
        df_seed = generate_ground_truth_dataset(n_days=365, seed=seed)
        res_seed = ModelCandidateBattery.evaluate_battery(df_seed, "energy_kwh", ["hdd18_3", "production_tons"])
        w = res_seed["selected_winner"]
        m = res_seed["candidate_models"][w]
        print(f"  Seed {seed:4}: winner = {w:18}, CV-MAPE = {m:>5.2f}%")
        assert w == "multiple_linear"

def test_3_6_formula_synthesis(gt_data):
    """
    STORY-3.6: EnPI DSL Formula Synthesis with ADR-010 Uncertainty.
    3.6-1: DSL formula output.
    3.6-2: DSL parses and evaluates.
    3.6-3: Unit dimensional analysis rejection.
    3.6-4: Uncertainty propagation (extrapolation penalty).
    3.6-5: Reproducibility manifest.
    """
    unit_map = {
        "energy_kwh": "kWh",
        "hdd18_3": "HDD",
        "production_tons": "tons"
    }

    # 3.6-1: Synthesize formula
    synth = FormulaSynthesisEngine.synthesize_dsl_formula(gt_data, "energy_kwh", ["hdd18_3", "production_tons"], unit_map)
    print(f"\n3.6-1 Generated EnPI DSL:\n  {synth['dsl_formula']}")

    c = synth["coefficients"]
    print(f"  Full-precision coefficients:")
    print(f"    intercept:       {c['beta_0']:.6f} ± {c['beta_0_se']:.6f}")
    print(f"    hdd18_3:         {c['beta_1']:.6f} ± {c['beta_1_se']:.6f}")
    print(f"    production_tons: {c['beta_2']:.6f} ± {c['beta_2_se']:.6f}")

    assert 4.5 <= c["beta_0"] <= 5.5
    assert 0.27 <= c["beta_1"] <= 0.33
    assert 0.18 <= c["beta_2"] <= 0.22
    assert c["beta_2_se"] > 0.001, "Production SE must not be displayed as 0.00"

    # 3.6-2: Evaluate DSL dynamically computed from coefficients
    eval_input = {"hdd18_3": 15.0, "production_tons": 200.0}
    expected_y = c["beta_0"] + c["beta_1"] * 15.0 + c["beta_2"] * 200.0
    res_eval = FormulaSynthesisEngine.evaluate_dsl(synth, eval_input)
    print(f"\n3.6-2 DSL Evaluation on input {eval_input}:")
    print(f"  Expected from DSL coeffs: {expected_y:.4f} {synth['target_unit']}")
    print(f"  Actual DSL evaluation:    {res_eval['evaluated_value']:.4f} {res_eval['target_unit']} (FSU={res_eval['fsu_uncertainty_pct']}%)")

    assert abs(res_eval["evaluated_value"] - round(expected_y, 2)) < 0.01

    # 3.6-3: Unit dimensional analysis
    with pytest.raises(UnitDimensionalError) as exc_info:
        FormulaSynthesisEngine.evaluate_dsl(
            synth,
            eval_input,
            input_units={"hdd18_3": "USD", "production_tons": "tons"}
        )
    print(f"\n3.6-3 Unit Mismatch Rejection Caught: {exc_info.value}")
    assert "Unit mismatch" in str(exc_info.value)

    # 3.6-4: Uncertainty propagation: near vs far from training mean
    mean_hdd = synth["training_means"]["hdd18_3"]
    mean_prod = synth["training_means"]["production_tons"]
    near_input = {"hdd18_3": mean_hdd, "production_tons": mean_prod}
    far_input = {"hdd18_3": 0.0, "production_tons": 10.0}

    eval_near = FormulaSynthesisEngine.evaluate_dsl(synth, near_input)
    eval_far = FormulaSynthesisEngine.evaluate_dsl(synth, far_input)
    print(f"\n3.6-4 Uncertainty Propagation:")
    print(f"  Near-training-mean FSU: {eval_near['fsu_uncertainty_pct']}%")
    print(f"  Far-from-training  FSU: {eval_far['fsu_uncertainty_pct']}% (must be higher)")

    assert eval_far["fsu_uncertainty_pct"] > eval_near["fsu_uncertainty_pct"]

    # 3.6-5: Reproducibility manifest
    hash1 = FormulaSynthesisEngine.generate_reproducibility_manifest(synth, seed=42)
    hash2 = FormulaSynthesisEngine.generate_reproducibility_manifest(synth, seed=42)
    print(f"\n3.6-5 Reproducibility Manifest:")
    print(f"  Run 1 Hash: {hash1}")
    print(f"  Run 2 Hash: {hash2}")

    assert hash1 == hash2
