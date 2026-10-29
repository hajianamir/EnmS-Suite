#!/usr/bin/env python3
import time
import json
import uuid
from datetime import datetime, timezone

def generate_simulated_telemetry_slice():
    now_iso = datetime.now(timezone.utc).isoformat()
    tenant_id = "11111111-1111-1111-1111-111111111111" # Campus North
    point_id  = "44444444-4444-4444-4444-444444444444" # AHU-01 Active Power
    
    # 3 Simulated Data Cycles representing 3 Anomaly Conditions:
    events = [
        {
            "condition": "SENSOR_FAULT",
            "recorded_at": now_iso,
            "point_id": point_id,
            "tenant_id": tenant_id,
            "value": -999.0, # Out-of-bounds sensor fault value
            "quality_flag": "BAD_SENSOR_FAULT"
        },
        {
            "condition": "OPERATIONAL_CHANGE",
            "recorded_at": now_iso,
            "point_id": point_id,
            "tenant_id": tenant_id,
            "value": 15.0, # Low weekend operational schedule change
            "quality_flag": "GOOD",
            "context": "PLANNED_SCHEDULE_OVERRIDE"
        },
        {
            "condition": "REAL_ENERGY_WASTE",
            "recorded_at": now_iso,
            "point_id": point_id,
            "tenant_id": tenant_id,
            "value": 85.4, # Baseload excess spike vs expected 45.0 kW baseline
            "quality_flag": "GOOD",
            "baseline_expected": 45.0
        }
    ]
    
    return events

if __name__ == "__main__":
    telemetry = generate_simulated_telemetry_slice()
    print(f"Generated {len(telemetry)} simulated protocol events for Vertical Slice.")
