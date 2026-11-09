# LG Smart Cottage ROI Calculation Summary (Korea v6)

## 1. Scenario Execution Overview
- Full Scenarios: 432 evaluated (3 Models x 2 Heat x 2 EV x 6 Occ x 3 Target x 2 Subsidy).
- DUO Max Incremental (Appendix): 72 AWHP scenarios (Baseline: existing AWHP + 5kW PV).
- Zero-Energy Deficit & LOL: Max deficit = 0.000000 kWh, Max LOL = 0.0 hrs across all 12 configurations.
- Feasible Payback (<=25 yrs): Central: 42/432 (9.7%), 3-yr Feasible: 0/432 (0.0%).
- Shortest Payback: 15.3 yrs (MONO Core 72, AWHP, Zero Bill / Near Zero, Occ 100%, EV 1).

## 2. Key Economic Indicators (Central Baseline, Full Basis)
- Propane Price: 2,812.26 KRW/kg (Opinet National Avg 2026-10 W4, VERIFIED).
- Subsidy Applied: 2.65M KRW (National 1.65M + Chuncheon 1.0M for 3kW, VERIFIED).
- Net CAPEX Range (Central): 18,135,354 ~ 210,882,040 KRW (Zero Energy: 49.2M ~ 210.9M KRW).
- Zero Energy Sizing: PV search lower bound 0.5kW applied; best combinations find 10.0~41.5 kW.
- Land Area Metric: pv_land_area_m2 = PV kW x 5 m2 added (50.0 ~ 207.5 m2, PLACEHOLDER).

## 3. Data Integrity & Verification Status
- PLACEHOLDER Count: 11 items (fx_rate, ground_mount_pv_extra, inverter_rep ...).
- UNVERIFIED Count: 25 items (household loads 3749/4094 kWh, Therma V under A-7, NREL ESS).
- VERIFIED Status: rollover_scheme (Article 18), PV 3kW cap (4.541M), Subsidies, Therma V specs.

## 4. Key Output & Report Files
- Full Table: `korea/output/results_all.csv` (432 rows) & `results_duomax_incremental.csv` (72 rows)
- Zero Energy Reference: `korea/output/zero_energy_reference.csv` (12 rows, min_capex == top1_capex)
- Unified Data: `korea/report/report_data.json` & Palette: `korea/report/color_tokens.md`
- Standalone Reports: `korea/report/LG_SC_Korea_ROI_Report.html` & `LG_SC_Korea_ROI_Report.pptx`
- Verification & Snapshots: `korea/output/validation.md` & `korea/report/snapshots/`