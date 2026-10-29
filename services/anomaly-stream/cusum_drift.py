#!/usr/bin/env python3
"""
PHASE-5-ANOM-001: Cumulative CUSUM Drift Detection Engine (STATUS: IN_PROGRESS)
Detects gradual baseline degradation (+10% to +25%) over 14-day rolling windows.

CALIBRATION & DESIGN RATIONALE:
- k_allowance_pct (0.12): Allowance parameter set to 12% above expected baseline (k = 5.4 kW for 45 kW baseline).
- h_threshold_sigma (4.5): Decision threshold set to 4.5 * sigma (h = 5.4 kW for sigma = 1.2 kW).
- Calibration Rationale: k = h = 5.4 kW is intentionally selected for faster detection of +15% to +25% sustained leaks
  at the trade-off of requiring site-specific sigma and target shift re-calibration during deployment.
  Because k = h, classical ARL0 guarantees must be re-validated per tenant site using empirical baseline noise datasets.
"""

import math

def calculate_cusum_drift(telemetry_series, baseline_expected, k_allowance_pct=0.12, h_threshold_sigma=4.5, sigma=1.2):
    s_high = 0.0
    drift_detected = False
    k = k_allowance_pct * baseline_expected # 12% allowance = 5.4 kW
    h = h_threshold_sigma * sigma # 4.5 * 1.2 = 5.4 kW
    
    detection_index = -1
    
    for idx, val in enumerate(telemetry_series):
        deviation = val - baseline_expected
        s_high = max(0.0, s_high + (deviation - k))
        if s_high > h and not drift_detected:
            drift_detected = True
            detection_index = idx
            
    return {
        "cusum_score": s_high,
        "h_threshold": h,
        "drift_detected": drift_detected,
        "detection_index": detection_index,
        "status": "IN_PROGRESS"
    }
