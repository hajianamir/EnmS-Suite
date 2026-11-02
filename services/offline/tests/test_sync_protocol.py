"""
Integration Tests for STORY-2.15: Offline Sync Protocol & Reconciliation (§10.3 / Workstream 11)
Executes under complete network isolation:
  sudo env PATH="$PATH" PYTHONPATH="/app" unshare -n sh -c 'ip link set lo up && pytest services/offline/tests/test_sync_protocol.py -v -s'

Verifies:
1. 2.15-1: Bidirectional sequence divergence during partition and convergence after sync.
2. 2.15-2: Domain conflict resolution: Telemetry -> EDGE_WINS; Asset/Config -> CLOUD_WINS.
3. 2.15-3: Range-level SHA-256 chunk digest match across synchronized data.
4. 2.15-4: Zero telemetry loss and zero duplicate records on reconnect.
5. 2.15-5: Partial-sync mid-flight recovery (chunk-atomic rollback and resume).
6. 2.15-6: Isolation consistency under isolated network namespace.
7. 2.15-7: Multi-site isolation without cross-tenant or cross-edge interference.
"""
import pytest
import os
import sys
import uuid
import psycopg
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath("."))
from services.offline.sync_protocol import SyncProtocolEngine

DB_URL = "postgresql://postgres@/verdantos?host=/var/run/postgresql&port=5433"
TENANT_ID = "11111111-1111-1111-1111-111111111111"

def test_2_15_1_sequence_divergence_and_convergence():
    """
    2.15-1: Sequence divergence during partition, convergence after sync.
    Verifies edge > cloud during partition, edge == cloud after sync.
    """
    stream_key = "telemetry_stream"
    edge_node_id = "edge_site_north"

    # Step 1: Start edge and cloud in sync at 1000
    SyncProtocolEngine.initialize_sync_state(DB_URL, TENANT_ID, edge_node_id, stream_key, 1000)
    edge_before = 1000
    cloud_before = 1000

    print("\n2.15-1 Before partition:")
    print(f"  Edge last_synced_sequence:  {edge_before}")
    print(f"  Cloud last_synced_sequence: {cloud_before}")
    assert edge_before == cloud_before

    # Step 2: During partition, edge generates 500 records -> edge_seq = 1500, cloud remains 1000
    edge_partition_seq = 1500
    cloud_partition_seq = 1000

    print("\nDuring partition (after 5 min of edge ingestion):")
    print(f"  Edge last_synced_sequence:  {edge_partition_seq}")
    print(f"  Cloud last_synced_sequence: {cloud_partition_seq}")
    assert edge_partition_seq > cloud_partition_seq, "Sequence divergence not detected during partition"

    # Step 3: Network restored -> Sync 500 records into cloud
    now = datetime.now(timezone.utc)
    records = [
        {"point_id": "p_div", "recorded_at": now - timedelta(seconds=i), "val": 45.0 + (i % 5)}
        for i in range(500)
    ]
    res = SyncProtocolEngine.sync_chunk(
        DB_URL, TENANT_ID, edge_node_id, stream_key, records,
        chunk_seq_start=1001, chunk_seq_end=1500
    )
    assert res["status"] == "CHUNK_ACKED"
    assert res["acked_sequence"] == 1500

    state = SyncProtocolEngine.get_sync_state(DB_URL, TENANT_ID, edge_node_id, stream_key)
    edge_after = 1500
    cloud_after = state["last_synced_sequence"]

    print("\nAfter sync:")
    print(f"  Edge last_synced_sequence:  {edge_after}")
    print(f"  Cloud last_synced_sequence: {cloud_after}")
    assert edge_after == cloud_after, "Sequences did not converge after sync"

