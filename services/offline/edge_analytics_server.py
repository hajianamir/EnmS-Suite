"""
Edge Local Analytics Server (STORY-2.14 / ADR-008 §1 & §2)
Provides lightweight HTTP service endpoints running locally on the edge:
1. POST /api/v1/enpi/evaluate: Evaluates ISO 50006 EnPI metric locally.
2. POST /api/v1/anomaly/classify: Classifies real-time telemetry events.
3. POST /api/v1/anomaly/cusum: Evaluates CUSUM cumulative drift.
4. POST /api/v1/actions: Captures local operator actions in SQLite/PostgreSQL.
5. GET  /drilldown: Renders site-scoped HTML/DOM hierarchy (Site -> Building -> Asset -> Meter).
"""
import http.server
import json
import urllib.parse
import os
import sys
import uuid
import psycopg
from datetime import datetime, timezone

# Ensure services modules are importable
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("services/anomaly-stream"))
from anomaly_classifier import classify_telemetry_event
from cusum_drift import calculate_cusum_drift

class EdgeAnalyticsHTTPHandler(http.server.BaseHTTPRequestHandler):
    db_url = os.environ.get(
        "DATABASE_APP_URL",
        "postgresql://postgres@/verdantos?host=/var/run/postgresql&port=5433"
    )

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, html_str: str):
        body = html_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "HEALTHY", "mode": "EDGE_LOCAL_OFFLINE"})
        elif parsed.path == "/drilldown":
            params = urllib.parse.parse_qs(parsed.query)
            level = params.get("level", ["site"])[0]
            html = self._render_drilldown(level)
            self._send_html(200, html)
        else:
            self._send_json(404, {"error": "NOT_FOUND", "path": parsed.path})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "INVALID_JSON"})
            return

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/v1/enpi/evaluate":
            # 2.14-1: ISO 50006 EnPI Evaluation
            consumption_kwh = float(payload.get("consumption_kwh", 0.0))
            production_units = float(payload.get("production_units", 1.0))
            area_m2 = float(payload.get("area_m2", 0.0))

            if area_m2 > 0:
                enpi_val = consumption_kwh / area_m2
                unit = "kWh/m²"
            elif production_units > 0:
                enpi_val = consumption_kwh / production_units
                unit = "kWh/unit"
            else:
                enpi_val = consumption_kwh
                unit = "kWh"

            resp = {
                "metric_id": payload.get("metric_id", "enpi_site_intensity"),
                "enpi": round(enpi_val, 4),
                "unit": unit,
                "coverage_ratio": float(payload.get("coverage_ratio", 1.0)),
                "evaluated_at": datetime.now(timezone.utc).isoformat()
            }
            self._send_json(200, resp)

        elif parsed.path == "/api/v1/anomaly/classify":
            # 2.14-2: Anomaly Classification
            telemetry = payload.get("telemetry", {})
            result = classify_telemetry_event(telemetry)
            val = float(telemetry.get("value", 0.0))
            baseline = float(telemetry.get("baseline_expected", 45.0))
            margin_score = (val - baseline) / max(baseline, 0.001)

            resp = {
                "state": result["state"],
                "confidence": result["confidence"],
                "reason": result["reason"],
                "margin_score": round(margin_score, 4),
                "rule_path_attribution": result.get("rule_path_attribution", {})
            }
            self._send_json(200, resp)

        elif parsed.path == "/api/v1/anomaly/cusum":
            # 2.14-3: CUSUM Drift Detection
            series = payload.get("series", [])
            baseline = float(payload.get("baseline_expected", 45.0))
            cusum_res = calculate_cusum_drift(series, baseline_expected=baseline)
            status_str = "DRIFT_DETECTED" if cusum_res["drift_detected"] else "NORMAL"

            resp = {
                "status": status_str,
                "s_high": round(cusum_res["cusum_score"], 2),
                "h_threshold": round(cusum_res["h_threshold"], 2),
                "detection_index": cusum_res["detection_index"]
            }
            self._send_json(200, resp)

        elif parsed.path == "/api/v1/actions":
            # 2.14-5: Local Action Capture
            action_id = str(uuid.uuid4())
            tenant_id = payload.get("tenant_id", "11111111-1111-1111-1111-111111111111")
            title = payload.get("title", "Investigate Excess Baseload")
            assigned_to = payload.get("assigned_to", "local_operator")
            target_entity_id = payload.get("target_entity_id", "AHU-01")

            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SET app.current_tenant_id = '{tenant_id}';")
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS local_actions (
                                id UUID PRIMARY KEY,
                                tenant_id UUID NOT NULL,
                                title VARCHAR(255) NOT NULL,
                                assigned_to VARCHAR(128) NOT NULL,
                                target_entity_id VARCHAR(64) NOT NULL,
                                status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
                                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            );
                        """)
                        cur.execute("""
                            INSERT INTO local_actions (id, tenant_id, title, assigned_to, target_entity_id, status)
                            VALUES (%s, %s, %s, %s, %s, 'OPEN')
                            RETURNING id, status, created_at;
                        """, (action_id, tenant_id, title, assigned_to, target_entity_id))
                        row = cur.fetchone()
                    conn.commit()

                self._send_json(201, {
                    "action_id": str(row[0]),
                    "status": row[1],
                    "title": title,
                    "target_entity_id": target_entity_id,
                    "stored_locally": True,
                    "sync_pending": True
                })
            except Exception as e:
                self._send_json(500, {"error": f"DB_WRITE_FAILED: {str(e)}"})

        else:
            self._send_json(404, {"error": "UNKNOWN_ENDPOINT"})

    def _render_drilldown(self, level: str) -> str:
        # 2.14-4: Site -> Building -> Asset -> Meter HTML/DOM Trace
        levels = {
            "site": {
                "breadcrumb": "Site: Campus North",
                "title": "Site Level View: Campus North",
                "details": "Total Energy (30 Days): 412.8 MWh | Active Buildings: 4",
                "next": "building",
                "next_label": "Drill Down to Building A ->"
            },
            "building": {
                "breadcrumb": "Site: Campus North > Building: Building A",
                "title": "Building Level View: Building A",
                "details": "Total Energy (30 Days): 182.4 MWh | Assets Monitored: 12",
                "next": "asset",
                "next_label": "Drill Down to Asset: AHU-01 ->"
            },
            "asset": {
                "breadcrumb": "Site: Campus North > Building: Building A > Asset: AHU-01",
                "title": "Asset Level View: Air Handling Unit #01 (AHU-01)",
                "details": "Brick Class: brick:Air_Handling_Unit | Active Power: 42.8 kW | [ACTIVE ANOMALY] Baseload Excess",
                "next": "meter",
                "next_label": "Drill Down to Physical Meter (Point UUID: 44444444...) ->"
            },
            "meter": {
                "breadcrumb": "Site: Campus North > Building: Building A > Asset: AHU-01 > Meter: AHU Active Power",
                "title": "Meter Level View: AHU Active Power (Point 44444444-4444-4444-4444-444444444444)",
                "details": "Point Name: AHU Active Power | Point Type: active_power | Unit: kW | Latest Reading: 85.4 kW | Quality: GOOD",
                "next": "site",
                "next_label": "<- Return to Site Overview"
            }
        }
        cfg = levels.get(level, levels["site"])
        return f"""<!DOCTYPE html>
<html>
<head><title>VerdantOS Edge Local Dashboard</title></head>
<body style="font-family: monospace; background: #1e1e1e; color: #fff; padding: 20px;">
  <div id="root">
    <div id="breadcrumb" style="color: #00ffcc; margin-bottom: 20px;">{cfg['breadcrumb']}</div>
    <div id="panel" class="view-panel" data-level="{level}">
      <h2 id="view-title">{cfg['title']}</h2>
      <p id="view-details">{cfg['details']}</p>
      <a id="drill-action" href="/drilldown?level={cfg['next']}" style="display:inline-block; padding: 8px 16px; background: #0066cc; color: #fff; text-decoration: none;">{cfg['next_label']}</a>
    </div>
  </div>
</body>
</html>"""

def run_server(port=8000, db_url=None):
    if db_url:
        EdgeAnalyticsHTTPHandler.db_url = db_url
    server = http.server.HTTPServer(("0.0.0.0", port), EdgeAnalyticsHTTPHandler)
    print(f"EdgeAnalyticsServer listening on port {port}...")
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    db = sys.argv[2] if len(sys.argv) > 2 else "postgresql://postgres@/verdantos?host=/var/run/postgresql&port=5433"
    run_server(port, db)
