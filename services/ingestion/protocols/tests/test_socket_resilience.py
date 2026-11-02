"""
Integration Tests for STORY-1.6 / PHASE-5-ADP-001: Mid-Flight TCP Socket Death & Payload Protection.
Simulates mid-flight connection reset using TCP socket RST flag (SO_LINGER)
and asserts:
1. Adapter detects ConnectionResetError / RemoteDisconnected (not generic 500).
2. In-flight payload #2 is preserved in store-and-forward buffer.
3. Upon server restoration, buffer flushes and sequence integrity is verified.
"""
import pytest
import socket
import threading
import time
import http.client
import sys
import os

sys.path.insert(0, os.path.abspath("."))
from services.ingestion.protocols.socket_resilience import ResilientProtocolAdapter, SocketDeathException

TEST_PORT = 19999

def run_rst_server(stop_event):
    """
    TCP server that accepts request 1 normally, but on request 2,
    abruptly resets the TCP connection using SO_LINGER (RST packet mid-flight).
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", TEST_PORT))
    server_sock.listen(5)
    server_sock.settimeout(2.0)

    request_count = 0
    while not stop_event.is_set():
        try:
            client, addr = server_sock.accept()
            request_count += 1
            if request_count == 1:
                # Request 1: Handle successfully
                raw = client.recv(1024)
                client.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                client.close()
            elif request_count == 2:
                # Request 2: Read partial request, then trigger abrupt mid-flight RST
                raw = client.recv(64)
                # SO_LINGER with l_onoff=1, l_linger=0 sends hard TCP RST on close
                import struct
                client.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                client.close()
            else:
                # Subsequent requests: succeed normally
                raw = client.recv(1024)
                client.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                client.close()
        except socket.timeout:
            pass
        except Exception:
            pass
    server_sock.close()

def test_midflight_socket_death_protects_inflight_payload():
    adapter = ResilientProtocolAdapter()
    stop_event = threading.Event()
    srv_thread = threading.Thread(target=run_rst_server, args=(stop_event,), daemon=True)
    srv_thread.start()
    time.sleep(0.2)

    try:
        # Request 1: succeeds
        payload_1 = {"seq": 1, "point_id": "meter_p1", "val": 42.0}
        res1 = adapter.send_with_socket_protection("127.0.0.1", TEST_PORT, payload_1)
        assert res1["status"] == 200
        assert adapter.delivered_sequence == [1]
        assert adapter.buffer_size() == 0

        # Request 2: Server resets connection mid-flight (TCP RST)
        payload_2 = {"seq": 2, "point_id": "meter_p2", "val": 84.0}
        with pytest.raises(SocketDeathException) as exc_info:
            adapter.send_with_socket_protection("127.0.0.1", TEST_PORT, payload_2)

        # Assertion: adapter detects ConnectionResetError or RemoteDisconnected
        underlying = exc_info.value.reason
        print(f"\nSTORY-1.6 Mid-Flight Socket Death Caught: {underlying.__class__.__name__}: {underlying}")
        assert isinstance(underlying, (ConnectionResetError, http.client.RemoteDisconnected, BrokenPipeError))

        # Assertion: payload 2 is buffered
        assert adapter.buffer_size() == 1
        assert adapter.buffer[0] == payload_2
        print(f"Store-and-forward buffer holds in-flight payload: {adapter.buffer[0]}")

        # Server is now accepting normal requests again: flush buffer
        flushed = adapter.flush_buffer("127.0.0.1", TEST_PORT)
        print(f"Server restored: flushed {flushed} buffered payloads")
        assert flushed == 1
        assert adapter.buffer_size() == 0
        assert adapter.delivered_sequence == [1, 2]
        print(f"Delivered sequence preserved: {adapter.delivered_sequence}")

    finally:
        stop_event.set()
        srv_thread.join()