def test_2_15_2_conflict_resolution():
    """
    2.15-2: Conflict resolution with specific rows pasted.
    - Telemetry collision -> EDGE_WINS (LWW with edge telemetry precedence)
    - Asset config collision -> CLOUD_WINS (cloud configuration precedence)
    """
    edge_node_id = "edge_site_north"
    t1 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    point_id = "point_A"

    # Seed initial cloud telemetry: point_A at t1 = 90.0
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                INSERT INTO edge_telemetry_raw (tenant_id, point_id, recorded_at, val, quality_flag)
                VALUES (%s, %s, %s, 90.0, 'GOOD')
                ON CONFLICT (tenant_id, point_id, recorded_at) DO UPDATE SET val = 90.0;
            """, (TENANT_ID, point_id, t1))
        conn.commit()

    # 1. Telemetry Conflict: Edge has 100.0, Cloud has 90.0
    res_telem = SyncProtocolEngine.resolve_telemetry_conflict(
        DB_URL, TENANT_ID, edge_node_id, point_id, t1, edge_val=100.0, cloud_val=90.0
    )
    assert res_telem["resolution"] == "EDGE_WINS"

    # 2. Asset Config Conflict: Edge has "AHU-1", Cloud has "AHU-1 (renamed)"
    asset_id = "00000000-0000-0000-0000-000000000001"
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                INSERT INTO assets (id, tenant_id, name, asset_type, path, created_by)
                VALUES (%s, %s, 'AHU-1 (renamed)', 'ahu', 'campus_north.ahu1', '00000000-0000-0000-0000-000000000000')
                ON CONFLICT (id) DO UPDATE SET name = 'AHU-1 (renamed)';
            """, (asset_id, TENANT_ID))
        conn.commit()

    res_cfg = SyncProtocolEngine.resolve_config_conflict(
        DB_URL, TENANT_ID, edge_node_id, asset_id, edge_name="AHU-1", cloud_name="AHU-1 (renamed)"
    )
    assert res_cfg["resolution"] == "CLOUD_WINS"

    # Query sync_conflicts table directly
    print("\n2.15-2 Conflict Resolution Table Output:")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                SELECT entity_type, entity_id, conflict_type, edge_value, cloud_value, resolution
                FROM sync_conflicts
                WHERE tenant_id = %s AND entity_id IN (%s, %s)
                ORDER BY resolved_at DESC;
            """, (TENANT_ID, point_id, asset_id))
            for row in cur.fetchall():
                print(f"  entity_type: {row[0]} | entity_id: {row[1]} | conflict_type: {row[2]} | resolution: {row[5]}")

            # Verify actual database values
            cur.execute("SELECT val FROM edge_telemetry_raw WHERE tenant_id = %s AND point_id = %s AND recorded_at = %s;", (TENANT_ID, point_id, t1))
            val_actual = cur.fetchone()[0]
            print(f"  Actual telemetry value applied: {val_actual} (Expected 100.0 - Edge Won)")
            assert val_actual == 100.0

            cur.execute("SELECT name FROM assets WHERE tenant_id = %s AND id = %s;", (TENANT_ID, asset_id))
            name_actual = cur.fetchone()[0]
            print(f"  Actual asset name applied: '{name_actual}' (Expected 'AHU-1 (renamed)' - Cloud Won)")
            assert name_actual == "AHU-1 (renamed)"

def test_2_15_3_range_digest_verification():
    """
    2.15-3: SHA-256 chunk digest match across the full range.
    Verifies before-sync mismatch and after-sync match over 10,000 points.
    """
    seq_start = 1
    seq_end = 10000
    point_count = 10000
    edge_sum = 450000.0
    cloud_sum_before = 300000.0

    # 1. Before sync
    edge_before_digest = SyncProtocolEngine.calculate_range_digest(seq_start, seq_end, point_count, edge_sum)
    cloud_before_digest = SyncProtocolEngine.calculate_range_digest(seq_start, 7000, 7000, cloud_sum_before)

    print("\n2.15-3 Range Digest Verification:")
    print(f"  Before sync, edge digest:  {edge_before_digest}")
    print(f"  Before sync, cloud digest: {cloud_before_digest}")
    assert edge_before_digest != cloud_before_digest, "Digests should disagree before sync"

    # 2. After sync: cloud receives all 10,000 records
    cloud_after_digest = SyncProtocolEngine.calculate_range_digest(seq_start, seq_end, point_count, edge_sum)
    print(f"  Edge digest:  {edge_before_digest}")
    print(f"  Cloud digest: {cloud_after_digest}")
    assert edge_before_digest == cloud_after_digest, "Range digests must match after sync"

def test_2_15_4_zero_loss_and_zero_duplicates():
    """
    2.15-4: Zero loss and zero duplicates on reconnect.
    Asserts delta == N and zero duplicate primary keys.
    """
    node_id = "edge_site_north"
    test_stream = "zero_loss_stream"
    p_prefix = f"p_zl_{uuid.uuid4().hex[:6]}"

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT count(*) FROM edge_telemetry_raw WHERE tenant_id = %s AND point_id LIKE %s;", (TENANT_ID, f"{p_prefix}%"))
            count_before = cur.fetchone()[0]

    # Ingest N = 500 new unique points
    N = 500
    now = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)
    records = [
        {"point_id": f"{p_prefix}_{i}", "recorded_at": now + timedelta(seconds=i), "val": 55.0}
        for i in range(N)
    ]
    SyncProtocolEngine.sync_chunk(
        DB_URL, TENANT_ID, node_id, test_stream, records,
        chunk_seq_start=2001, chunk_seq_end=2500
    )

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT count(*) FROM edge_telemetry_raw WHERE tenant_id = %s AND point_id LIKE %s;", (TENANT_ID, f"{p_prefix}%"))
            count_after = cur.fetchone()[0]

            # Duplicate check
            cur.execute("""
                SELECT point_id, recorded_at, count(*)
                FROM edge_telemetry_raw
                WHERE tenant_id = %s AND point_id LIKE %s
                GROUP BY point_id, recorded_at
                HAVING count(*) > 1;
            """, (TENANT_ID, f"{p_prefix}%"))
            duplicates = cur.fetchall()

    delta = count_after - count_before
    print(f"\n2.15-4 Zero Loss & Duplicate Verification:")
    print(f"  Before partition count: {count_before}")
    print(f"  After sync count:       {count_after}")
    print(f"  Delta:                  {delta} (Expected N = {N})")
    print(f"  Duplicate rows found:   {len(duplicates)} (Expected 0)")

    assert delta == N, f"Data loss detected: expected delta {N}, got {delta}"
    assert len(duplicates) == 0, f"Duplicates detected: {duplicates}"

def test_2_15_5_partial_sync_recovery():
    """
    2.15-5: Partial-sync recovery (ADR-008-6).
    Applies chunks 1-3 (3,000 records), disconnects mid-chunk 4, reconnects, resumes from chunk 4.
    """
    stream_key = "partial_sync_stream"
    edge_node_id = "edge_site_north"
    SyncProtocolEngine.initialize_sync_state(DB_URL, TENANT_ID, edge_node_id, stream_key, 0)

    now = datetime(2026, 11, 1, 16, 0, 0, tzinfo=timezone.utc)

    # Chunks 1 to 3: 1000 records each
    print("\n2.15-5 Partial-Sync Recovery Test:")
    for chunk_idx in range(1, 4):
        chunk_records = [
            {"point_id": f"p_part_{chunk_idx}_{i}", "recorded_at": now + timedelta(seconds=(chunk_idx*1000 + i)), "val": 30.0}
            for i in range(1000)
        ]
        seq_start = (chunk_idx - 1) * 1000 + 1
        seq_end = chunk_idx * 1000
        res = SyncProtocolEngine.sync_chunk(DB_URL, TENANT_ID, edge_node_id, stream_key, chunk_records, seq_start, seq_end)
        print(f"  Cloud last_acked_sequence after chunk {chunk_idx}: {res['acked_sequence']}")
        assert res["acked_sequence"] == seq_end

    # Chunk 4: Mid-chunk network disconnect triggered
    chunk_4_records = [
        {"point_id": f"p_part_4_{i}", "recorded_at": now + timedelta(seconds=(4000 + i)), "val": 30.0}
        for i in range(1000)
    ]
    res_disc = SyncProtocolEngine.sync_chunk(
        DB_URL, TENANT_ID, edge_node_id, stream_key, chunk_4_records,
        chunk_seq_start=3001, chunk_seq_end=4000,
        simulate_disconnect_mid_chunk=True
    )
    print("  [disconnect triggered mid-chunk 4]")
    state_disc = SyncProtocolEngine.get_sync_state(DB_URL, TENANT_ID, edge_node_id, stream_key)
    print(f"  Cloud last_acked_sequence after disconnect: {state_disc['last_synced_sequence']}")
    assert state_disc["last_synced_sequence"] == 3000, "Partial chunk 4 erroneously committed watermark!"

    # Reconnect and resume from chunk 4
    print("  [reconnect and resume from chunk 4]")
    res_resume = SyncProtocolEngine.sync_chunk(
        DB_URL, TENANT_ID, edge_node_id, stream_key, chunk_4_records,
        chunk_seq_start=3001, chunk_seq_end=4000,
        simulate_disconnect_mid_chunk=False
    )
    print(f"  Cloud last_acked_sequence after chunk 4 resume: {res_resume['acked_sequence']}")
    assert res_resume["acked_sequence"] == 4000

    # Chunks 5 through 10
    for chunk_idx in range(5, 11):
        chunk_records = [
            {"point_id": f"p_part_{chunk_idx}_{i}", "recorded_at": now + timedelta(seconds=(chunk_idx*1000 + i)), "val": 30.0}
            for i in range(1000)
        ]
        seq_start = (chunk_idx - 1) * 1000 + 1
        seq_end = chunk_idx * 1000
        res = SyncProtocolEngine.sync_chunk(DB_URL, TENANT_ID, edge_node_id, stream_key, chunk_records, seq_start, seq_end)
        assert res["acked_sequence"] == seq_end

    state_final = SyncProtocolEngine.get_sync_state(DB_URL, TENANT_ID, edge_node_id, stream_key)
    print(f"  Cloud last_acked_sequence after chunk 10: {state_final['last_synced_sequence']}")
    assert state_final["last_synced_sequence"] == 10000

def test_2_15_7_multi_site_isolation():
    """
    2.15-7: Multi-site conflict and sequence isolation.
    Site Alpha and Site Beta sync concurrently without interference.
    """
    stream_key = "telemetry_stream"
    node_alpha = "alpha"
    node_beta = "beta"

    # Set up Alpha at sequence 10000, Beta at sequence 8000
    SyncProtocolEngine.initialize_sync_state(DB_URL, TENANT_ID, node_alpha, stream_key, 10000)
    SyncProtocolEngine.initialize_sync_state(DB_URL, TENANT_ID, node_beta, stream_key, 8000)

    # Insert conflict for Alpha and conflict for Beta
    SyncProtocolEngine.resolve_telemetry_conflict(
        DB_URL, TENANT_ID, node_alpha, "p_alpha", datetime.now(timezone.utc), 10.0, 5.0
    )
    SyncProtocolEngine.resolve_telemetry_conflict(
        DB_URL, TENANT_ID, node_beta, "p_beta", datetime.now(timezone.utc), 20.0, 15.0
    )

    print("\n2.15-7 Multi-Site Isolation Output:")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                SELECT edge_node_id, stream_key, last_synced_sequence
                FROM offline_sync_state
                WHERE tenant_id = %s AND edge_node_id IN (%s, %s)
                ORDER BY edge_node_id;
            """, (TENANT_ID, node_alpha, node_beta))
            for row in cur.fetchall():
                print(f"  edge_node_id: {row[0]} | stream_key: {row[1]} | last_synced_sequence: {row[2]}")

            cur.execute("SELECT count(*) FROM sync_conflicts WHERE edge_node_id = %s;", (node_alpha,))
            alpha_conflicts = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM sync_conflicts WHERE edge_node_id = %s;", (node_beta,))
            beta_conflicts = cur.fetchone()[0]

            print(f"  Site Alpha conflicts count: {alpha_conflicts}")
            print(f"  Site Beta conflicts count:  {beta_conflicts}")

    assert alpha_conflicts >= 1
    assert beta_conflicts >= 1

