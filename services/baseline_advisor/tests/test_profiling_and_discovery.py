"""
Integration Tests for STORY-3.1 (Data Profiling) & STORY-3.2 (Variable Discovery)
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
from services.baseline_advisor.profiling_engine import DataProfilingEngine
from services.baseline_advisor.variable_discovery import VariableDiscoveryEngine

@pytest.fixture(scope="module")
def gt_data():
    return generate_ground_truth_dataset(n_days=365, seed=42)

def test_3_1_1_sample_rate_and_gap_analysis(gt_data):
    """
    3.1-1: Sample rate and gap analysis on ground-truth dataset.
    """
    res = DataProfilingEngine.analyze_sampling_and_gaps(gt_data["timestamp"].tolist())

    print("\n3.1-1 Sample Rate & Gap Analysis Output:")
    print(f"  Sample count: {res['sample_count']}")
    print(f"  Sample interval distribution: {res['sample_interval_distribution']}")
    print(f"  Gap count: {res['gap_count']}")
    print(f"  Coverage ratio: {res['coverage_ratio']}")

    assert res["sample_count"] == 365
    assert res["gap_count"] == 0
    assert res["coverage_ratio"] == 1.0
    assert "1d x 365 (uniform)" in res["sample_interval_distribution"]

def test_3_1_2_seasonality_detection(gt_data):
    """
    3.1-2: STL seasonality & trend decomposition.
    Ground truth has no true seasonality by construction -> assert seasonal_strength < 0.3.
    """
    res = DataProfilingEngine.evaluate_stl_seasonality(gt_data["energy_kwh"].values, period=7)

    print("\n3.1-2 Seasonality & Trend Strength Output:")
    print(f"  STL seasonal strength:    {res['seasonal_strength']}")
    print(f"  STL trend strength:       {res['trend_strength']}")
    print(f"  Detected seasonal period: {res['detected_seasonal_period']}")

    # Ground truth formula has no calendar seasonality -> assert weak seasonal strength
    assert res["seasonal_strength"] < 0.3, f"False positive: seasonal strength {res['seasonal_strength']} >= 0.3"
    assert res["detected_seasonal_period"] == "none"

def test_3_1_3_stationarity_tests(gt_data):
    """
    3.1-3: Stationarity tests (ADF & KPSS) on raw series and residuals.
    """
    # Calculate OLS residuals from true drivers
    X = np.column_stack([np.ones(len(gt_data)), gt_data["hdd18_3"], gt_data["production_tons"]])
    y = gt_data["energy_kwh"].values
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    residuals = y - X @ beta

    res = DataProfilingEngine.test_stationarity(y, residuals)

    print("\n3.1-3 Stationarity Tests Output:")
    print(f"  Raw series: ADF p-value = {res['raw_adf_p']}, KPSS p-value = {res['raw_kpss_p']}")
    print(f"  Residuals:  ADF p-value = {res['residuals_adf_p']}, KPSS p-value = {res['residuals_kpss_p']}")

    # Driver residuals must be stationary Gaussian noise -> ADF p-value < 0.05
    assert res["residuals_adf_p"] < 0.05, f"Residuals non-stationary: ADF p = {res['residuals_adf_p']}"

def test_3_1_4_outlier_detection(gt_data):
    """
    3.1-4: IQR outlier detection.
    Gaussian noise by construction has ~1.4% (approx 5) outliers at 1.5 * IQR.
    """
    res = DataProfilingEngine.detect_iqr_outliers(gt_data["energy_kwh"].values)

    print("\n3.1-4 Outlier Detection Output:")
    print(f"  IQR outlier count: {res['outlier_count']} (expected: ~5 on 365 samples)")
    print(f"  Outlier percentage: {res['outlier_percentage']}%")

    # In 365 standard normal samples, expect between 0 and 10 outliers (< 3%)
    assert res["outlier_count"] <= 10
    assert res["outlier_percentage"] <= 3.0

def test_3_1_5_pelt_changepoint_detection(gt_data):
    """
    3.1-5: PELT change point detection.
    Constant physical regime by construction -> assert changepoints <= 1.
    """
    res = DataProfilingEngine.detect_pelt_changepoints(gt_data["energy_kwh"].values)

    print("\n3.1-5 Change Point Detection Output:")
    print(f"  PELT change points detected: {res['pelt_changepoints_detected']}")

    # Ground truth has constant coefficients across all 365 days
    assert res["pelt_changepoints_detected"] <= 1

def test_3_2_1_variable_correlation_ranking(gt_data):
    """
    3.2-1: Correlation ranking across candidate variables.
    True drivers: hdd18_3, production_tons.
    Non-drivers: hour_of_day, day_of_week.
    """
    candidates = ["hdd18_3", "production_tons", "day_of_week", "hour_of_day"]
    ranked = VariableDiscoveryEngine.rank_candidate_variables(gt_data, "energy_kwh", candidates)

    print("\n3.2-1 Candidate Variable Ranking Output:")
    for r in ranked:
        print(f"  {r['variable']:16}: Pearson r = {r['pearson_r']:>6.2f}, Spearman rho = {r['spearman_rho']:>6.2f}, MI = {r['mutual_info']:>6.2f}, Granger p = {r['granger_p']:>6.2f}")

    # Map MI scores
    mi_map = {r["variable"]: r["mutual_info"] for r in ranked}

    # HDD and production must significantly outscore non-drivers on mutual information
    # HDD and production must significantly outscore non-drivers on mutual information
    assert mi_map["hdd18_3"] > mi_map["day_of_week"] * 2.0
    assert mi_map["production_tons"] > mi_map["day_of_week"] * 2.0
    assert mi_map["hdd18_3"] >= 0.08
    assert mi_map["production_tons"] >= 0.40

def test_3_2_2_proposed_driver_subset(gt_data):
    """
    3.2-2: Proposed driver subset selection with VIF filtering.
    Asserts exact set equality: proposed_drivers == ['production_tons', 'hdd18_3'] or vice-versa.
    """
    candidates = ["hdd18_3", "production_tons", "day_of_week", "hour_of_day"]
    ranked = VariableDiscoveryEngine.rank_candidate_variables(gt_data, "energy_kwh", candidates)
    subset_res = VariableDiscoveryEngine.select_proposed_driver_subset(gt_data, ranked, vif_threshold=5.0)

    print("\n3.2-2 Proposed Driver Subset Output:")
    print(f"  Proposed drivers: {subset_res['proposed_drivers']}")
    print(f"  VIF scores:       {subset_res['vif_scores']}")
    print(f"  Rejected:         {subset_res['rejected']}")

    # VIF must be < 5 for all proposed drivers
    for driver, vif in subset_res["vif_scores"].items():
        assert vif < 5.0, f"VIF {vif} exceeds 5.0 threshold for driver {driver}"

    # Exact set equality: only the true generating variables must be proposed
    assert set(subset_res["proposed_drivers"]) == {"hdd18_3", "production_tons"}
    assert "day_of_week" in subset_res["rejected"]
    assert "hour_of_day" in subset_res["rejected"]
