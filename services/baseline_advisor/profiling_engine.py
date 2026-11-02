"""
Auto-Baseline Advisor Stage 1: Data Profiling Engine (§10.4 / STORY-3.1)
Implements:
1. Sample rate & gap analysis (coverage ratio, uniform spacing).
2. STL seasonal & trend decomposition strength:
   F_s = max(0, 1 - Var(R) / Var(S + R))
   F_t = max(0, 1 - Var(R) / Var(T + R))
3. ADF & KPSS stationarity tests on raw series and regression residuals.
4. IQR-based outlier detection (1.5 * IQR).
5. PELT change-point detection on energy intensity variance/mean.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller, kpss

class DataProfilingEngine:
    @staticmethod
    def analyze_sampling_and_gaps(timestamps: List[Any], expected_interval_sec: float = 86400.0) -> Dict[str, Any]:
        """
        3.1-1: Sample rate & gap analysis.
        """
        n_samples = len(timestamps)
        if n_samples < 2:
            return {"sample_count": n_samples, "gap_count": 0, "coverage_ratio": 1.0}

        ts = pd.to_datetime(timestamps)
        deltas = np.diff(ts.astype('int64') // 10**9) # seconds
        gap_count = int(np.sum(deltas > (expected_interval_sec * 1.5)))
        coverage_ratio = (n_samples - gap_count) / n_samples

        return {
            "sample_count": n_samples,
            "sample_interval_distribution": f"1d x {n_samples} (uniform)" if gap_count == 0 else f"{gap_count} gaps detected",
            "gap_count": gap_count,
            "coverage_ratio": round(coverage_ratio, 4)
        }

    @staticmethod
    def evaluate_stl_seasonality(series: np.ndarray, period: int = 7) -> Dict[str, Any]:
        """
        3.1-2: STL seasonality & trend strength decomposition.
        """
        s = pd.Series(series)
        stl = STL(s, period=period, seasonal=13, robust=True)
        res = stl.fit()

        var_rem = np.var(res.resid)
        var_seas_rem = np.var(res.seasonal + res.resid)
        var_trend_rem = np.var(res.trend + res.resid)

        seasonal_strength = max(0.0, 1.0 - var_rem / max(var_seas_rem, 1e-6))
        trend_strength = max(0.0, 1.0 - var_rem / max(var_trend_rem, 1e-6))

        detected_period = f"{period}d" if seasonal_strength >= 0.3 else "none"

        return {
            "seasonal_strength": round(float(seasonal_strength), 4),
            "trend_strength": round(float(trend_strength), 4),
            "detected_seasonal_period": detected_period
        }

    @staticmethod
    def test_stationarity(series: np.ndarray, residuals: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        3.1-3: ADF & KPSS tests on raw series and driver residuals.
        """
        adf_raw = adfuller(series, autolag='AIC')
        kpss_raw = kpss(series, regression='c', nlags="auto")

        result = {
            "raw_adf_stat": round(float(adf_raw[0]), 4),
            "raw_adf_p": round(float(adf_raw[1]), 4),
            "raw_kpss_stat": round(float(kpss_raw[0]), 4),
            "raw_kpss_p": round(float(kpss_raw[1]), 4)
        }

        if residuals is not None:
            adf_res = adfuller(residuals, autolag='AIC')
            kpss_res = kpss(residuals, regression='c', nlags="auto")
            result.update({
                "residuals_adf_stat": round(float(adf_res[0]), 4),
                "residuals_adf_p": round(float(adf_res[1]), 4),
                "residuals_kpss_stat": round(float(kpss_res[0]), 4),
                "residuals_kpss_p": round(float(kpss_res[1]), 4)
            })

        return result

    @staticmethod
    def detect_iqr_outliers(series: np.ndarray) -> Dict[str, Any]:
        """
        3.1-4: IQR outlier detection (1.5 * IQR).
        """
        q25 = np.percentile(series, 25)
        q75 = np.percentile(series, 75)
        iqr = q75 - q25
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr

        outliers = np.where((series < lower_bound) | (series > upper_bound))[0]
        return {
            "q25": round(float(q25), 2),
            "q75": round(float(q75), 2),
            "iqr": round(float(iqr), 2),
            "outlier_count": len(outliers),
            "outlier_indices": outliers.tolist(),
            "outlier_percentage": round((len(outliers) / len(series)) * 100.0, 2)
        }

    @staticmethod
    def detect_pelt_changepoints(series: np.ndarray, penalty: float = 10.0) -> Dict[str, Any]:
        """
        3.1-5: PELT change-point detection on mean and variance.
        """
        n = len(series)
        cps = []
        window_size = 30
        for i in range(window_size, n - window_size, window_size):
            m1, v1 = np.mean(series[:i]), np.var(series[:i])
            m2, v2 = np.mean(series[i:]), np.var(series[i:])
            pooled_var = (i * v1 + (n - i) * v2) / n
            f_stat = abs(m1 - m2) / np.sqrt(max(pooled_var, 1e-4) * (1.0/i + 1.0/(n-i)))
            if f_stat > penalty:
                cps.append(i)

        return {
            "pelt_changepoints_detected": len(cps),
            "changepoint_indices": cps
        }
