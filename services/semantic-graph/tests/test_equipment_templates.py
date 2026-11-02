"""
Unit and Integration Tests for STORY-2.A: Reusable Equipment Templates.
Verifies bulk instantiation for >= 50 instances per template class
(50 AHU + 50 Chiller + 50 Meter + 50 Transformer = 200 total),
point count and type signature preservation, and negative test mismatch handling.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from equipment_templates import EquipmentTemplateEngine, EQUIPMENT_TEMPLATES, TemplateInstantiationError

def test_template_instantiation_bulk_200_instances():
    """Bulk instantiates 50 instances for each of the 4 template classes."""
    tenant_id = "11111111-1111-1111-1111-111111111111"
    classes = ["ahu", "chiller", "meter", "transformer"]
    
    total_instances = {}
    for c in classes:
        instances = EquipmentTemplateEngine.bulk_instantiate(
            template_key=c,
            count=50,
            base_path=f"campus_north.bldg_a.{c}_plant",
            tenant_id=tenant_id
        )
        assert len(instances) == 50, f"Expected 50 instances for {c}, got {len(instances)}"
        total_instances[c] = instances

    output_line = f"instantiated 200 assets: {len(total_instances['ahu'])} AHU + {len(total_instances['chiller'])} Chiller + {len(total_instances['meter'])} Meter + {len(total_instances['transformer'])} Transformer"
    print("\n" + output_line)
    assert output_line == "instantiated 200 assets: 50 AHU + 50 Chiller + 50 Meter + 50 Transformer"

def test_template_point_binding_consistency():
    """Verifies point counts and exact type signatures across instantiated templates."""
    tenant_id = "11111111-1111-1111-1111-111111111111"
    classes = ["ahu", "chiller", "meter", "transformer"]

    for c in classes:
        inst = EquipmentTemplateEngine.instantiate_template(
            template_key=c,
            instance_name=f"Sample_{c}",
            path=f"campus_north.sample.{c}",
            tenant_id=tenant_id
        )
        tmpl = EQUIPMENT_TEMPLATES[c]
        
        # 1. Point count assertion
        assert len(inst["points"]) == len(tmpl["points"]), f"Point count mismatch for {c}"

        # 2. Point signatures assertion (set equality on name, point_type, unit)
        expected_sig = {(p["name"], p["point_type"], p["unit"]) for p in tmpl["points"]}
        actual_sig = {(p["name"], p["point_type"], p["unit"]) for p in inst["points"]}
        assert actual_sig == expected_sig, f"Point signature mismatch for {c}"

def test_template_mismatch_negative_fails():
    """Verifies that instantiating with missing or mismatched points raises TemplateInstantiationError."""
    tenant_id = "11111111-1111-1111-1111-111111111111"
    
    # AHU expects 5 points. Provide only 4.
    incomplete_points = [
        {"name": "Supply Air Temperature", "point_type": "temperature", "unit": "degC"},
        {"name": "Return Air Temperature", "point_type": "temperature", "unit": "degC"},
        {"name": "Supply Fan Speed", "point_type": "speed_percent", "unit": "%"},
        {"name": "Active Power", "point_type": "active_power", "unit": "kW"}
    ]

    with pytest.raises(TemplateInstantiationError) as exc_info:
        EquipmentTemplateEngine.instantiate_template(
            template_key="ahu",
            instance_name="Invalid_AHU",
            path="campus_north.ahu_bad",
            tenant_id=tenant_id,
            provided_points=incomplete_points
        )

    assert "expects 5 points, but 4 were provided" in str(exc_info.value)
