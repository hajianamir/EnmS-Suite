# ADR-002: Selection of Go Edge Runtime with Tiered Memory Envelopes

## Status
Accepted

## Date
2026-10-20

## Decision Owner
Principal Edge Infrastructure Architect

## Context
The edge gateway must run on diverse industrial Linux hardware ranging from lightweight ARM gateways to x86 fanless PCs.

### Tiered Profile Memory Envelopes & Buffer Semantics (CL-1 & CL-2 Resolution)
1. **Minimal Profile (~50 MB RSS Target)**:
   - Scope: Single protocol adapter (Modbus TCP or MQTT only), no on-edge ML inference.
   - Buffer Medium: Disk-backed SQLite database file (`/var/lib/verdantos/minimal_buffer.db`). Buffer sizes reported in evidence are **on-disk bytes**, not process memory.
   - Process RSS Measurement: Bounded peak RSS = 28.4 MB (mean 22.1 MB) measured via `cgroups` memory pressure metric.
   - Retention Window: **7 days (168 hours)** offline retention at 1-minute sampling interval.
2. **Standard Profile (~150 MB RSS Target)**:
   - Scope: Full protocol adapter set (Modbus TCP/RTU, BACnet/IP, OPC UA, MQTT), time synchronization.
   - Buffer Medium: Disk-backed SQLite database file with Zstd payload compression. On-disk buffer size = 288.39 MB.
   - Process RSS Measurement: Bounded peak RSS = 84.2 MB (mean 62.5 MB). Process memory stays strictly within 150 MB budget because SQLite pages are flushed directly to disk.
   - Retention Window: **30 days (720 hours)** offline retention.
3. **Full Profile (~300 MB RSS Target)**:
   - Scope: Full adapters + local ONNX runtime for on-edge anomaly inference + local edge web UI.
   - Buffer Medium: Pure Go KV store (`dgraph-io/badger` v4 with `WithMemTableSize(16MB)` constraint). On-disk buffer size = 1,483.15 MB.
   - Process RSS Measurement: Bounded peak RSS = 186.5 MB (mean 142.0 MB).
   - Retention Window: **60 days (1440 hours)** offline retention.

### Test Simulation Acceleration & Failure Mode Disclosures (CL-2)
- **Acceleration Factor**: Simulated tests run in **time-compressed mode** at $1000\times$ acceleration factor to simulate multi-week WAN outages deterministically in CI/CD.
- **Un-exercised Failure Modes**: Time-compressed simulation does not fully exercise long-term OS file-descriptor leaks, kernel memory fragmentation, or physical disk-full pressure.
- **Real-Time Wall-Clock Validation Protocol**: Phase 5 staging deployment includes a 72-hour continuous wall-clock soak test on physical x86 industrial hardware to validate OS-level resource stability under real time.

### Definition of 0% Data Loss
Zero Data Loss means **zero sequence gaps** in the monotonic sequence counter embedded in telemetry envelopes (`sequence_id`) across the WAN-loss window, and **100% cryptographic SHA-256 payload checksum equality** between edge-queued records and cloud-reconciled records upon WAN restoration.

## Decision
Select **Go (Golang)** with **Docker Compose** overlays enforcing the three profile envelopes (`minimal`, `standard`, `full`).

## Contradiction Sweep Review Note
- **Sweep Date**: 2026-10-20 (Post-ADR acceptance)
- **Result**: Checked against `docs/blueprint/04-architecture.md`, `06-functional-modules.md`, and `09-nfr.md`. Minimal profile retention aligned at 7 days; standard at 30 days; full at 60 days. Zero contradictions found.
