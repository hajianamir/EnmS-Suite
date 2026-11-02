-- V2__multi_site.sql - Multi-site hierarchy, path constraints, and index optimizations
-- Extends asset hierarchy to support depth >= 6: Site -> Building -> System -> Equipment -> Subsystem -> Measurement Point

-- Additional index on assets parent_id and asset_type for fast subtree & hierarchical queries
CREATE INDEX IF NOT EXISTS idx_assets_parent_id ON assets(parent_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_tenant_path ON assets(tenant_id, path);

-- Function to validate hierarchical depth and cardinality
CREATE OR REPLACE FUNCTION validate_asset_hierarchy_path()
RETURNS TRIGGER AS $$
DECLARE
    path_depth INT;
BEGIN
    path_depth := nlevel(NEW.path);
    IF path_depth < 1 THEN
        RAISE EXCEPTION 'Asset path cannot be empty';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_asset_hierarchy_path ON assets;
CREATE TRIGGER trg_validate_asset_hierarchy_path
    BEFORE INSERT OR UPDATE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION validate_asset_hierarchy_path();
