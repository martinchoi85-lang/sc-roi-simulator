# LG Smart Cottage ROI Calculation Summary (Korea)

## 1. Scenario Execution Overview
- Full Scenarios: 432 evaluated (3 Models x 2 Heat x 2 EV x 6 Occ x 3 Target x 2 Subsidy).
- DUO Max Incremental (Appendix): 72 AWHP scenarios (Baseline: existing AWHP + 5kW PV).
- Zero-Energy Deficit & LOL: Max deficit = 0.000000 kWh, Max LOL = 0.0 hrs (100% Zero Deficit Satisfied).
- Feasible Payback (<=25 yrs): 24 / 432 cases (Near-Zero-Bill no solution: 144).
- Contract Power Peak Range: 0.0 ~ 9.3 kW.

## 2. Key Economic Indicators (Central Baseline)
- Payback Range (Feasible): 16.9 ~ 22.6 yrs (Avg: 20.5 yrs).
- Net CAPEX Range: 19,122,183 ~ 383,260,000 KRW.
- Annual Savings Year 1: 97,430 ~ 3,434,547 KRW (Baseline includes propane).
- AWHP 70% Subsidy Sensitivity: Payback improves by avg 1.6 yrs for AWHP.

## 3. Data Integrity & Metadata Status
- PLACEHOLDER Count (5): subsidy.ess_subsidy.unit_rate_per_kwh, subsidy.ess_subsidy.max_cap, load.ev_charge_start_hour ...
- UNVERIFIED Count (15): houses.MONO Core 72.appliances_desc, houses.DUO Max 45.base_pv_capacity_kw, tariff.super_user_rate ...
- Weather Source: Chuncheon WMO 471010 TMYx EPW (1,490.6 kWh/m2 GHI, 15-min interpolated).

## 4. Key Output Files
- Full Table: `korea/output/results_all.csv` (432 rows)
- Zero Energy Reference Table: `korea/output/zero_energy_reference.csv` (12 rows)
- Appendix Table: `korea/output/results_duomax_incremental.csv` (72 rows)
- Verification Report: `korea/output/validation.md`
- Diagnostics Charts: `korea/output/charts/`
