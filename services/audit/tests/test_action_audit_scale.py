"""
Integration Tests for Phase 5 Workstream 5: Action/PDCA/Audit at Scale (§5.11 / STORY-W5)
Verifies:
1. W5-1: 10,000 actions bulk creation throughput.
2. W5-2: 1,000,000 audit records verification time within SLO.
3. W5-3: Chain integrity and tamper detection at volume.
4. W5-4: PDCA workflow integrity (transitions recorded in action_history).
5. W5-5: Action-to-EnPI linkage at scale (1,000 linked vs 9,000 unlinked).
6. W5-6: Customer-facing SLO confirmation for annual ISO 50001 audit verification.
"""
import pytest
import os
import sys
import time
import uuid
import json
import psycopg

sys.path.insert(0, os.path.abspath("."))
from services.audit.scale_audit_engine import ScaleAuditEngine

DB_URL = "postgresql://postgres@/verdantos?host=/var/run/postgresql&port=5433"
TENANT_ID = "11111111-1111-1111-1111-111111111111"

def test_w5_1_and_w5_5_action_items_at_scale():
    """
    W5-1: 10,000 actions bulk creation and throughput.
    W5-5: Action-to-EnPI linkage at scale (1,000 linked to ENPI_kwh_per_m2, 9,000 unlinked).
    """
    n_actions = 10000
    n_linked = 1000
    owner_id = "00000000-0000-0000-0000-000000000000"

    # Clean existing test actions for tenant
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("DELETE FROM action_items WHERE tenant_id = %s;", (TENANT_ID,))
        conn.commit()

    actions_batch = []
    for i in range(n_actions):
        act_id = str(uuid.uuid4())
        enpi_id = "ENPI_kwh_per_m2" if i < n_linked else None
        title = f"Action {i} - Mitigate Baseload"
        actions_batch.append((act_id, TENANT_ID, title, owner_id, "OPEN", enpi_id, owner_id))

    t0 = time.time()
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.executemany("""
                INSERT INTO action_items (id, tenant_id, title, owner_id, status, enpi_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, actions_batch)
        conn.commit()
    elapsed = time.time() - t0

    print(f"\nW5-1 Bulk Action Creation at Scale:")
    print(f"  Inserted {n_actions} actions in {elapsed:.2f}s ({n_actions / elapsed:.1f} actions/sec)")

    # Assert 10,000 actions
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT count(*) FROM action_items WHERE status = 'OPEN';")
            total_open = cur.fetchone()[0]
            print(f"  SELECT COUNT(*) FROM action_items WHERE status = 'OPEN' -> {total_open}")
            assert total_open == n_actions

            # W5-5: Linkage at scale
            cur.execute("SELECT count(*) FROM action_items WHERE enpi_id = 'ENPI_kwh_per_m2';")
            linked_count = cur.fetchone()[0]
            print(f"\nW5-5 Action-to-EnPI Linkage at Scale:")
            print(f"  SELECT COUNT(*) FROM action_items WHERE enpi_id = 'ENPI_kwh_per_m2' -> {linked_count} (Expected: {n_linked})")
            assert linked_count == n_linked

def test_w5_4_pdca_workflow_integrity():
    """
    W5-4: PDCA workflow integrity.
    Create nonconformity -> assign corrective action -> mark resolved -> verify action_history.
    """
    action_id = str(uuid.uuid4())
    user_id = "00000000-0000-0000-0000-000000000000"

    # Step 1: Create Nonconformity action in PLAN status
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                INSERT INTO action_items (id, tenant_id, title, owner_id, status, created_by)
                VALUES (%s, %s, 'NC-2026-001: Excess Baseload during Holiday', %s, 'PLAN', %s);
            """, (action_id, TENANT_ID, user_id, user_id))

            cur.execute("""
                INSERT INTO action_history (action_id, tenant_id, old_status, new_status, transition_reason, transitioned_by)
                VALUES (%s, %s, NULL, 'PLAN', 'Nonconformity identified in automated EnPI audit', %s);
            """, (action_id, TENANT_ID, user_id))
        conn.commit()

    # Step 2: Transition PLAN -> DO (assigned to field tech)
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("UPDATE action_items SET status = 'DO' WHERE id = %s;", (action_id,))
            cur.execute("""
                INSERT INTO action_history (action_id, tenant_id, old_status, new_status, transition_reason, transitioned_by)
                VALUES (%s, %s, 'PLAN', 'DO', 'Assigned damper adjustment to mechanical contractor', %s);
            """, (action_id, TENANT_ID, user_id))
        conn.commit()

    # Step 3: Transition DO -> CHECK (measure post-fix verification)
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("UPDATE action_items SET status = 'CHECK' WHERE id = %s;", (action_id,))
            cur.execute("""
                INSERT INTO action_history (action_id, tenant_id, old_status, new_status, transition_reason, transitioned_by)
                VALUES (%s, %s, 'DO', 'CHECK', 'Physical damper fixed; monitoring baseload for 7 days', %s);
            """, (action_id, TENANT_ID, user_id))
        conn.commit()

    # Step 4: Transition CHECK -> ACT (resolved / standardized)
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("UPDATE action_items SET status = 'ACT' WHERE id = %s;", (action_id,))
            cur.execute("""
                INSERT INTO action_history (action_id, tenant_id, old_status, new_status, transition_reason, transitioned_by)
                VALUES (%s, %s, 'CHECK', 'ACT', 'Savings verified via IPMVP Option B; closed', %s);
            """, (action_id, TENANT_ID, user_id))
        conn.commit()

    # Query progression
    print("\nW5-4 PDCA Action Transition Progression:")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                SELECT old_status, new_status, transition_reason, transitioned_at
                FROM action_history
                WHERE action_id = %s
                ORDER BY transitioned_at ASC;
            """, (action_id,))
            rows = cur.fetchall()
            for r in rows:
                print(f"  Transition: {str(r[0]):5} -> {r[1]:5} | Reason: {r[2]} | At: {str(r[3])[:19]}")

    assert len(rows) == 4
    assert rows[0][1] == "PLAN"
    assert rows[1][1] == "DO"
    assert rows[2][1] == "CHECK"
    assert rows[3][1] == "ACT"

def test_w5_2_w5_3_w5_6_audit_scale_1m_and_tamper():
    """
    W5-2: 1,000,000 audit records verification time within SLO.
    W5-3: Chain integrity & tamper detection at volume (record #500,000 tampered).
    W5-6: Customer-facing SLO confirmation for annual ISO 50001 audit verification.
    """
    n_records = 1000000
    print(f"\nGenerating and verifying {n_records:,} SHA-256 audit records...")

    # Generate synthetic audit records with valid cryptographic chaining
    records = []
    prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    ent_id = "00000000-0000-0000-0000-000000000001"
    act = "TELEMETRY_LOG"
    payload = {"val": 42.0}

    # Pre-compute chunk hashes in batches for speed
    t0_gen = time.time()
    for i in range(n_records):
        cur_hash = ScaleAuditEngine.compute_record_hash(ent_id, act, payload, prev_hash)
        records.append({
            "entity_id": ent_id,
            "action_type": act,
            "payload_after": payload,
            "cryptographic_hash": cur_hash,
            "previous_hash": prev_hash
        })
        prev_hash = cur_hash
    gen_time = time.time() - t0_gen
    print(f"  Generated {n_records:,} cryptographically chained records in {gen_time:.2f}s")

    # W5-2 & W5-6: Verify intact chain of 1M records
    t0_verify = time.time()
    is_valid, count, reason = ScaleAuditEngine.verify_chain(records)
    verify_time = time.time() - t0_verify

    print(f"\nW5-2 & W5-6 Chain Verification Performance at Scale:")
    print(f"  SUCCESS: {count:,} records verified in {verify_time:.2f}s")
    print(f"  Verification Throughput: {count / verify_time:,.0f} records/sec")
    print(f"  Customer-Facing Annual Audit Target: < 300.0s (5 minutes) -> Actual: {verify_time:.2f}s")

    assert is_valid is True
    assert count == n_records
    assert reason == "CHAIN_INTACT"
    assert verify_time < 300.0, f"Verification time {verify_time:.2f}s exceeds 5-minute SLO target"

    # W5-3: Tamper record #500,000 and verify immediate detection
    tamper_idx = 500000
    tampered_records = list(records)
    tampered_records[tamper_idx] = dict(tampered_records[tamper_idx])
    tampered_records[tamper_idx]["payload_after"] = {"val": 999.0} # Manipulated energy reading

    t0_tamper = time.time()
    is_valid_t, count_t, reason_t = ScaleAuditEngine.verify_chain(tampered_records)
    tamper_detect_time = time.time() - t0_tamper

    print(f"\nW5-3 Tamper Detection at Volume (Record #{tamper_idx:,}):")
    print(f"  Result: {reason_t}")
    print(f"  Detection Index: {count_t} (Detected in {tamper_detect_time:.2f}s)")

    assert is_valid_t is False
    assert count_t == tamper_idx
    assert "TAMPER_DETECTED" in reason_t
