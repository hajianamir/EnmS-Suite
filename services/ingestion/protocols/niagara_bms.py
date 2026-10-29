#!/usr/bin/env python3
"""
Phase 5 Workstream 1: Tier 1 Tridium Niagara 4 BMS Fox/BACnet Driver Integration
"""

import json
import urllib.request
import urllib.error

class NiagaraBMSAdapter:
    def __init__(self, niagara_host, station_name):
        self.host = niagara_host
        self.station = station_name

    def format_niagara_history_payload(self, ord_path, timestamp, value):
        """Formats Niagara 4 History ord query payload."""
        return {
            "station": self.station,
            "ord": ord_path, # e.g. "station:|slot:/Drivers/BacnetNetwork/AHU_01/Power"
            "timestamp": timestamp,
            "value": value
        }

    def query_niagara_station_ord(self, endpoint_url, ord_path):
        """Queries Niagara Station HTTP REST/Ord API endpoint and handles network/station timeouts."""
        data = json.dumps({"station": self.station, "ord": ord_path}).encode('utf-8')
        req = urllib.request.Request(
            endpoint_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return {"status_code": response.getcode(), "body": json.loads(response.read().decode('utf-8'))}
        except urllib.error.HTTPError as e:
            return {"status_code": e.code, "error": f"HTTPError {e.code}: {e.reason}"}
        except Exception as e:
            return {"status_code": 504, "error": f"Station Timeout / Connection Error: {str(e)}"}

if __name__ == "__main__":
    adapter = NiagaraBMSAdapter("192.168.1.100", "CampusNorthStation")
    msg = adapter.format_niagara_history_payload("station:|slot:/Drivers/BacnetNetwork/AHU_01/Power", "2026-10-20T22:00:00Z", 42.8)
    print("Niagara BMS Payload Formatted:", json.dumps(msg))
