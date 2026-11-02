# VerdantOS Bulk Asset Export Format Specification (Version 1 - Canonical Seed Format)

## 1. Overview & Specification Metadata
- **Format Version**: `1.0.0`
- **Specification Status**: Active / Canonical Seed Format
- **MIME Type**: `text/csv; charset=utf-8`
- **RFC Standard**: Conforms strictly to **RFC 4180** (CRLF or LF terminated, comma-separated, double-quote escaped).

---

## 2. Column Specification & Field Ordering
The canonical CSV export emits exactly 7 columns in the strict order defined below:

| Ordinal | Column Header | Data Type | Nullable | Description & Domain Rules |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `id` | UUID (v4) | No | Canonical unique primary key of the asset. |
| **2** | `tenant_id` | UUID (v4) | No | Owner tenant organization UUID enforcing tenant boundary. |
| **3** | `name` | String(255) | No | Human-readable asset name. |
| **4** | `asset_type` | Enum String | No | Asset taxonomy tier: `site`, `building`, `system`, `equipment`, `subsystem`, `point`, `ahu`, `chiller`, `meter`, `transformer`. |
| **5** | `path` | PostgreSQL `ltree` | No | Dot-delimited canonical hierarchy path (e.g. `campus_north.bldg_a.ahu_01`). |
| **6** | `parent_id` | UUID (v4) | Yes | Direct parent asset UUID (`""` / empty string for root `site` nodes). |
| **7** | `brick_class` | URI String | Yes | Brick Schema ontology class (e.g. `brick:Air_Handling_Unit`, `brick:Electrical_Meter`). |

---

## 3. Compared vs. Excluded Fields (Data Loss & Preservation Boundaries)

### 3.1 Compared Fields (Export Contract Preservation)
- `id`: Checked for exact identity round-trip.
- `tenant_id`: Checked for multi-tenant isolation preservation.
- `name`: Checked for string literal equivalence.
- `asset_type`: Checked for taxonomy preservation.
- `path`: Checked for exact dot-delimited hierarchy equivalence.
- `parent_id`: Checked for parent-child relationship integrity.
- `brick_class`: Checked for semantic model ontology alignment.

### 3.2 Excluded Fields & Design Rationale
- `created_at` & `updated_at`: **Excluded**. Generated dynamically by database triggers (`DEFAULT NOW()`). Storing them in seed CSV would cause false drift detection on re-import.
- `is_deleted`: **Excluded**. The canonical bulk export represents active operational assets (`WHERE is_deleted = FALSE`). Soft-deleted records are handled via tombstone sync.
- `attributes` & `haystack_tags`: **Excluded from v1.0**. Retained for export format v2.0 (Full Backup). Version 1.0 is optimized as a lightweight seed, template, and migration interchange contract.