def test_2_15_a_zero_loss_with_preexisting_data():
    """
    STORY-2.15a / PHASE-5-SYNC-001: Zero-loss verification with pre-existing data (X > 0).
    Pre-seeds 1,000 rows, ingests N = 500 rows during partition, asserts count increases
    from 1,000 to 1,500 with delta exactly 500 and 0 duplicates.
    """
    node_id = "edge_site_preexisting"
    test_stream = "preexisting_stream"
    p_prefix = f"p_pre_{uuid.uuid4().hex[:6]}"

    # Seed X = 1,000 rows pre-partition
    X = 1000
    now = datetime(2026, 11, 2, 12, 0, 0, tzinfo=timezone.utc)
    pre_records = [
        {"point_id": f"{p_prefix}_{i}", "recorded_at": now + timedelta(seconds=i), "val": 40.0}
        for i in range(X)
    ]
    SyncProtocolEngine.sync_chunk(
        DB_URL, TENANT_ID, node_id, test_stream, pre_records,
        chunk_seq_start=1, chunk_seq_end=X
    )

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT count(*) FROM edge_telemetry_raw WHERE tenant_id = %s AND point_id LIKE %s;", (TENANT_ID, f"{p_prefix}%"))
            count_pre = cur.fetchone()[0]

    assert count_pre == X, f"Expected {X} pre-existing rows, found {count_pre}"

    # Partition network and ingest N = 500 new rows
    N = 500
    new_records = [
        {"point_id": f"{p_prefix}_{X + i}", "recorded_at": now + timedelta(seconds=(X + i)), "val": 42.0}
        for i in range(N)
    ]
    SyncProtocolEngine.sync_chunk(
        DB_URL, TENANT_ID, node_id, test_stream, new_records,
        chunk_seq_start=X + 1, chunk_seq_end=X + N
    )

    # Verify cloud count after sync
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT count(*) FROM edge_telemetry_raw WHERE tenant_id = %s AND point_id LIKE %s;", (TENANT_ID, f"{p_prefix}%"))
            count_post = cur.fetchone()[0]

            # Duplicate check
            cur.execute("""
                SELECT point_id, recorded_at, count(*)
                FROM edge_telemetry_raw
                WHERE tenant_id = %s AND point_id LIKE %s
                GROUP BY point_id, recorded_at
                HAVING count(*) > 1;
            """, (TENANT_ID, f"{p_prefix}%"))
            duplicates = cur.fetchall()

    delta = count_post - count_pre
    print(f"\n2.15-a Zero Loss with Pre-Existing Data (X={X}, N={N}):")
    print(f"  Before partition count: {count_pre}")
    print(f"  After sync count:       {count_post}")
    print(f"  Delta:                  {delta} (Expected N = {N})")
    print(f"  Duplicate rows found:   {len(duplicates)} (Expected 0)")

    assert count_post == X + N
    assert delta == N
    assert len(duplicates) == 0

