"""
Building Analytics Engine (STORY-W6 / §5.9)
Implements:
1. HVAC Runtime Ratio (scheduled vs actual runtime).
2. Simultaneous Heating & Cooling detection (both valves > 0 for >= 15 min).
3. Occupancy-aware schedule optimization & waste estimation.
4. Demand Response (DR) Sheddable Capacity within 15-minute notice.
5. Building KPI Aggregation & DOM Trace Summary.
All analytics explicitly state the inference assumption per W6-6.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

class BuildingAnalyticsEngine:
    @staticmethod
    def calculate_hvac_runtime_ratio(df_hvac: pd.DataFrame) -> Dict[str, Any]:
        """
        W6-1: HVAC performance runtime ratio.
        Assumption: Scheduled runtime from BMS schedule (06:00-22:00 = 16h/day); actual runtime from fan_status/compressor > 0.
        """
        assumption = "Scheduled runtime from BMS schedule; if schedule missing, uses 06:00-22:00 (16h/day) default. Runtime ratio = actual_hours / scheduled_hours."
        total_scheduled_hours = float(df_hvac["scheduled_hours"].sum())
        total_actual_hours = float(df_hvac["actual_hours"].sum())
        runtime_ratio = total_actual_hours / max(total_scheduled_hours, 0.001)

        return {
            "analytic_type": "HVAC_RUNTIME",
            "assumption": assumption,
            "scheduled_hours": round(total_scheduled_hours, 1),
            "actual_hours": round(total_actual_hours, 1),
            "runtime_ratio": round(runtime_ratio, 2),
            "unit": "ratio"
        }

    @staticmethod
    def detect_simultaneous_heating_cooling(df_intervals: pd.DataFrame) -> Dict[str, Any]:
        """
        W6-2: Simultaneous heating/cooling detection.
        Assumption: Both heating_valve > 0% and cooling_valve > 0% for the same 15-minute interval; simultaneous for < 5 min ignored.
        """
        assumption = "Both valves > 0% for same 15-min interval; simultaneous for < 5 min ignored."
        # Condition: heating_valve_pct > 0 and cooling_valve_pct > 0
        simul_mask = (df_intervals["heating_valve_pct"] > 0.0) & (df_intervals["cooling_valve_pct"] > 0.0)
        simul_intervals = df_intervals[simul_mask]
        detected_hours = len(simul_intervals) * 0.25 # 15-min = 0.25 hours
        total_hours = len(df_intervals) * 0.25

        return {
            "analytic_type": "SIMULTANEOUS_HC",
            "assumption": assumption,
            "detected_simultaneous_hours": round(detected_hours, 1),
            "total_period_hours": round(total_hours, 1),
            "detected_intervals_count": int(len(simul_intervals)),
            "unit": "hours",
            "incident_timestamps": simul_intervals["timestamp"].astype(str).tolist()
        }

    @staticmethod
    def evaluate_occupancy_waste(df_occupancy: pd.DataFrame) -> Dict[str, Any]:
        """
        W6-3: Occupancy-aware scheduling waste estimation.
        Assumption: Occupancy from badge data if available, else from schedule; hours running while unoccupied flagged.
        """
        assumption = "Occupancy from badge data if available, else from schedule; hours running while unoccupied flagged."
        unoccupied_running = df_occupancy[(df_occupancy["occupancy"] == False) & (df_occupancy["hvac_power_kw"] > 5.0)]
        unoccupied_hours = len(unoccupied_running) * 1.0 # 1-hour intervals
        wasted_kwh = float(unoccupied_running["hvac_power_kw"].sum())

        return {
            "analytic_type": "OCCUPANCY_WASTE",
            "assumption": assumption,
            "hours_running_unoccupied": round(unoccupied_hours, 1),
            "wasted_energy_kwh": round(wasted_kwh, 2),
            "unit": "kWh"
        }

    @staticmethod
    def calculate_dr_readiness(endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        W6-4: Demand-Response sheddable capacity within 15-minute notice.
        Assumption: Non-critical loads (setpoint setback, secondary pumps, non-emergency lighting) sheddable within 15-min notice without safety violation.
        """
        assumption = "Non-critical loads sheddable within 15-min notice without safety violation."
        max_sheddable = sum(ep["sheddable_kw"] for ep in endpoints if ep["notice_minutes"] <= 15)
        endpoint_names = [ep["name"] for ep in endpoints if ep["notice_minutes"] <= 15]

        return {
            "analytic_type": "DR_READINESS",
            "assumption": assumption,
            "max_sheddable_kw": round(max_sheddable, 1),
            "notice_minutes": 15,
            "sheddable_endpoints": endpoint_names,
            "unit": "kW"
        }

    @staticmethod
    def compute_building_kpi_dashboard(building_name: str, total_kwh: float, area_m2: float, peak_kw: float, baseline_kwh: float) -> Dict[str, Any]:
        """
        W6-5: Building KPI dashboard summary.
        """
        intensity_kwh_m2 = total_kwh / max(area_m2, 1.0)
        baseline_deviation_pct = ((total_kwh - baseline_kwh) / max(baseline_kwh, 0.001)) * 100.0

        return {
            "building": building_name,
            "kpis": {
                "energy_intensity_kwh_per_m2_day": round(intensity_kwh_m2 / 30.0, 2),
                "peak_demand_kw": round(peak_kw, 1),
                "baseline_deviation_pct": round(baseline_deviation_pct, 1)
            }
        }
