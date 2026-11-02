"""
Auto-Baseline Advisor Stage 4: ANOVA & Statistical Hypothesis Suite (§10.4 / STORY-3.5)
Implements:
1. One-way ANOVA:
   - day_of_week (7 groups)
   - shift (3 groups)
   - season (4 quarters)
2. Two-way ANOVA with interaction:
   - day_of_week x season
3. t-tests on multiple linear regression coefficients.
4. F-test on nested models (driver inclusion).
5. ANCOVA: baseline vs reporting period comparison controlling for drivers.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols

class ANOVASuite:
    @staticmethod
    def one_way_anova(df: pd.DataFrame, target_col: str, group_col: str) -> Dict[str, Any]:
        groups = [group[target_col].values for _, group in df.groupby(group_col)]
        f_stat, p_val = stats.f_oneway(*groups)
        return {
            "group_col": group_col,
            "n_groups": len(groups),
            "f_statistic": round(float(f_stat), 4),
            "p_value": round(float(p_val), 4)
        }

    @staticmethod
    def two_way_anova(df: pd.DataFrame, target_col: str, factor1: str, factor2: str) -> Dict[str, Any]:
        formula = f"{target_col} ~ C({factor1}) + C({factor2}) + C({factor1}):C({factor2})"
        model = ols(formula, data=df).fit()
        table = sm.stats.anova_lm(model, typ=2)

        return {
            "factor1_p": round(float(table.loc[f"C({factor1})", "PR(>F)"]), 4),
            "factor2_p": round(float(table.loc[f"C({factor2})", "PR(>F)"]), 4),
            "interaction_p": round(float(table.loc[f"C({factor1}):C({factor2})", "PR(>F)"]), 4)
        }

    @staticmethod
    def regression_t_tests(df: pd.DataFrame, target_col: str, driver_cols: List[str]) -> Dict[str, Any]:
        X = sm.add_constant(df[driver_cols])
        y = df[target_col]
        model = sm.OLS(y, X).fit()

        t_results = {}
        for var in model.params.index:
            t_results[var] = {
                "coef": round(float(model.params[var]), 4),
                "t_stat": round(float(model.tvalues[var]), 4),
                "p_value": round(float(model.pvalues[var]), 6)
            }
        return t_results

    @staticmethod
    def nested_f_test(df: pd.DataFrame, target_col: str, restricted_cols: List[str], extra_col: str) -> Dict[str, Any]:
        # Restricted model
        X_res = sm.add_constant(df[restricted_cols])
        y = df[target_col]
        m_res = sm.OLS(y, X_res).fit()

        # Full model with extra driver
        X_full = sm.add_constant(df[restricted_cols + [extra_col]])
        m_full = sm.OLS(y, X_full).fit()

        # F-test between nested models
        f_test = m_full.compare_f_test(m_res)
        f_stat = f_test[0]
        p_val = f_test[1]

        return {
            "extra_col": extra_col,
            "f_statistic": round(float(f_stat), 4),
            "p_value": round(float(p_val), 6),
            "significant_improvement": p_val < 0.05
        }

    @staticmethod
    def ancova_period_test(
        df_base: pd.DataFrame,
        df_rep: pd.DataFrame,
        target_col: str,
        driver_cols: List[str]
    ) -> Dict[str, Any]:
        df_b = df_base.copy()
        df_b["period"] = "baseline"
        df_r = df_rep.copy()
        df_r["period"] = "reporting"
        combined = pd.concat([df_b, df_r], ignore_index=True)

        formula = f"{target_col} ~ C(period) + " + " + ".join(driver_cols)
        model = ols(formula, data=combined).fit()
        table = sm.stats.anova_lm(model, typ=2)

        period_p = round(float(table.loc["C(period)", "PR(>F)"]), 4)
        period_f = round(float(table.loc["C(period)", "F"]), 4)

        return {
            "period_f_statistic": period_f,
            "period_p_value": period_p,
            "significant_period_effect": period_p < 0.05
        }
