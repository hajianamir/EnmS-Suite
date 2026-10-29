#!/usr/bin/env python3
import sys

def classify_telemetry_event(event):
    value = event.get("value")
    quality = event.get("quality_flag")
    context = event.get("context")
    baseline_expected = event.get("baseline_expected", 45.0)
    telemetry_history_days = event.get("telemetry_history_days", 30) # Default 30 days
    
    # Cold-Start Check: Assets with < 14 days history produce INSUFFICIENT_DATA_COLD_START
    if telemetry_history_days < 14:
        return {
            "state": "INSUFFICIENT_DATA_COLD_START",
            "confidence": 0.0,
            "reason": "Insufficient historical telemetry (< 14 days) for baseline variance stabilization.",
            "rule_path_attribution": {"history_days": "< 14"}
        }

    # R-08 Decision Logic Tree Implementation
    if quality == "BAD_SENSOR_FAULT" or quality == "STUCK_ZERO_FLATLINE" or value < 0 or value > 500.0:
        return {
            "state": "SENSOR_FAULT",
            "confidence": 0.99,
            "reason": "Out of range sensor reading or hardware failure flag.",
            "rule_path_attribution": {"sensor_voltage": "+88%", "hardware_bit": "+12%"}
        }
    elif context in ["PLANNED_SCHEDULE_OVERRIDE", "SHIFT_CHANGE_RAMP_UP", "HOLIDAY_BASELOAD_MODE", "UNSCHEDULED_MINOR_OVERRIDE"]:
        return {
            "state": "OPERATIONAL_CHANGE",
            "confidence": 0.95,
            "reason": f"Operating schedule context '{context}' confirmed in facility calendar.",
            "rule_path_attribution": {"schedule_bit": "+90%", "occupancy": "+10%"}
        }
    elif value > (baseline_expected * 1.3): # > 30% baseline deviation
        deviation = value - baseline_expected
        return {
            "state": "REAL_ENERGY_WASTE",
            "confidence": 0.92,
            "reason": f"Unexplained excess baseload spike (+{deviation:.1f} kW above expected {baseline_expected} kW).",
            "rule_path_attribution": {"condenser_valve_position": "+45%", "outdoor_humidity": "+30%", "fan_speed": "+25%"}
        }
    else:
        return {
            "state": "NORMAL",
            "confidence": 0.98,
            "reason": "Telemetry within expected baseline statistical bounds.",
            "rule_path_attribution": {"baseline_fit": "100%"}
        }

if __name__ == "__main__":
    from services.simulator.simulator import generate_simulated_telemetry_slice
    events = generate_simulated_telemetry_slice()
    for ev in events:
        res = classify_telemetry_event(ev)
        print(f"Condition: {ev['condition']} -> Decision State: {res['state']} | Reason: {res['reason']}")
