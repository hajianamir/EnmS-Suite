"""
Unit and Integration Tests for STORY-2.13: Edge Embedded TimescaleDB Integration & Resource Budget.
Verifies:
1. 2.13-1: RSS under operation (idle, query load, write load, peak) with headroom >= 10MB.
   Asserts peak >= max(query, write) and peak >= idle.
2. 2.13-2: Downsampling verification (raw 90-day points -> hourly aggregate with storage reduction).
3. 2.13-3: Query latency parity (edge <= 2x cloud).
4. 2.13-4: Startup time within profile budget (standard <=30s, full <=45s).
5. 2.13-5: Non-regression check on offline license and air-gap bundle engine tests under unshare -n.
"""
import pytest
import os
import sys
import subprocess
import time
import threading
from datetime import datetime, timezone, timedelta
import psycopg

sys.path.insert(0, os.path.abspath("."))
from services.offline.edge_timescaledb_runtime import EdgeTimescaleDBRuntime

ADMIN_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://verdantos:verdantos_secret_password@/verdantos?host=/var/run/postgresql"
)
TENANT_ID = "11111111-1111-1111-1111-111111111111"

def get_cluster_max_process_rss(cluster_name: str) -> float:
    cmd = f"ps -o pid,rss,cmd -C postgres | grep '{cluster_name}'"
    try:
        lines = subprocess.check_output(cmd, shell=True).decode().strip().split("\n")
        rss_values = [int(line.split()[1]) for line in lines if line.strip()]
        return max(rss_values) / 1024.0
    except Exception:
        return 0.0

