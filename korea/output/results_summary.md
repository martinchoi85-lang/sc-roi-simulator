# LG Smart Cottage ROI Calculation Summary (Korea)

## 1. Scenario Execution Overview
- Full Scenarios: 432 evaluated (3 Models x 2 Heat x 2 EV x 6 Occ x 3 Target x 2 Subsidy).
- DUO Max Incremental (Appendix): 72 AWHP scenarios (Baseline: existing AWHP + 5kW PV).
- Zero-Energy Deficit & LOL: Max deficit = 0.000000 kWh, Max LOL = 0.0 hrs (100% Zero Deficit Satisfied).
- Feasible Payback (<=25 yrs): Low: 94/432, Central: 40/432, High: 36/432 (No Sol: 144).
- Contract Power Peak Range: 0.0 ~ 9.3 kW.

## 2. Key Economic Indicators (Central Baseline)
- Note: ESS costs are based on overseas benchmarks (NREL Q1 2021 & NREL ATB, fx=1400 KRW/USD).
- Payback Range (Feasible Central): 15.3 ~ 24.1 yrs (Avg: 19.8 yrs).
- Net CAPEX Range (Central): 17,693,686 ~ 345,598,403 KRW.
- Annual Savings Year 1: 97,430 ~ 3,390,092 KRW (Baseline includes propane).
- AWHP 70% Subsidy Sensitivity: Payback improves by avg 1.5 yrs (Max 9.8M KRW).

## 3. Data Integrity & Metadata Status
- PLACEHOLDER Count (13): capex.fx_krw_per_usd, capex.ground_mount_pv.threshold_kw, capex.ground_mount_pv.excess_cost_per_kw ...
- UNVERIFIED Count (28): houses.MONO Core 72.appliances_desc, houses.MONO Core 72.included_appliances, houses.DUO Max 45.base_pv_capacity_kw ...
- Weather Source: Chuncheon WMO 471010 TMYx EPW (1,490.6 kWh/m2 GHI, 15-min interpolated).

## 4. Key Output Files
- Full Table: `korea/output/results_all.csv` (432 rows)
- Zero Energy Reference Table: `korea/output/zero_energy_reference.csv` (12 rows, grid search & top 5)
- Appendix Table: `korea/output/results_duomax_incremental.csv` (72 rows)
- Verification Report: `korea/output/validation.md`
- Debug Day 34: `korea/output/debug_day34.csv` (15-min PV metrics)
- Diagnostics Charts: `korea/output/charts/`
