"""100-year cash flow and payback period calculation engine (v9).

Rules:
- Duration: 100 years, undiscounted, fixed tariffs/fuel prices, repeated TMY weather.
- Annual savings = Baseline total energy cost - Alternative total energy cost (PV degradation accounted).
- Deduct replacement costs in incurred years:
  - PV module: 25-yr lifetime (0.5%/yr degradation, resets to 1.0 upon replacement in Yr 26, 51, 76).
  - Inverter: 12-yr lifetime (replaced in Yr 13, 25, 37, 49, 61, 73, 85, 97).
  - ESS battery: 10-yr lifetime (replaced in Yr 11, 21, 31, 41, 51, 61, 71, 81, 91).
  - AWHP: 15-yr lifetime (replaced in Yr 16, 31, 46, 61, 76, 91).
- Payback period = The exact point where cumulative cash flow crosses 0 and remains >= 0 through Year 100.
  Linear interpolation within year (1 decimal place).
- If not recovered within 100 years: "불가능" (reason_code="NOT_RECOVERED_100Y", payback_years=None).
- If Year 1 annual savings <= 0: "불가능(연간 이득 없음)" (reason_code="NO_ANNUAL_SAVINGS", payback_years=None).
- Output 25-year cumulative net savings.
"""

from typing import Any, Dict, Optional, Tuple, Union
import numpy as np


def calculate_100y_cashflow(
    net_capex: float,
    baseline_annual_cost: float,
    alternative_year1_cost: float,
    baseline_propane_cost: float,
    alternative_propane_cost: float,
    pv_capacity_kw: float = 0.0,
    ess_capacity_kwh: float = 0.0,
    is_awhp: bool = False,
    pv_turnkey_cost: float = 0.0,
    inverter_replacement_cost: float = 0.0,
    ess_replacement_cost: float = 0.0,
    awhp_replacement_cost: float = 0.0,
    pv_degradation_annual: float = 0.005,
) -> Dict[str, Any]:
    """Calculates 100-year cash flow, replacements, and payback period."""
    total_savings_y1 = max(0.0, baseline_annual_cost - alternative_year1_cost)
    propane_savings = max(0.0, baseline_propane_cost - alternative_propane_cost)
    electricity_savings_y1 = max(0.0, total_savings_y1 - propane_savings)

    # 100-year cash flow arrays (indices 0 to 100)
    years = np.arange(101)
    annual_savings = np.zeros(101, dtype=float)
    replacements = np.zeros(101, dtype=float)
    net_annual_cf = np.zeros(101, dtype=float)
    cumulative_cf = np.zeros(101, dtype=float)

    # Year 0 initial CAPEX
    cumulative_cf[0] = -net_capex

    # Calculate year-by-year from Year 1 to 100
    for y in range(1, 101):
        # 1. PV Module degradation and replacement reset
        # Replaced at end of year 25, 50, 75 (i.e. starts fresh in year 26, 51, 76)
        cycle_year = (y - 1) % 25
        pv_deg_factor = max(0.0, 1.0 - cycle_year * pv_degradation_annual)

        # Annual energy bill savings in year y
        s_elec = electricity_savings_y1 * pv_deg_factor if pv_capacity_kw > 0 else electricity_savings_y1
        s_prop = propane_savings
        annual_savings[y] = s_elec + s_prop

        # 2. Replacement costs incurred in year y
        rep_cost = 0.0
        # PV Module replacement (every 25 years: year 26, 51, 76)
        if pv_capacity_kw > 0 and y in (26, 51, 76):
            rep_cost += pv_turnkey_cost

        # Inverter replacement (every 12 years: year 13, 25, 37, 49, 61, 73, 85, 97)
        if pv_capacity_kw > 0 and y in (13, 25, 37, 49, 61, 73, 85, 97):
            rep_cost += inverter_replacement_cost

        # ESS battery replacement (every 10 years: year 11, 21, 31, 41, 51, 61, 71, 81, 91)
        if ess_capacity_kwh > 0 and y in (11, 21, 31, 41, 51, 61, 71, 81, 91):
            rep_cost += ess_replacement_cost

        # AWHP replacement (every 15 years: year 16, 31, 46, 61, 76, 91)
        if is_awhp and y in (16, 31, 46, 61, 76, 91):
            rep_cost += awhp_replacement_cost

        replacements[y] = rep_cost
        net_annual_cf[y] = annual_savings[y] - rep_cost
        cumulative_cf[y] = cumulative_cf[y - 1] + net_annual_cf[y]

    # Payback period determination
    # Case A: Year 1 gross annual savings <= 0
    if total_savings_y1 <= 0.0:
        payback_years = None
        payback_period_str = "불가능(연간 이득 없음)"
        reason_code = "NO_ANNUAL_SAVINGS"

    # Case B: Free/Zero CAPEX
    elif net_capex <= 0.0:
        payback_years = 0.0
        payback_period_str = "0.0"
        reason_code = "IMMEDIATE_ZERO_CAPEX"

    # Case C: Not recovered by Year 100
    elif cumulative_cf[100] < 0.0:
        payback_years = None
        payback_period_str = "불가능"
        reason_code = "NOT_RECOVERED_100Y"

    # Case D: Recovered and stays >= 0 through Year 100
    else:
        # Search backward from year 100 to find the last year where cum_cf was negative
        last_neg_year = None
        for y in range(100, -1, -1):
            if cumulative_cf[y] < 0.0:
                last_neg_year = y
                break

        if last_neg_year is None:
            payback_years = 0.0
            payback_period_str = "0.0"
            reason_code = "IMMEDIATE_PAYBACK"
        elif last_neg_year >= 100:
            payback_years = None
            payback_period_str = "불가능"
            reason_code = "NOT_RECOVERED_100Y"
        else:
            # Linear interpolation between last_neg_year and last_neg_year + 1
            y_neg = last_neg_year
            y_pos = last_neg_year + 1
            cf_neg = cumulative_cf[y_neg]
            cf_pos = cumulative_cf[y_pos]
            diff = cf_pos - cf_neg
            fraction = (-cf_neg / diff) if diff > 0 else 0.0
            fraction = max(0.0, min(1.0, fraction))
            payback_years = round(y_neg + fraction, 1)
            payback_period_str = f"{payback_years:.1f}"
            reason_code = "PAYBACK_RECOVERED"

    return {
        "payback_years": payback_years,
        "payback_period_str": payback_period_str,
        "reason_code": reason_code,
        "annual_savings_y1": round(total_savings_y1, 0),
        "cumulative_cashflow_100y": cumulative_cf.tolist(),
        "annual_savings_100y": annual_savings.tolist(),
        "replacements_100y": replacements.tolist(),
        "net_savings_25y": round(float(cumulative_cf[25]), 0),
        "net_savings_100y": round(float(cumulative_cf[100]), 0),
    }
