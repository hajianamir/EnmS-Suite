"""
Scale Audit & Hash-Chain Verification Engine (STORY-W5 / §5.11)
Provides high-throughput append-only SHA-256 hash chaining and standalone verification.
"""
import hashlib
import json
import uuid
import time
from typing import Dict, List, Any, Tuple

class ScaleAuditEngine:
    @staticmethod
    def compute_record_hash(entity_id: str, action_type: str, payload_after: dict, prev_hash: str) -> str:
        body = json.dumps(payload_after, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(body).hexdigest()
        chained = f"{entity_id}|{action_type}|{payload_hash}|{prev_hash}".encode("utf-8")
        return hashlib.sha256(chained).hexdigest()

    @staticmethod
    def verify_chain(records: List[Dict[str, Any]]) -> Tuple[bool, int, str]:
        """
        Verifies SHA-256 hash chain sequentially.
        Returns (is_valid, record_count, failure_reason_if_any).
        """
        prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        for idx, rec in enumerate(records):
            if rec["previous_hash"] != prev_hash:
                return False, idx, f"TAMPER_DETECTED: previous_hash mismatch at index {idx}"

            expected_hash = ScaleAuditEngine.compute_record_hash(
                rec["entity_id"],
                rec["action_type"],
                rec["payload_after"],
                rec["previous_hash"]
            )
            if rec["cryptographic_hash"] != expected_hash:
                return False, idx, f"TAMPER_DETECTED: cryptographic_hash corrupted at index {idx} (expected {expected_hash}, got {rec['cryptographic_hash']})"

            prev_hash = rec["cryptographic_hash"]

        return True, len(records), "CHAIN_INTACT"
