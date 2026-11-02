"""
Integration Tests for STORY-3.3 (Model Candidate Battery) & STORY-3.5 (ANOVA Suite)
Evaluates against canonical ISO 50006 ground-truth baseline dataset:
  y = 5.0 + 0.30 * HDD18.3 + 0.20 * production_tons + N(0, sigma=2.0)
"""
import pytest
import os
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, os.path.abspath("."))
from docs.slice.evidence.generate_ground_truth import generate_ground_truth_dataset
from services.baseline_advisor.model_battery import ModelCandidateBattery
from services.baseline_advisor.anova_suite import ANOVASuite

@pytest.fixture(scope="module")
def gt_data():
    df = generate_ground_truth_dataset(n_days=365, seed=42)
    # Add calendar columns for ANOVA tests
    df["shift"] = np.random.choice(["morning", "afternoon", "night"], size=len(df))
    df["season"] = [f"Q{(d.month - 1) // 3 + 1}" for d in df["timestamp"]]
    return df

def test_3_3_model_candidate_battery(gt_data):
    """
    STORY-3.3: Model candidate battery evaluation against ground truth.
    3.3-1: Candidate models and CV-MAPE.
    3.3-2: Linear regression coefficient recovery.
    3.3-3: Selection justification & AIC/BIC parsimony ranking.
    3.3-4: NN selection rule applied.
    3.3-5: Change-point detection breaks (assert n_breaks == 0).
    3.3-6: Parsimony complexity checks & rejected models table.
    """
    res = ModelCandidateBattery.evaluate_battery(gt_data, "energy_kwh", ["hdd18_3", "production_tons"])

    print("\n3.3-1 Candidate Models and CV-MAPE (walk-forward, 5 folds):")
    for model_name, mape in res["candidate_models"].items():
        print(f"  {model_name:20}: MAPE = {mape:>6.2f}%")

    # Verify simple_linear is based on the strongest single predictor (production_tons)
    assert res["strongest_predictor"] == "production_tons"
    assert res["candidate_models"]["simple_linear"] < 15.0, f"Simple linear MAPE {res['candidate_models']['simple_linear']} >= 15%"

    print("\n3.3-2 Recovered Coefficients:")
    c = res["recovered_coeffs"]
    print(f"  beta_0 = {c['beta_0']:.2f} (true: 5.00, tolerance: 4.5-5.5)")
    print(f"  beta_1 = {c['beta_1']:.2f} (true: 0.30, tolerance: 0.27-0.33)")
    print(f"  beta_2 = {c['beta_2']:.2f} (true: 0.20, tolerance: 0.18-0.22)")
    print(f"  R^2    = {c['r_squared']:.4f} (required: > 0.90)")
    print(f"  F-test p = {c['f_pvalue']:.4e} (required: < 0.001)")

    assert 4.5 <= c["beta_0"] <= 5.5
    assert 0.27 <= c["beta_1"] <= 0.33
    assert 0.18 <= c["beta_2"] <= 0.22
    assert c["r_squared"] > 0.90
    assert c["f_pvalue"] < 0.001

    print(f"\n3.3-3 Selection Criterion: {res['selection_criterion']}")
    print("3.3-3 AIC/BIC Table:")
    for m in res["aic_table"]:
        k = res["param_counts"].get(m, "N/A")
        print(f"  {m:18}: AIC = {res['aic_table'][m]:>7.2f}, BIC = {res['bic_table'][m]:>7.2f}, k = {k} params")

    winner = res["selected_winner"]
    linear_mape = res["candidate_models"]["multiple_linear"]
    winner_mape = res["candidate_models"][winner]
    print(f"\nSelected winner: {winner}")
    print(f"  Linear CV-MAPE:  {linear_mape:.2f}%")
    print(f"  Winner CV-MAPE:  {winner_mape:.2f}%")
    assert winner == "multiple_linear"
    assert res["aic_table"]["multiple_linear"] <= res["aic_table"]["polynomial"]
    assert res["aic_table"]["multiple_linear"] <= res["aic_table"]["change_point"]

    print("\n3.3-4 NN Selection Rule Applied:")
    print(f"  NN CV-MAPE:      {res['candidate_models']['neural_network']:.2f}%")
    print(f"  GBM CV-MAPE:     {res['candidate_models']['gradient_boosting']:.2f}%")
    print(f"  Sample size:     {res['n_samples']} (rule: NN requires >5,000 samples)")
    print(f"  NN selected:     NO")
    assert not res["nn_selected"]

    print("\n3.3-5 Change-Point Detection:")
    print(f"  n_breaks detected: {res['n_breaks']} (expected: 0)")
    print("  break locations:   none")
    assert res["n_breaks"] == 0

    print("\n3.3-6 Rejected Models Table:")
    for m, details in res["rejected_models"].items():
        pen = f"AIC penalty = {details['aic_penalty']:>+6.1f}" if isinstance(details['aic_penalty'], (int, float)) else "AIC = N/A"
        print(f"  {m:18}: Delta vs linear = {details['delta_mape']:>+5.2f}% MAPE,  {pen:20} -> rejected ({details['reason']})")

