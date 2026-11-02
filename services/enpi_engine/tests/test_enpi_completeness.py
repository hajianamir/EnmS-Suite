"""
Integration Tests for Phase 5 Workstream 3: EnPI & Baseline Completeness at Scale (§5.1)
Verifies:
1. W3-1: Multi-method baseline evaluation on ground truth.
2. W3-2: M&V savings reconciliation and IPMVP confidence interval.
3. W3-3: Scoped dependency graph impact analysis (EnPI baseline version propagation).
4. W3-4: Late data recomputation with structured audit event logging.
"""
import pytest
import os
import sys
import pandas as pd
import numpy as np
import psycopg
import json

sys.path.insert(0, os.path.abspath("."))
from docs.slice.evidence.generate_ground_truth import generate_ground_truth_dataset
from services.enpi_engine.engine import EnPIEngine

DB_URL = "postgresql://postgres@/verdantos?host=/var/run/postgresql&port=5433"
TENANT_ID = "11111111-1111-1111-1111-111111111111"

@pytest.fixture(scope="module")
def gt_data():
    return generate_ground_truth_dataset(n_days=365, seed=42)

def test_w3_1_method_comparison_on_ground_truth(gt_data):
    """
    W3-1: Method comparison on ground truth.
    Asserts OLS, Change-point, Option B, and Option C all recover beta within +-10% of [5.0, 0.30, 0.20].
    Asserts Degree-day (1P) reports beta2 = 0.00 by design.
    """
    methods = EnPIEngine.evaluate_ground_truth_methods(gt_data)

    print("\nW3-1 Methods evaluated on ground-truth (y = 5.0 + 0.30*HDD + 0.20*production + N(0,2.0)):")
    print(f"  | {'Method':18} | {'beta0':>5} | {'beta1':>5} | {'beta2':>5} | {'R2':>4} | {'CV-MAPE':>7} |")
    print("  |--------------------|-------|-------|-------|------|---------|")
    for m in methods:
        print(f"  | {m['method']:18} | {m['beta0']:>5.2f} | {m['beta1']:>5.2f} | {m['beta2']:>5.2f} | {m['r2']:>4.2f} | {m['mape']:>6.2f}% |")

    # Assertions for 2-driver models:
    for m in methods:
        if m["method"] in ["OLS (2-driver)", "Change-point (3P)", "IPMVP Option B", "IPMVP Option C"]:
            assert 4.5 <= m["beta0"] <= 5.5, f"{m['method']} beta0 {m['beta0']} outside [4.5, 5.5]"
            assert 0.27 <= m["beta1"] <= 0.33, f"{m['method']} beta1 {m['beta1']} outside [0.27, 0.33]"
            assert 0.18 <= m["beta2"] <= 0.22, f"{m['method']} beta2 {m['beta2']} outside [0.18, 0.22]"
            assert m["r2"] >= 0.90
        elif m["method"] == "Degree-day (1P)":
            assert m["beta2"] == 0.00
            assert m["r2"] < 0.20

def test_w3_2_mv_savings_reconciliation(gt_data):
    """
    W3-2: M&V savings reconciliation.
    Asserts baseline predicted == baseline actual within 0.01 kWh.
    Asserts savings reconciliation: abs(savings - (predicted - actual)) < 0.01.
    """
    df_base = gt_data.iloc[:275].copy() # 275 days baseline
    df_rep = gt_data.iloc[275:].copy()   # 90 days reporting period

    res = EnPIEngine.calculate_mv_savings(df_base, df_rep)

    delta_base = abs(res['baseline_actual'] - res['baseline_predicted'])
    print("\nW3-2 M&V Savings Reconciliation:")
    print(f"  Baseline predicted (sum over baseline period): {res['baseline_predicted']:.2f} kWh")
    print(f"  Baseline actual    (sum over baseline period): {res['baseline_actual']:.2f} kWh")
    print(f"  Delta:                                          {delta_base:.2f} kWh")
    print(f"  Reporting predicted: {res['reporting_predicted']:.2f} kWh")
    print(f"  Reporting actual:    {res['reporting_actual']:.2f} kWh")
    print(f"  Savings:             {res['savings']:.2f} kWh")
    print(f"  Savings 95% CI:      [{res['savings_ci'][0]:.2f}, {res['savings_ci'][1]:.2f}]")

    # Reconciliations
    assert abs(res["baseline_actual"] - res["baseline_predicted"]) < 0.01
    assert abs(res["savings"] - (res["reporting_predicted"] - res["reporting_actual"])) < 0.01
    assert res["savings"] > 0
    assert res["savings_ci"][0] < res["savings"] < res["savings_ci"][1]

