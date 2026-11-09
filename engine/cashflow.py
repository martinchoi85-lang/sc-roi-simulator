"""25-year cash flow and payback period calculation."""

from typing import Dict, Any, Union
import numpy as np


def calculate_25y_cashflow(
    net_capex: float,
    baseline_annual_cost: float,
    alternative_year1_cost: float,
    baseline_propane_cost: float,
    alternative_propane_cost: float,
    ess_replacement_cost: float,
    inverter_replacement_cost: float,
    pv_degradation_annual: float = 0.005,
) -> Dict[str, Any]:
    """Calculates 25-year undiscounted cash flow, annual degradation, replacements, and payback.

    Args:
        net_capex: Initial net capital investment at Year 0 (KRW)
        baseline_annual_cost: Total Year 1 energy cost of baseline (electric + propane) (KRW)
        alternative_year1_cost: Total Year 1 energy cost of alternative (electric + propane) (KRW)
        baseline_propane_cost: Baseline propane cost (KRW)
        alternative_propane_cost: Alternative propane cost (KRW)
        ess_replacement_cost: Battery replacement cost incurred at Year 11 (KRW)
        inverter_replacement_cost: Inverter replacement cost incurred at Year 13 (KRW)
        pv_degradation_annual: PV degradation rate (default 0.005 = 0.5%/year)

    Returns:
        Dict containing:
        - 'payback_period_str': e.g. "8.4" or ">25"
        - 'payback_years': float value (or 999.0 if >25)
        - 'annual_savings_y1': Year 1 gross energy bill savings
        - 'cumulative_cashflow_25y': Array of cumulative cash flow for years 0 to 25
        - 'net_savings_25y': Net 25-year cumulative cash flow at year 25
    """
    total_savings_y1 = max(0.0, baseline_annual_cost - alternative_year1_cost)

    # Separate savings into propane component and electricity component
    propane_savings = max(0.0, baseline_propane_cost - alternative_propane_cost)
    electricity_savings_y1 = max(0.0, total_savings_y1 - propane_savings)

    years = np.arange(26)  # 0 to 25
    annual_cashflows = np.zeros(26, dtype=float)
    cumulative_cf = np.zeros(26, dtype=float)

    # Year 0: Outflow
    annual_cashflows[0] = -net_capex
    cumulative_cf[0] = -net_capex

    payback_years = 999.0
    payback_period_str = ">25"
    break_even_found = False

    for yr in range(1, 26):
        # PV degradation on electricity savings
        deg_factor = (1.0 - pv_degradation_annual) ** (yr - 1)
        yr_elec_savings = electricity_savings_y1 * deg_factor
        yr_savings = yr_elec_savings + propane_savings

        # Replacements
        replacements = 0.0
        if yr == 11:
            replacements += ess_replacement_cost
        if yr == 13:
            replacements += inverter_replacement_cost

        net_yr_cf = yr_savings - replacements
        annual_cashflows[yr] = net_yr_cf
        cumulative_cf[yr] = cumulative_cf[yr - 1] + net_yr_cf

        # Check for break-even
        if not break_even_found and cumulative_cf[yr] >= 0:
            # Linear interpolation within the year
            prev_cf = cumulative_cf[yr - 1]
            diff = cumulative_cf[yr] - prev_cf
            if diff > 1e-4:
                fractional = (-prev_cf) / diff
                payback_years = (yr - 1) + fractional
            else:
                payback_years = float(yr)

            payback_years = round(payback_years, 2)
            payback_period_str = str(payback_years)
            break_even_found = True

    return {
        "payback_period_str": payback_period_str,
        "payback_years": payback_years,
        "annual_savings_y1": round(total_savings_y1, 0),
        "cumulative_cashflow_25y": cumulative_cf,
        "net_savings_25y": round(cumulative_cf[25], 0),
    }

