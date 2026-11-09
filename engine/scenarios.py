"""Full scenario execution runner across the 432 parameter combinations."""

from typing import Dict, Any, List, Tuple
from pathlib import Path
import numpy as np
import pandas as pd

from engine.weather import load_weather_data
from engine.occupancy import generate_occupancy_calendar
from engine.thermal_5r1c import simulate_thermal_5r1c
from engine.dhw import calculate_dhw_load
from engine.ev import calculate_ev_load
from engine.appliance_load import calculate_appliance_load
from engine.heat_pump import simulate_hvac_and_dhw
from engine.pv import simulate_pv_generation_1kwp
from engine.ess import simulate_ess_dispatch, simulate_ess_dispatch_steady_state
from engine.tariffs.korea import KoreaTariffCalculator
from engine.capex import calculate_capex_breakdown
from engine.cashflow import calculate_25y_cashflow
from engine.sizing import size_zero_energy, size_zero_bill, size_near_zero_bill


def run_all_scenarios(
    config_values: Dict[str, Any],
    weather_df: pd.DataFrame,
    placeholders_list: List[str] = None,
    unverifieds_list: List[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Runs all 432 scenarios and returns results, DUO Max incremental, profiles, and verification data."""
    if placeholders_list is None:
        placeholders_list = []
    if unverifieds_list is None:
        unverifieds_list = []

    country_cfg = config_values["country"]
    houses_cfg = config_values["houses"]
    tariff_cfg = config_values["tariff"]
    capex_cfg = config_values["capex"]
    subsidy_cfg = config_values["subsidy"]
    load_cfg = config_values["load"]
    equip_cfg = config_values["equipment"]

    dates = pd.DatetimeIndex(weather_df["timestamp"])
    dt_h = 0.25
    design_margin = float(country_cfg.get("design_margin", 1.0))
    deg_25 = 0.995**24

    lat = float(country_cfg["latitude"])
    lon = float(country_cfg["longitude"])
    tz = str(country_cfg.get("timezone", "Asia/Seoul"))
    p_pv1_kw = simulate_pv_generation_1kwp(
        weather_df, lat, lon, tilt=25.0, azimuth=180.0, timezone=tz, pv_equipment_config=equip_cfg["pv_system"]
    )

    tariff_calc = KoreaTariffCalculator(tariff_cfg)
    net_metering_scheme = str(tariff_cfg.get("net_metering_scheme", "monthly_net"))

    peak_months = [int(m) for m in load_cfg.get("peak_summer_season_months", [7, 8])]
    if "peak_fall_season_months" in load_cfg:
        peak_months.extend([int(m) for m in load_cfg["peak_fall_season_months"]])

    axes = country_cfg["scenario_axes"]
    house_models = axes["house_models"]
    heating_packages = axes["heating_packages"]
    ev_options = [int(v) for v in axes["ev_options"]]
    occupancy_rates = [float(v) for v in axes["occupancy_rates"]]
    target_models = axes["target_models"]
    subsidy_options = [bool(v) for v in axes["subsidy_options"]]

    # Phase 1: Pre-compute the 72 unique load profiles
    print("Pre-computing 72 load profiles across houses, heating packages, EVs, and occupancies...")
    load_cache = {}

    for h_name in house_models:
        h_cfg = houses_cfg[h_name]
        occupants = int(h_cfg["occupants"])

        for heat_pkg in heating_packages:
            for ev_opt in ev_options:
                for occ_rate in occupancy_rates:
                    is_occ_day, occ_presence = generate_occupancy_calendar(
                        occ_rate, dates, peak_months=peak_months, forced_peak_day=None
                    )

                    p_app_kw, internal_heat_w = calculate_appliance_load(occupants, is_occ_day, load_cfg, house_config=h_cfg)
                    q_dhw_kw = calculate_dhw_load(occupants, is_occ_day, load_cfg)
                    t_in, q_heat_kw, q_cool_kw = simulate_thermal_5r1c(
                        h_cfg, weather_df["temp_air"].values, weather_df["ghi"].values,
                        occ_presence, internal_heat_w, is_occ_day
                    )

                    p_ev_kw = calculate_ev_load(ev_opt, occ_rate, is_occ_day, load_cfg)
                    hvac_res = simulate_hvac_and_dhw(
                        heat_pkg, q_heat_kw, q_cool_kw, q_dhw_kw,
                        weather_df["temp_air"].values, equip_cfg, tariff_cfg
                    )

                    total_p_load_kw = p_app_kw + p_ev_kw + hvac_res["p_hvac_kw"]

                    key = (h_name, occ_rate, ev_opt, heat_pkg)
                    load_cache[key] = {
                        "p_load_kw": total_p_load_kw,
                        "p_app_kw": p_app_kw,
                        "p_ev_kw": p_ev_kw,
                        "p_hvac_kw": hvac_res["p_hvac_kw"],
                        "propane_kwh": hvac_res["propane_kwh"],
                        "propane_kg": hvac_res["propane_kg"],
                        "propane_cost": hvac_res["propane_cost"],
                        "backup_heater_hours": hvac_res["backup_heater_hours"],
                        "backup_heater_kwh": hvac_res["backup_heater_kwh"],
                        "annual_awhp_actual_kwh": hvac_res["annual_awhp_actual_kwh"],
                        "is_occ_day": is_occ_day,
                    }

    # Phase 2: Compute Zero-Energy sizing for the 12 combinations (House x Heat x EV)
    print("Sizing 12 zero_energy configurations (365-day critical_day search & steady-state LOL=0)...")
    zero_energy_sizings = {}
    zero_energy_references = {}

    for h_name in house_models:
        h_cfg = houses_cfg[h_name]
        for heat_pkg in heating_packages:
            for ev_opt in ev_options:
                p_load_100 = load_cache[(h_name, 1.00, ev_opt, heat_pkg)]["p_load_kw"]
                all_occ_loads = [
                    load_cache[(h_name, oc, ev_opt, heat_pkg)]["p_load_kw"] for oc in occupancy_rates
                ]

                ze_res = size_zero_energy(
                    p_load_100_kw=p_load_100,
                    all_occupancy_loads=all_occ_loads,
                    p_pv1_kw=p_pv1_kw,
                    dates=dates,
                    house_config=h_cfg,
                    equipment_config=equip_cfg,
                    capex_config=capex_cfg,
                    design_margin=design_margin,
                    ghi_arr=weather_df["ghi"].values,
                )
                key = (h_name, heat_pkg, ev_opt)
                zero_energy_sizings[key] = ze_res
                zero_energy_references[key] = ze_res["reference_data"]

    # Phase 3: Compute Baseline costs (Gas Boiler + Grid electricity)
    baseline_cache = {}
    for h_name in house_models:
        for occ_rate in occupancy_rates:
            for ev_opt in ev_options:
                gb_data = load_cache[(h_name, occ_rate, ev_opt, "PV+ESS+가스보일러")]
                p_load_gb = gb_data["p_load_kw"]
                gb_propane_cost = gb_data["propane_cost"]

                disp_gb = simulate_ess_dispatch(
                    np.zeros_like(p_load_gb), p_load_gb, 0.0,
                    equip_cfg["ess_system"], is_off_grid=False, dt_hours=dt_h
                )
                bill_gb = tariff_calc.calculate_annual_bill(
                    disp_gb["p_grid_import_kw"], disp_gb["p_grid_export_kw"], dates, net_metering_scheme
                )
                base_total_cost = bill_gb["annual_total_bill"] + gb_propane_cost

                baseline_cache[(h_name, occ_rate, ev_opt)] = {
                    "baseline_electric_bill": bill_gb["annual_total_bill"],
                    "baseline_propane_cost": gb_propane_cost,
                    "baseline_total_cost": base_total_cost,
                }

    # Incremental baseline for DUO Max 45 (AWHP + 5kW PV)
    duo_incremental_base_cache = {}
    if "DUO Max 45" in house_models:
        for occ_rate in occupancy_rates:
            for ev_opt in ev_options:
                awhp_data = load_cache[("DUO Max 45", occ_rate, ev_opt, "PV+ESS+AWHP")]
                p_load_awhp = awhp_data["p_load_kw"]
                p_pv_5kw = 5.0 * p_pv1_kw
                disp_5kw = simulate_ess_dispatch(
                    p_pv_5kw, p_load_awhp, 0.0, equip_cfg["ess_system"], is_off_grid=False, dt_hours=dt_h
                )
                bill_5kw = tariff_calc.calculate_annual_bill(
                    disp_5kw["p_grid_import_kw"], disp_5kw["p_grid_export_kw"], dates, net_metering_scheme
                )
                duo_incremental_base_cache[(occ_rate, ev_opt)] = {
                    "base_electric_bill": bill_5kw["annual_total_bill"],
                    "base_total_cost": bill_5kw["annual_total_bill"],
                }

    print("Evaluating 432 scenarios + DUO Max incremental (AWHP 72 rows)...")
    results = []
    duo_incremental_results = []
    saved_profiles = {}
    scenario_id = 1
    duo_inc_id = 1

    placeholder_str = "; ".join(placeholders_list)
    unverified_str = "; ".join(unverifieds_list)

    peak_import_kw_list = []

    for h_name in house_models:
        h_cfg = houses_cfg[h_name]
        for heat_pkg in heating_packages:
            for ev_opt in ev_options:
                ze_sizing = zero_energy_sizings[(h_name, heat_pkg, ev_opt)]

                for occ_rate in occupancy_rates:
                    load_data = load_cache[(h_name, occ_rate, ev_opt, heat_pkg)]
                    p_load_kw = load_data["p_load_kw"]
                    alt_propane_cost = load_data["propane_cost"]

                    base_info = baseline_cache[(h_name, occ_rate, ev_opt)]
                    base_total_cost = base_info["baseline_total_cost"]
                    base_propane_cost = base_info["baseline_propane_cost"]

                    for target_m in target_models:
                        for with_sub in subsidy_options:
                            is_off_grid = (target_m == "zero_energy")
                            if "가스보일러" in heat_pkg:
                                external_energy = "propane (전력 기준, 프로판 별도)" if target_m == "zero_energy" else "propane"
                            else:
                                external_energy = "none"

                            if target_m == "zero_energy":
                                size_res = ze_sizing
                                pv_cap = size_res["pv_capacity_kw"]
                                ess_cap = size_res["ess_capacity_kwh"]

                                # Periodic steady-state dispatch under 25-yr performance baseline
                                sim_ess_cfg = dict(equip_cfg["ess_system"])
                                sim_ess_cfg["usable_dod"] = 0.70
                                sim_ess_cfg["soc_min"] = 0.15
                                sim_ess_cfg["soc_max"] = 0.85

                                p_pv_ze = pv_cap * deg_25 * p_pv1_kw
                                disp_ze = simulate_ess_dispatch_steady_state(
                                    p_pv_ze, p_load_kw, ess_cap,
                                    sim_ess_cfg, is_off_grid=True, dt_hours=dt_h
                                )
                                loss_of_load_hrs = round(disp_ze["loss_of_load_hours"], 1)

                                bill_res = {
                                    "annual_total_bill": 0.0,
                                    "annual_base_fee": 0.0,
                                    "annual_variable_fee": 0.0,
                                    "annual_vat_and_fund": 0.0,
                                    "annual_billed_kwh": 0.0,
                                }
                                dispatch_res = disp_ze

                            elif target_m == "zero_bill":
                                size_res = size_zero_bill(
                                    p_load_kw, p_pv1_kw, dates, h_cfg, equip_cfg,
                                    tariff_calc, net_metering_scheme
                                )
                                pv_cap = size_res["pv_capacity_kw"]
                                ess_cap = size_res["ess_capacity_kwh"]
                                bill_res = size_res["bill"]
                                dispatch_res = size_res["dispatch"]
                                loss_of_load_hrs = 0.0

                            elif target_m == "near_zero_bill":
                                size_res = size_near_zero_bill(
                                    p_load_kw, p_pv1_kw, dates, h_cfg, equip_cfg,
                                    capex_cfg, subsidy_cfg, tariff_calc, heat_pkg, with_sub,
                                    baseline_annual_cost=base_total_cost,
                                    baseline_propane_cost=base_propane_cost,
                                    alternative_propane_cost=alt_propane_cost,
                                    net_metering_scheme=net_metering_scheme,
                                )
                                pv_cap = size_res["pv_capacity_kw"]
                                ess_cap = size_res["ess_capacity_kwh"]
                                bill_res = size_res["bill"]
                                dispatch_res = size_res["dispatch"]
                                loss_of_load_hrs = 0.0

                            max_imp_kw = float(np.max(dispatch_res["p_grid_import_kw"])) if not is_off_grid else 0.0
                            peak_import_kw_list.append((max_imp_kw, h_name, heat_pkg, ev_opt, occ_rate))

                            inverter_req_kw = size_res.get("inverter_required_kw", round(max(3.0, float(np.max(p_load_kw))), 1))

                            # Granular CAPEX breakdown across Low / Central / High tiers
                            capex_info = calculate_capex_breakdown(
                                pv_capacity_kw=pv_cap,
                                ess_capacity_kwh=ess_cap,
                                heating_package=heat_pkg,
                                with_subsidy=with_sub,
                                is_off_grid=is_off_grid,
                                capex_config=capex_cfg,
                                subsidy_config=subsidy_cfg,
                                max_import_kw=max_imp_kw,
                                capex_basis="full",
                            )

                            alt_total_cost = bill_res["annual_total_bill"] + alt_propane_cost

                            # Cashflow for Low, Central, High
                            cf_central = calculate_25y_cashflow(
                                net_capex=capex_info["net_capex_central"],
                                baseline_annual_cost=base_total_cost,
                                alternative_year1_cost=alt_total_cost,
                                baseline_propane_cost=base_propane_cost,
                                alternative_propane_cost=alt_propane_cost,
                                ess_replacement_cost=capex_info["ess_replacement_cost"],
                                inverter_replacement_cost=capex_info["inverter_replacement_cost"],
                                pv_degradation_annual=float(equip_cfg["pv_system"]["annual_degradation_rate"]),
                            )
                            cf_res = cf_central

                            cf_low = calculate_25y_cashflow(
                                net_capex=capex_info["net_capex_low"],
                                baseline_annual_cost=base_total_cost,
                                alternative_year1_cost=alt_total_cost,
                                baseline_propane_cost=base_propane_cost,
                                alternative_propane_cost=alt_propane_cost,
                                ess_replacement_cost=capex_info["ess_replacement_cost"],
                                inverter_replacement_cost=capex_info["inverter_replacement_cost"],
                                pv_degradation_annual=float(equip_cfg["pv_system"]["annual_degradation_rate"]),
                            )

                            cf_high = calculate_25y_cashflow(
                                net_capex=capex_info["net_capex_high"],
                                baseline_annual_cost=base_total_cost,
                                alternative_year1_cost=alt_total_cost,
                                baseline_propane_cost=base_propane_cost,
                                alternative_propane_cost=alt_propane_cost,
                                ess_replacement_cost=capex_info["ess_replacement_cost"],
                                inverter_replacement_cost=capex_info["inverter_replacement_cost"],
                                pv_degradation_annual=float(equip_cfg["pv_system"]["annual_degradation_rate"]),
                            )

                            # AWHP 70% Subsidy Sensitivity Cash Flow
                            cf_awhp70 = calculate_25y_cashflow(
                                net_capex=capex_info["net_capex_awhp70"],
                                baseline_annual_cost=base_total_cost,
                                alternative_year1_cost=alt_total_cost,
                                baseline_propane_cost=base_propane_cost,
                                alternative_propane_cost=alt_propane_cost,
                                ess_replacement_cost=capex_info["ess_replacement_cost"],
                                inverter_replacement_cost=capex_info["inverter_replacement_cost"],
                                pv_degradation_annual=float(equip_cfg["pv_system"]["annual_degradation_rate"]),
                            )

                            target_capex_3y = size_res.get("target_capex_for_3y", capex_info["net_capex"])
                            min_payback_val = size_res.get("min_payback_years", cf_res["payback_years"])

                            row = {
                                "scenario_id": scenario_id,
                                "house_model": h_name,
                                "floor_area_m2": float(h_cfg["floor_area"]),
                                "heating_package": heat_pkg,
                                "external_energy": external_energy,
                                "ev_count": ev_opt,
                                "occupancy_rate": occ_rate,
                                "target_model": target_m,
                                "subsidy_applied": with_sub,
                                "capex_basis": "full",
                                "pv_capacity_kw": pv_cap,
                                "pv_capacity_bol_kw": size_res.get("pv_capacity_bol_kw", pv_cap),
                                "pv_capacity_tmy_kw": size_res.get("pv_capacity_tmy_kw", pv_cap),
                                "pv_capacity_month_avg_kw": size_res.get("pv_capacity_month_avg_kw", pv_cap),
                                "pv_effective_25y_kw": round(pv_cap * deg_25, 2),
                                "ess_capacity_kwh": ess_cap,
                                "ess_capacity_bol_kwh": size_res.get("ess_capacity_bol_kwh", ess_cap),
                                "ess_usable_kwh": round(ess_cap * 0.70, 2),
                                "contract_power_kw": capex_info["contract_power_kw"],
                                "inverter_required_kw": inverter_req_kw,
                                "critical_day": ze_sizing.get("critical_day", "2026-02-03"),
                                "sizing_status": size_res.get("sizing_status", "optimal"),
                                "min_payback_years": min_payback_val,
                                "target_capex_for_3y_krw": target_capex_3y,
                                "loss_of_load_hours": loss_of_load_hrs,
                                # Energy Metrics
                                "annual_load_total_kwh": round(float(np.sum(p_load_kw) * dt_h), 1),
                                "annual_pv_generation_kwh": round(float(np.sum(pv_cap * p_pv1_kw) * dt_h), 1),
                                "annual_grid_import_kwh": round(float(dispatch_res.get("total_import_kwh", 0.0)), 1),
                                "annual_grid_export_kwh": round(float(dispatch_res.get("total_export_kwh", 0.0)), 1),
                                "annual_propane_kg": round(load_data["propane_kg"], 1),
                                "annual_propane_cost_krw": round(alt_propane_cost, 0),
                                "backup_heater_hours": round(load_data["backup_heater_hours"], 1),
                                "backup_heater_kwh": round(load_data["backup_heater_kwh"], 1),
                                "annual_awhp_actual_kwh": round(load_data["annual_awhp_actual_kwh"], 1),
                                # Electricity Bill Breakdown
                                "annual_base_fee_krw": round(bill_res["annual_base_fee"], 0),
                                "annual_variable_fee_krw": round(bill_res["annual_variable_fee"], 0),
                                "annual_vat_and_fund_krw": round(bill_res["annual_vat_and_fund"], 0),
                                "annual_total_electricity_bill_krw": round(bill_res["annual_total_bill"], 0),
                                "baseline_total_energy_cost_krw": round(base_total_cost, 0),
                                "alternative_year1_energy_cost_krw": round(alt_total_cost, 0),
                                "annual_savings_year1_krw": cf_res["annual_savings_y1"],
                                # Granular CAPEX Breakdown (Central)
                                "pv_turnkey_cost_krw": capex_info["pv_turnkey_cost"],
                                "pv_turnkey_krw": capex_info["pv_turnkey_krw"],
                                "ground_mount_cost_krw": capex_info["ground_mount_cost"],
                                "ground_mount_krw": capex_info["ground_mount_krw"],
                                "ess_cost_krw": capex_info["ess_cost"],
                                "awhp_turnkey_cost_krw": capex_info["awhp_turnkey_cost"],
                                "awhp_major_equipment_cost_krw": capex_info["awhp_major_equipment_cost"],
                                "awhp_electric_other_cost_krw": capex_info["awhp_electric_other_cost"],
                                "distribution_board_cost_krw": capex_info["distribution_board_cost"],
                                "wiring_expansion_cost_krw": capex_info["wiring_expansion_cost"],
                                "grid_interconnection_cost_krw": capex_info["grid_connection_cost"],
                                "gross_capex_krw": capex_info["gross_capex"],
                                "pv_subsidy_krw": capex_info["pv_subsidy"],
                                "awhp_subsidy_krw": capex_info["awhp_subsidy"],
                                "ess_subsidy_krw": capex_info["ess_subsidy"],
                                "total_subsidy_krw": capex_info["total_subsidy"],
                                "net_capex_krw": capex_info["net_capex"],
                                "ess_replacement_cost_krw": capex_info["ess_replacement_cost"],
                                "inverter_replacement_cost_krw": capex_info["inverter_replacement_cost"],
                                # Low / Central / High Outputs
                                "net_capex_low_krw": capex_info["net_capex_low"],
                                "net_capex_central_krw": capex_info["net_capex_central"],
                                "net_capex_high_krw": capex_info["net_capex_high"],
                                "payback_low": cf_low["payback_period_str"],
                                "payback_central": cf_central["payback_period_str"],
                                "payback_high": cf_high["payback_period_str"],
                                # Financial metrics (Central)
                                "payback_period_str": cf_res["payback_period_str"],
                                "payback_years": cf_res["payback_years"],
                                "net_savings_25y_krw": cf_res["net_savings_25y"],
                                "net_capex_awhp70_krw": capex_info["net_capex_awhp70"],
                                "payback_awhp70": cf_awhp70["payback_period_str"],
                                # Metadata status
                                "has_placeholder": len(placeholders_list) > 0,
                                "placeholder_count": len(placeholders_list),
                                "placeholder_items": placeholder_str,
                                "has_unverified": len(unverifieds_list) > 0,
                                "unverified_count": len(unverifieds_list),
                                "unverified_items": unverified_str,
                            }
                            results.append(row)

                            # Save representative profiles
                            if h_name == "MONO Core 54" and occ_rate in (1.0, 0.5) and ev_opt == 0 and with_sub is True:
                                profile_name = f"{h_name}_{heat_pkg}_{target_m}_occ{int(occ_rate*100)}"
                                saved_profiles[profile_name] = {
                                    "timestamp": weather_df["timestamp"],
                                    "p_load_kw": np.round(p_load_kw, 3),
                                    "p_pv_kw": np.round(pv_cap * p_pv1_kw, 3),
                                    "soc": np.round(dispatch_res["soc"], 3),
                                    "p_grid_import_kw": np.round(dispatch_res["p_grid_import_kw"], 3),
                                    "p_grid_export_kw": np.round(dispatch_res["p_grid_export_kw"], 3),
                                    "peak_day": ze_sizing["critical_day_number"],
                                    "critical_day": ze_sizing["critical_day_number"],
                                }

                            # DUO Max Incremental: ONLY AWHP cases (72 rows)
                            if h_name == "DUO Max 45" and heat_pkg == "PV+ESS+AWHP":
                                inc_base_cost = duo_incremental_base_cache[(occ_rate, ev_opt)]["base_total_cost"]
                                inc_capex_info = calculate_capex_breakdown(
                                    pv_capacity_kw=pv_cap,
                                    ess_capacity_kwh=ess_cap,
                                    heating_package=heat_pkg,
                                    with_subsidy=with_sub,
                                    is_off_grid=is_off_grid,
                                    capex_config=capex_cfg,
                                    subsidy_config=subsidy_cfg,
                                    max_import_kw=max_imp_kw,
                                    capex_basis="incremental",
                                )
                                inc_alt_cost = bill_res["annual_total_bill"]

                                inc_cf = calculate_25y_cashflow(
                                    net_capex=inc_capex_info["net_capex_central"],
                                    baseline_annual_cost=inc_base_cost,
                                    alternative_year1_cost=inc_alt_cost,
                                    baseline_propane_cost=0.0,
                                    alternative_propane_cost=0.0,
                                    ess_replacement_cost=inc_capex_info["ess_replacement_cost"],
                                    inverter_replacement_cost=inc_capex_info["inverter_replacement_cost"],
                                    pv_degradation_annual=float(equip_cfg["pv_system"]["annual_degradation_rate"]),
                                )

                                inc_cf_low = calculate_25y_cashflow(
                                    net_capex=inc_capex_info["net_capex_low"],
                                    baseline_annual_cost=inc_base_cost,
                                    alternative_year1_cost=inc_alt_cost,
                                    baseline_propane_cost=0.0,
                                    alternative_propane_cost=0.0,
                                    ess_replacement_cost=inc_capex_info["ess_replacement_cost"],
                                    inverter_replacement_cost=inc_capex_info["inverter_replacement_cost"],
                                    pv_degradation_annual=float(equip_cfg["pv_system"]["annual_degradation_rate"]),
                                )

                                inc_cf_high = calculate_25y_cashflow(
                                    net_capex=inc_capex_info["net_capex_high"],
                                    baseline_annual_cost=inc_base_cost,
                                    alternative_year1_cost=inc_alt_cost,
                                    baseline_propane_cost=0.0,
                                    alternative_propane_cost=0.0,
                                    ess_replacement_cost=inc_capex_info["ess_replacement_cost"],
                                    inverter_replacement_cost=inc_capex_info["inverter_replacement_cost"],
                                    pv_degradation_annual=float(equip_cfg["pv_system"]["annual_degradation_rate"]),
                                )

                                inc_row = dict(row)
                                inc_row["scenario_id"] = duo_inc_id
                                inc_row["capex_basis"] = "incremental"
                                inc_row["contract_power_kw"] = inc_capex_info["contract_power_kw"]
                                inc_row["baseline_total_energy_cost_krw"] = round(inc_base_cost, 0)
                                inc_row["alternative_year1_energy_cost_krw"] = round(inc_alt_cost, 0)
                                inc_row["annual_savings_year1_krw"] = inc_cf["annual_savings_y1"]
                                inc_row["pv_turnkey_cost_krw"] = inc_capex_info["pv_turnkey_cost"]
                                inc_row["pv_turnkey_krw"] = inc_capex_info["pv_turnkey_krw"]
                                inc_row["ground_mount_cost_krw"] = inc_capex_info["ground_mount_cost"]
                                inc_row["ground_mount_krw"] = inc_capex_info["ground_mount_krw"]
                                inc_row["ess_cost_krw"] = inc_capex_info["ess_cost"]
                                inc_row["awhp_turnkey_cost_krw"] = inc_capex_info["awhp_turnkey_cost"]
                                inc_row["awhp_major_equipment_cost_krw"] = inc_capex_info["awhp_major_equipment_cost"]
                                inc_row["awhp_electric_other_cost_krw"] = inc_capex_info["awhp_electric_other_cost"]
                                inc_row["grid_interconnection_cost_krw"] = inc_capex_info["grid_connection_cost"]
                                inc_row["gross_capex_krw"] = inc_capex_info["gross_capex"]
                                inc_row["pv_subsidy_krw"] = inc_capex_info["pv_subsidy"]
                                inc_row["awhp_subsidy_krw"] = inc_capex_info["awhp_subsidy"]
                                inc_row["ess_subsidy_krw"] = inc_capex_info["ess_subsidy"]
                                inc_row["total_subsidy_krw"] = inc_capex_info["total_subsidy"]
                                inc_row["net_capex_krw"] = inc_capex_info["net_capex"]
                                inc_row["net_capex_low_krw"] = inc_capex_info["net_capex_low"]
                                inc_row["net_capex_central_krw"] = inc_capex_info["net_capex_central"]
                                inc_row["net_capex_high_krw"] = inc_capex_info["net_capex_high"]
                                inc_row["payback_low"] = inc_cf_low["payback_period_str"]
                                inc_row["payback_central"] = inc_cf["payback_period_str"]
                                inc_row["payback_high"] = inc_cf_high["payback_period_str"]
                                inc_row["payback_period_str"] = inc_cf["payback_period_str"]
                                inc_row["payback_years"] = inc_cf["payback_years"]
                                inc_row["net_savings_25y_krw"] = inc_cf["net_savings_25y"]
                                duo_incremental_results.append(inc_row)
                                duo_inc_id += 1

                            scenario_id += 1

    df_results = pd.DataFrame(results)
    df_duo_inc = pd.DataFrame(duo_incremental_results)

    peak_import_kw_list.sort(key=lambda x: x[0], reverse=True)
    top_5_peaks = peak_import_kw_list[:5]

    verification_data = {
        "zero_energy_sizings": zero_energy_sizings,
        "zero_energy_references": zero_energy_references,
        "top_5_peaks": top_5_peaks,
        "peak_import_kw_list": peak_import_kw_list,
        "load_cache": load_cache,
    }

    return df_results, df_duo_inc, saved_profiles, verification_data
