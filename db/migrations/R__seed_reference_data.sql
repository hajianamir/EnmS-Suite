-- Repeatable Seed Migration: R__seed_reference_data.sql
-- Intentionally using Flyway repeatable migration semantics (R__) so seed fixtures can be updated idempotently.
INSERT INTO tenants (id, name, slug, plan_tier) 
VALUES ('11111111-1111-1111-1111-111111111111', 'Campus North Tenant', 'campus-north', 'standard')
ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO organization_units (id, tenant_id, name, code, created_by)
VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'Facilities North', 'FAC-N', '00000000-0000-0000-0000-000000000000')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO assets (id, tenant_id, org_unit_id, path, name, asset_type, brick_class, created_by)
VALUES ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'campus_north.bldg_a.ahu_01', 'AHU Building A 01', 'ahu', 'brick:Air_Handling_Unit', '00000000-0000-0000-0000-000000000000')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO measurement_points (id, tenant_id, asset_id, name, point_type, unit, created_by)
VALUES ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', 'AHU-01 Active Power', 'active_power', 'kW', '00000000-0000-0000-0000-000000000000')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
