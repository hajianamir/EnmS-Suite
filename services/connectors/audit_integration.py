"""
VerdantOS Connector Cryptographic Audit Trail Integration (STORY-2.11 / §10.2 / §5.11)
Integrates connector sync runs into the platform's SHA-256 cryptographic hash-chain ledger.
Computes digest of error_summary, chains to prior entry hash, and appends to composite pack.
"""
from typing import Dict, List, Any, Optional
import hashlib
import json
import uuid
import psycopg

class ConnectorAuditLedger:
    @staticmethod
    def compute_sha256(data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def append_connector_run_to_audit_trail(
        db_url: str,
        tenant_id: str,
        run_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        2.11-1 & 2.11-2: Appends connector run to the platform's unified SHA-256 hash-chain ledger.
        Embeds error_summary_sha256 and links to the previous entry hash.
        """
        run_id = run_record["id"]
        source_id = run_record["source_id"]
        rows_read = run_record.get("rows_read", 0)
        rows_committed = run_record.get("rows_committed", 0)
        rows_rejected = run_record.get("rows_rejected", 0)
        error_summary = run_record.get("error_summary", [])
        
        # 1. Compute digest of error_summary JSONB
        error_summary_json = json.dumps(error_summary, sort_keys=True)
        error_summary_sha256 = ConnectorAuditLedger.compute_sha256(error_summary_json)

        payload_after = {
            "run_id": run_id,
            "source_id": source_id,
            "rows_read": rows_read,
            "rows_committed": rows_committed,
            "rows_rejected": rows_rejected,
            "error_summary_sha256": error_summary_sha256
        }
        payload_after_json = json.dumps(payload_after, sort_keys=True)

        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SET app.current_tenant_id = '{tenant_id}';")
                
                # Fetch last audit hash in chain
                cur.execute("SELECT cryptographic_hash FROM audit_trail ORDER BY created_at DESC LIMIT 1;")
                last_row = cur.fetchone()
                previous_hash = last_row[0] if last_row else "GENESIS_BLOCK_00000000000000000000000000000000"

                # Compute new entry hash = SHA256(previous_hash + payload_after_json)
                entry_hash = ConnectorAuditLedger.compute_sha256(previous_hash + payload_after_json)
                entry_id = str(uuid.uuid4())
                user_id = '00000000-0000-0000-0000-000000000000'

                cur.execute(
                    """
                    INSERT INTO audit_trail (id, tenant_id, entity_type, entity_id, action_type, changed_by, payload_after, cryptographic_hash, previous_hash)
                    VALUES (%s, %s, 'connector_run', %s, 'EXECUTE_SYNC', %s, %s, %s, %s);
                    """,
                    (entry_id, tenant_id, run_id, user_id, json.dumps(payload_after), entry_hash, previous_hash)
                )
                conn.commit()

        return {
            "entry_id": entry_id,
            "tenant_id": tenant_id,
            "run_id": run_id,
            "payload_after": payload_after,
            "previous_hash": previous_hash,
            "entry_hash": entry_hash
        }
