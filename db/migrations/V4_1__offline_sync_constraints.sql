-- V4_1__offline_sync_constraints.sql - Offline Sync Constraints and Defaults (Workstream 11)

-- Schema-N-1: Validate conflict resolution enum values
ALTER TABLE sync_conflicts 
  ADD CONSTRAINT conflict_resolution_valid 
  CHECK (resolution IN ('EDGE_WINS', 'CLOUD_WINS', 'MANUAL', 'EDGE_PRECEDENCE', 'CLOUD_PRECEDENCE', 'MANUAL_REVIEW', 'ROLLBACK_TRIGGERED'));

-- Schema-N-2: Validate conflict type enum values
ALTER TABLE sync_conflicts 
  ADD CONSTRAINT conflict_type_valid 
  CHECK (conflict_type IN ('TELEMETRY_LWW', 'CONFIG_CONFLICT', 'SEQUENCE_GAP', 'TELEMETRY_OVERWRITE', 'CONFIG_DRIFT', 'TIMESTAMP_COLLISION', 'BUNDLE_MIGRATION_FAILED'));

-- Schema-N-3: Default status to PENDING_FIRST_SYNC
ALTER TABLE offline_sync_state 
  ALTER COLUMN status SET DEFAULT 'PENDING_FIRST_SYNC';
