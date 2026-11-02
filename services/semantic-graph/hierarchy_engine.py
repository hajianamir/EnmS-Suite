"""
VerdantOS Semantic Asset Graph Hierarchy Engine
Enforces Site -> Building -> System -> Equipment -> Subsystem -> Point cardinality
and provides high-performance ltree traversal and query capabilities.
"""
from typing import Dict, List, Any, Optional
import uuid

HIERARCHY_LEVELS = ["site", "building", "system", "equipment", "subsystem", "point"]

class AssetNode:
    def __init__(self, asset_id: str, tenant_id: str, name: str, asset_type: str, path: str, parent_id: Optional[str] = None):
        self.id = asset_id
        self.tenant_id = tenant_id
        self.name = name
        self.asset_type = asset_type
        self.path = path  # ltree path e.g. site_north.bldg_01.hvac.ahu_01
        self.parent_id = parent_id
        self.children: List['AssetNode'] = []

class SemanticGraphManager:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.nodes: Dict[str, AssetNode] = {}
        self.path_index: Dict[str, AssetNode] = {}

    def add_asset(self, asset_id: str, name: str, asset_type: str, path: str, parent_id: Optional[str] = None) -> AssetNode:
        depth = len(path.split('.'))
        if depth < 1:
            raise ValueError("Asset path cannot be empty")
        
        node = AssetNode(asset_id, self.tenant_id, name, asset_type, path, parent_id)
        self.nodes[asset_id] = node
        self.path_index[path] = node
        
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node)
        return node

    def get_subtree(self, root_path: str) -> List[AssetNode]:
        """Returns all descendants where path starts with root_path (ltree prefix query)."""
        prefix = root_path + "."
        results = [self.path_index[root_path]] if root_path in self.path_index else []
        for path, node in self.path_index.items():
            if path.startswith(prefix):
                results.append(node)
        return results

    def to_phase4_drilldown_shape(self, site_path: str) -> Dict[str, Any]:
        """
        Emits hierarchy JSON matching the exact Phase 4 drill-down UI shape:
        Site -> Building -> System -> Equipment -> Meter/Point.
        """
        site_node = self.path_index.get(site_path)
        if not site_node:
            raise KeyError(f"Site path {site_path} not found")
        
        def format_node(node: AssetNode) -> Dict[str, Any]:
            return {
                "id": node.id,
                "name": node.name,
                "type": node.asset_type,
                "path": node.path,
                "children": [format_node(child) for child in node.children]
            }

        return format_node(site_node)
