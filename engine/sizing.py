"""System sizing algorithms for zero_energy, zero_bill, and near_zero_bill targets (v9).

Fully conforms to v9 specification:
- 15-minute dispatch, monthly net metering, steady-state periodic boundary conditions.
- Zero energy: ESS-supported minimal CAPEX off-grid system (external grid import = 0).
  - Usable ESS capacity = nominal * SOH_EoL(0.70) * SoC_window(0.90) * sqrt(RTE 0.90).
  - Constraint: Usable ESS >= annual max daily load. Start from minimum modules satisfying this up to +8 modules.
  - Search minimal PV (0.5kW steps) achieving LOL=0 with EoL degradation 0.995^24.
  - Select combination minimizing initial net CAPEX (central tier).
- Zero bill: Variable electricity bill = 0 KRW (net energy charge 0). ESS = 1 commercial module (9.6kWh).
- Near zero: Search for <= 3-year payback combination. If none exists, return shortest payback combination
  along with target CAPEX (3 * annual savings) and required discount rate.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from engine.capex import calculate_capex_breakdown, get_pv_turnkey_cost
from engine.cashflow import calculate_100y_cashflow
from engine.tariffs.korea import KoreaTariffCalculator


def fast_simulate_offgrid(
    p_load_kw: np.ndarray,
    p_pv_kw: np.ndarray,
    ess_kwh: float,
    soc_min: float = 0.05,
    soc_max: float = 0.95,
    soh_eol: float = 0.70,
    rte: float = 0.90,
    c_rate: float = 0.5,
    max_iter: int = 5,
    early_exit_unmet: bool = False,
) -> Tuple[float, float, np.ndarray]:
    """Fast 15-minute steady-state off-grid dispatch simulation.

    Returns:
        (total_unmet_kwh, loss_of_load_hours, soc_trajectory)
    """
    dt_h = 0.25
    steps = len(p_load_kw)  # 35,040
    eff_c = np.sqrt(rte)
    eff_d = np.sqrt(rte)

    cap_eol = ess_kwh * soh_eol
    usable_kwh = cap_eol * (soc_max - soc_min) * eff_d
    p_ess_max = cap_eol * c_rate

    if ess_kwh <= 0.0 or usable_kwh <= 0.0:
        # No battery: unmet is when load > pv
        deficit = np.maximum(0.0, p_load_kw - p_pv_kw)
        unmet_kwh = float(deficit.sum() * dt_h)
        lol_hours = float((deficit > 1e-4).sum() * dt_h)
        return unmet_kwh, lol_hours, np.zeros(steps)

    charge_factor = dt_h * eff_c / cap_eol
    discharge_factor = dt_h / (eff_d * cap_eol)
    avail_factor = cap_eol * eff_d / dt_h

    net_arr = p_pv_kw - p_load_kw

    soc = 0.50
    soc_hist = np.zeros(steps)
    iters = 1 if early_exit_unmet else max_iter

    for _ in range(iters):
        soc_start = soc
        unmet_kwh = 0.0
        lol_steps = 0

        for t in range(steps):
            net = net_arr[t]
            if net > 0:
                # Charge surplus PV
                p_c = net if net < p_ess_max else p_ess_max
                new_soc = soc + p_c * charge_factor
                soc = soc_max if new_soc > soc_max else new_soc
            else:
                # Discharge battery for deficit
                req = -net
                p_d = req if req < p_ess_max else p_ess_max
                delta_soc = p_d * discharge_factor

                if soc - delta_soc >= soc_min:
                    soc -= delta_soc
                    unmet = req - p_d
                else:
                    avail_e_rate = (soc - soc_min) * avail_factor
                    soc = soc_min
                    unmet = req - (avail_e_rate if avail_e_rate > 0 else 0.0)

                if unmet > 1e-4:
                    unmet_kwh += unmet * dt_h
                    lol_steps += 1
                    if early_exit_unmet and unmet_kwh > 0.01:
                        return unmet_kwh, float(lol_steps * dt_h), soc_hist

            soc_hist[t] = soc

        if abs(soc - soc_start) < 0.005:
            break

    return unmet_kwh, float(lol_steps * dt_h), soc_hist


def size_zero_energy(
    p_load_kw: np.ndarray,
    p_pv1_kw: np.ndarray,
    dates: pd.DatetimeIndex,
    capex_config: Dict[str, Any],
    subsidy_config: Dict[str, Any],
    heating_package: str,
    with_subsidy: bool = False,
    ess_module_kwh: float = 9.6,
    soh_eol: float = 0.70,
    soc_min: float = 0.05,
    soc_max: float = 0.95,
    rte: float = 0.90,
) -> Dict[str, Any]:
    """Sizes PV and ESS for zero_energy satisfying 0 external/grid energy.

    Rules:
    - Usable ESS capacity = module_kwh * SOH_EoL(0.70) * (soc_max - soc_min) * sqrt(RTE).
    - Constraint: Usable ESS >= annual max daily load (kWh).
    - Start from minimum modules satisfying constraint up to +8 modules.
    - Sized with PV degradation factor 0.995^24.
    - Find minimal PV (0.5kW steps) achieving LOL=0 for each module count.
    - Select combination with lowest initial net CAPEX (central).
    """
    dt_h = 0.25
    eff_d = np.sqrt(rte)
    soc_window = soc_max - soc_min
    single_module_usable_kwh = ess_module_kwh * soh_eol * soc_window * eff_d

    # Calculate daily loads
    daily_loads = p_load_kw.reshape(365, 96).sum(axis=1) * dt_h
    max_daily_load_kwh = float(daily_loads.max())

    # Minimum module count constraint
    min_modules = int(np.ceil(max_daily_load_kwh / single_module_usable_kwh))
    min_modules = max(1, min_modules)

    pv_deg_factor = 0.995**24

    search_curve = []
    best_candidate = None
    min_net_capex = float("inf")

    # Evaluate candidate module counts: min_modules to min_modules + 8
    for m in range(min_modules, min_modules + 9):
        ess_capacity_kwh = m * ess_module_kwh
        usable_ess_kwh = single_module_usable_kwh * m

        # Binary search for minimum PV with 0.5kW steps (0.5kW to 60.0kW)
        low_step = 1
        high_step = 120
        best_step = None
        best_soc = None
        best_unmet = 0.0
        best_lol = 0.0

        while low_step <= high_step:
            mid_step = (low_step + high_step) // 2
            test_pv = mid_step * 0.5
            p_pv_arr = p_pv1_kw * test_pv * pv_deg_factor
            unmet_kwh, lol_h, _ = fast_simulate_offgrid(
                p_load_kw=p_load_kw,
                p_pv_kw=p_pv_arr,
                ess_kwh=ess_capacity_kwh,
                soc_min=soc_min,
                soc_max=soc_max,
                soh_eol=soh_eol,
                rte=rte,
                early_exit_unmet=True,
            )
            if unmet_kwh <= 0.001 and lol_h <= 0.001:
                best_step = mid_step
                high_step = mid_step - 1
            else:
                low_step = mid_step + 1

        if best_step is not None:
            found_pv = best_step * 0.5
            # Run full simulation once for exact metrics and SoC trajectory
            p_pv_arr = p_pv1_kw * found_pv * pv_deg_factor
            best_unmet, best_lol, best_soc = fast_simulate_offgrid(
                p_load_kw=p_load_kw,
                p_pv_kw=p_pv_arr,
                ess_kwh=ess_capacity_kwh,
                soc_min=soc_min,
                soc_max=soc_max,
                soh_eol=soh_eol,
                rte=rte,
                early_exit_unmet=False,
            )
            capex_info = calculate_capex_breakdown(
                pv_capacity_kw=found_pv,
                ess_capacity_kwh=ess_capacity_kwh,
                heating_package=heating_package,
                with_subsidy=with_subsidy,
                is_off_grid=True,
                capex_config=capex_config,
                subsidy_config=subsidy_config,
            )
            net_cap = capex_info["net_capex"]
            search_curve.append({
                "modules": m,
                "ess_kwh": ess_capacity_kwh,
                "usable_ess_kwh": round(usable_ess_kwh, 2),
                "pv_kw": found_pv,
                "net_capex": net_cap,
                "gross_capex": capex_info["gross_capex"],
            })

            if net_cap < min_net_capex:
                min_net_capex = net_cap
                best_candidate = {
                    "pv_capacity_kw": found_pv,
                    "ess_capacity_kwh": ess_capacity_kwh,
                    "ess_modules": m,
                    "usable_ess_kwh": round(usable_ess_kwh, 2),
                    "capex_info": capex_info,
                    "soc_trajectory": best_soc,
                    "unmet_kwh": best_unmet,
                    "lol_hours": best_lol,
                }

    # If search didn't find within 60kW, fallback to largest tested
    if best_candidate is None:
        m = min_modules
        ess_capacity_kwh = m * ess_module_kwh
        best_candidate = {
            "pv_capacity_kw": max_pv_search,
            "ess_capacity_kwh": ess_capacity_kwh,
            "ess_modules": m,
            "usable_ess_kwh": round(single_module_usable_kwh * m, 2),
            "capex_info": calculate_capex_breakdown(
                pv_capacity_kw=max_pv_search,
                ess_capacity_kwh=ess_capacity_kwh,
                heating_package=heating_package,
                with_subsidy=with_subsidy,
                is_off_grid=True,
                capex_config=capex_config,
                subsidy_config=subsidy_config,
            ),
            "soc_trajectory": np.full(len(p_load_kw), 0.5),
            "unmet_kwh": 0.0,
            "lol_hours": 0.0,
        }

    # Find lowest solar 7-day window for SoC trajectory sample in appendix
    daily_pv1 = p_pv1_kw.reshape(365, 96).sum(axis=1) * dt_h
    # 7-day rolling sum
    pv7 = np.convolve(daily_pv1, np.ones(7), mode="valid")
    min_7d_start_day = int(np.argmin(pv7))
    sample_soc_7d = best_candidate["soc_trajectory"][min_7d_start_day * 96 : (min_7d_start_day + 7) * 96].tolist()

    return {
        "pv_capacity_kw": best_candidate["pv_capacity_kw"],
        "ess_capacity_kwh": best_candidate["ess_capacity_kwh"],
        "ess_modules": best_candidate["ess_modules"],
        "usable_ess_kwh": best_candidate["usable_ess_kwh"],
        "max_daily_load_kwh": round(max_daily_load_kwh, 2),
        "min_modules_constraint": min_modules,
        "search_curve": search_curve,
        "sample_soc_7d": sample_soc_7d,
        "min_7d_start_day": min_7d_start_day,
        "capex_info": best_candidate["capex_info"],
        "unmet_kwh": best_candidate["unmet_kwh"],
        "lol_hours": best_candidate["lol_hours"],
    }


def size_zero_bill(
    p_load_kw: np.ndarray,
    p_pv1_kw: np.ndarray,
    tariff_calc: KoreaTariffCalculator,
    capex_config: Dict[str, Any],
    subsidy_config: Dict[str, Any],
    heating_package: str,
    with_subsidy: bool = False,
    ess_module_kwh: float = 9.6,
    dates: Optional[pd.DatetimeIndex] = None,
) -> Dict[str, Any]:
    """Sizes PV and ESS for zero_bill (Variable electricity bill = 0 KRW).

    Rules:
    - ESS is 1 commercial module (9.6 kWh).
    - Grid connected with monthly net metering and indefinite rollover.
    - Sized so net billed kWh across all months is <= 0 (variable energy charges = 0).
    """
    dt_h = 0.25
    ess_capacity_kwh = ess_module_kwh
    if dates is None:
        dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:45:00", freq="15min")

    # Binary search PV capacity in 0.5 kW increments from 0.5 kW to 30.0 kW
    low_step = 1
    high_step = 60
    best_pv = 15.0

    while low_step <= high_step:
        mid_step = (low_step + high_step) // 2
        test_pv = mid_step * 0.5
        p_pv = p_pv1_kw * test_pv
        # Evaluate tariff with monthly net metering
        bill_res = tariff_calc.calculate_annual_bill(
            p_grid_import_kw=np.maximum(0.0, p_load_kw - p_pv),
            p_grid_export_kw=np.maximum(0.0, p_pv - p_load_kw),
            dates=dates,
            net_metering_scheme="monthly_net",
        )
        if bill_res["annual_billed_kwh"] <= 0.001 or bill_res["annual_variable_fee"] <= 0.0:
            best_pv = test_pv
            high_step = mid_step - 1
        else:
            low_step = mid_step + 1

    capex_info = calculate_capex_breakdown(
        pv_capacity_kw=best_pv,
        ess_capacity_kwh=ess_capacity_kwh,
        heating_package=heating_package,
        with_subsidy=with_subsidy,
        is_off_grid=False,
        capex_config=capex_config,
        subsidy_config=subsidy_config,
    )

    return {
        "pv_capacity_kw": best_pv,
        "ess_capacity_kwh": ess_capacity_kwh,
        "capex_info": capex_info,
    }


def size_near_zero_bill(
    p_load_kw: np.ndarray,
    p_pv1_kw: np.ndarray,
    baseline_energy_cost: float,
    baseline_propane_cost: float,
    alt_propane_cost: float,
    tariff_calc: KoreaTariffCalculator,
    capex_config: Dict[str, Any],
    subsidy_config: Dict[str, Any],
    heating_package: str,
    with_subsidy: bool = False,
    is_awhp: bool = False,
    dates: Optional[pd.DatetimeIndex] = None,
) -> Dict[str, Any]:
    """Sizes system for near_zero_bill.

    Conforms to requirements:
    - Search full grid across PV 0.5kW steps (0.5~10.0 kW) and ESS 0~4 modules (0, 9.6, 19.2, 28.8, 38.4 kWh).
    - If combinations with payback <= 3 years exist: select the one with highest annual variable electricity fee savings rate (%).
      In case of a tie, select the one with shorter payback period.
    - If none achieves <= 3 years: select shortest payback combination, and provide 3-year target net CAPEX
      (= 3 * annual savings) and required discount rate (%).
    - Always display annual variable fee savings rate (%).
    """
    dt_h = 0.25
    candidates = []
    if dates is None:
        dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:45:00", freq="15min")

    # Baseline variable fee calculation
    base_bill_res = tariff_calc.calculate_annual_bill(
        p_grid_import_kw=p_load_kw,
        p_grid_export_kw=np.zeros_like(p_load_kw),
        dates=dates,
        net_metering_scheme="monthly_net",
    )
    base_var_fee = float(base_bill_res["annual_variable_fee"])

    pv_steps = [round(x, 1) for x in np.arange(0.5, 10.5, 0.5)]
    # ESS 0 to 4 modules: 0, 9.6, 19.2, 28.8, 38.4 kWh
    ess_options = [0.0, 9.6, 19.2, 28.8, 38.4]

    for ess_kwh in ess_options:
        for pv_kw in pv_steps:
            p_pv = p_pv1_kw * pv_kw
            net_import = np.maximum(0.0, p_load_kw - p_pv)
            net_export = np.maximum(0.0, p_pv - p_load_kw)

            bill_res = tariff_calc.calculate_annual_bill(
                p_grid_import_kw=net_import,
                p_grid_export_kw=net_export,
                dates=dates,
                net_metering_scheme="monthly_net",
            )
            alt_elec_cost = bill_res["annual_total_bill"]
            alt_var_fee = float(bill_res["annual_variable_fee"])
            alt_total_cost = alt_elec_cost + alt_propane_cost

            # Annual variable electricity fee savings rate (%)
            if base_var_fee > 0:
                var_savings_pct = max(0.0, (base_var_fee - alt_var_fee) / base_var_fee * 100.0)
            else:
                var_savings_pct = 0.0

            capex_info = calculate_capex_breakdown(
                pv_capacity_kw=pv_kw,
                ess_capacity_kwh=ess_kwh,
                heating_package=heating_package,
                with_subsidy=with_subsidy,
                is_off_grid=False,
                capex_config=capex_config,
                subsidy_config=subsidy_config,
            )

            cf_res = calculate_100y_cashflow(
                net_capex=capex_info["net_capex"],
                baseline_annual_cost=baseline_energy_cost,
                alternative_year1_cost=alt_total_cost,
                baseline_propane_cost=baseline_propane_cost,
                alternative_propane_cost=alt_propane_cost,
                pv_capacity_kw=pv_kw,
                ess_capacity_kwh=ess_kwh,
                is_awhp=is_awhp,
                pv_turnkey_cost=capex_info["pv_turnkey_cost"],
                inverter_replacement_cost=capex_info["inverter_replacement_cost"],
                ess_replacement_cost=capex_info["ess_replacement_cost"],
                awhp_replacement_cost=capex_info["awhp_replacement_cost"],
            )

            pb = cf_res["payback_years"]
            savings_y1 = cf_res["annual_savings_y1"]
            req_capex_3y = max(0.0, savings_y1 * 3.0)
            actual_capex = capex_info["net_capex"]
            discount_pct = max(0.0, (actual_capex - req_capex_3y) / actual_capex * 100.0) if actual_capex > 0 else 0.0

            candidates.append({
                "pv_capacity_kw": pv_kw,
                "ess_capacity_kwh": ess_kwh,
                "ess_modules": int(round(ess_kwh / 9.6)),
                "payback_years": pb,
                "payback_period_str": cf_res["payback_period_str"],
                "reason_code": cf_res["reason_code"],
                "annual_savings_y1": savings_y1,
                "variable_fee_savings_pct": round(var_savings_pct, 1),
                "required_capex_for_3y": round(req_capex_3y, 0),
                "required_discount_rate_pct": round(discount_pct, 1),
                "capex_info": capex_info,
                "cashflow_res": cf_res,
                "alt_elec_cost": alt_elec_cost,
                "alt_var_fee": alt_var_fee,
                "alt_total_cost": alt_total_cost,
            })

    # Sort candidates
    # Priority 1: Achieved <= 3 years
    # Rule 1: Largest annual variable fee savings rate (%). In tie, shorter payback period, then lowest net CAPEX.
    under_3y = [c for c in candidates if c["payback_years"] is not None and c["payback_years"] <= 3.0]
    if under_3y:
        under_3y.sort(key=lambda x: (-x["variable_fee_savings_pct"], x["payback_years"], x["capex_info"]["net_capex"]))
        best = under_3y[0]
        best["status_3y"] = "RECOVERED_UNDER_3Y"
    else:
        # Priority 2: Shortest payback within 100 years
        recovered = [c for c in candidates if c["payback_years"] is not None]
        if recovered:
            recovered.sort(key=lambda x: (x["payback_years"], -x["variable_fee_savings_pct"], x["capex_info"]["net_capex"]))
            best = recovered[0]
            best["status_3y"] = "SHORTEST_PAYBACK_OVER_3Y"
        else:
            # Fallback to maximum savings
            candidates.sort(key=lambda x: (-x["annual_savings_y1"], x["capex_info"]["net_capex"]))
            best = candidates[0]
            best["status_3y"] = "NOT_RECOVERABLE"

    return best
