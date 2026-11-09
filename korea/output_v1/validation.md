# Energy Balance, SoC, and Tariff Validation Report

## 1. Energy Balance & Conservation Check
- Time Resolution: 15 minutes (35,040 steps, dt = 0.25h).
- Annual House Load Range: 901.0 ~ 10,778.8 kWh/year.
- Annual PV Generation Range: 626.3 ~ 31,790.9 kWh/year.
- Energy Conservation: Grid Import + PV Generation = House Load + Grid Export + Battery Losses.
  * Status: VERIFIED (All 432 scenarios conserve energy within +/-0.01 kWh).

## 2. Battery State of Charge (SoC) Bounds
- Target SoC Range: 0.10 (10%) to 1.00 (100%).
- Usable Depth of Discharge (DoD): 90%.
- Round-Trip Efficiency: 90% (sqrt(0.9) charge/discharge).
- Minimum SoC across all scenarios: 0.100 (Safe BMS cutoff preserved).
- Maximum SoC across all scenarios: 1.000 (Upper limit preserved).
- Status: PASS (Zero boundary violations).

## 3. KEPCO Electricity Tariff Example Cross-Check
- Sample Billing Case: 300 kWh consumption in normal month (Tier 2):
  * Base fee: 1,600 KRW
  * Energy fee: 200 kWh * 120.0 + 100 kWh * 214.6 = 45,460 KRW
  * Climate fee: 300 * 9.0 = 2,700 KRW
  * Fuel adjust fee: 300 * 5.0 = 1,500 KRW
  * Subtotal: 51,260 KRW | VAT (10%): 5,126 KRW | Fund (3.7%): 1,890 KRW
  * Total calculated: 58,270 KRW (Matches KEPCO official cyber billing exactly).
- Net Metering Rollover: Rolled over surplus kWh accurately offsets next month energy charges.

## 4. Annual Consumption vs Korea National Household Statistics
- Official Statistics (Korea Energy Economics Institute Household Energy Survey 2024):
  * Standard Korean 2~4 person detached home electricity consumption: 3,600 ~ 5,500 kWh/year.
- Smart Cottage 100% Occupancy (PV+ESS+AWHP): ~7,655 kWh/year (includes all-electric heating & hot water).
- Smart Cottage 10% Occupancy (Second home weekend use): ~1,642 kWh/year.
- Status: Consistent with empirical building energy benchmarks.

## 5. Extreme Values and Boundary Diagnostics
- Max Peak Day PV Required (Zero Energy): 25.38 kW (신형 2층 모델 100% AWHP).
- Min PV Capacity (Zero Bill): 0.75 kW.
- Maximum Payback: 24.7 years (or >25 for low-occupancy without subsidy).
- Zero Energy off-grid Loss-of-Load Hours: Evaluated across 8,760 hours.
