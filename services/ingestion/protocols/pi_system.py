#!/usr/bin/env python3
"""
Phase 5 Workstream 1: Tier 1 AVEVA PI System Integration Adapter

DIRECTIONAL INTEGRATION PATHS:
- Ingest Path (Data Read): Executed via PI Web API batch GET endpoints (`query_pi_web_api_batch_read`).
  Retrieves historical or real-time stream values from PI Data Archive / Asset Framework.
- Publish Path (Data Write): Executed via OMF (OSIsoft Message Format) payload formatters (`format_omf_telemetry_message`).
  Publishes VerdantOS computed EnPIs / energy metrics back into customer's PI System.
"""

import json
import urllib.request
import urllib.error

class PISystemAdapter:
    def __init__(self, pi_web_api_url, dataserver_name):
        self.url = pi_web_api_url
        self.dataserver = dataserver_name

    def query_pi_web_api_batch_read(self, endpoint_url, web_ids):
        """INGEST PATH (READ): Queries PI Web API batch GET endpoint for stream values."""
        data = json.dumps({"webIds": web_ids}).encode('utf-8')
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
            return {"status_code": 500, "error": str(e)}

    def format_omf_telemetry_message(self, point_id, timestamp, value, quality="Good"):
        """PUBLISH PATH (WRITE): Formats OMF (OSIsoft Message Format) data message payload."""
        return {
            "containerId": f"Point_{point_id}",
            "values": [
                {
                    "Time": timestamp,
                    "Value": value,
                    "Questionable": (quality != "Good")
                }
            ]
        }

    def send_omf_payload_to_endpoint(self, endpoint_url, payload):
        """PUBLISH PATH (WRITE): Sends OMF payload to PI Web API / OMF endpoint."""
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            endpoint_url,
            data=data,
            headers={'Content-Type': 'application/json', 'omfversion': '1.1', 'action': 'create'}
        )
        try:
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return {"status_code": response.getcode(), "body": json.loads(response.read().decode('utf-8'))}
        except urllib.error.HTTPError as e:
            return {"status_code": e.code, "error": f"HTTPError {e.code}: {e.reason}"}
        except Exception as e:
            return {"status_code": 500, "error": str(e)}

if __name__ == "__main__":
    adapter = PISystemAdapter("https://pi.campus.north/piwebapi", "PIServerNorth")
    msg = adapter.format_omf_telemetry_message("44444444-4444-4444-4444-444444444444", "2026-10-20T22:00:00Z", 42.8)
    print("AVEVA PI OMF Payload Formatted:", json.dumps(msg))
