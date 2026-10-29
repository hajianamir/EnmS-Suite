# ADR-003: Multi-Tenancy Boundary and Migration Path Strategy

## Status
Accepted

## Date
2026-10-20

## Decision Owner
Principal Security Architect

## Context
VerdantOS serves mid-market SMEs, large commercial building portfolios, enterprise industrial sites, and white-label partners.

## Plan Tier Isolation & Step-by-Step Migration Path (K-2 Resolution)

| Plan Tier | Isolation Strategy | Encryption Key Scope | Migration Path From/To | Noisy-Neighbor Control |
| :--- | :--- | :--- | :--- | :--- |
| **SME / Standard SaaS** | Shared Database + PostgreSQL Row-Level Security (RLS) | Shared KMS Key | Baseline default tier; migrates to Enterprise via schema export script. | Per-tenant API rate limits (100 req/min). |
| **Enterprise Cloud** | Schema-per-tenant on shared DB cluster | Per-tenant KMS Key | Upgradable to Dedicated via database dump & restore. | Dedicated Kubernetes namespace & CPU/RAM limits. |
| **Private Cloud / Air-Gapped** | Dedicated Database instance & dedicated K8s cluster | Customer-Managed KMS (BYOK) | Isolated environment; no automatic outbound cloud migration. | Physical hardware / VPC isolation. |

### Step-by-Step Migration Procedure (`shared-rls` -> `dedicated-vpc`)
1. **Schema Extraction**: Execute `pg_dump --section=schema` filtering records where `tenant_id = target_uuid`.
2. **RLS Policy Strip**: Strip `tenant_isolation_*` RLS policies from DDL for dedicated database execution.
3. **Data Dump & Re-encryption**: Export tenant records, re-encrypt payloads using customer's dedicated KMS key (`BYOK`), and load into target dedicated PostgreSQL database.
4. **DNS & Token Switch**: Update tenant realm routing in Keycloak to point API traffic to dedicated VPC API Gateway endpoint.

## Contradiction Sweep Review Note
- **Sweep Date**: 2026-10-20 (Post-ADR acceptance)
- **Result**: Checked against `docs/blueprint/05-domain-data-model.md`, `09-nfr.md`, and `11-apis-integrations.md`. DDL schema verified to support RLS policies, schema-per-tenant, and dedicated extraction. Zero contradictions found.
