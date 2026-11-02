"""
VerdantOS Reusable Equipment Templates Engine (STORY-2.A)
Provides standardized templates for AHU, Chiller, Meter, and Transformer
with strict point-binding consistency and validation against Brick/Haystack classes.
"""
from typing import Dict, List, Any, Optional
import uuid

# Standardized template definitions with exact required points
EQUIPMENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ahu": {
        "class_name": "AHU",
        "brick_class": "brick:Air_Handling_Unit",
        "haystack_tag": "ahu",
        "points": [
            {"name": "Supply Air Temperature", "point_type": "temperature", "unit": "degC"},
            {"name": "Return Air Temperature", "point_type": "temperature", "unit": "degC"},
            {"name": "Supply Fan Speed", "point_type": "speed_percent", "unit": "%"},
            {"name": "Active Power", "point_type": "active_power", "unit": "kW"},
            {"name": "Cooling Valve Command", "point_type": "command_percent", "unit": "%"}
        ]
    },
    "chiller": {
        "class_name": "Chiller",
        "brick_class": "brick:Chiller",
        "haystack_tag": "chiller",
        "points": [
            {"name": "Chilled Water Supply Temp", "point_type": "temperature", "unit": "degC"},
            {"name": "Chilled Water Return Temp", "point_type": "temperature", "unit": "degC"},
            {"name": "Compressor Power", "point_type": "active_power", "unit": "kW"},
            {"name": "Chilled Water Flow Rate", "point_type": "flow_rate", "unit": "m3/h"}
        ]
    },
    "meter": {
        "class_name": "Meter",
        "brick_class": "brick:Electrical_Meter",
        "haystack_tag": "meter",
        "points": [
            {"name": "Active Power", "point_type": "active_power", "unit": "kW"},
            {"name": "Total Active Energy", "point_type": "energy", "unit": "kWh"},
            {"name": "Power Factor", "point_type": "power_factor", "unit": "ratio"}
        ]
    },
    "transformer": {
        "class_name": "Transformer",
        "brick_class": "brick:Transformer",
        "haystack_tag": "transformer",
        "points": [
            {"name": "Winding Temperature", "point_type": "temperature", "unit": "degC"},
            {"name": "Load Current Phase A", "point_type": "current", "unit": "A"},
            {"name": "Load Current Phase B", "point_type": "current", "unit": "A"},
            {"name": "Load Current Phase C", "point_type": "current", "unit": "A"}
        ]
    }
}

class TemplateInstantiationError(ValueError):
    """Raised when point bindings violate the template contract."""
    pass

class EquipmentTemplateEngine:
    @staticmethod
    def instantiate_template(
        template_key: str,
        instance_name: str,
        path: str,
        tenant_id: str,
        provided_points: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Instantiates an equipment asset from a template definition.
        If provided_points is omitted, automatically binds all template points.
        If provided_points is given, strictly validates count and point signatures.
        """
        template_key_clean = template_key.lower().strip()
        if template_key_clean not in EQUIPMENT_TEMPLATES:
            raise TemplateInstantiationError(f"Unknown equipment template '{template_key}'")

        tmpl = EQUIPMENT_TEMPLATES[template_key_clean]
        expected_points = tmpl["points"]

        # Validate provided points if passed explicitly
        if provided_points is not None:
            if len(provided_points) != len(expected_points):
                raise TemplateInstantiationError(
                    f"Template '{template_key_clean}' expects {len(expected_points)} points, "
                    f"but {len(provided_points)} were provided"
                )
            
            # Verify point types match
            expected_signatures = {(p["name"], p["point_type"], p["unit"]) for p in expected_points}
            provided_signatures = {(p.get("name"), p.get("point_type"), p.get("unit")) for p in provided_points}
            if expected_signatures != provided_signatures:
                diff = expected_signatures.symmetric_difference(provided_signatures)
                raise TemplateInstantiationError(
                    f"Point bindings for template '{template_key_clean}' do not match expected signature. Divergence: {diff}"
                )
            active_points = provided_points
        else:
            # Auto-generate bound points from template definition
            active_points = [
                {
                    "id": str(uuid.uuid4()),
                    "name": p["name"],
                    "point_type": p["point_type"],
                    "unit": p["unit"]
                }
                for p in expected_points
            ]

        return {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "name": instance_name,
            "asset_type": template_key_clean,
            "brick_class": tmpl["brick_class"],
            "haystack_tag": tmpl["haystack_tag"],
            "path": path,
            "points": active_points
        }

    @staticmethod
    def bulk_instantiate(
        template_key: str,
        count: int,
        base_path: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Instantiates multiple instances of an equipment template without manual point mapping."""
        instances = []
        for i in range(count):
            name = f"{template_key.upper()}_{i:03d}"
            path = f"{base_path}.{template_key.lower()}_{i:03d}"
            inst = EquipmentTemplateEngine.instantiate_template(
                template_key=template_key,
                instance_name=name,
                path=path,
                tenant_id=tenant_id
            )
            instances.append(inst)
        return instances
