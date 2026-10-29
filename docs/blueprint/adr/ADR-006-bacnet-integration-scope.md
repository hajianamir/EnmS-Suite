# ADR-006: Standalone BACnet/IP vs Niagara-Mediated BACnet Strategy

## Status
Accepted

## Date
2026-10-20

## Decision Owner
Principal OT Network Architect

## Context
VerdantOS deployment sites include both modern commercial facilities with Tridium Niagara 4 BMS framework installed and standalone industrial buildings lacking Tridium Niagara middleware.

## Decision & Tier 1 Protocol Architecture
VerdantOS supports **both** BACnet integration patterns under Tier 1 scope:
1. **Standalone BACnet/IP (Native Go Driver)**: The edge gateway runs a native, open-source Go BACnet/IP stack (`gobacnet`) for direct WHO-IS/I-AM device discovery and ReadProperty execution. *Target*: Sites without Tridium Niagara, eliminating Niagara station licensing fees.
2. **Niagara-Mediated BACnet/IP (Niagara Station Driver)**: For sites with existing Niagara 4 stations, the edge gateway queries Niagara History ORDs over Niagara Web / Fox API. *Target*: Facilities with complex Niagara station point mappings already configured.

## Contradiction Sweep Review Note
- **Sweep Date**: 2026-10-20 (Post-ADR acceptance)
- **Result**: Checked against `docs/blueprint/04-architecture.md`, `06-functional-modules.md`, and `10-tech-stack.md`. Standalone BACnet/IP and Niagara BMS driver patterns aligned across all documents. Zero contradictions found.

## Consequences
- *Positive*: Enables zero-licensing-cost deployment on standalone sites while retaining full compatibility with enterprise Niagara BMS installations.
- *Negative*: Edge gateway maintains two distinct BACnet ingestion driver paths.
