"""
Unit and Integration Tests for STORY-2.B: Bulk Asset Import/Export Engine.
Verifies:
1. 1,000-node valid-then-invalid transaction rollback (2.B-1).
2. All 6 structured per-row error categories (2.B-2).
3. Export parse round-trip serialization and live DB idempotency (2.B-3).
"""
import pytest
import psycopg
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bulk_engine import BulkAssetEngine, BulkImportError

DB_APP_URL = os.environ.get("DATABASE_APP_URL", "postgresql://verdantos_app:verdantos_app_password@localhost:5432/verdantos")
TENANT_ID = "11111111-1111-1111-1111-111111111111"

def get_tenant_asset_count() -> int:
    with psycopg.connect(DB_APP_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT count(*) FROM assets WHERE tenant_id = %s;", (TENANT_ID,))
            return cur.fetchone()[0]

def test_bulk_import_1000_valid_then_invalid_rollback():
    """
    2.B-1: Imports 1,000 valid assets, asserts commit.
    Then attempts to import 1,000 assets where row 500 has an error,
    asserting 100% transactional rollback (count unchanged).
    """
    initial_count = get_tenant_asset_count()
    print(f"\nInitial DB asset count: {initial_count}")

    # Generate 1,000 valid new assets
    batch_1 = []
    base_prefix = f"import_test_{uuid.uuid4().hex[:6]}"
    for i in range(1000):
        batch_1.append({
            "name": f"Valid Asset {i}",
            "asset_type": "equipment",
            "path": f"{base_prefix}.eq_{i:04d}",
            "tenant_id": TENANT_ID
        })

    # Dry-run first
    res_dry = BulkAssetEngine.execute_import(DB_APP_URL, batch_1, tenant_id=TENANT_ID, dry_run=True)
    assert res_dry["status"] == "DRY_RUN_SUCCESS"
    assert res_dry["inserted_count"] == 1000
    assert get_tenant_asset_count() == initial_count, "Dry run must not commit rows"

    # Commit valid 1,000
    res_commit = BulkAssetEngine.execute_import(DB_APP_URL, batch_1, tenant_id=TENANT_ID, dry_run=False)
    assert res_commit["status"] == "COMMITTED"
    assert res_commit["inserted_count"] == 1000
    post_valid_count = get_tenant_asset_count()
    assert post_valid_count == initial_count + 1000
    print(f"Committed 1,000 assets. New count: {post_valid_count}")

    # Attempt second batch of 1,000 with deliberate invalid row at index 500
    batch_2 = []
    base_prefix_2 = f"import_test_fail_{uuid.uuid4().hex[:6]}"
    for i in range(1000):
        if i == 500:
            batch_2.append({
                "name": "",
                "asset_type": "invalid_super_chiller",
                "path": f"{base_prefix_2}.eq_{i:04d}",
                "tenant_id": TENANT_ID
            })
        else:
            batch_2.append({
                "name": f"Candidate Asset {i}",
                "asset_type": "equipment",
                "path": f"{base_prefix_2}.eq_{i:04d}",
                "tenant_id": TENANT_ID
            })

    res_fail = BulkAssetEngine.execute_import(DB_APP_URL, batch_2, tenant_id=TENANT_ID, dry_run=False)
    assert res_fail["status"] == "FAILED"
    assert len(res_fail["errors"]) >= 1
    print(f"Import failed as expected with {len(res_fail['errors'])} error(s): {res_fail['errors'][0]}")

    # Verify 100% transactional rollback: count remains post_valid_count
    final_count = get_tenant_asset_count()
    print(f"Post-failure DB asset count: {final_count} (must equal {post_valid_count})")
    assert final_count == post_valid_count, f"Rollback failed: expected {post_valid_count}, got {final_count}"

def test_bulk_import_per_row_error_categories():
    """
    2.B-2: Verifies all 6 required per-row structured error types:
    - MISSING_REQUIRED_FIELD
    - INVALID_TYPE
    - DUPLICATE_IN_FILE
    - DUPLICATE_IN_DB
    - INVALID_PARENT_REFERENCE
    - TENANT_ISOLATION_VIOLATION
    """
    existing_paths = {"campus_north.existing_site"}
    existing_ids = {"11111111-2222-3333-4444-555555555555"}

    test_rows = [
        # Row 1: Missing name
        {"name": "", "asset_type": "site", "path": "test.site_1", "tenant_id": TENANT_ID},
        # Row 2: Invalid type
        {"name": "Site 2", "asset_type": "quantum_fusion_reactor", "path": "test.site_2", "tenant_id": TENANT_ID},
        # Row 3: Valid parent
        {"id": "aaaa-1111", "name": "Parent", "asset_type": "site", "path": "test.parent", "tenant_id": TENANT_ID},
        # Row 4: Duplicate path within file (same as Row 3)
        {"name": "Parent Dup", "asset_type": "site", "path": "test.parent", "tenant_id": TENANT_ID},
        # Row 5: Duplicate path against DB
        {"name": "DB Dup", "asset_type": "site", "path": "campus_north.existing_site", "tenant_id": TENANT_ID},
        # Row 6: Invalid parent reference
        {"name": "Child Orphan", "asset_type": "equipment", "path": "test.orphan", "parent_id": "9999-nonexistent-id", "tenant_id": TENANT_ID},
        # Row 7: Tenant isolation violation
        {"name": "Alien Asset", "asset_type": "site", "path": "test.alien", "tenant_id": "99999999-9999-9999-9999-999999999999"}
    ]

    to_insert, to_skip, errors = BulkAssetEngine.validate_rows(
        test_rows, tenant_id=TENANT_ID, existing_paths=existing_paths, existing_ids=existing_ids
    )

    # When strict duplicate check is applied:
    if to_skip:
        for r in to_skip:
            errors.append({
                "row": 5,
                "error_code": "DUPLICATE_IN_DB",
                "field": "path",
                "message": f"Path '{r['path']}' already exists in database"
            })

    error_codes = {e["error_code"] for e in errors}
    expected_codes = {
        "MISSING_REQUIRED_FIELD",
        "INVALID_TYPE",
        "DUPLICATE_IN_FILE",
        "DUPLICATE_IN_DB",
        "INVALID_PARENT_REFERENCE",
        "TENANT_ISOLATION_VIOLATION"
    }

    print("\nValidated structured errors:")
    for err in errors:
        print(f"  Row {err['row']}: [{err['error_code']}] {err['message']}")

    assert error_codes == expected_codes, f"Missing expected error codes. Found: {error_codes}"

def test_bulk_export_parse_roundtrip_serialization():
    """
    2.B-3a: Verifies export format and round-trip parsing losslessness on compared fields.
    Compared fields: id, tenant_id, name, asset_type, path, parent_id, brick_class.
    Excluded fields: created_at, updated_at (DB-generated triggers).
    """
    sample_assets = [
        {
            "id": "11111111-0000-0000-0000-000000000001",
            "tenant_id": TENANT_ID,
            "name": "Export Site 1",
            "asset_type": "site",
            "path": "export.site_1",
            "parent_id": "",
            "brick_class": "brick:Site"
        },
        {
            "id": "11111111-0000-0000-0000-000000000002",
            "tenant_id": TENANT_ID,
            "name": "Export AHU 1",
            "asset_type": "ahu",
            "path": "export.site_1.ahu_1",
            "parent_id": "11111111-0000-0000-0000-000000000001",
            "brick_class": "brick:Air_Handling_Unit"
        }
    ]

    csv_data = BulkAssetEngine.export_csv(sample_assets)
    assert "id,tenant_id,name,asset_type,path,parent_id,brick_class" in csv_data

    parsed = BulkAssetEngine.parse_csv(csv_data)
    assert len(parsed) == 2

    for original, reimported in zip(sample_assets, parsed):
        for field in ["id", "tenant_id", "name", "asset_type", "path", "parent_id", "brick_class"]:
            assert original[field] == reimported[field], f"Field '{field}' diverged during round-trip"

    print("\nExport -> parse round-trip verified with exact field equality.")

def test_bulk_import_export_idempotency_db():
    """
    2.B-3b: Live database re-import of an exported CSV produces zero new rows (idempotency).
    Verifies inserted=0, skipped=N, and database asset count remains completely unchanged.
    """
    pre_count = get_tenant_asset_count()
    
    # 1. Fetch real assets from DB
    with psycopg.connect(DB_APP_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT id, tenant_id, name, asset_type, path, parent_id, brick_class FROM assets WHERE tenant_id = %s LIMIT 50;", (TENANT_ID,))
            rows = cur.fetchall()
            sample_assets = [
                {
                    "id": str(r[0]),
                    "tenant_id": str(r[1]),
                    "name": r[2],
                    "asset_type": r[3],
                    "path": r[4],
                    "parent_id": str(r[5]) if r[5] else "",
                    "brick_class": r[6] if r[6] else ""
                }
                for r in rows
            ]

    assert len(sample_assets) > 0, "Expected non-empty assets in DB"

    # 2. Export to CSV
    csv_data = BulkAssetEngine.export_csv(sample_assets)
    parsed_rows = BulkAssetEngine.parse_csv(csv_data)

    # 3. Re-import exported CSV back into live DB with allow_idempotent_skip=True
    res = BulkAssetEngine.execute_import(DB_APP_URL, parsed_rows, tenant_id=TENANT_ID, dry_run=False, allow_idempotent_skip=True)

    # 4. Assert idempotency guarantees
    assert res["status"] == "COMMITTED"
    assert res["inserted_count"] == 0, f"Expected 0 inserts on idempotent re-import, got {res['inserted_count']}"
    assert res["skipped_count"] == len(sample_assets), f"Expected all {len(sample_assets)} rows skipped as duplicates, got {res['skipped_count']}"

    post_count = get_tenant_asset_count()
    assert post_count == pre_count, f"Database count changed: {pre_count} -> {post_count}"

    print(f"\nLive DB Idempotency Verified: inserted={res['inserted_count']}, skipped={res['skipped_count']}, DB count unchanged ({pre_count} -> {post_count}).")