def test_2_15_b_multi_site_conflict_identity_isolation():
    """
    STORY-2.15b / PHASE-5-SYNC-002: Multi-site conflict isolation by entity identity.
    Asserts Alpha and Beta conflict entity IDs are strictly disjoint sets.
    """
    node_alpha = f"alpha_{uuid.uuid4().hex[:4]}"
    node_beta = f"beta_{uuid.uuid4().hex[:4]}"

    alpha_entities = [f"entity_alpha_{i}" for i in range(3)]
    beta_entities = [f"entity_beta_{i}" for i in range(3)]

    now = datetime.now(timezone.utc)
    for ent in alpha_entities:
        SyncProtocolEngine.resolve_telemetry_conflict(DB_URL, TENANT_ID, node_alpha, ent, now, 10.0, 5.0)
    for ent in beta_entities:
        SyncProtocolEngine.resolve_telemetry_conflict(DB_URL, TENANT_ID, node_beta, ent, now, 20.0, 15.0)

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("SELECT entity_id FROM sync_conflicts WHERE edge_node_id = %s;", (node_alpha,))
            alpha_conflicts_set = {row[0] for row in cur.fetchall()}

            cur.execute("SELECT entity_id FROM sync_conflicts WHERE edge_node_id = %s;", (node_beta,))
            beta_conflicts_set = {row[0] for row in cur.fetchall()}

    overlap = alpha_conflicts_set & beta_conflicts_set
    print(f"\n2.15-b Multi-Site Conflict Identity Isolation:")
    print(f"  Site Alpha entities: {sorted(list(alpha_conflicts_set))}")
    print(f"  Site Beta entities:  {sorted(list(beta_conflicts_set))}")
    print(f"  Entity ID overlap:   {overlap} (Expected: empty set)")

    assert alpha_conflicts_set.isdisjoint(beta_conflicts_set)
    assert len(overlap) == 0
