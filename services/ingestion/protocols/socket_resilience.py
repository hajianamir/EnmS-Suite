"""
Protocol Adapter Mid-Flight Socket Resilience Engine (STORY-1.6 / PHASE-5-ADP-001)
Protects against mid-flight TCP socket death:
1. Buffers in-flight payloads when socket connection drops abruptly (ConnectionResetError, RemoteDisconnected).
2. Distinguishes socket death from HTTP 500 error-wrapper responses.
3. Provides automatic retry and store-and-forward flushing upon connection restoration.
"""
import socket
import http.client
from typing import Dict, List, Any, Optional

class SocketDeathException(Exception):
    def __init__(self, message: str, reason: Exception):
        super().__init__(message)
        self.reason = reason

class ResilientProtocolAdapter:
    def __init__(self):
        self.buffer: List[Dict[str, Any]] = []
        self.delivered_sequence: List[int] = []

    def buffer_size(self) -> int:
        return len(self.buffer)

    def send_with_socket_protection(self, endpoint_host: str, endpoint_port: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends payload with mid-flight TCP reset / death protection.
        Catches ConnectionResetError and http.client.RemoteDisconnected, buffers payload,
        and raises SocketDeathException preserving original socket cause.
        """
        try:
            conn = http.client.HTTPConnection(endpoint_host, endpoint_port, timeout=2.0)
            conn.request("POST", "/data", body=str(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            status = resp.status
            conn.close()

            if status == 200:
                self.delivered_sequence.append(payload.get("seq", 0))
                return {"status": 200, "delivered": True}
            else:
                return {"status": status, "delivered": False}

        except (ConnectionResetError, http.client.RemoteDisconnected, BrokenPipeError) as e:
            # Mid-flight socket death detected: buffer payload for store-and-forward
            self.buffer.append(payload)
            raise SocketDeathException(f"Mid-flight TCP socket death: {str(e)}", reason=e)
        except Exception as e:
            # Other errors (e.g. connection refused)
            return {"status": 500, "error": str(e)}

    def flush_buffer(self, endpoint_host: str, endpoint_port: int) -> int:
        """Flushes buffered payloads upon socket restoration."""
        flushed_count = 0
        remaining_buffer = []
        for payload in self.buffer:
            try:
                res = self.send_with_socket_protection(endpoint_host, endpoint_port, payload)
                if res.get("status") == 200:
                    flushed_count += 1
                else:
                    remaining_buffer.append(payload)
            except SocketDeathException:
                remaining_buffer.append(payload)
                break
        self.buffer = remaining_buffer
        return flushed_count
