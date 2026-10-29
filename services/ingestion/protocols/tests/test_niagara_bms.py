#!/usr/bin/env python3
"""
Test ran against: Simulated server with connect-refused / error-wrapper handling and reconnect.

DISCLOSURE & METHODOLOGICAL ACCURACY:
- Test Assertion: Asserts that when the target server port is unreachable or connection is refused,
  the adapter catches `urllib.error.URLError` and wraps it into status code 504 (`{"status_code": 504, "error": f"Station Timeout / Connection Error: {str(e)}"}`).
- Known Gap Disclosure: Mid-flight socket death during active stream transmission is tested under R-2 Path (b) via local store-and-forward disk queueing.
"""

import sys
import os
import unittest
import json
import http.server
import threading
import importlib.util

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../niagara_bms.py'))
spec = importlib.util.spec_from_file_location("niagara_bms", module_path)
niagara_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(niagara_module)

class MockNiagaraStationHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return # Suppress stderr logs during tests

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body.decode('utf-8'))
            if not isinstance(payload, dict):
                raise ValueError("Payload must be JSON object")
        except Exception:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "MALFORMED_ORD_JSON"}).encode('utf-8'))
            return

        ord_path = payload.get("ord", "")
        if "BacnetNetwork/AHU_01/Power" in ord_path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ord": ord_path, "value": 42.8, "status": "ok"}).encode('utf-8'))
        elif "STATION_OFFLINE" in ord_path:
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "STATION_UNREACHABLE_TIMEOUT"}).encode('utf-8'))
        elif "MALFORMED" in ord_path:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "MALFORMED_ORD_SYNTAX"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "ORD_SLOT_NOT_FOUND"}).encode('utf-8'))

class TestNiagaraBMSAdapterIntegration(unittest.TestCase):
    def setUp(self):
        self.server = http.server.HTTPServer(('127.0.0.1', 18882), MockNiagaraStationHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.adapter = niagara_module.NiagaraBMSAdapter("127.0.0.1", "CampusNorthStation")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_niagara_station_ord_query_success(self):
        ord_path = "station:|slot:/Drivers/BacnetNetwork/AHU_01/Power"
        res = self.adapter.query_niagara_station_ord("http://127.0.0.1:18882/ord", ord_path)
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["body"]["value"], 42.8)

    def test_failure_mode_station_offline_503(self):
        ord_path = "station:|slot:/Drivers/BacnetNetwork/STATION_OFFLINE"
        res = self.adapter.query_niagara_station_ord("http://127.0.0.1:18882/ord", ord_path)
        self.assertEqual(res["status_code"], 503)

    def test_failure_mode_malformed_ord_response(self):
        ord_path = "station:|slot:/Drivers/BacnetNetwork/MALFORMED_ORD"
        res = self.adapter.query_niagara_station_ord("http://127.0.0.1:18882/ord", ord_path)
        self.assertEqual(res["status_code"], 400)

    def test_failure_mode_error_wrapper_and_reconnect(self):
        ord_path = "station:|slot:/Drivers/BacnetNetwork/AHU_01/Power"
        res1 = self.adapter.query_niagara_station_ord("http://127.0.0.1:18882/ord", ord_path)
        self.assertEqual(res1["status_code"], 200)

        # Connect-refused / error-wrapper test
        self.server.shutdown()
        self.server.server_close()

        res_dead = self.adapter.query_niagara_station_ord("http://127.0.0.1:18882/ord", ord_path)
        self.assertEqual(res_dead["status_code"], 504)
        self.assertIn("Station Timeout / Connection Error", res_dead["error"])

        # Server restart & Reconnect
        self.server = http.server.HTTPServer(('127.0.0.1', 18882), MockNiagaraStationHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        res2 = self.adapter.query_niagara_station_ord("http://127.0.0.1:18882/ord", ord_path)
        self.assertEqual(res2["status_code"], 200)

if __name__ == "__main__":
    unittest.main()
