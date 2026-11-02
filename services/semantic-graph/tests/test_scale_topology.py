"""
Integration Tests for STORY-2.D: Workstream 2 Acceptance Criterion #1.
Verifies instantiation of a multi-site topology: 3 sites, 10 buildings per site (30 total),
multiple system classes per building, and equipment instantiated from templates within each system.
"""
import pytest
import psycopg
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from equipment_templates import EquipmentTemplateEngine

DB_APP_URL = os.environ.get("DATABASE_APP_URL", "postgresql://verdantos_app:verdantos_app_password@localhost:5432/verdantos")
TENANT_ID = "11111111-1111-1111-1111-111111111111"

def test_instantiate_3_sites_10_buildings_topology():
    """
    STORY-2.D: Instantiates 3 sites, 10 buildings per site (30 buildings total),
    and populates multi-class equipment from templates (AHU, Chiller, Meter, Transformer).
    Verifies database aggregation: SELECT site_id, COUNT(*) FROM assets GROUP BY site_id.
    """
    site_names = ["site_alpha", "site_beta", "site_gamma"]
    template_classes = ["ahu", "chiller", "meter", "transformer"]

    # Generate assets for 3 sites x 10 buildings
    all_assets = []
    for s_idx, s_name in enumerate(site_names):
        site_id = str(uuid.uuid4())
        all_assets.append({
            "id": site_id,
            "tenant_id": TENANT_ID,
            "name": f"Enterprise Campus {s_name.upper()}",
            "asset_type": "site",
            "path": s_name,
            "parent_id": None
        })
        for b_idx in range(10):
            bldg_id = str(uuid.uuid4())
            bldg_path = f"{s_name}.bldg_{b_idx:02d}"
            all_assets.append({
                "id": bldg_id,
                "tenant_id": TENANT_ID,
                "name": f"Building {b_idx}",
                "asset_type": "building",
                "path": bldg_path,
                "parent_id": site_id
            })
            # Add 4 equipment items (one of each template class) per building
            for c in template_classes:
                eq_inst = EquipmentTemplateEngine.instantiate_template(
                    template_key=c,
                    instance_name=f"{c.upper()}_{b_idx:02d}",
                    path=f"{bldg_path}.{c}",
                    tenant_id=TENANT_ID
                )
                all_assets.append({
                    "id": eq_inst["id"],
                    "tenant_id": TENANT_ID,
                    "name": eq_inst["name"],
                    "asset_type": eq_inst["asset_type"],
                    "path": eq_inst["path"],
                    "parent_id": bldg_id,
                    "brick_class": eq_inst["brick_class"]
                })

    # Insert into PostgreSQL
    with psycopg.connect(DB_APP_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_tenant_id = '{TENANT_ID}';")
            cur.execute("DELETE FROM assets WHERE subpath(path, 0, 1)::text IN ('site_alpha', 'site_beta', 'site_gamma');")
            user_id = '00000000-0000-0000-0000-000000000000'
            insert_batch = [
                (a["id"], a["tenant_id"], a["name"], a["asset_type"], a["path"], a["parent_id"], a.get("brick_class"), user_id)
                for a in all_assets
            ]
            cur.executemany(
                "INSERT INTO assets (id, tenant_id, name, asset_type, path, parent_id, brick_class, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;",
                insert_batch
            )
            conn.commit()

            # Execute topology count aggregation
            cur.execute("""
                SELECT subpath(path, 0, 1)::text as site_root, count(*) 
                FROM assets 
                WHERE subpath(path, 0, 1)::text IN ('site_alpha', 'site_beta', 'site_gamma')
                GROUP BY site_root 
                ORDER BY site_root;
            """)
            site_counts = cur.fetchall()

    print("\nTopology Distribution by Site Root:")
    for root, cnt in site_counts:
        print(f"  Site: {root:<12} | Node Count: {cnt}")

    assert len(site_counts) == 3, f"Expected 3 distinct sites, found {len(site_counts)}"
    # Each site has 1 site + 10 buildings + 40 equipment = 51 nodes
    for root, cnt in site_counts:
        assert cnt == 51, f"Expected 51 nodes for site {root}, got {cnt}"

    total_instantiated = sum(c[1] for c in site_counts)
    output_line = f"instantiated 3 sites, 10 buildings each, {total_instantiated} assets across 4 template classes"
    print("\n" + output_line)
    assert output_line == "instantiated 3 sites, 10 buildings each, 153 assets across 4 template classes"
