# UI Dashboard Drill-Down Route & Rendered Structure (OC-1 Status: DISCLOSED PARTIAL)

## 1. Route Path & Component Mounting
- **Mounting Component Source**: `web/src/DrillDownDashboard.tsx`
- **Application Route**: `/drilldown` on `web-dashboard:3000` (React 18 Shell).
- **Execution Disclosure**:
  - *Current Status*: **AUTHORED & UNIT TESTED**.
  - *Rendering Disclosure*: The component DOM state transitions (`Site -> Building -> Asset -> Meter`) have been unit tested in Jest. Live browser headless rendering and screenshot PNG capture against the running `web-dashboard` Docker container will be executed during **Phase 5 Workstream 6 (Building Analytics & Full UI Delivery)**.

---

## 2. Intended DOM Structure & State Trace
The component executes interactive state transitions across four distinct levels:

```
[Level 1: Site View]
  ├── Title: Campus North (412.8 MWh)
  └── Trigger: Button "Drill Down to Building A ->" -> Sets state: level = 'building'

[Level 2: Building View]
  ├── Title: Building A (182.4 MWh)
  └── Trigger: Button "Drill Down to Asset: AHU-01 ->" -> Sets state: level = 'asset'

[Level 3: Asset View]
  ├── Title: Air Handling Unit #01 (AHU-01) [brick:Air_Handling_Unit]
  ├── Alert Badge: [ACTIVE ANOMALY] Baseload Excess (+40.4 kW above expected 45.0 kW)
  └── Trigger: Button "Drill Down to Physical Meter" -> Sets state: level = 'meter'

[Level 4: Meter View]
  ├── Title: Physical Meter Point 44444444-4444-4444-4444-444444444444
  ├── Reading: 85.4 kW | Quality: GOOD | Sampling: 60s
  └── Trigger: Button "Return to Site Overview" -> Sets state: level = 'site'
```
