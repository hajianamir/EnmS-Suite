"""
Unit and Integration Tests for STORY-2.1: Multi-Site Hierarchy Enforcer.
Verifies depth >= 6 ltree path support, in-memory traversal benchmark,
10,000-node live PostgreSQL benchmark with EXPLAIN ANALYZE, non-superuser
PostgreSQL Row-Level Security (RLS) tenant isolation, and byte-identical
Phase 4 drill-down response shape preservation.
"""
import time
import uuid
import sys
import os
import re
import json
import pytest
import psycopg

# Ensure semantic-graph directory is in import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hierarchy_engine import SemanticGraphManager, HIERARCHY_LEVELS

DB_APP_URL = os.environ.get("DATABASE_APP_URL", "postgresql://verdantos_app:verdantos_app_password@localhost:5432/verdantos")

def test_ltree_depth_six_support():
    manager = SemanticGraphManager(tenant_id="tenant-alpha")
    # Depth 6 hierarchy: Site -> Building -> System -> Equipment -> Subsystem -> Point
    path_depth_6 = "campus_north.bldg_10.hvac_plant.chiller_01.compressor_stage_a.active_power"
    node = manager.add_asset(
        asset_id=str(uuid.uuid4()),
        name="Chiller 01 Compressor Active Power",
        asset_type="point",
        path=path_depth_6
    )
    assert len(node.path.split('.')) == 6
    assert node.path in manager.path_index

def test_multi_site_traversal_and_isolation_in_memory():
    manager = SemanticGraphManager(tenant_id="tenant-corp")
    # Site 1
    s1 = manager.add_asset("site-1", "North Campus", "site", "north_campus")
    b1 = manager.add_asset("bldg-1", "Building 1", "building", "north_campus.bldg_1", parent_id="site-1")
    e1 = manager.add_asset("ahu-1", "AHU 1", "equipment", "north_campus.bldg_1.ahu_1", parent_id="bldg-1")
    
    # Site 2
    s2 = manager.add_asset("site-2", "South Campus", "site", "south_campus")
    b2 = manager.add_asset("bldg-2", "Building 2", "building", "south_campus.bldg_2", parent_id="site-2")
    
    # Query Site 1 subtree
    site1_tree = manager.get_subtree("north_campus")
    assert len(site1_tree) == 3
    paths = [n.path for n in site1_tree]
    assert "north_campus" in paths
    assert "north_campus.bldg_1" in paths
    assert "north_campus.bldg_1.ahu_1" in paths
    assert "south_campus" not in paths

def test_multi_site_10000_node_benchmark_in_memory():
    manager = SemanticGraphManager(tenant_id="benchmark-tenant")
    # Construct exactly 10,000 nodes in memory
    count = 0
    for s in range(5):
        s_id = f"s-{s}"
        manager.add_asset(s_id, f"Site {s}", "site", f"site_{s}")
        count += 1
        for b in range(10):
            b_id = f"b-{s}-{b}"
            manager.add_asset(b_id, f"Bldg {b}", "building", f"site_{s}.bldg_{b}", parent_id=s_id)
            count += 1
            for eq in range(199):
                if count >= 10000:
                    break
                eq_id = f"eq-{s}-{b}-{eq}"
                manager.add_asset(eq_id, f"Eq {eq}", "equipment", f"site_{s}.bldg_{b}.eq_{eq}", parent_id=b_id)
                count += 1
            if count >= 10000:
                break
        if count >= 10000:
            break

    assert len(manager.nodes) == 10000, f"Expected 10,000 nodes, got {len(manager.nodes)}"

    # Benchmark in-memory subtree query
    start_time = time.perf_counter()
    subtree = manager.get_subtree("site_0")
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    print(f"Traversed {len(subtree)} descendant nodes from 10,000 node in-memory tree in {duration_ms:.2f}ms")
    assert duration_ms < 10.0, f"Query took {duration_ms:.2f}ms which exceeds the 10ms threshold"
    assert len(subtree) > 1000