def test_w3_3_dependency_graph_impact_analysis():
    """
    W3-3: Dependency graph with scoped impact analysis.
    Baseline BL_001 feeds ENPI_kwh_per_m2, ENPI_kwh_per_unit, ENPI_peak_demand.
    Unrelated ENPI_water_per_m2 feeds on BL_002.
    Asserts all 3 dependent EnPIs advance to v2; unrelated EnPI remains untouched.
    """
    # Seed definitions & dependencies
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            enpis = [
                ("ENPI_kwh_per_m2", "kWh/m²", "00000000-0000-0000-0000-000000000001", 1),
                ("ENPI_kwh_per_unit", "kWh/unit", "00000000-0000-0000-0000-000000000001", 1),
                ("ENPI_peak_demand", "kW", "00000000-0000-0000-0000-000000000001", 1),
                ("ENPI_water_per_m2", "m³/m²", "00000000-0000-0000-0000-000000000002", 1) # Unrelated
            ]
            for eid, unit, bl_id, ver in enpis:
                cur.execute("""
                    INSERT INTO enpi_definitions (id, tenant_id, name, target_unit, current_baseline_id, current_baseline_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET current_baseline_version = %s;
                """, (eid, TENANT_ID, eid, unit, bl_id, ver, ver))

                cur.execute("""
                    INSERT INTO enpi_baseline_dependencies (enpi_id, baseline_id, tenant_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (enpi_id, baseline_id) DO NOTHING;
                """, (eid, bl_id, TENANT_ID))

                cur.execute("""
                    INSERT INTO enpi_state (enpi_id, tenant_id, baseline_id, baseline_version, latest_value)
                    VALUES (%s, %s, %s, %s, 5.0)
                    ON CONFLICT (enpi_id) DO UPDATE SET baseline_version = %s;
                """, (eid, TENANT_ID, bl_id, ver, ver))
        conn.commit()

    print("\nW3-3 Scoped Dependency Graph Impact Analysis:")
    print("Before baseline update:")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT enpi_id, baseline_version FROM enpi_state ORDER BY enpi_id;")
            for r in cur.fetchall():
                print(f"  {r[0]:20} -> baseline_version = v{r[1]}")

    # Trigger baseline update on BL_001 to v2
    affected = EnPIEngine.propagate_baseline_update(DB_URL, TENANT_ID, "00000000-0000-0000-0000-000000000001", new_version=2)
    print("\nAfter baseline update on BL_001:")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT enpi_id, baseline_version FROM enpi_state ORDER BY enpi_id;")
            rows = {r[0]: r[1] for r in cur.fetchall()}
            for eid, ver in rows.items():
                print(f"  {eid:20} -> baseline_version = v{ver}")

    assert rows["ENPI_kwh_per_m2"] == 2
    assert rows["ENPI_kwh_per_unit"] == 2
    assert rows["ENPI_peak_demand"] == 2
    assert rows["ENPI_water_per_m2"] == 1, "Unrelated EnPI was erroneously updated!"

def test_w3_4_late_data_recomputation():
    """
    W3-4: Late data recomputation with auditable event log (Option A).
    """
    point_id = "pt_late_4444"
    recorded_at = "2024-08-15T00:00:00Z"

    # Set up initial EnPI value 5.02
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("UPDATE enpi_state SET latest_value = 5.02 WHERE enpi_id = 'ENPI_kwh_per_m2';")
        conn.commit()

    res = EnPIEngine.process_late_data_recomputation(
        DB_URL, TENANT_ID, point_id, recorded_at, late_value=120.0,
        affected_enpis=["ENPI_kwh_per_m2"]
    )

    print("\nW3-4 Late Data Recomputation Audit Event Log:")
    print(f"  Event Type:       {res['event_type']}")
    print(f"  Reason:           {res['reason']}")
    print(f"  Point ID:         {res['point_id']}")
    print(f"  Point Recorded At:{res['point_recorded_at']}")
    print(f"  Affected EnPIs:   {res['affected_enpi_ids']}")
    print(f"  Old Value:        {res['old_value']}")
    print(f"  New Value:        {res['new_value']}")
    print(f"  Delta %:          {res['delta_pct']}%")

    assert res["old_value"] == 5.02
    assert res["new_value"] == 5.04
    assert res["delta_pct"] == 0.40

    # Verify audit record in database table
    query_sql = """
        SELECT event_type, reason, point_id, point_recorded_at, affected_enpi_ids, 
               old_value, new_value, delta_pct
        FROM enpi_recomputation_log 
        WHERE tenant_id = %s AND point_id = %s;
    """
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute(query_sql, (TENANT_ID, point_id))
            log_row = cur.fetchone()
            assert log_row is not None
            print("\nW3-4 Database Log Row Queried Directly:")
            print("  event_type      | reason    | point_id     | point_recorded_at      | affected_enpis      | old_val | new_val | delta_pct")
            print(f"  {log_row[0]:15} | {log_row[1]:9} | {log_row[2]:12} | {str(log_row[3])[:22]} | {log_row[4]} | {log_row[5]:.2f}    | {log_row[6]:.2f}    | {log_row[7]:.2f}")
            assert log_row[0] == "ENPI_RECOMPUTED"
            assert log_row[1] == "LATE_DATA"
            assert float(log_row[5]) == 5.02
            assert round(float(log_row[6]), 2) == 5.04
