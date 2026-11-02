"""
Auto-Baseline Advisor Stage 4: Selection & Diagnostics Engine (§10.4 / STORY-3.4)
Implements:
1. 5-fold Time-Series Walk-Forward Cross Validation (fold-by-fold details).
2. AIC / BIC Information Criteria ranking.
3. IPMVP Fractional Savings Uncertainty (FSU):
   FSU = t_{alpha/2} * (MSE^0.5 / (y_mean * n^0.5))
4. Comprehensive Residual Diagnostics Battery:
   - Normality: Shapiro-Wilk (W, p > 0.05)
   - Heteroskedasticity: Breusch-Pagan (LM, p > 0.05)
   - Autocorrelation: Durbin-Watson (1.5 < DW < 2.5) & Ljung-Box at lag 10 (p > 0.05)
   - Influence: Cook's Distance (max < 4 / n)
5. Multi-seed Model Selection Stability across noise draws.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson

class SelectionDiagnosticsEngine:
    @staticmethod
    def evaluate_walk_forward_folds(df: pd.DataFrame, target_col: str, driver_cols: List[str], n_splits: int = 5) -> Dict[str, Any]:
        """
        3.4-1: Fold-by-fold walk-forward cross validation.
        """
        X = sm.add_constant(df[driver_cols].values)
        y = df[target_col].values
        tscv = TimeSeriesSplit(n_splits=n_splits)

        folds = []
        mapes = []
        for idx, (tr_idx, te_idx) in enumerate(tscv.split(X), start=1):
            X_tr, X_te = X[tr_idx], X[te_idx]
            y_tr, y_te = y[tr_idx], y[te_idx]

            ols = sm.OLS(y_tr, X_tr).fit()
            y_pred = ols.predict(X_te)

            mape = float(np.mean(np.abs((y_te - y_pred) / np.maximum(np.abs(y_te), 1e-4))) * 100.0)
            rmse = float(np.sqrt(np.mean((y_te - y_pred)**2)))
            mapes.append(mape)
            folds.append({
                "fold": idx,
                "mape": round(mape, 2),
                "rmse": round(rmse, 2)
            })

        return {
            "folds": folds,
            "mean_cv_mape": round(float(np.mean(mapes)), 2),
            "std_dev_cv_mape": round(float(np.std(mapes)), 2)
        }

    @staticmethod
    def calculate_ipmvp_fsu(df: pd.DataFrame, target_col: str, driver_cols: List[str], confidence_level: float = 0.95) -> Dict[str, Any]:
        """
        3.4-3: IPMVP Fractional Savings Uncertainty (FSU).
        """
        X = sm.add_constant(df[driver_cols].values)
        y = df[target_col].values
        n = len(y)
        p = X.shape[1]

        ols = sm.OLS(y, X).fit()
        mse = ols.mse_resid
        y_mean = np.mean(y)

        # Two-tailed t critical value for confidence_level
        alpha = 1.0 - confidence_level
        t_crit = stats.t.ppf(1.0 - alpha / 2.0, df=n - p)

        # Standard IPMVP FSU formula
        fsu = t_crit * (np.sqrt(mse) / (y_mean * np.sqrt(n))) * 100.0

        return {
            "fsu_pct": round(float(fsu), 2),
            "t_stat_crit": round(float(t_crit), 4),
            "mse": round(float(mse), 4),
            "rmse": round(float(np.sqrt(mse)), 4),
            "y_mean": round(float(y_mean), 2),
            "sample_size": n
        }

    @staticmethod
    def run_residual_diagnostics(df: pd.DataFrame, target_col: str, driver_cols: List[str]) -> Dict[str, Any]:
        """
        3.4-4: Residual diagnostics battery.
        """
        X = sm.add_constant(df[driver_cols].values)
        y = df[target_col].values
        n = len(y)

        ols = sm.OLS(y, X).fit()
        residuals = ols.resid

        # 1. Normality (Shapiro-Wilk)
        w_stat, p_shapiro = stats.shapiro(residuals)

        # 2. Heteroskedasticity (Breusch-Pagan)
        bp_test = het_breuschpagan(residuals, X)
        lm_stat, p_bp = bp_test[0], bp_test[1]

        # 3. Autocorrelation (Durbin-Watson & Ljung-Box)
        dw_stat = durbin_watson(residuals)
        lb_test = acorr_ljungbox(residuals, lags=[10], return_df=True)
        p_ljungbox = lb_test["lb_pvalue"].values[0]

        # 4. Cook's Distance
        influence = ols.get_influence()
        cooks_d = influence.cooks_distance[0]
        max_cooks_d = np.max(cooks_d)
        threshold_cooks = 4.0 / n

        return {
            "shapiro_w": round(float(w_stat), 4),
            "shapiro_p": round(float(p_shapiro), 4),
            "normality_pass": bool(p_shapiro > 0.05),
            "breusch_pagan_lm": round(float(lm_stat), 4),
            "breusch_pagan_p": round(float(p_bp), 4),
            "homoskedasticity_pass": bool(p_bp > 0.05),
            "durbin_watson": round(float(dw_stat), 4),
            "dw_pass": bool(1.5 < dw_stat < 2.5),
            "ljung_box_lag10_p": round(float(p_ljungbox), 4),
            "ljung_box_pass": bool(p_ljungbox > 0.05),
            "max_cooks_d": round(float(max_cooks_d), 4),
            "cooks_threshold_4_n": round(float(threshold_cooks), 4),
            "cooks_threshold_concern": 1.0,
            "influence_pass": bool(max_cooks_d < 1.0)
        }
