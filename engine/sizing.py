"""System sizing algorithms for zero_energy, zero_bill, and near_zero_bill targets."""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from engine.ess import simulate_ess_dispatch, simulate_ess_dispatch_steady_state
from engine.tariffs.korea import KoreaTariffCalculator
from engine.capex import calculate_capex_breakdown, get_pv_turnkey_cost
from engine.cashflow import calculate_25y_cashflow


def size_zero_energy(
    p_load_100_kw: np.ndarray,
    all_occupancy_loads: List[np.ndarray],
    p_pv1_kw: np.ndarray,
    dates: pd.DatetimeIndex,
    house_config: Dict[str, Any],
    equipment_config: Dict[str, Any],
    capex_config: Dict[str, Any],
    design_margin: float = 1.0,
    ghi_arr: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Sizes PV and ESS for zero_energy satisfying 0 external/grid energy across all occupancies.

    Rules:
    - PV = max_d(daily_load / daily_pv1) over 365 days. The day creating this value is critical_day.
    - Performance baseline: PV 25-yr degradation 0.995^24, ESS usable capacity 70%.
    - ESS is integer multiple of 9.6 kWh modules, ceiling based on daily SoC cycle deficit / (DoD * sqrt(rte)).
    - Sized using 100% occupancy load, identical sizing applied across all 6 occupancy rates.
    - Annual 15-minute simulation in periodic steady-state (start SoC == end SoC). Surplus PV curtailed.
    - If any occupancy has unmet load > 0.001 kWh, increment PV by 0.5kW and ESS by 9.6kWh to find min-CAPEX combination.
    - Final loss_of_load_hours must be 0 across all cases.
    - Inverter capacity >= peak load kW including ESS discharge.
    """
    dt_h = 0.25
    deg_25 = 0.995**24
    ess_cfg = equipment_config["ess_system"]
    rte = float(ess_cfg.get("round_trip_efficiency", {}).get("value", 0.90) if isinstance(ess_cfg.get("round_trip_efficiency"), dict) else ess_cfg.get("round_trip_efficiency", 0.90))
    min_mod_kwh = float(equipment_config.get("ess_min_module_kwh", 9.6))

    # Daily sums of 100% load and 1kWp PV
    daily_loads_100 = np.sum(p_load_100_kw.reshape(365, 96), axis=1) * dt_h
    daily_pv1 = np.sum(p_pv1_kw.reshape(365, 96), axis=1) * dt_h
    daily_pv1_safe = np.maximum(0.01, daily_pv1)

    # 1. Critical Day Search (PV = max_d(load / pv1))
    ratios = daily_loads_100 / daily_pv1_safe
    crit_day_idx = int(np.argmax(ratios))
    crit_date_str = dates[crit_day_idx * 96].strftime("%Y-%m-%d")
    crit_day_num = crit_day_idx + 1

    crit_load_kwh = float(daily_loads_100[crit_day_idx])
    crit_pv1_kwh = float(daily_pv1[crit_day_idx])
    if ghi_arr is not None:
        daily_ghi = np.sum(ghi_arr.reshape(365, 96), axis=1) * dt_h / 1000.0
        crit_ghi_kwh_m2 = float(daily_ghi[crit_day_idx])
    else:
        crit_ghi_kwh_m2 = 0.2465

    raw_pv_req = (crit_load_kwh / crit_pv1_kwh) * float(design_margin)
    pv_init = float(np.ceil(raw_pv_req * 2.0) / 2.0)  # 0.5kW step

    # 2. ESS Initial Sizing based on Daily SoC cycle max deficit
    p_pv_init = pv_init * p_pv1_kw
    daily_deficits = np.sum(np.maximum(0.0, p_load_100_kw - p_pv_init).reshape(365, 96), axis=1) * dt_h
    max_daily_deficit = float(np.max(daily_deficits))

    # Usable DoD = 70%
    usable_dod = 0.70
    ess_req_kwh = max_daily_deficit / (usable_dod * np.sqrt(rte))
    n_modules_init = max(1, int(np.ceil(ess_req_kwh / min_mod_kwh)))
    ess_init = float(n_modules_init * min_mod_kwh)

    # 3. Old Peak-Day Method for Reference Comparison
    old_peak_day_idx = int(np.argmax(daily_loads_100))
    old_pv_cap = round(float(daily_loads_100[old_peak_day_idx] / daily_pv1_safe[old_peak_day_idx]), 2)
    mask_old = (dates.dayofyear.values - 1) == old_peak_day_idx
    old_peak_def = float(np.sum(np.maximum(0.0, p_load_100_kw[mask_old] - old_pv_cap * p_pv1_kw[mask_old])) * dt_h)
    old_ess_cap = max(5.0, round(old_peak_def / (0.90 * np.sqrt(rte)), 2))

    # Simulation config under 25-yr performance baseline (DoD 70%, usable SoC [0.15, 0.85])
    sim_ess_cfg = dict(ess_cfg)
    sim_ess_cfg["usable_dod"] = 0.70
    sim_ess_cfg["soc_min"] = 0.15
    sim_ess_cfg["soc_max"] = 0.85

    # Evaluate old method shortfall on 100% load
    old_disp = simulate_ess_dispatch_steady_state(
        p_pv_kw=old_pv_cap * deg_25 * p_pv1_kw,
        p_load_kw=p_load_100_kw,
        battery_capacity_kwh=old_ess_cap,
        ess_config=sim_ess_cfg,
        is_off_grid=True,
        dt_hours=dt_h,
    )
    old_lol_hours = float(old_disp["loss_of_load_hours"])
    old_unmet_kwh = float(old_disp["total_unmet_kwh"])

    # 4. Search Minimal CAPEX Combination with LOL = 0 across ALL 6 occupancies
    rte_sqrt = np.sqrt(rte)

    def fast_simulate_offgrid(p_pv_eff: np.ndarray, p_load: np.ndarray, ess_c: float) -> Tuple[float, float]:
        """Fast 2-pass periodic steady-state offgrid simulation."""
        soc = 0.50
        n = len(p_pv_eff)
        p_unmet = np.zeros(n, dtype=float)
        for _ in range(2):
            cur_stored = ess_c * soc
            p_unmet.fill(0.0)
            for i in range(n):
                net = p_pv_eff[i] - p_load[i]
                if net > 0:
                    room = 0.85 * ess_c - cur_stored
                    chg = min(net, ess_c * 0.50, max(0.0, room / (rte_sqrt * dt_h)))
                    cur_stored += chg * rte_sqrt * dt_h
                else:
                    deficit = -net
                    avail = cur_stored - 0.15 * ess_c
                    dis = min(deficit, ess_c * 0.50, max(0.0, (avail * rte_sqrt) / dt_h))
                    cur_stored -= (dis / rte_sqrt) * dt_h
                    rem = deficit - dis
                    if rem > 1e-5:
                        p_unmet[i] = rem
            soc = cur_stored / ess_c
        return float(np.sum(p_unmet) * dt_h), float(np.sum(p_unmet > 0) * dt_h)

    # Sort loads so heaviest load (100% occupancy) is tested first for early pruning
    sorted_loads = sorted(all_occupancy_loads, key=lambda x: float(np.sum(x)), reverse=True)

    def evaluate_combination(pv_c: float, ess_c: float) -> Tuple[float, float]:
        """Returns (max_unmet_kwh, max_lol_hours) across all 6 occupancy profiles with early exit."""
        p_pv_eff = pv_c * deg_25 * p_pv1_kw
        max_u = 0.0
        max_lol = 0.0
        for pl in sorted_loads:
            u, lol = fast_simulate_offgrid(p_pv_eff, pl, ess_c)
            if u > max_u:
                max_u = u
            if lol > max_lol:
                max_lol = lol
            if max_u > 0.001:
                return max_u, max_lol
        return max_u, max_lol

    # Check initial sizing
    init_unmet, init_lol = evaluate_combination(pv_init, ess_init)

    # Build candidates sorted strictly by Central CAPEX
    candidates = []
    ess_unit_cfg = capex_config.get("ess_system", {}).get("unit_cost_per_kwh", {}).get("central", {})
    ess_unit_central = float(ess_unit_cfg.get("value", 1775200.0) if isinstance(ess_unit_cfg, dict) else (ess_unit_cfg or 1775200.0))
    for m in range(0, 8):
        ess_c = ess_init + m * min_mod_kwh
        for s in range(0, 21):
            pv_c = pv_init + s * 0.5
            cost = get_pv_turnkey_cost(pv_c, capex_config, tier="central") + ess_c * ess_unit_central
            candidates.append((cost, pv_c, ess_c))
    candidates.sort(key=lambda x: x[0])

    feasible_candidates = []
    for cost, pv_c, ess_c in candidates:
        u, lol = evaluate_combination(pv_c, ess_c)
        if u <= 0.001 and lol == 0.0:
            feasible_candidates.append({
                "pv_kw": pv_c,
                "ess_kwh": ess_c,
                "capex_central_krw": cost,
                "unmet_kwh": u,
                "lol_hours": lol,
            })

    if feasible_candidates:
        best_pv = feasible_candidates[0]["pv_kw"]
        best_ess = feasible_candidates[0]["ess_kwh"]
        min_capex_val = feasible_candidates[0]["capex_central_krw"]
    else:
        best_pv = pv_init
        best_ess = ess_init
        min_capex_val = get_pv_turnkey_cost(best_pv, capex_config, tier="central") + best_ess * ess_unit_central

    # 5. Required Inverter Capacity (Peak load kW + ESS discharge capacity)
    peak_load_kw = float(np.max(p_load_100_kw))
    inverter_required_kw = round(max(3.0, peak_load_kw), 1)

    # 6. Final verification on optimal combination
    final_max_unmet, final_max_lol = evaluate_combination(best_pv, best_ess)

    # Top 5 feasible combinations
    top5 = feasible_candidates[:5]
    top_entries = {}
    for idx in range(5):
        rank = idx + 1
        if idx < len(top5):
            top_entries[f"top{rank}_pv_kw"] = top5[idx]["pv_kw"]
            top_entries[f"top{rank}_ess_kwh"] = top5[idx]["ess_kwh"]
            top_entries[f"top{rank}_capex_krw"] = top5[idx]["capex_central_krw"]
        else:
            top_entries[f"top{rank}_pv_kw"] = None
            top_entries[f"top{rank}_ess_kwh"] = None
            top_entries[f"top{rank}_capex_krw"] = None

    # Reference data for zero_energy_reference.csv
    reference_data = {
        "critical_day_date": crit_date_str,
        "critical_day_number": crit_day_num,
        "critical_day_load_kwh": round(crit_load_kwh, 2),
        "critical_day_pv1_kwh": round(crit_pv1_kwh, 2),
        "critical_day_ghi_kwh_m2": round(crit_ghi_kwh_m2, 2),
        "initial_pv_kw": round(pv_init, 2),
        "initial_ess_kwh": round(ess_init, 2),
        "initial_unmet_kwh": round(init_unmet, 4),
        "optimal_pv_kw": round(best_pv, 2),
        "optimal_ess_kwh": round(best_ess, 2),
        "inverter_required_kw": inverter_required_kw,
        "final_unmet_kwh": round(final_max_unmet, 6),
        "final_loss_of_load_hours": round(final_max_lol, 2),
        "min_capex_central_krw": round(min_capex_val, 0),
        "grid_candidates_count": len(candidates),
        "feasible_candidates_count": len(feasible_candidates),
        "old_method_pv_kw": round(old_pv_cap, 2),
        "old_method_ess_kwh": round(old_ess_cap, 2),
        "old_method_lol_hours": round(old_lol_hours, 1),
        "old_method_unmet_kwh": round(old_unmet_kwh, 2),
    }
    reference_data.update(top_entries)

    return {
        "pv_capacity_kw": round(best_pv, 2),
        "pv_capacity_bol_kw": round(best_pv, 2),
        "pv_capacity_tmy_kw": round(best_pv, 2),
        "pv_capacity_month_avg_kw": round(best_pv, 2),
        "pv_effective_25y_kw": round(best_pv * deg_25, 2),
        "ess_capacity_kwh": round(best_ess, 2),
        "ess_capacity_bol_kwh": round(best_ess, 2),
        "ess_usable_kwh": round(best_ess * usable_dod, 2),
        "sizing_status": "optimal" if final_max_unmet <= 0.001 else "warning_unmet",
        "critical_day": crit_date_str,
        "critical_day_number": crit_day_num,
        "critical_day_load_kwh": round(crit_load_kwh, 2),
        "critical_day_pv1_kwh": round(crit_pv1_kwh, 2),
        "inverter_required_kw": inverter_required_kw,
        "reference_data": reference_data,
        "final_max_unmet_kwh": final_max_unmet,
    }


def size_zero_bill(
    p_load_kw: np.ndarray,
    p_pv1_kw: np.ndarray,
    dates: pd.DatetimeIndex,
    house_config: Dict[str, Any],
    equipment_config: Dict[str, Any],
    tariff_calculator: KoreaTariffCalculator,
    net_metering_scheme: str = "monthly_net",
) -> Dict[str, Any]:
    """Sizes minimum PV capacity to achieve zero variable electricity bill with 1 ESS module (9.6kWh)."""
    dt_h = 0.25
    ess_cfg = equipment_config["ess_system"]
    min_ess_kwh = float(equipment_config.get("ess_min_module_kwh", 9.6))

    search_grid = np.arange(0.1, 25.05, 0.05)
    chosen_pv = search_grid[-1]
    chosen_dispatch = None
    chosen_bill = None

    for pv_cand in search_grid:
        p_pv = pv_cand * p_pv1_kw
        disp = simulate_ess_dispatch(
            p_pv, p_load_kw, min_ess_kwh, ess_cfg, is_off_grid=False, dt_hours=dt_h
        )
        bill = tariff_calculator.calculate_annual_bill(
            disp["p_grid_import_kw"], disp["p_grid_export_kw"], dates, net_metering_scheme
        )

        if bill["annual_billed_kwh"] <= 0.01 or bill["annual_variable_fee"] <= 0.1:
            chosen_pv = pv_cand
            chosen_dispatch = disp
            chosen_bill = bill
            break

    if chosen_dispatch is None:
        p_pv = chosen_pv * p_pv1_kw
        chosen_dispatch = simulate_ess_dispatch(
            p_pv, p_load_kw, min_ess_kwh, ess_cfg, is_off_grid=False, dt_hours=dt_h
        )
        chosen_bill = tariff_calculator.calculate_annual_bill(
            chosen_dispatch["p_grid_import_kw"], chosen_dispatch["p_grid_export_kw"], dates, net_metering_scheme
        )

    pv_size = round(chosen_pv, 2)
    peak_load = float(np.max(p_load_kw))

    return {
        "pv_capacity_kw": pv_size,
        "pv_capacity_bol_kw": pv_size,
        "pv_capacity_tmy_kw": pv_size,
        "pv_capacity_month_avg_kw": pv_size,
        "ess_capacity_kwh": min_ess_kwh,
        "ess_capacity_bol_kwh": min_ess_kwh,
        "sizing_status": "optimal",
        "inverter_required_kw": round(max(3.0, peak_load), 1),
        "dispatch": chosen_dispatch,
        "bill": chosen_bill,
    }


def size_near_zero_bill(
    p_load_kw: np.ndarray,
    p_pv1_kw: np.ndarray,
    dates: pd.DatetimeIndex,
    house_config: Dict[str, Any],
    equipment_config: Dict[str, Any],
    capex_config: Dict[str, Any],
    subsidy_config: Dict[str, Any],
    tariff_calculator: KoreaTariffCalculator,
    heating_package: str,
    with_subsidy: bool,
    baseline_annual_cost: float,
    baseline_propane_cost: float,
    alternative_propane_cost: float,
    net_metering_scheme: str = "monthly_net",
) -> Dict[str, Any]:
    """Searches PV in 0.5 kW steps for near_zero_bill target with 1 ESS module (9.6kWh)."""
    dt_h = 0.25
    ess_cfg = equipment_config["ess_system"]
    min_ess_kwh = float(equipment_config.get("ess_min_module_kwh", 9.6))

    search_steps = np.arange(0.5, 15.5, 0.5)

    valid_solutions = []
    all_evaluations = []

    for pv_cand in search_steps:
        p_pv = pv_cand * p_pv1_kw
        disp = simulate_ess_dispatch(
            p_pv, p_load_kw, min_ess_kwh, ess_cfg, is_off_grid=False, dt_hours=dt_h
        )
        bill = tariff_calculator.calculate_annual_bill(
            disp["p_grid_import_kw"], disp["p_grid_export_kw"], dates, net_metering_scheme
        )

        max_imp_kw = float(np.max(disp["p_grid_import_kw"]))
        capex_info = calculate_capex_breakdown(
            pv_capacity_kw=pv_cand,
            ess_capacity_kwh=min_ess_kwh,
            heating_package=heating_package,
            with_subsidy=with_subsidy,
            is_off_grid=False,
            capex_config=capex_config,
            subsidy_config=subsidy_config,
            max_import_kw=max_imp_kw,
            capex_basis="full",
        )

        alt_y1_cost = bill["annual_total_bill"] + alternative_propane_cost
        cf = calculate_25y_cashflow(
            net_capex=capex_info["net_capex"],
            baseline_annual_cost=baseline_annual_cost,
            alternative_year1_cost=alt_y1_cost,
            baseline_propane_cost=baseline_propane_cost,
            alternative_propane_cost=alternative_propane_cost,
            ess_replacement_cost=capex_info["ess_replacement_cost"],
            inverter_replacement_cost=capex_info["inverter_replacement_cost"],
        )

        eval_data = {
            "pv_cand": pv_cand,
            "payback_years": cf["payback_years"],
            "variable_fee": bill["annual_variable_fee"],
            "dispatch": disp,
            "bill": bill,
            "capex_info": capex_info,
            "cashflow": cf,
        }
        all_evaluations.append(eval_data)

        if cf["payback_years"] <= 3.0:
            valid_solutions.append(eval_data)

    peak_load = float(np.max(p_load_kw))
    inv_req = round(max(3.0, peak_load), 1)

    if valid_solutions:
        valid_solutions.sort(key=lambda x: (x["variable_fee"], x["payback_years"]))
        chosen = valid_solutions[0]
        pv_size = chosen["pv_cand"]

        return {
            "pv_capacity_kw": round(pv_size, 2),
            "pv_capacity_bol_kw": round(pv_size, 2),
            "pv_capacity_tmy_kw": round(pv_size, 2),
            "pv_capacity_month_avg_kw": round(pv_size, 2),
            "ess_capacity_kwh": min_ess_kwh,
            "ess_capacity_bol_kwh": min_ess_kwh,
            "sizing_status": "optimal",
            "min_payback_years": chosen["payback_years"],
            "target_capex_for_3y": chosen["capex_info"]["net_capex"],
            "inverter_required_kw": inv_req,
            "dispatch": chosen["dispatch"],
            "bill": chosen["bill"],
        }
    else:
        all_evaluations.sort(key=lambda x: x["payback_years"])
        best = all_evaluations[0]
        pv_size = best["pv_cand"]
        year1_savings = best["cashflow"]["annual_savings_y1"]
        target_capex_3y = round(year1_savings * 3.0, 0)

        return {
            "pv_capacity_kw": round(pv_size, 2),
            "pv_capacity_bol_kw": round(pv_size, 2),
            "pv_capacity_tmy_kw": round(pv_size, 2),
            "pv_capacity_month_avg_kw": round(pv_size, 2),
            "ess_capacity_kwh": min_ess_kwh,
            "ess_capacity_bol_kwh": min_ess_kwh,
            "sizing_status": "no_solution",
            "min_payback_years": best["payback_years"],
            "target_capex_for_3y": target_capex_3y,
            "inverter_required_kw": inv_req,
            "dispatch": best["dispatch"],
            "bill": best["bill"],
        }
