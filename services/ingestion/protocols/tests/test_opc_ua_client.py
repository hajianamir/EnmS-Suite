#!/usr/bin/env python3
"""
Test ran against: Simulated OPC UA In-Process Protocol Server Instance & Session Contract
"""

import sys
import os
import unittest
import importlib.util

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../opc_ua_client.py'))
spec = importlib.util.spec_from_file_location("opc_ua_client", module_path)
opc_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opc_module)

class TestOPCUAClientAdapterIntegration(unittest.TestCase):
    def setUp(self):
        self.adapter = opc_module.OPCUAClientAdapter("opc.tcp://127.0.0.1:4840")

    def test_opc_ua_session_connect_and_subscription(self):
        connected = self.adapter.connect_session()
        self.assertTrue(connected)
        
        node_id = "ns=2;s=Device.AHU_01.ActivePower"
        msg = self.adapter.format_opc_monitored_item(node_id, "2026-10-20T22:00:00Z", 42.8, status_code=0)
        self.assertEqual(msg["endpoint"], "opc.tcp://127.0.0.1:4840")
        self.assertEqual(msg["status_code"], "Good")

    def test_failure_mode_unconnected_session_error(self):
        node_id = "ns=2;s=Device.AHU_01.ActivePower"
        with self.assertRaises(ConnectionError):
            self.adapter.format_opc_monitored_item(node_id, "2026-10-20T22:00:00Z", 42.8, status_code=0)

    def test_failure_mode_connection_loss_and_resubscribe(self):
        self.adapter.connect_session()
        # Simulate socket disconnection mid-flight
        self.adapter.session_active = False
        
        # Verify disconnect caught
        with self.assertRaises(ConnectionError):
            self.adapter.format_opc_monitored_item("ns=2;s=Device.AHU_01.ActivePower", "2026-10-20T22:00:00Z", 42.8)
            
        # Re-establish session & resubscribe
        self.adapter.connect_session()
        msg = self.adapter.format_opc_monitored_item("ns=2;s=Device.AHU_01.ActivePower", "2026-10-20T22:00:00Z", 42.8)
        self.assertEqual(msg["status_code"], "Good")

    def test_failure_mode_malformed_node_id(self):
        self.adapter.connect_session()
        with self.assertRaises(ValueError):
            # Invalid node ID format lacking namespace prefix 'ns='
            self.adapter.format_opc_monitored_item("INVALID_NODE_ID_STRING", "2026-10-20T22:00:00Z", 42.8)

if __name__ == "__main__":
    unittest.main()
