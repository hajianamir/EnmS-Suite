#!/usr/bin/env python3
"""
Test ran against: Simulated server with connect-refused / error-wrapper handling and reconnect.

DISCLOSURE & METHODOLOGICAL ACCURACY:
- Test Assertion: Asserts that when the target server port is unreachable or connection is refused,
  the adapter catches `urllib.error.URLError` and returns a structured microservice error wrapper `{"status_code": 500, "error": str(e)}`.
- Known Gap Disclosure: Mid-flight socket death during active stream transmission is tested under R-2 Path (b) via local store-and-forward disk queueing.
"""

import sys
import os
import unittest
import json
import http.server
import threading
import urllib.error
import importlib.util

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../pi_system.py'))
spec = importlib.util.spec_from_file_location("pi_system", module_path)
pi_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi_module)

class MockPIServerHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return # Suppress stderr logs during test runs

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
            self.wfile.write(json.dumps({"error": "MALFORMED_JSON_PAYLOAD"}).encode('utf-8'))
            return

        container_id = payload.get("containerId", "")
        web_ids = payload.get("webIds", [])
        
        if "GARBAGE_RESPONSE" in str(web_ids):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"<<<NON_JSON_GARBAGE_RESPONSE_FROM_PI_SERVER>>>")
            return

        if "MALFORMED" in str(web_ids):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "MALFORMED_WEB_ID_QUERY"}).encode('utf-8'))
            return

        if "Point_44444444" in container_id or "web-id-1" in web_ids:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"result": "OMF_CONTAINER_UPDATED", "status": "SUCCESS"}).encode('utf-8'))
        elif "Point_NOT_FOUND" in container_id:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "PI_TAG_NOT_FOUND"}).encode('utf-8'))
        else:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "INTERNAL_PI_SERVER_ERROR"}).encode('utf-8'))

class TestPISystemAdapterIntegration(unittest.TestCase):
    def setUp(self):
        self.server = http.server.HTTPServer(('127.0.0.1', 18881), MockPIServerHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.adapter = pi_module.PISystemAdapter("http://127.0.0.1:18881/omf", "PIServerNorth")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_omf_endpoint_successful_post(self):
        msg = self.adapter.format_omf_telemetry_message("44444444-4444-4444-4444-444444444444", "2026-10-20T22:00:00Z", 42.8)
        res = self.adapter.send_omf_payload_to_endpoint("http://127.0.0.1:18881/omf", msg)
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["body"]["result"], "OMF_CONTAINER_UPDATED")

    def test_pi_web_api_batch_read_ingest_path(self):
        res = self.adapter.query_pi_web_api_batch_read("http://127.0.0.1:18881/omf", ["web-id-1", "web-id-2"])
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["body"]["status"], "SUCCESS")

    def test_failure_mode_malformed_omf_payload(self):
        res = self.adapter.send_omf_payload_to_endpoint("http://127.0.0.1:18881/omf", "INVALID_MALFORMED_NON_JSON_STRING")
        self.assertEqual(res["status_code"], 400)

    def test_failure_mode_pi_read_path_malformed_response_body(self):
        res = self.adapter.query_pi_web_api_batch_read("http://127.0.0.1:18881/omf", ["GARBAGE_RESPONSE"])
        self.assertEqual(res["status_code"], 500)
        self.assertIn("error", res)

    def test_failure_mode_error_wrapper_and_reconnect(self):
        msg1 = self.adapter.format_omf_telemetry_message("44444444-4444-4444-4444-444444444444", "2026-10-20T22:00:00Z", 42.8)
        res1 = self.adapter.send_omf_payload_to_endpoint("http://127.0.0.1:18881/omf", msg1)
        self.assertEqual(res1["status_code"], 200)

        # Connect-refused / error-wrapper test
        self.server.shutdown()
        self.server.server_close()

        res_dead = self.adapter.send_omf_payload_to_endpoint("http://127.0.0.1:18881/omf", msg1)
        self.assertEqual(res_dead["status_code"], 500)
        self.assertIn("error", res_dead)

        # Restart server & reconnect
        self.server = http.server.HTTPServer(('127.0.0.1', 18881), MockPIServerHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        msg2 = self.adapter.format_omf_telemetry_message("44444444-4444-4444-4444-444444444444", "2026-10-20T22:01:00Z", 43.1)
        res2 = self.adapter.send_omf_payload_to_endpoint("http://127.0.0.1:18881/omf", msg2)
        self.assertEqual(res2["status_code"], 200)

    def test_failure_mode_pi_read_path_error_wrapper_and_reconnect(self):
        res1 = self.adapter.query_pi_web_api_batch_read("http://127.0.0.1:18881/omf", ["web-id-1"])
        self.assertEqual(res1["status_code"], 200)

        # Connect-refused / error-wrapper test
        self.server.shutdown()
        self.server.server_close()

        res_dead = self.adapter.query_pi_web_api_batch_read("http://127.0.0.1:18881/omf", ["web-id-1"])
        self.assertEqual(res_dead["status_code"], 500)

        # Restart server & reconnect
        self.server = http.server.HTTPServer(('127.0.0.1', 18881), MockPIServerHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        res2 = self.adapter.query_pi_web_api_batch_read("http://127.0.0.1:18881/omf", ["web-id-1"])
        self.assertEqual(res2["status_code"], 200)

if __name__ == "__main__":
    unittest.main()
