"""
VerdantOS Bulk Asset Import/Export Engine (STORY-2.B)
Supports CSV and JSON bulk import/export with schema validation,
per-row structured error reporting, dry-run preview, and 100% transactional rollback on error.
"""
from typing import Dict, List, Any, Optional, Tuple
import csv
import io
import json
import uuid
import psycopg

class BulkImportError(Exception):
    """Raised when bulk import contains invalid rows during execution."""
    def __init__(self, errors: List[Dict[str, Any]]):
        super().__init__(f"Bulk import failed with {len(errors)} error(s)")
        self.errors = errors

class BulkAssetEngine:
    REQUIRED_COLUMNS = ["name", "asset_type", "path"]
    VALID_ASSET_TYPES = {"site", "building", "system", "equipment", "subsystem", "point", "ahu", "chiller", "meter", "transformer"}

    @staticmethod
    def parse_csv(csv_text: str) -> List[Dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        return [dict(row) for row in reader]

    @staticmethod
    def export_csv(assets: List[Dict[str, Any]]) -> str:
        """Export assets to canonical CSV format."""
        fields = ["id", "tenant_id", "name", "asset_type", "path", "parent_id", "brick_class"]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for a in assets:
            writer.writerow({
                "id": str(a.get("id", "")),
                "tenant_id": str(a.get("tenant_id", "")),
                "name": a.get("name", ""),
                "asset_type": a.get("asset_type", ""),
                "path": a.get("path", ""),
                "parent_id": str(a.get("parent_id", "") or ""),
                "brick_class": a.get("brick_class", "") or ""
            })
        return output.getvalue()

    @staticmethod
    def validate_rows(
        rows: List[Dict[str, Any]],
        tenant_id: str,
        existing_paths: Optional[set] = None,
        existing_ids: Optional[set] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validates imported rows against the 6 required error categories:
        1. MISSING_REQUIRED_FIELD
        2. INVALID_TYPE
        3. DUPLICATE_IN_FILE
        4. DUPLICATE_IN_DB
        5. INVALID_PARENT_REFERENCE
        6. TENANT_ISOLATION_VIOLATION
        Returns: (rows_to_insert, rows_to_skip, errors)
        """
        rows_to_insert = []
        rows_to_skip = []
        errors = []
        seen_paths = set()
        seen_ids = set() if existing_ids is None else set(existing_ids)
        existing_paths = existing_paths or set()

        file_ids = {r.get("id") for r in rows if r.get("id")}
        all_known_ids = seen_ids.union(file_ids)

        for idx, row in enumerate(rows, start=1):
            row_errors = []

            # 1. Missing required fields
            for req in BulkAssetEngine.REQUIRED_COLUMNS:
                if not row.get(req) or not str(row[req]).strip():
                    row_errors.append({
                        "row": idx,
                        "error_code": "MISSING_REQUIRED_FIELD",
                        "field": req,
                        "message": f"Row {idx}: Missing required field '{req}'"
                    })

            # 2. Invalid type
            asset_type = str(row.get("asset_type", "")).strip().lower()
            if asset_type and asset_type not in BulkAssetEngine.VALID_ASSET_TYPES:
                row_errors.append({
                    "row": idx,
                    "error_code": "INVALID_TYPE",
                    "field": "asset_type",
                    "message": f"Row {idx}: Invalid asset_type '{asset_type}'. Valid types: {sorted(BulkAssetEngine.VALID_ASSET_TYPES)}"
                })

            # 3. Duplicate path in file
            path = str(row.get("path", "")).strip()
            if path:
                if path in seen_paths:
                    row_errors.append({
                        "row": idx,
                        "error_code": "DUPLICATE_IN_FILE",
                        "field": "path",
                        "message": f"Row {idx}: Duplicate path '{path}' within import file"
                    })
                seen_paths.add(path)

            # 4. Duplicate path in DB -> Eligible for idempotent skip
            is_db_duplicate = False
            if path and path in existing_paths:
                is_db_duplicate = True

            # 5. Invalid parent reference
            parent_id = row.get("parent_id")
            if parent_id and str(parent_id).strip() and str(parent_id).strip() not in all_known_ids:
                row_errors.append({
                    "row": idx,
                    "error_code": "INVALID_PARENT_REFERENCE",
                    "field": "parent_id",
                    "message": f"Row {idx}: Parent ID '{parent_id}' does not exist"
                })

            # 6. Tenant isolation violation
            row_tenant = row.get("tenant_id")
            if row_tenant and str(row_tenant).strip() != tenant_id:
                row_errors.append({
                    "row": idx,
                    "error_code": "TENANT_ISOLATION_VIOLATION",
                    "field": "tenant_id",
                    "message": f"Row {idx}: Row tenant_id '{row_tenant}' does not match session tenant_id '{tenant_id}'"
                })

            if row_errors:
                errors.extend(row_errors)
            elif is_db_duplicate:
                rows_to_skip.append(row)
            else:
                rows_to_insert.append(row)

        return rows_to_insert, rows_to_skip, errors

    @staticmethod
    def execute_import(
        db_url: str,
        rows: List[Dict[str, Any]],
        tenant_id: str,
        dry_run: bool = False,
        allow_idempotent_skip: bool = True
    ) -> Dict[str, Any]:
        """
        Executes bulk import transactionally into PostgreSQL.
        If any row has validation errors or dry_run=True, performs a clean 100% ROLLBACK.
        """
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Fetch existing paths and IDs for the tenant
                cur.execute(f"SET app.current_tenant_id = '{tenant_id}';")
                cur.execute("SELECT path, id FROM assets WHERE tenant_id = %s;", (tenant_id,))
                res = cur.fetchall()
                existing_paths = {row[0] for row in res}
                existing_ids = {str(row[1]) for row in res}

                to_insert, to_skip, errors = BulkAssetEngine.validate_rows(
                    rows, tenant_id, existing_paths=existing_paths, existing_ids=existing_ids
                )

                # If duplicate paths in DB are not allowed (strict mode), flag as error
                if not allow_idempotent_skip and to_skip:
                    for row in to_skip:
                        errors.append({
                            "row": 0,
                            "error_code": "DUPLICATE_IN_DB",
                            "field": "path",
                            "message": f"Path '{row['path']}' already exists in database"
                        })

                if errors:
                    conn.rollback()
                    return {
                        "status": "FAILED",
                        "dry_run": dry_run,
                        "inserted_count": 0,
                        "skipped_count": 0,
                        "errors": errors
                    }

                if dry_run:
                    conn.rollback()
                    return {
                        "status": "DRY_RUN_SUCCESS",
                        "dry_run": True,
                        "inserted_count": len(to_insert),
                        "skipped_count": len(to_skip),
                        "errors": []
                    }

                # Transactional insert
                user_id = '00000000-0000-0000-0000-000000000000'
                insert_batch = []
                for r in to_insert:
                    row_id = r.get("id") or str(uuid.uuid4())
                    parent = r.get("parent_id") or None
                    b_class = r.get("brick_class") or None
                    insert_batch.append((
                        row_id,
                        tenant_id,
                        r["name"],
                        r["asset_type"],
                        r["path"],
                        parent,
                        b_class,
                        user_id
                    ))

                if insert_batch:
                    cur.executemany(
                        "INSERT INTO assets (id, tenant_id, name, asset_type, path, parent_id, brick_class, created_by) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                        insert_batch
                    )
                conn.commit()

                return {
                    "status": "COMMITTED",
                    "dry_run": False,
                    "inserted_count": len(insert_batch),
                    "skipped_count": len(to_skip),
                    "errors": []
                }
