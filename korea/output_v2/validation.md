# LG Smart Cottage ROI Simulation & Physical Validation Report

## 1. KEPCO Electricity Tariff Example Verification
- Reference Billing Case: 300 kWh consumption in normal month (Low Voltage Residential Tier 2):
  * Base Fee: 1,600 KRW
  * Energy Charge: (200 kWh * 120.0) + (100 kWh * 214.6) = 45,460 KRW
  * Climate Environment Charge: 300 kWh * 9.0 = 2,700 KRW
  * Fuel Cost Adjustment Charge: 300 kWh * 5.0 = 1,500 KRW
  * Subtotal: 51,260 KRW
  * VAT (10%, rounded): 5,126 KRW
  * Public Service Fund (2.7%, cut under 10 KRW): 51,260 * 0.027 = 1,384.02 -> 1,380 KRW
  * Calculated Total: 51,260 + 5,126 + 1,380 = 57,766 -> 57,760 KRW (Cut under 10 KRW).
  * Test Status: Passed unit test `test_tariff_300kwh_example` with exact value 57,760 KRW.
- Super-User Rate: 704.5 KRW/kWh verified on >1,000 kWh consumption in winter and summer months.
- Steady-State Rollover: Fixed-point iteration ensures Dec-31 surplus equals Jan-1 beginning surplus.

## 2. Design Day, Load, and PV/ESS Invariance across Occupancy Rates
- Zero Energy Rule: Design day selected from 100% occupancy load profile and forced across all occupancy rates.
- Sizing consistency: Exactly 12 unique PV/ESS sizing results applied across all 6 occupancy rates.
| House Model | Heating Package | EV | Design Date | Day Total Load (kWh) | 1kWp PV Gen (kWh) | Sized PV (kW) | Sized ESS (kWh) |
|---|---|---|---|---|---|---|---|
| MONO Core 54 | PV+ESS+가스보일러 | 0 | 2026-08-04 (Day 216) | 19.55 | 5.12 | 3.82 | 6.33 |
| MONO Core 54 | PV+ESS+가스보일러 | 1 | 2026-08-04 (Day 216) | 26.48 | 5.12 | 5.17 | 13.90 |
| MONO Core 54 | PV+ESS+AWHP | 0 | 2026-01-16 (Day 16) | 22.31 | 0.77 | 28.81 | 19.06 |
| MONO Core 54 | PV+ESS+AWHP | 1 | 2026-01-16 (Day 16) | 29.23 | 0.77 | 37.75 | 26.95 |
| MONO Core 72 | PV+ESS+가스보일러 | 0 | 2026-08-04 (Day 216) | 25.07 | 5.12 | 4.90 | 8.66 |
| MONO Core 72 | PV+ESS+가스보일러 | 1 | 2026-08-04 (Day 216) | 32.00 | 5.12 | 6.25 | 16.15 |
| MONO Core 72 | PV+ESS+AWHP | 0 | 2026-01-16 (Day 16) | 28.15 | 0.77 | 36.36 | 23.94 |
| MONO Core 72 | PV+ESS+AWHP | 1 | 2026-01-16 (Day 16) | 35.08 | 0.77 | 45.30 | 31.79 |
| DUO Max 45 | PV+ESS+가스보일러 | 0 | 2026-08-04 (Day 216) | 18.66 | 5.12 | 3.64 | 6.26 |
| DUO Max 45 | PV+ESS+가스보일러 | 1 | 2026-08-04 (Day 216) | 25.58 | 5.12 | 5.00 | 13.83 |
| DUO Max 45 | PV+ESS+AWHP | 0 | 2026-08-04 (Day 216) | 20.32 | 5.12 | 3.97 | 7.44 |
| DUO Max 45 | PV+ESS+AWHP | 1 | 2026-08-04 (Day 216) | 27.24 | 5.12 | 5.32 | 14.89 |

## 3. TMY Daily vs Monthly-Average PV Generation Difference
- Weather Dataset Path: `D:\Projects\smart-cottage-roi\korea\source\tmy_korea_jincheon_15min.csv`
- Annual Global Horizontal Irradiance (GHI): 1291.3 kWh/m2/year.
- Observation on TMY Day vs Month-Average Sizing:
  * In synthetic clear-sky weather, daily clearness Kt is constant, yielding <1% difference.
  * Under realistic weather with cloudy/rainy cycles and monsoon season (Kt varying 0.15 to 0.82),
    a sunny design day exhibits 1kWp generation 20~40% higher than monthly average, causing
    TMY-based PV capacity to be smaller than month-average PV capacity. On cloudy design days, the reverse holds.

