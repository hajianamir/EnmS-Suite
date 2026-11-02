"""
Auto-Baseline Advisor Stage 2: Variable Discovery Engine (§10.4 / STORY-3.2)
Implements:
1. Multi-metric correlation & causality battery:
   - Pearson linear correlation (r)
   - Spearman rank monotonic correlation (rho)
   - Mutual Information (MI, non-linear dependencies)
   - Granger Causality (time-series predictive power)
2. Variance Inflation Factor (VIF) multicollinearity filter:
   VIF_j = 1 / (1 - R_j^2)
   Proposed subset: top-N by MI with VIF < 5.0.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from scipy import stats
from sklearn.feature_selection import mutual_info_regression
from statsmodels.tsa.stattools import grangercausalitytests
from statsmodels.stats.outliers_influence import variance_inflation_factor

class VariableDiscoveryEngine:
    @staticmethod
    def rank_candidate_variables(
        df: pd.DataFrame,
        target_col: str,
        candidate_cols: List[str]
    ) -> List[Dict[str, Any]]:
        """
        3.2-1: Correlation ranking across candidates using Pearson, Spearman, MI, and Granger.
        """
        y = df[target_col].values
        results = []

        # MI regression across all candidates
        X_all = df[candidate_cols].values
        # Add small jitter if column is constant to avoid MI computation error
        if np.all(X_all[:, 0] == X_all[0, 0]):
            X_all[:, 0] += np.random.normal(0, 1e-6, len(y))

        mi_scores = mutual_info_regression(X_all, y, random_state=42)

        for idx, col in enumerate(candidate_cols):
            x = df[col].values
            # Pearson & Spearman
            if np.all(x == x[0]): # Constant series
                r, p_pearson = 0.0, 1.0
                rho, p_spearman = 0.0, 1.0
                granger_p = 1.0
            else:
                r, p_pearson = stats.pearsonr(x, y)
                rho, p_spearman = stats.spearmanr(x, y)

                # Granger causality test (lag 1)
                try:
                    gc_data = np.column_stack([y, x])
                    gc_res = grangercausalitytests(gc_data, maxlag=[1], verbose=False)
                    granger_p = gc_res[1][0]['ssr_ftest'][1]
                except Exception:
                    granger_p = 1.0

            results.append({
                "variable": col,
                "pearson_r": round(float(r), 4),
                "pearson_p": round(float(p_pearson), 4),
                "spearman_rho": round(float(rho), 4),
                "spearman_p": round(float(p_spearman), 4),
                "mutual_info": round(float(mi_scores[idx]), 4),
                "granger_p": round(float(granger_p), 4)
            })

        # Rank by MI descending
        results.sort(key=lambda d: d["mutual_info"], reverse=True)
        return results

    @staticmethod
    def select_proposed_driver_subset(
        df: pd.DataFrame,
        ranked_candidates: List[Dict[str, Any]],
        vif_threshold: float = 5.0,
        mi_threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        3.2-2: Selects proposed driver subset filtered by MI > threshold and VIF < 5.0.
        """
        # Filter by MI threshold and non-constant
        initial_candidates = [
            c["variable"] for c in ranked_candidates
            if c["mutual_info"] >= mi_threshold and df[c["variable"]].std() > 1e-4
        ]

        if not initial_candidates:
            return {"proposed_drivers": [], "vif_scores": {}, "rejected": [c["variable"] for c in ranked_candidates]}

        # Compute VIF iteratively to drop multicollinear features
        current_candidates = list(initial_candidates)
        while True:
            X = df[current_candidates].values
            # Add intercept for VIF calculation
            X_with_const = np.column_stack([np.ones(len(X)), X])
            vifs = [variance_inflation_factor(X_with_const, i+1) for i in range(len(current_candidates))]

            max_vif = max(vifs) if vifs else 0.0
            if max_vif > vif_threshold and len(current_candidates) > 1:
                # Drop the candidate with highest VIF
                drop_idx = int(np.argmax(vifs))
                current_candidates.pop(drop_idx)
            else:
                break

        vif_dict = {
            col: round(float(vifs[i]), 2)
            for i, col in enumerate(current_candidates)
        }

        all_vars = [c["variable"] for c in ranked_candidates]
        rejected = [col for col in all_vars if col not in current_candidates]

        return {
            "proposed_drivers": current_candidates,
            "vif_scores": vif_dict,
            "rejected": rejected
        }
