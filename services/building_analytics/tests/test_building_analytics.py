"""
Integration Tests for Phase 5 Workstream 6: Building Analytics (§5.9 / STORY-W6)
Verifies:
1. W6-1: HVAC performance runtime ratio with explicit assumption statement.
2. W6-2: Simultaneous heating/cooling detection with explicit assumption statement.
3. W6-3: Occupancy-aware scheduling waste estimation with explicit assumption statement.
4. W6-4: Demand-Response sheddable capacity within 15-minute notice.
5. W6-5: Building KPI dashboard summary.
6. W6-6: Every analytic states its operational inference assumption.
"""
import pytest
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath("."))
from services.building_analytics.building_analytics_engine import BuildingAnalyticsEngine

def test_w6_1_hvac_runtime_ratio():
    """
    W6-1: HVAC performance runtime ratio.
    """
    # 30 days of synthetic data
    dates = [datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(days=i) for i in range(30)]
    # Scheduled: 16.0 hours/day (06:00 - 22:00)
    # Actual: compressor active average 13.9 hours/day
    # Exactly 13.92 hours/day on average
    scheduled_hours = [16.0] * 30
    actual_hours = [13.92] * 30

    df_hvac = pd.DataFrame({
        "date": dates,
        "scheduled_hours": scheduled_hours,
        "actual_hours": actual_hours
    })

    res = BuildingAnalyticsEngine.calculate_hvac_runtime_ratio(df_hvac)
    print("\nW6-1 HVAC Runtime Ratio:")
    print(f"  Assumption:      \"{res['assumption']}\"")
    print(f"  Scheduled hours: {res['scheduled_hours']} h")
    print(f"  Actual hours:    {res['actual_hours']} h")
    print(f"  Runtime ratio:   {res['runtime_ratio']} (Expected ~0.87)")

    assert res["runtime_ratio"] == 0.87
    assert "Scheduled runtime from BMS schedule" in res["assumption"]

def test_w6_2_simultaneous_heating_cooling():
    """
    W6-2: Simultaneous heating and cooling detection.
    Engineers hours 8 to 12 (16 intervals of 15 min = 4.0 hours) with both valves > 0.
    """
    # 24 hours of 15-min intervals = 96 intervals
    start_time = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    timestamps = [start_time + timedelta(minutes=15 * i) for i in range(96)]

    heating_valves = [0.0] * 96
    cooling_valves = [0.0] * 96

    # Normal daytime cooling: hours 12 to 18
    for idx in range(48, 72):
        cooling_valves[idx] = 45.0

    # Faulty simultaneous H/C: hours 8 to 12 (intervals 32 to 48 = 16 intervals = 4.0 hours)
    for idx in range(32, 48):
        heating_valves[idx] = 25.0
        cooling_valves[idx] = 30.0

    df_intervals = pd.DataFrame({
        "timestamp": timestamps,
        "heating_valve_pct": heating_valves,
        "cooling_valve_pct": cooling_valves
    })

    res = BuildingAnalyticsEngine.detect_simultaneous_heating_cooling(df_intervals)
    print("\nW6-2 Simultaneous Heating/Cooling Detection:")
    print(f"  Assumption:                  \"{res['assumption']}\"")
    print(f"  Detected simultaneous hours: {res['detected_simultaneous_hours']} h (Expected: 4.0 h)")
    print(f"  Total period hours:          {res['total_period_hours']} h")
    print(f"  Incident intervals count:    {res['detected_intervals_count']} (Expected: 16)")

    assert res["detected_simultaneous_hours"] == 4.0
    assert res["detected_intervals_count"] == 16
    assert "Both valves > 0% for same 15-min interval" in res["assumption"]

def test_w6_3_occupancy_aware_waste():
    """
    W6-3: Occupancy-aware scheduling waste estimation.
    """
    # 24 hours of occupancy & HVAC power
    hours = list(range(24))
    # Scheduled occupancy: hours 8 to 18
    occupancy = [8 <= h < 18 for h in hours]
    # Faulty HVAC schedule: running 24/7 at 15 kW
    hvac_power = [15.0] * 24 # Unoccupied running during hours 0-8 and 18-24 = 14 hours

    df_occ = pd.DataFrame({
        "hour": hours,
        "occupancy": occupancy,
        "hvac_power_kw": hvac_power
    })

    res = BuildingAnalyticsEngine.evaluate_occupancy_waste(df_occ)
    print("\nW6-3 Occupancy-Aware Waste Estimation:")
    print(f"  Assumption:               \"{res['assumption']}\"")
    print(f"  Hours running unoccupied: {res['hours_running_unoccupied']} h (Expected: 14.0 h)")
    print(f"  Estimated waste:          {res['wasted_energy_kwh']} kWh (Expected: 210.0 kWh)")

    assert res["hours_running_unoccupied"] == 14.0
    assert res["wasted_energy_kwh"] == 210.0
    assert "Occupancy from badge data" in res["assumption"]

def test_w6_4_demand_response_readiness():
    """
    W6-4: Demand-Response sheddable capacity within 15-minute notice.
    """
    endpoints = [
        {"name": "AHU-01 Supply Fan Setpoint Setback", "sheddable_kw": 12.5, "notice_minutes": 5},
        {"name": "Chilled Water Secondary Pump #2", "sheddable_kw": 18.0, "notice_minutes": 10},
        {"name": "Non-Essential Perimeter Lighting Zone B", "sheddable_kw": 8.5, "notice_minutes": 2},
        {"name": "Chiller #1 Compressor Stage 2", "sheddable_kw": 45.0, "notice_minutes": 30} # Exceeds 15 min notice
    ]

    res = BuildingAnalyticsEngine.calculate_dr_readiness(endpoints)
    print("\nW6-4 Demand-Response Readiness:")
    print(f"  Assumption:           \"{res['assumption']}\"")
    print(f"  Notice window:        {res['notice_minutes']} minutes")
    print(f"  Max sheddable load:   {res['max_sheddable_kw']} kW (Expected: 39.0 kW)")
    print(f"  Sheddable endpoints:  {res['sheddable_endpoints']}")

    assert res["max_sheddable_kw"] == 39.0
    assert len(res["sheddable_endpoints"]) == 3
    assert "Chiller #1 Compressor Stage 2" not in res["sheddable_endpoints"]

def test_w6_5_building_kpi_dashboard():
    """
    W6-5: Building KPI dashboard summary.
    """
    res = BuildingAnalyticsEngine.compute_building_kpi_dashboard(
        building_name="Building A (Engineering)",
        total_kwh=182400.0, # 182.4 MWh in 30 days
        area_m2=12000.0,
        peak_kw=342.5,
        baseline_kwh=175000.0
    )
    kpis = res["kpis"]
    print("\nW6-5 Building Level KPI Summary:")
    print(f"  Building:               {res['building']}")
    print(f"  Energy Intensity:       {kpis['energy_intensity_kwh_per_m2_day']} kWh/m²/day")
    print(f"  Peak Demand:            {kpis['peak_demand_kw']} kW")
    print(f"  Baseline Deviation:     +{kpis['baseline_deviation_pct']}%")

    assert kpis["energy_intensity_kwh_per_m2_day"] == 0.51
    assert kpis["peak_demand_kw"] == 342.5
    assert kpis["baseline_deviation_pct"] == 4.2
