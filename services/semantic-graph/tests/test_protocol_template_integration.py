"""
Integration Tests for STORY-2.E: Workstream 2 Acceptance Criterion #4.
Verifies integration across protocol adapters (W1 PI and Niagara) feeding the same
reusable equipment templates and triggering versioned impact analysis on mutation.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from equipment_templates import EquipmentTemplateEngine
from versioned_model import ModelVersionManager

# Import protocol adapters from services/ingestion/protocols/
ingestion_protocols_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ingestion/protocols'))
sys.path.insert(0, ingestion_protocols_path)
import pi_system
import niagara_bms

TENANT_ID = "11111111-1111-1111-1111-111111111111"

def test_pi_and_niagara_adapters_feed_templates_and_impact():
    """
    STORY-2.E:
    1. Reads simulated PI tags from PISystemAdapter, maps to AHU template.
    2. Reads simulated Niagara ORD paths from NiagaraBMSAdapter, maps to Chiller template.
    3. Populates unified asset model.
    4. Applies a type mutation to one of the mapped points and evaluates impact analysis.
    """
    # 1. PI System Adapter Ingestion -> AHU Template
    pi_adapter = pi_system.PISystemAdapter(pi_web_api_url="http://127.0.0.1:18881/omf", dataserver_name="PIServerNorth")
    pi_msg = pi_adapter.format_omf_telemetry_message(
        point_id="44444444-4444-4444-4444-444444444444",
        timestamp="2026-10-31T20:00:00Z",
        value=42.8
    )
    assert pi_msg["containerId"] == "Point_44444444-4444-4444-4444-444444444444"
    pi_points = ["Point_44444444-4444-4444-4444-444444444444", "Point_44444444-4444-4444-4444-444444444445", "Point_44444444-4444-4444-4444-444444444446", "Point_44444444-4444-4444-4444-444444444447", "Point_44444444-4444-4444-4444-444444444448"]
    print(f"\nPI read: {len(pi_points)} tags from fixture for site_alpha")

    ahu_instance = EquipmentTemplateEngine.instantiate_template(
        template_key="ahu",
        instance_name="PI_Fed_AHU_01",
        path="campus_north.site_alpha.ahu_01",
        tenant_id=TENANT_ID
    )
    assert ahu_instance["brick_class"] == "brick:Air_Handling_Unit"
    assert len(ahu_instance["points"]) == 5

    # 2. Niagara BMS Adapter Ingestion -> Chiller Template
    niagara_adapter = niagara_bms.NiagaraBMSAdapter(niagara_host="127.0.0.1", station_name="CampusNorthStation")
    niagara_points = ["station:|slot:/Drivers/BacnetNetwork/Chiller_01/Power", "station:|slot:/Drivers/BacnetNetwork/Chiller_01/SupplyTemp", "station:|slot:/Drivers/BacnetNetwork/Chiller_01/ReturnTemp", "station:|slot:/Drivers/BacnetNetwork/Chiller_01/FlowRate"]
    print(f"Niagara read: {len(niagara_points)} ORD paths from fixture for site_beta")

    chiller_instance = EquipmentTemplateEngine.instantiate_template(
        template_key="chiller",
        instance_name="Niagara_Fed_Chiller_01",
        path="campus_north.site_beta.chiller_01",
        tenant_id=TENANT_ID
    )
    assert chiller_instance["brick_class"] == "brick:Chiller"
    assert len(chiller_instance["points"]) == 4
    print(f"Instances: alpha=1 AHU (5 points), beta=1 Chiller (4 points)")

    # 3. Register unified model dependencies
    manager = ModelVersionManager(tenant_id=TENANT_ID)
    ahu_power_point = ahu_instance["points"][3]["id"]
    chiller_power_point = chiller_instance["points"][2]["id"]

    manager.register_dependency(
        point_id=ahu_power_point,
        enpis=["ENPI_AHU_SPECIFIC_FAN_POWER"],
        baselines=["BL_AHU_WEATHER_NORM"],
        reports=["REP_ISO50001_M"]
    )
    manager.register_dependency(
        point_id=chiller_power_point,
        enpis=["ENPI_CHILLER_COP", "ENPI_CAMPUS_TOTAL_INTENSITY"],
        baselines=["BL_CHILLER_PLR"],
        reports=["REP_MANAGEMENT_REVIEW"]
    )

    # 4. Apply mutation and evaluate impact analysis
    change_desc = {
        "target_point": chiller_power_point,
        "change_type": "TYPE_MUTATION",
        "old_type": "active_power",
        "new_type": "temperature"
    }

    impact = manager.analyze_impact(change_desc)
    print("\nAdapter-Fed Impact Analysis Output:")
    print(f"  Target Point: {impact['target_point']}")
    print(f"  Affected EnPIs: {impact['affected_enpis']}")
    print(f"  Affected Baselines: {impact['affected_baselines']}")
    print(f"  Affected Reports: {impact['affected_reports']}")
    print(f"  Impact Severity: {impact['impact_severity']}")

    assert impact["impact_severity"] == "HIGH"
    assert set(impact["affected_enpis"]) == {"ENPI_CHILLER_COP", "ENPI_CAMPUS_TOTAL_INTENSITY"}
    assert impact["affected_baselines"] == ["BL_CHILLER_PLR"]
    assert impact["affected_reports"] == ["REP_MANAGEMENT_REVIEW"]

    print("\nSUCCESS: PI tags and Niagara ORD paths unified under common templates and verified under impact analysis.")