def test_multi_site_10000_node_benchmark_database():
    """
    Executes production-shaped tenant-scoped ltree query across >=10,000 PostgreSQL rows
    using non-superuser role verdantos_app without forcing enable_seqscan=off.
    """
    with psycopg.connect(DB_APP_URL) as conn:
        with conn.cursor() as cur:
            # Set tenant context so RLS permits viewing tenant assets
            cur.execute("SET app.current_tenant_id = '11111111-1111-1111-1111-111111111111';")

            # Verify total tenant nodes >= 10,000
            cur.execute("SELECT count(*) FROM assets WHERE tenant_id = '11111111-1111-1111-1111-111111111111';")
            total_assets = cur.fetchone()[0]
            assert total_assets >= 10000, f"Expected >= 10,000 assets, found {total_assets}"
            
            # Execute EXPLAIN (ANALYZE, BUFFERS) for tenant-scoped query without enable_seqscan=off
            query = """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
            SELECT id, path FROM assets
            WHERE tenant_id = '11111111-1111-1111-1111-111111111111'
              AND path <@ 'campus_north.site_0.bldg_0';
            """
            cur.execute(query)
            plan_lines = [row[0] for row in cur.fetchall()]
            plan_text = "\n".join(plan_lines)
            print("\n10,000-ROW PRODUCTION EXPLAIN ANALYZE OUTPUT:\n" + plan_text)

            # Parse execution time
            match = re.search(r"Execution Time: ([\d.]+) ms", plan_text)
            assert match is not None, "Execution Time could not be parsed from EXPLAIN output"
            exec_time = float(match.group(1))
            print(f"\n10,000-Node PostgreSQL Query Execution Time: {exec_time:.2f} ms")
            assert exec_time < 10.0, f"PostgreSQL Execution Time {exec_time}ms exceeds 10ms threshold"

def test_postgresql_rls_tenant_isolation_non_superuser():
    """
    Directly verifies PostgreSQL Row Level Security tenant isolation on assets table
    using non-superuser role verdantos_app (verifying rolsuper=false and rolbypassrls=false).
    """
    with psycopg.connect(DB_APP_URL) as conn:
        with conn.cursor() as cur:
            # Gap-3 Check: Verify role is non-superuser and has no BYPASSRLS
            cur.execute("SELECT session_user;")
            role = cur.fetchone()[0]
            cur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s;", (role,))
            is_super, bypass = cur.fetchone()
            assert not is_super, f"Test running as superuser '{role}' — RLS is bypassed"
            assert not bypass, f"Test role '{role}' has BYPASSRLS — RLS is bypassed"

            # Set session to Tenant A
            cur.execute("SET app.current_tenant_id = '11111111-1111-1111-1111-111111111111';")
            cur.execute("SELECT count(*) FROM assets WHERE tenant_id = '11111111-1111-1111-1111-111111111111';")
            tenant_a_count = cur.fetchone()[0]
            assert tenant_a_count > 0, "Tenant A should see its own assets"

            # Attempt cross-tenant SELECT for Tenant B
            cur.execute("SELECT count(*) FROM assets WHERE tenant_id = '99999999-9999-9999-9999-999999999999';")
            cross_tenant_count = cur.fetchone()[0]
            assert cross_tenant_count == 0, f"RLS violation: expected 0 rows, got {cross_tenant_count}"

def test_drilldown_shape_byte_identical_to_phase4_fixture():
    """
    Full-dict equality verification against the committed Phase 4 drilldown fixture,
    preserving the exact contract consumed by web/src/DrillDownDashboard.tsx.
    """
    fixture_path = "docs/slice/evidence/drilldown_fixture.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    manager = SemanticGraphManager(tenant_id="11111111-1111-1111-1111-111111111111")
    s = manager.add_asset("33333333-3333-3333-3333-333333333330", "Campus North", "site", "campus_north")
    b = manager.add_asset("33333333-3333-3333-3333-333333333331", "Building A", "building", "campus_north.bldg_a", parent_id=s.id)
    e = manager.add_asset("33333333-3333-3333-3333-333333333333", "AHU Building A 01", "ahu", "campus_north.bldg_a.ahu_01", parent_id=b.id)
    
    actual = manager.to_phase4_drilldown_shape("campus_north")
    assert actual == expected, f"Drilldown shape diverged from fixture: {actual} != {expected}"
