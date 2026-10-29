# 12. UX/UI, Copy Guidelines & English Terminology Governance (R-14)

## 12.1 User Interface Design System
- **Design Philosophy**: High data density, dark-mode first for control room monitoring, WCAG 2.1 AA compliant contrast ratios.
- **String Externalization Rule**: 100% of UI strings externalized in JSON resource files (`locales/en-US.json`). Enforced by frontend build linter (`eslint-plugin-i18n-json`).

---

## 12.2 Terminology Glossary Standard

| Approved Canonical Term | Deprecated / Prohibited Terms | Exact Definition |
| :--- | :--- | :--- |
| **EnPI (Energy Performance Indicator)** | Energy metric, KPI, Usage number | Quantitative value or measure of energy performance as defined by ISO 50006. |
| **Baseline Model** | Average curve, Expected line | Quantified reference line representing energy consumption under normalized conditions. |
| **Nonconformity** | Violation, Error, Fail | Non-fulfillment of an ISO 50001 requirement or operational energy target. |
| **Significant Energy Use (SEU)** | Big meter, High energy asset | Energy use accounting for substantial energy consumption and offering key savings potential. |
| **Action Item** | Task, Todo, Project | Structured PDCA task linked to expected vs realized energy savings. |

---

## 12.3 Dashboard Layout & Textual Wireframes

```
+-----------------------------------------------------------------------------------+
|  [VerdantOS]  Site: Campus North | Bldg 4   [Global Search...] (Elena Rostova - EnMgr) |
+-----------------------------------------------------------------------------------+
| NAV: [Dashboard] [Assets] [EnPI & Baseline] [Anomalies (3)] [Actions] [ISO Audit]  |
+-----------------------------------------------------------------------------------+
| KPI Overview (Last 30 Days):                                                     |
| +---------------------+ +---------------------+ +---------------------------------+ |
| | Total Energy        | | Normalized EnPI     | | Active ISO Actions             | |
| | 412.8 MWh (-4.2%)   | | 12.4 kWh/m² (-8%)  | | 4 Open ($12.5k Est. Savings)  | |
| +---------------------+ +---------------------+ +---------------------------------+ |
+-----------------------------------------------------------------------------------+
| Main Chart Window: Energy Consumption vs Baseline (CUSUM Overlay)                  |
| [Line Chart: Actual Consumption (Blue) vs Expected Baseline Model v1.2 (Dotted)]  |
| [Sub-chart: Cumulative Sum of Savings (Green Trend line showing $8,400 saved)]     |
+-----------------------------------------------------------------------------------+
| Active Anomalies & Root Causes:                                                    |
| - [HIGH] Chiller #2 Baseload Spike (+28 kW) | RCA: Condenser Valve Bypass (88%) | [Action]
| - [MED] AHU-04 Extended Schedule Run       | RCA: Override switch left active  | [Dismiss]
+-----------------------------------------------------------------------------------+
```
