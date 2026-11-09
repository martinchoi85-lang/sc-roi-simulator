# LG Smart Cottage ROI Calculation Summary (Korea)

## 1. Execution Overview
- Total Scenarios Evaluated: 432 (432 Full Basis + 144 DUO Max Incremental)
- Feasible Payback Scenarios (<=25 yrs): 131 / 432
- Near-Zero-Bill No Solutions (Payback >3 yrs): 144
- Roof PV Capacity Exceeded: 65 cases (Flagged)

## 2. Key Financial Indicators
- Minimum Payback Period: 6.1 years
- Average Feasible Payback: 16.9 years
- Net CAPEX Range: 6,903,600 ~ 98,608,000 KRW
- Annual Savings Range (Year 1): 85,480 ~ 3,112,016 KRW

## 3. Data Status (11 PLACEHOLDERs, 12 UNVERIFIEDs)
- PLACEHOLDER (11): houses.MONO Core 54.roof_pv_capacity_max, houses.MONO Core 72.roof_pv_capacity_max, capex.pv_cost_per_w, capex.inverter_cost_per_w ...
- UNVERIFIED (12): houses.MONO Core 72.appliances_desc, houses.DUO Max 45.roof_pv_capacity_max, houses.DUO Max 45.base_pv_capacity_kw, capex.ess_min_module_kwh ...
- All baseline costs include propane (2,780.15 KRW/kg, 46.3 MJ/kg) + grid electricity.

## 4. Primary Outputs
- Raw Table: `korea/output/results_all.csv` (432 rows)
- DUO Max Incremental: `korea/output/results_duomax_incremental.csv` (144 rows)
- Verification Report: `korea/output/validation.md`
- Visual Diagnostics: `korea/output/charts/`
