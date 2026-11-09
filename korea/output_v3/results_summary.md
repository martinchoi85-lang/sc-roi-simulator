# LG Smart Cottage ROI Calculation Summary (Korea)

## 1. Scenario Execution Overview
- Full Scenarios: 432 evaluated (3 Models x 2 Heat x 2 EV x 6 Occ x 3 Target x 2 Subsidy).
- DUO Max Incremental (Appendix): 72 AWHP scenarios (Baseline: existing AWHP + 5kW PV).
- Feasible Payback (<=25 yrs): 158 / 432 cases (Near-Zero-Bill no solution: 144).
- Contract Power Peak Range: 3.0 ~ 8.8 kW (All within physical limits).

## 2. Key Economic Indicators
- Payback Range (Feasible): 5.9 ~ 24.9 yrs (Avg: 16.0 yrs).
- Net CAPEX Range: 5,436,600 ~ 53,879,500 KRW.
- Annual Savings Year 1: 97,340 ~ 3,434,547 KRW (Baseline includes propane).
- AWHP 70% Subsidy Sensitivity: Payback improves by avg 1.7 yrs for AWHP.

## 3. Data Integrity & Metadata Status
- PLACEHOLDER Count (20): capex.pv_system.unit_cost_per_w.low, capex.pv_system.unit_cost_per_w.central, capex.pv_system.unit_cost_per_w.high ...
- UNVERIFIED Count (10): houses.MONO Core 72.appliances_desc, houses.DUO Max 45.base_pv_capacity_kw, tariff.super_user_rate ...
- Weather Source: Chuncheon WMO 471010 TMYx EPW (1,490.6 kWh/m2 GHI, 15-min interpolated).

## 4. Key Output Files
- Full Table: `korea/output/results_all.csv` (432 rows)
- Appendix Table: `korea/output/results_duomax_incremental.csv` (72 rows)
- Verification Report: `korea/output/validation.md`
- Diagnostics Charts: `korea/output/charts/`
