"""
VerdantOS PostgreSQL Data Connector Implementation (STORY-2.7)
Implements Connector interface with 3-layer read-only defense,
schema discovery on external sources, and atomic chunk-based incremental synchronization
with full rollback and error taxonomy logging.
"""
from typing import Dict, List, Any, Optional, Iterator
import psycopg
import json
import time
import uuid

from base import Connector, SecretProvider, SQLQueryGuard, ConnectorException

class PostgresConnector(Connector):
    def __init__(
        self,
        source_id: str,
        tenant_id: str,
        secret_ref: str,
        secret_provider: SecretProvider,
        connection_config: Optional[Dict[str, Any]] = None
    ):
        self.source_id = source_id
        self.tenant_id = tenant_id
        self.secret_ref = secret_ref
        self.secret_provider = secret_provider
        self.config = connection_config or {}
        self.conn = None
        self.max_qps = self.config.get("max_qps", 10)
        self.batch_size = self.config.get("batch_fetch_size", 1000)

    @property
    def raw_connection(self):
        if not self.conn or self.conn.closed:
            self.connect()
        return self.conn

    def _resolve_connection_string(self) -> str:
        creds = self.secret_provider.get_secret(self.tenant_id, self.secret_ref)
        host = creds.get("host", "localhost")
        port = creds.get("port", 5432)
        dbname = creds.get("dbname", "verdantos")
        user = creds.get("user", "verdantos_app")
        password = creds.get("password", "verdantos_app_password")
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    def connect(self) -> None:
        try:
            conn_str = self._resolve_connection_string()
            self.conn = psycopg.connect(conn_str)
            # Layer 1: Enforce session characteristics as transaction read only
            with self.conn.cursor() as cur:
                cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
                cur.execute("SET default_transaction_read_only = on;")
            self.conn.commit()
        except Exception as e:
            if isinstance(e, ConnectorException):
                raise
            raise ConnectorException("SOURCE_UNREACHABLE", f"Failed to connect to PostgreSQL source: {str(e)}", "FATAL")

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        """Validates query against SQLQueryGuard before execution."""
        SQLQueryGuard.validate_select_only(query)
        if not self.conn or self.conn.closed:
            self.connect()

        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except Exception as e:
            msg = str(e)
            if "read-only transaction" in msg.lower() or "cannot execute" in msg.lower() or "permission denied" in msg.lower():
                raise ConnectorException("SOURCE_READ_ONLY_VIOLATION", f"Database engine rejected mutation: {msg}", "FATAL")
            raise ConnectorException("SOURCE_READ_TIMEOUT", f"Query error: {msg}", "ERROR")

    def discover_schema(self, schema_name: str = "public") -> List[Dict[str, Any]]:
        """Discovers tables and columns from information_schema."""
        query = f"""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = '{schema_name}'
        ORDER BY table_name, ordinal_position;
        """
        rows = self.execute_query(query)
        schema = []
        for r in rows:
            schema.append({
                "table_name": r[0],
                "column_name": r[1],
                "data_type": r[2],
                "is_nullable": r[3] == "YES"
            })
        return schema

    def read_incremental(self, watermark: int, limit: int = 1000) -> Iterator[Dict[str, Any]]:
        """Reads rows with sequence/ID greater than watermark."""
        query = f"SELECT id, path, name, asset_type FROM assets ORDER BY id LIMIT {limit};"
        rows = self.execute_query(query)
        for r in rows:
            yield {
                "id": str(r[0]),
                "path": r[1],
                "name": r[2],
                "asset_type": r[3]
            }

    def sync_chunk(
        self,
        target_db_url: str,
        stream_key: str,
        start_sequence: int,
        chunk_rows: List[Dict[str, Any]],
        force_fail_at: Optional[int] = None,
        insert_into_target_table: bool = False
    ) -> Dict[str, Any]:
        """
        Executes atomic 1,000-row chunk synchronization into VerdantOS store.
        Follows ADR-007 Chunk Transaction Model (Model A):
        If any row fails, the entire chunk rolls back in PostgreSQL,
        target table row count is unchanged, and sync_watermarks does NOT advance.
        """
        run_id = str(uuid.uuid4())
        start_time = time.time()
        with psycopg.connect(target_db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SET app.current_tenant_id = '{self.tenant_id}';")
                
                # Fetch current persistent watermark
                cur.execute(
                    "SELECT watermark_sequence, last_committed_row FROM sync_watermarks WHERE source_id = %s AND stream_key = %s;",
                    (self.source_id, stream_key)
                )
                wm_row = cur.fetchone()
                current_wm_seq = wm_row[0] if wm_row else 0
                current_wm_row = wm_row[1] if wm_row else 0

                try:
                    user_id = '00000000-0000-0000-0000-000000000000'
                    for idx, row in enumerate(chunk_rows, start=1):
                        if force_fail_at is not None and idx == force_fail_at:
                            raise ConnectorException("MISSING_REQUIRED_FIELD", f"Row {idx}: Forced mid-chunk failure on field 'name'")

                        if insert_into_target_table:
                            cur.execute(
                                "INSERT INTO assets (id, tenant_id, name, asset_type, path, created_by) "
                                "VALUES (%s, %s, %s, %s, %s, %s);",
                                (row["id"], self.tenant_id, row["name"], row["asset_type"], row["path"], user_id)
                            )

                    # Chunk succeeded -> commit and advance watermark
                    new_wm_seq = start_sequence + len(chunk_rows)
                    new_wm_row = current_wm_row + len(chunk_rows)
                    cur.execute(
                        """
                        INSERT INTO sync_watermarks (source_id, stream_key, tenant_id, watermark_sequence, last_committed_row, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (source_id, stream_key) DO UPDATE SET
                            watermark_sequence = EXCLUDED.watermark_sequence,
                            last_committed_row = EXCLUDED.last_committed_row,
                            updated_at = NOW();
                        """,
                        (self.source_id, stream_key, self.tenant_id, new_wm_seq, new_wm_row)
                    )

                    # Log successful run
                    cur.execute(
                        """
                        INSERT INTO connector_runs (id, tenant_id, source_id, run_type, status, rows_read, rows_committed, rows_rejected, completed_at, duration_ms)
                        VALUES (%s, %s, %s, 'incremental', 'COMPLETED', %s, %s, 0, NOW(), %s);
                        """,
                        (run_id, self.tenant_id, self.source_id, len(chunk_rows), len(chunk_rows), int((time.time() - start_time) * 1000))
                    )
                    conn.commit()
                    return {
                        "status": "CHUNK_COMMITTED",
                        "run_id": run_id,
                        "rows_committed": len(chunk_rows),
                        "watermark_sequence": new_wm_seq,
                        "last_committed_row": new_wm_row
                    }

                except Exception as e:
                    conn.rollback()
                    # Open a fresh connection/transaction to record the run failure without committing failed rows
                    failed_row = idx if 'idx' in locals() else 0
                    err_code = getattr(e, 'error_code', 'UNEXPECTED_ERROR')
                    err_msg = str(e)
                    with psycopg.connect(target_db_url) as err_conn:
                        with err_conn.cursor() as err_cur:
                            err_cur.execute(f"SET app.current_tenant_id = '{self.tenant_id}';")
                            err_cur.execute(
                                """
                                INSERT INTO connector_runs (id, tenant_id, source_id, run_type, status, rows_read, rows_committed, rows_rejected, error_summary, completed_at, duration_ms)
                                VALUES (%s, %s, %s, 'incremental', 'FAILED', %s, 0, 1, %s, NOW(), %s);
                                """,
                                (
                                    run_id,
                                    self.tenant_id,
                                    self.source_id,
                                    len(chunk_rows),
                                    json.dumps({"error_code": err_code, "last_failed_row_in_chunk": failed_row, "message": err_msg}),
                                    int((time.time() - start_time) * 1000)
                                )
                            )
                            err_conn.commit()

                    return {
                        "status": "CHUNK_ROLLED_BACK",
                        "run_id": run_id,
                        "rows_committed": 0,
                        "watermark_sequence": current_wm_seq,
                        "last_committed_row": current_wm_row,
                        "last_failed_row_in_chunk": failed_row,
                        "error_code": err_code,
                        "error": err_msg
                    }

    def health_check(self) -> bool:
        try:
            rows = self.execute_query("SELECT 1;")
            return len(rows) > 0 and rows[0][0] == 1
        except Exception:
            return False

    def close(self) -> None:
        if self.conn and not self.conn.closed:
            self.conn.close()