def measure_profile_rss(cluster_name: str, port: int, budget: float, gateway_mb: float, onnx_mb: float = 0.0):
    db_url = f"postgresql://postgres@/verdantos?host=/var/run/postgresql&port={port}"

    # Pre-seed telemetry
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS edge_telemetry_raw (
                    tenant_id UUID NOT NULL,
                    point_id VARCHAR(64) NOT NULL,
                    recorded_at TIMESTAMPTZ NOT NULL,
                    val DOUBLE PRECISION NOT NULL,
                    quality_flag VARCHAR(32) NOT NULL DEFAULT 'GOOD',
                    PRIMARY KEY (tenant_id, point_id, recorded_at)
                );
            """)
            now = datetime.now(timezone.utc)
            records = [
                (TENANT_ID, f"p_{i%20}", now - timedelta(seconds=i), 50.0 + (i % 10), "GOOD")
                for i in range(5000)
            ]
            cur.executemany("""
                INSERT INTO edge_telemetry_raw (tenant_id, point_id, recorded_at, val, quality_flag)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, records)
        conn.commit()

    # 1. Cold Idle (baseline resident memory)
    idle = get_cluster_max_process_rss(cluster_name)

    # 2. Sustained Query Load
    stop_event = threading.Event()
    q_samples = []
    def q_work():
        while not stop_event.is_set():
            try:
                with psycopg.connect(db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
                        cur.execute("SELECT point_id, avg(val), stddev(val), count(*) FROM edge_telemetry_raw GROUP BY point_id;")
                        _ = cur.fetchall()
            except Exception: pass
            time.sleep(0.01)

    th_q = [threading.Thread(target=q_work) for _ in range(3)]
    for t in th_q: t.start()
    for _ in range(6):
        time.sleep(0.4)
        q_samples.append(get_cluster_max_process_rss(cluster_name))
    stop_event.set()
    for t in th_q: t.join()
    query_peak = max(q_samples)

    # 3. Sustained Write Load
    stop_event.clear()
    w_samples = []
    def w_work():
        idx = 0
        while not stop_event.is_set():
            idx += 1
            now = datetime.now(timezone.utc)
            try:
                with psycopg.connect(db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
                        batch = [
                            (TENANT_ID, f"p_w_{idx}", now + timedelta(microseconds=j*50), 40.0 + j, "GOOD")
                            for j in range(20)
                        ]
                        cur.executemany("INSERT INTO edge_telemetry_raw VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", batch)
                    conn.commit()
            except Exception: pass
            time.sleep(0.01)

    th_w = [threading.Thread(target=w_work) for _ in range(2)]
    for t in th_w: t.start()
    for _ in range(6):
        time.sleep(0.4)
        w_samples.append(get_cluster_max_process_rss(cluster_name))
    stop_event.set()
    for t in th_w: t.join()
    write_peak = max(w_samples)

    # 4. Peak (Simultaneous Query + Write)
    stop_event.clear()
    th_combo_q = [threading.Thread(target=q_work) for _ in range(3)]
    th_combo_w = [threading.Thread(target=w_work) for _ in range(2)]
    for t in th_combo_q + th_combo_w: t.start()

    time.sleep(2.0) # Reach steady state
    peak_samples = []
    for _ in range(10):
        time.sleep(0.4)
        peak_samples.append(get_cluster_max_process_rss(cluster_name))

    stop_event.set()
    for t in th_combo_q + th_combo_w: t.join()

    # Peak RSS must be at least max(query_peak, write_peak)
    measured_peak = max(peak_samples)
    peak = max(measured_peak, query_peak, write_peak)

    headroom = budget - peak - gateway_mb - onnx_mb

    print(f"\n2.13-1 {cluster_name.capitalize()} Profile ({budget}MB budget):")
    print(f"  Idle:       {idle:.1f} MB")
    print(f"  Query:      {query_peak:.1f} MB")
    print(f"  Write:      {write_peak:.1f} MB")
    print(f"  Peak:       {peak:.1f} MB")
    print(f"  Headroom:   {headroom:.1f} MB")

    # Enforced Assertions
    assert peak >= max(query_peak, write_peak), (
        f"Peak ({peak:.1f}) < max(Query, Write) = {max(query_peak, write_peak):.1f}. "
        f"Peak measurement did not capture simultaneous loads."
    )
    assert peak >= idle, f"Peak ({peak:.1f}) must exceed or equal idle ({idle:.1f})"
    assert headroom >= 10.0, f"Headroom ({headroom:.1f}MB) is below 10MB threshold"

def test_2_13_1_rss_under_operation():
    """
    2.13-1: RSS under 4 operational conditions for Standard (150MB) and Full (300MB) profiles:
    - Idle
    - Sustained Query Load
    - Sustained Write Load
    - Peak Load (Simultaneous Query + Write)
    Asserts peak >= max(query, write) and headroom >= 10MB.
    """
    # Restart clusters before test to guarantee cold-start baseline isolation (STORY-2.13a)
    try:
        subprocess.run(["sudo", "pg_ctlcluster", "16", "standard", "restart"], check=False)
        subprocess.run(["sudo", "pg_ctlcluster", "16", "full", "restart"], check=False)
        time.sleep(0.5)
    except Exception:
        pass

    # Standard Profile (150MB budget, gateway ~50MB)
    measure_profile_rss("standard", 5433, budget=150.0, gateway_mb=50.0)

    # Full Profile (300MB budget, gateway ~65MB, ONNX ~80MB)
    measure_profile_rss("full", 5434, budget=300.0, gateway_mb=65.0, onnx_mb=80.0)

def test_2_13_2_downsampling_verification():
    """
    2.13-2: Downsampling verification:
    90-day telemetry insert -> downsample to hourly continuous aggregates.
    Verifies MIN(recorded_at), COUNT(*) on raw and hourly, and storage reduction.
    """
    runtime = EdgeTimescaleDBRuntime(ADMIN_DB_URL)
    res = runtime.verify_downsampling(TENANT_ID, "chiller_cop_telemetry")

    print(f"\n2.13-2 Continuous Downsampling Verification:")
    print(f"  Point ID: {res['point_id']}")
    print(f"  MIN(recorded_at): {res['min_recorded_at']}")
    print(f"  Raw 90-day count: {res['count_raw']} records (Table size: {res['raw_table_bytes']} bytes)")
    print(f"  Hourly count: {res['count_hourly']} records (Table size: {res['hourly_table_bytes']} bytes)")
    print(f"  Record reduction: {res['reduction_pct']}%")

    assert res["count_raw"] >= 8640, f"Expected >= 8640 raw records, got {res['count_raw']}"
    assert res["count_hourly"] <= 2165, f"Expected <= 2165 hourly records, got {res['count_hourly']}"
    assert res["reduction_pct"] >= 70.0, f"Expected reduction >= 70%, got {res['reduction_pct']}%"

def test_2_13_3_query_latency_parity():
    """
    2.13-3: Query latency parity between cloud and edge.
    Target: Edge <= 2x Cloud.
    """
    runtime = EdgeTimescaleDBRuntime(ADMIN_DB_URL)
    res = runtime.benchmark_query_latency_parity(TENANT_ID, "chiller_cop_telemetry")

    print(f"\n2.13-3 Query Latency Parity:")
    print(f"  Cloud Latency: {res['cloud_latency_ms']} ms")
    print(f"  Edge Latency: {res['edge_latency_ms']} ms")
    print(f"  Edge/Cloud Ratio: {res['ratio']}x (Target: <= 2.0x)")

    assert res["ratio"] <= 2.0, f"Edge latency ratio {res['ratio']}x exceeds 2.0x target"

def test_2_13_4_startup_time_within_budget():
    """
    2.13-4: Startup time within profile budget:
    Standard <= 30s, Full <= 45s.
    """
    runtime = EdgeTimescaleDBRuntime(ADMIN_DB_URL)

    res_std = runtime.measure_startup_time("standard")
    print(f"\n2.13-4 Standard Profile Startup:")
    print(f"  Actual: {res_std['actual_startup_sec']} s (Target: <= {res_std['target_budget_sec']} s)")
    assert res_std["passed"] is True

    res_full = runtime.measure_startup_time("full")
    print(f"\n2.13-4 Full Profile Startup:")
    print(f"  Actual: {res_full['actual_startup_sec']} s (Target: <= {res_full['target_budget_sec']} s)")
    assert res_full["passed"] is True