## 4. Baseline Energy Cost & Propane Gas Inclusion
- Baseline Definition: All scenarios compared against 'PV=0, ESS=0, Gas Boiler (propane), Grid electricity'.
- Propane Retail Price: 2,780.15 KRW/kg (Opinet Gangwon Region retail price, G1 item 25).
- Propane Net Heating Value: 46.3 MJ/kg = 12.8611 kWh/kg (Energy Law Enforcement Rules, G1 item 32).
- Verification: In all AWHP scenarios, annual propane cost is 0 KRW and baseline propane cost is included in savings.
- Baseline Energy Cost Range: 253,552 ~ 3,112,016 KRW/year.

## 5. Subsidy Rule Application Check
- Rule 1: Capacity > 3.3 kW -> PV Subsidy = 0 KRW.
  * Verified: 0 violations found (0 expected).
- Rule 2: Off-grid (zero_energy) -> PV Subsidy = 0 KRW.
  * Verified: 0 violations found (0 expected).
- Rule 3: AWHP Subsidy Rate = 70% of 14,000,000 KRW = 9,800,000 KRW (UNVERIFIED).
- Rule 4: ESS Subsidy = 0 KRW (PLACEHOLDER).

## 6. Comparison with G4 Field Statistics
- Official / Survey Reference Values from `korea/source/g4.csv`:
  * `가구원수·면적별 전력 사용량`: 457.7 kWh/month (4-person household average = 5,492.4 kWh/year).
  * `인원별 급탕량`: 75~150 L/person/day (conservative baseline model uses 50 L/person/day).
  * `EV 연간 주행거리`: 13,140 km/year.
  * `EV 공인 전비`: 5.2 km/kWh.
  * `LG Therma V 외기온별 COP`: 4.70 (7℃), 3.70 (2℃), 2.70 (-7℃).
  * `LG 시스템에어컨 냉방 효율`: 4.40 W/W.
- Simulated Smart Cottage Annual Loads:
  * MONO Core 54 (2 persons, 100% occ, gas boiler, EV=0): 3,620.8 kWh/year.
  * DUO Max 45 (2 persons, 100% occ, AWHP, EV=1): 7,204.7 kWh/year.

## 7. Complete List of PLACEHOLDER and UNVERIFIED Parameters
### PLACEHOLDER Items (No reference or unconfirmed in source G1~G4):
- `houses.MONO Core 54.roof_pv_capacity_max`: status=PLACEHOLDER
- `houses.MONO Core 72.roof_pv_capacity_max`: status=PLACEHOLDER
- `capex.pv_cost_per_w`: status=PLACEHOLDER
- `capex.inverter_cost_per_w`: status=PLACEHOLDER
- `capex.ess_cost_per_kwh`: status=PLACEHOLDER
- `capex.installation_fixed_cost`: status=PLACEHOLDER
- `capex.inverter_replacement_cost_ratio`: status=PLACEHOLDER
- `capex.ess_replacement_cost_ratio`: status=PLACEHOLDER
- `subsidy.ess_subsidy_rate_per_kwh`: status=PLACEHOLDER
- `subsidy.ess_subsidy_max_cap`: status=PLACEHOLDER
- `load.ev_charge_start_hour`: status=PLACEHOLDER

### UNVERIFIED Items (General web page, blog, or single vendor quote):
- `houses.MONO Core 72.appliances_desc`: status=UNVERIFIED
- `houses.DUO Max 45.roof_pv_capacity_max`: status=UNVERIFIED
- `houses.DUO Max 45.base_pv_capacity_kw`: status=UNVERIFIED
- `capex.ess_min_module_kwh`: status=UNVERIFIED
- `capex.awhp_additional_capex`: status=UNVERIFIED
- `subsidy.pv_subsidy_rate_under_2kw`: status=UNVERIFIED
- `subsidy.pv_subsidy_rate_2_to_3kw`: status=UNVERIFIED
- `subsidy.pv_subsidy_max_threshold_kw`: status=UNVERIFIED
- `subsidy.awhp_subsidy_rate`: status=UNVERIFIED
- `load.standby_power`: status=UNVERIFIED
- `equipment.awhp_system.cop_heat_at_minus_15c`: status=UNVERIFIED
- `equipment.awhp_system.cop_dhw`: status=UNVERIFIED