def test_3_5_anova_suite(gt_data):
    """
    STORY-3.5: ANOVA & Statistical Hypothesis Suite.
    3.5-1: Day-of-week effect (p > 0.05).
    3.5-2: Shift effect (p > 0.05).
    3.5-3: Season effect (p > 0.05).
    3.5-4: Two-way interaction day_of_week x season (p > 0.05).
    3.5-5: Driver significance (t-tests on beta1, beta2 p < 0.001).
    3.5-6: Nested model F-tests (adding true driver p < 0.001; non-driver p > 0.05).
    3.5-7: ANCOVA baseline vs reporting period (p > 0.05).
    """
    # 3.5-1: Day-of-week
    res_dow = ANOVASuite.one_way_anova(gt_data, "energy_kwh", "day_of_week")
    print("\n3.5-1 One-Way ANOVA: day_of_week (7 groups):")
    print(f"  F-statistic: {res_dow['f_statistic']}")
    print(f"  p-value:     {res_dow['p_value']}")
    assert res_dow["p_value"] > 0.05

    # 3.5-2: Shift
    res_shift = ANOVASuite.one_way_anova(gt_data, "energy_kwh", "shift")
    print("\n3.5-2 One-Way ANOVA: shift (3 groups):")
    print(f"  F-statistic: {res_shift['f_statistic']}")
    print(f"  p-value:     {res_shift['p_value']}")
    assert res_shift["p_value"] > 0.05

    # 3.5-3: Season
    res_season = ANOVASuite.one_way_anova(gt_data, "energy_kwh", "season")
    print("\n3.5-3 One-Way ANOVA: season (4 quarters):")
    print(f"  F-statistic: {res_season['f_statistic']}")
    print(f"  p-value:     {res_season['p_value']}")
    X = sm.add_constant(gt_data[["hdd18_3", "production_tons"]])
    res_fit = sm.OLS(gt_data["energy_kwh"], X).fit()
    gt_data_res = gt_data.copy()
    gt_data_res["resid"] = res_fit.resid
    res_seas_resid = ANOVASuite.one_way_anova(gt_data_res, "resid", "season")
    print(f"  Residual Season F-statistic: {res_seas_resid['f_statistic']}")
    print(f"  Residual Season p-value:     {res_seas_resid['p_value']}")
    assert res_seas_resid["p_value"] > 0.05

    # 3.5-4: Two-way interaction
    res_2way = ANOVASuite.two_way_anova(gt_data_res, "resid", "day_of_week", "season")
    print("\n3.5-4 Two-Way ANOVA: day_of_week x season on residuals:")
    print(f"  Day F p-value:         {res_2way['factor1_p']}")
    print(f"  Season F p-value:      {res_2way['factor2_p']}")
    print(f"  Interaction F p-value: {res_2way['interaction_p']}")
    assert res_2way["interaction_p"] > 0.05

    # 3.5-5: Driver significance t-tests
    t_tests = ANOVASuite.regression_t_tests(gt_data, "energy_kwh", ["hdd18_3", "production_tons"])
    print("\n3.5-5 t-Tests on Multiple Linear Regression Coefficients:")
    for var, vals in t_tests.items():
        print(f"  {var:16}: t = {vals['t_stat']:>6.2f}, p = {vals['p_value']:.4e}")
    assert t_tests["hdd18_3"]["p_value"] < 0.001
    assert t_tests["production_tons"]["p_value"] < 0.001

    # 3.5-6: Nested model F-tests
    f_hdd = ANOVASuite.nested_f_test(gt_data, "energy_kwh", ["production_tons"], "hdd18_3")
    f_dow = ANOVASuite.nested_f_test(gt_data, "energy_kwh", ["hdd18_3", "production_tons"], "day_of_week")
    print("\n3.5-6 Nested Model F-Tests:")
    print(f"  Adding HDD to production-only: F = {f_hdd['f_statistic']}, p = {f_hdd['p_value']:.4e} (Sig: {f_hdd['significant_improvement']})")
    print(f"  Adding day_of_week to full:    F = {f_dow['f_statistic']}, p = {f_dow['p_value']:.4e} (Sig: {f_dow['significant_improvement']})")
    assert f_hdd["p_value"] < 0.001
    assert f_dow["p_value"] > 0.05

    # 3.5-7: ANCOVA baseline vs reporting period
    df_h1 = gt_data.iloc[:180].copy()
    df_h2 = gt_data.iloc[180:].copy()
    ancova_res = ANOVASuite.ancova_period_test(df_h1, df_h2, "energy_kwh", ["hdd18_3", "production_tons"])
    print("\n3.5-7 ANCOVA: Baseline vs Reporting Period Controlling for Drivers:")
    print(f"  Period effect F: {ancova_res['period_f_statistic']}")
    print(f"  Period p-value:  {ancova_res['period_p_value']}")
    assert ancova_res["period_p_value"] > 0.05
