"""Full scenario execution runner for LG Smart Cottage ROI Calculation (v9).

Simulates all 420 scenarios across:
- 7 House-Occupant pairs:
  - MONO Core 54 (1p, 2p)
  - MONO Core 72 (1p, 2p, 3p)
  - DUO Max 45 (1p, 2p)
- 2 Heating packages:
  - Gas boiler (Propane)
  - AWHP (LG Therma V)
- 5 Occupancy rates: 1.00, 0.70, 0.50, 0.30, 0.15
- 3 Target models: near_zero_bill, zero_bill, zero_energy
- 2 Subsidy options: False (None), True (2026 PV Subsidy)
Total scenarios: 7 * 2 * 5 * 3 * 2 = 420.
All models start with 0 pre-installed PV/ESS/AWHP.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from engine.weather import load_weather_data
from engine.thermal_5r1c import simulate_thermal_5r1c
from engine.heat_pump import simulate_hvac_and_dhw
from engine.pv import simulate_pv_generation_1kwp
from engine.tariffs.korea import KoreaTariffCalculator
from engine.capex import calculate_capex_breakdown
from engine.cashflow import calculate_100y_cashflow
from engine.occupancy_tus import OccupancyTUSModel
from engine.sizing import size_zero_energy, size_zero_bill, size_near_zero_bill, fast_simulate_offgrid


def run_all_scenarios(
    config_values: Dict[str, Any],
    weather_df: pd.DataFrame,
    placeholders_list: List[str] = None,
    unverifieds_list: List[str] = None,
    assumptions_list: List[str] = None,
    kosis_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Runs all 420 scenarios and returns results, energy comparison, ZE sizing, and metadata."""
    if placeholders_list is None:
        placeholders_list = []
    if unverifieds_list is None:
        unverifieds_list = []
    if assumptions_list is None:
        assumptions_list = []

    country_cfg = config_values["country"]
    houses_cfg = config_values["houses"]
    tariff_cfg = config_values["tariff"]
    capex_cfg = config_values["capex"]
    subsidy_cfg = config_values["subsidy"]
    load_cfg = config_values["load"]
    equip_cfg = config_values["equipment"]
    lifetimes_cfg = config_values.get("lifetimes", {})

    dates = pd.DatetimeIndex(weather_df["timestamp"])
    dt_h = 0.25

    lat = float(country_cfg["latitude"])
    lon = float(country_cfg["longitude"])
    tz = str(country_cfg.get("timezone", "Asia/Seoul"))
    p_pv1_kw = simulate_pv_generation_1kwp(
        weather_df, lat, lon, tilt=25.0, azimuth=180.0, timezone=tz, pv_equipment_config=equip_cfg["pv_system"]
    )

    tariff_calc = KoreaTariffCalculator(tariff_cfg)
    propane_unit_cost = float(tariff_cfg.get("propane_unit_cost_krw_per_kg", {}).get("value", 2812.26) if isinstance(tariff_cfg.get("propane_unit_cost_krw_per_kg"), dict) else tariff_cfg.get("propane_unit_cost_krw_per_kg", 2812.26))
    propane_energy_density_mj = float(tariff_cfg.get("propane_heating_value_mj_per_kg", {}).get("value", 46.3) if isinstance(tariff_cfg.get("propane_heating_value_mj_per_kg"), dict) else tariff_cfg.get("propane_heating_value_mj_per_kg", 46.3))
    propane_kwh_per_kg = propane_energy_density_mj / 3.6  # 12.861 kWh/kg

    boiler_cfg = equip_cfg.get("gas_boiler", {})
    boiler_eff_raw = boiler_cfg.get("efficiency", 0.90)
    boiler_eff = float(boiler_eff_raw.get("value", 0.90) if isinstance(boiler_eff_raw, dict) else boiler_eff_raw)

    if kosis_dir is None:
        kosis_dir = Path("korea/source/kosis")

    # Scenario axes definition (420 scenarios)
    house_occupant_pairs = [
        {"house": "MONO Core 54", "occupants": 1},
        {"house": "MONO Core 54", "occupants": 2},
        {"house": "MONO Core 72", "occupants": 1},
        {"house": "MONO Core 72", "occupants": 2},
        {"house": "MONO Core 72", "occupants": 3},
        {"house": "DUO Max 45", "occupants": 1},
        {"house": "DUO Max 45", "occupants": 2},
    ]

    heating_packages = ["가스보일러", "AWHP"]
    occupancy_rates = [1.00, 0.70, 0.50, 0.30, 0.15]
    target_models = ["near_zero_bill", "zero_bill", "zero_energy"]
    subsidy_options = [False, True]

    # Pre-simulate occupancy and loads across 7 pairs x 5 occupancy rates = 35 load cases
    print("Pre-computing 35 load sets via OccupancyTUSModel (Mode A/B)...")
    load_cache = {}
    tus_fit_meta = None
    load_mode = "B"
    load_mode_detail = ""
    kosis_val_meta = {}
    appliance_err_meta = {}

    for pair in house_occupant_pairs:
        h_name = pair["house"]
        occ = pair["occupants"]
        h_cfg = houses_cfg[h_name]

        tus_model = OccupancyTUSModel(
            kosis_dir=kosis_dir,
            load_config=load_cfg,
            house_config=h_cfg,
            weather_df=weather_df,
            occupants=occ,
            seed=42,
        )
        load_mode = tus_model.mode
        load_mode_detail = tus_model.mode_detail

        for occ_rate in occupancy_rates:
            key = (h_name, occ, occ_rate)
            tus_res = tus_model.simulate_year(occupancy_rate=occ_rate)
            if tus_fit_meta is None:
                # Mode A Section 4.4 reproduction validation (2,000 person-days)
                if tus_model.mode == "A":
                    val_results = tus_model.run_reproduction_validation(n_person_days=2000)
                    fits = val_results.get("fit_12", [])
                    all_sleep = [f["mae"] for f in fits if f["curve"] == "sleep"] or [0.0]
                    all_out = [f["mae"] for f in fits if f["curve"] == "away"] or [0.0]
                    all_cook = [f["mae"] for f in fits if f["curve"] == "cook"] or [0.0]
                    all_bcast = [f["mae"] for f in fits if f["curve"] == "media"] or [0.0]
                    tus_fit_meta = {
                        "sleep": {"mae_pct_p": round(float(np.mean(all_sleep)), 2), "threshold_pct_p": 2.0, "status": "PASS" if np.mean(all_sleep) <= 2.0 else "FAIL"},
                        "away": {"mae_pct_p": round(float(np.mean(all_out)), 2), "threshold_pct_p": 2.0, "status": "PASS" if np.mean(all_out) <= 2.0 else "FAIL"},
                        "cook": {"mae_pct_p": round(float(np.mean(all_cook)), 2), "threshold_pct_p": 2.0, "status": "PASS" if np.mean(all_cook) <= 2.0 else "FAIL"},
                        "broadcast": {"mae_pct_p": round(float(np.mean(all_bcast)), 2), "threshold_pct_p": 2.0, "status": "PASS" if np.mean(all_bcast) <= 2.0 else "FAIL"},
                    }
                else:
                    tus_fit_meta = tus_res.get("tus_fit", {})
                kosis_val_meta = tus_res["kosis_validation"]
                appliance_err_meta = tus_res["appliance_calibration_errors"]

            # Thermal 5R1C simulation
            q_occ_w = tus_res["occupants_active_15min"] * 80.0
            sleeping_arr = (np.array(tus_res["persons_state_15min"]) == 2).sum(axis=0).astype(float)
            t_indoor, q_heat_kw, q_cool_kw, t_set = simulate_thermal_5r1c(
                house_config=h_cfg,
                temp_air=weather_df["temp_air"].values,
                ghi=weather_df["ghi"].values,
                occupant_presence=tus_res["is_occupied_15min"].astype(float),
                internal_heat_gain_w=q_occ_w,
                is_occupied_day=tus_res["is_occupied_day_365"],
                heat_setpoint_schedule=tus_res["heat_setpoint_15min"],
                occupants_active=tus_res["occupants_active_15min"],
                occupants_sleeping=sleeping_arr,
            )

            # DHW heat requirement (kWh/15min)
            # Q = m * Cp * delta_T (Cp = 4.186 kJ/kg*K, delta_T = 55 - 15 = 40K)
            dhw_liters = tus_res["dhw_liters_15min"]
            q_dhw_kwh = dhw_liters * 4.186 * 40.0 / 3600.0
            q_dhw_kw = q_dhw_kwh / dt_h

            load_cache[key] = {
                "tus_res": tus_res,
                "t_indoor": t_indoor,
                "q_heat_kw": q_heat_kw,
                "q_cool_kw": q_cool_kw,
                "q_dhw_kw": q_dhw_kw,
                "t_set": t_set,
                "base_elec_kw": tus_res["total_elec_base_load_kw_15min"],
            }

    # Pre-calculate Baseline for each of the 35 (h_name, occ, occ_rate) combinations
    # Baseline = Gas boiler (propane) + KEPCO grid electricity, 0 PV, 0 ESS, 0 Subsidy
    baseline_cache = {}
    cop_cool_std = float(equip_cfg["awhp_system"].get("cop_cool_nominal", 4.40))
    for pair in house_occupant_pairs:
        h_name = pair["house"]
        occ = pair["occupants"]
        for occ_rate in occupancy_rates:
            ld = load_cache[(h_name, occ, occ_rate)]

            # Gas boiler covers heating and DHW
            annual_heat_kwh = float(ld["q_heat_kw"].sum() * dt_h)
            annual_dhw_kwh = float(ld["q_dhw_kw"].sum() * dt_h)
            annual_thermal_kwh = annual_heat_kwh + annual_dhw_kwh
            propane_kg = annual_thermal_kwh / (boiler_eff * propane_kwh_per_kg)
            gas_bill = propane_kg * propane_unit_cost

            # Grid electricity covers appliances, lighting, and air conditioning cooling (COP 4.40 identical)
            p_cool_elec = np.where(ld["q_cool_kw"] > 0, ld["q_cool_kw"] / cop_cool_std, 0.0)
            p_elec_total = ld["base_elec_kw"] + p_cool_elec
            elec_bill_res = tariff_calc.calculate_annual_bill(
                p_grid_import_kw=p_elec_total,
                p_grid_export_kw=np.zeros(len(dates)),
                dates=dates,
                net_metering_scheme="monthly_net",
            )
            elec_bill = elec_bill_res["annual_total_bill"]

            baseline_cache[(h_name, occ, occ_rate)] = {
                "p_elec_total_kw": p_elec_total,
                "grid_import_kwh": float(p_elec_total.sum() * dt_h),
                "grid_export_kwh": 0.0,
                "billed_kwh": float(p_elec_total.sum() * dt_h),
                "electric_bill_krw": round(elec_bill, 0),
                "propane_kg": round(propane_kg, 1),
                "gas_bill_krw": round(gas_bill, 0),
                "total_energy_cost_krw": round(elec_bill + gas_bill, 0),
            }

    # Pre-calculate HVAC electric load for AWHP cases
    awhp_load_cache = {}
    awhp_equip_cfg = equip_cfg.get("awhp_system", {})
    for pair in house_occupant_pairs:
        h_name = pair["house"]
        occ = pair["occupants"]
        h_cfg = houses_cfg[h_name]
        for occ_rate in occupancy_rates:
            ld = load_cache[(h_name, occ, occ_rate)]
            hvac_res = simulate_hvac_and_dhw(
                heating_package="AWHP",
                q_heat_kw=ld["q_heat_kw"],
                q_cool_kw=ld["q_cool_kw"],
                q_dhw_kw=ld["q_dhw_kw"],
                temp_air=weather_df["temp_air"].values,
                equipment_config=equip_cfg,
                tariff_config=tariff_cfg,
                house_config=h_cfg,
                t_indoor=ld["t_indoor"],
                t_set_heat=ld["tus_res"]["heat_setpoint_15min"],
            )
            p_awhp_elec = hvac_res["p_hvac_kw"]
            p_total_elec_awhp = ld["base_elec_kw"] + p_awhp_elec

            awhp_load_cache[(h_name, occ, occ_rate)] = {
                "p_awhp_elec": p_awhp_elec,
                "p_total_elec": p_total_elec_awhp,
                "hvac_res": hvac_res,
            }

    # Size all 3 targets for the 70 unique cases (7 pairs x 2 heating x 5 occupancies)
    print("Sizing systems (Zero Energy, Zero Bill, Near Zero) for 70 unique cases...")
    ze_sizing_cache = {}
    zb_sizing_cache = {}
    nz_sizing_cache = {}
    ze_sizing_rows = []

    for pair in house_occupant_pairs:
        h_name = pair["house"]
        occ = pair["occupants"]
        for heat_pkg in heating_packages:
            is_awhp = heat_pkg == "AWHP"
            for occ_rate in occupancy_rates:
                base_data = baseline_cache[(h_name, occ, occ_rate)]
                base_total_cost = base_data["total_energy_cost_krw"]
                base_gas_cost = base_data["gas_bill_krw"]
                base_propane_kg = base_data["propane_kg"]

                if is_awhp:
                    p_load_kw = awhp_load_cache[(h_name, occ, occ_rate)]["p_total_elec"]
                    alt_propane_kg = 0.0
                    alt_gas_cost = 0.0
                else:
                    p_load_kw = base_data["p_elec_total_kw"]
                    alt_propane_kg = base_propane_kg
                    alt_gas_cost = base_gas_cost

                # 1. Zero Energy Sizing
                ze_res = size_zero_energy(
                    p_load_kw=p_load_kw,
                    p_pv1_kw=p_pv1_kw,
                    dates=dates,
                    capex_config=capex_cfg,
                    subsidy_config=subsidy_cfg,
                    heating_package=heat_pkg,
                    with_subsidy=False,
                    soc_min=0.00,
                    soc_max=1.00,
                    soh_eol=0.70,
                    rte=0.90,
                )
                ze_sizing_cache[(h_name, occ, heat_pkg, occ_rate)] = ze_res

                # Evaluate LOL if 100% occupancy system applied to this occupancy rate
                ze_100_res = ze_sizing_cache.get((h_name, occ, heat_pkg, 1.00), ze_res)
                unmet_100_sys, lol_100_sys, _ = fast_simulate_offgrid(
                    p_load_kw=p_load_kw,
                    p_pv_kw=p_pv1_kw * ze_100_res["pv_capacity_kw"] * (0.995**24),
                    ess_kwh=ze_100_res["ess_capacity_kwh"],
                )

                ze_sizing_rows.append({
                    "house_model": h_name,
                    "occupants": occ,
                    "house_occupants_label": f"{h_name} ({occ}인)",
                    "heating_package": heat_pkg,
                    "occupancy_rate": occ_rate,
                    "occupancy_rate_pct": f"{int(occ_rate*100)}%",
                    "max_daily_load_kwh": ze_res["max_daily_load_kwh"],
                    "ess_modules": ze_res["ess_modules"],
                    "ess_capacity_kwh": ze_res["ess_capacity_kwh"],
                    "usable_ess_kwh": ze_res["usable_ess_kwh"],
                    "pv_capacity_kw": ze_res["pv_capacity_kw"],
                    "net_capex_krw": ze_res["capex_info"]["net_capex"],
                    "gross_capex_krw": ze_res["capex_info"]["gross_capex"],
                    "unmet_kwh": ze_res["unmet_kwh"],
                    "lol_hours": ze_res["lol_hours"],
                    "lol_hours_using_100occ_sys": round(lol_100_sys, 2),
                })

                # 2. Zero Bill Sizing
                zb_res = size_zero_bill(
                    p_load_kw=p_load_kw,
                    p_pv1_kw=p_pv1_kw,
                    tariff_calc=tariff_calc,
                    capex_config=capex_cfg,
                    subsidy_config=subsidy_cfg,
                    heating_package=heat_pkg,
                    with_subsidy=False,
                    dates=dates,
                )
                zb_sizing_cache[(h_name, occ, heat_pkg, occ_rate)] = zb_res

                # 3. Near Zero Sizing
                nz_res = size_near_zero_bill(
                    p_load_kw=p_load_kw,
                    p_pv1_kw=p_pv1_kw,
                    baseline_energy_cost=base_total_cost,
                    baseline_propane_cost=base_gas_cost,
                    alt_propane_cost=alt_gas_cost,
                    tariff_calc=tariff_calc,
                    capex_config=capex_cfg,
                    subsidy_config=subsidy_cfg,
                    heating_package=heat_pkg,
                    with_subsidy=False,
                    is_awhp=is_awhp,
                    dates=dates,
                )
                nz_sizing_cache[(h_name, occ, heat_pkg, occ_rate)] = nz_res

    df_ze_sizing = pd.DataFrame(ze_sizing_rows)

    # Run the 420 scenarios
    print("Executing all 420 scenarios...")
    results_all_rows = []
    energy_comp_rows = []

    scenario_id = 1
    for pair in house_occupant_pairs:
        h_name = pair["house"]
        occ = pair["occupants"]

        for heat_pkg in heating_packages:
            is_awhp = heat_pkg == "AWHP"

            for occ_rate in occupancy_rates:
                base_data = baseline_cache[(h_name, occ, occ_rate)]
                base_total_cost = base_data["total_energy_cost_krw"]
                base_elec_cost = base_data["electric_bill_krw"]
                base_gas_cost = base_data["gas_bill_krw"]
                base_propane_kg = base_data["propane_kg"]

                if is_awhp:
                    p_load_kw = awhp_load_cache[(h_name, occ, occ_rate)]["p_total_elec"]
                    alt_propane_kg = 0.0
                    alt_gas_cost = 0.0
                else:
                    p_load_kw = base_data["p_elec_total_kw"]
                    alt_propane_kg = base_propane_kg
                    alt_gas_cost = base_gas_cost

                for target in target_models:
                    for with_sub in subsidy_options:
                        # Fetch pre-sized capacity
                        if target == "zero_energy":
                            ze_res = ze_sizing_cache[(h_name, occ, heat_pkg, occ_rate)]
                            pv_kw = ze_res["pv_capacity_kw"]
                            ess_kwh = ze_res["ess_capacity_kwh"]
                            is_off_grid = True
                            grid_import_kwh = 0.0
                            grid_export_kwh = 0.0
                            billed_kwh = 0.0
                            alt_elec_cost = 0.0
                            status_near_zero = "N/A"
                            req_capex_3y = 0.0
                            req_discount_pct = 0.0

                        elif target == "zero_bill":
                            zb_res = zb_sizing_cache[(h_name, occ, heat_pkg, occ_rate)]
                            pv_kw = zb_res["pv_capacity_kw"]
                            ess_kwh = zb_res["ess_capacity_kwh"]
                            is_off_grid = False
                            p_pv = p_pv1_kw * pv_kw
                            bill_res = tariff_calc.calculate_annual_bill(
                                p_grid_import_kw=np.maximum(0.0, p_load_kw - p_pv),
                                p_grid_export_kw=np.maximum(0.0, p_pv - p_load_kw),
                                dates=dates,
                                net_metering_scheme="monthly_net",
                            )
                            grid_import_kwh = float(np.maximum(0.0, p_load_kw - p_pv).sum() * dt_h)
                            grid_export_kwh = float(np.maximum(0.0, p_pv - p_load_kw).sum() * dt_h)
                            billed_kwh = bill_res["annual_billed_kwh"]
                            alt_elec_cost = bill_res["annual_total_bill"]
                            status_near_zero = "N/A"
                            req_capex_3y = 0.0
                            req_discount_pct = 0.0

                        else:  # near_zero_bill
                            nz_res = nz_sizing_cache[(h_name, occ, heat_pkg, occ_rate)]
                            pv_kw = nz_res["pv_capacity_kw"]
                            ess_kwh = nz_res["ess_capacity_kwh"]
                            is_off_grid = False
                            alt_elec_cost = nz_res["alt_elec_cost"]
                            status_near_zero = nz_res["status_3y"]

                            p_pv = p_pv1_kw * pv_kw
                            grid_import_kwh = float(np.maximum(0.0, p_load_kw - p_pv).sum() * dt_h)
                            grid_export_kwh = float(np.maximum(0.0, p_pv - p_load_kw).sum() * dt_h)
                            bill_res = tariff_calc.calculate_annual_bill(
                                p_grid_import_kw=np.maximum(0.0, p_load_kw - p_pv),
                                p_grid_export_kw=np.maximum(0.0, p_pv - p_load_kw),
                                dates=dates,
                                net_metering_scheme="monthly_net",
                            )
                            billed_kwh = bill_res["annual_billed_kwh"]

                        # Calculate CAPEX with current subsidy option
                        capex_info = calculate_capex_breakdown(
                            pv_capacity_kw=pv_kw,
                            ess_capacity_kwh=ess_kwh,
                            heating_package=heat_pkg,
                            with_subsidy=with_sub,
                            is_off_grid=is_off_grid,
                            capex_config=capex_cfg,
                            subsidy_config=subsidy_cfg,
                        )

                        alt_total_cost = round(alt_elec_cost + alt_gas_cost, 0)
                        annual_savings_y1 = round(base_total_cost - alt_total_cost, 0)

                        if target == "near_zero_bill":
                            req_capex_3y = max(0.0, annual_savings_y1 * 3.0)
                            act_cap = capex_info["net_capex"]
                            req_discount_pct = max(0.0, (act_cap - req_capex_3y) / act_cap * 100.0) if act_cap > 0 else 0.0

                        # 100-year cash flow and payback calculation
                        cf_res = calculate_100y_cashflow(
                            net_capex=capex_info["net_capex"],
                            baseline_annual_cost=base_total_cost,
                            alternative_year1_cost=alt_total_cost,
                            baseline_propane_cost=base_gas_cost,
                            alternative_propane_cost=alt_gas_cost,
                            pv_capacity_kw=pv_kw,
                            ess_capacity_kwh=ess_kwh,
                            is_awhp=is_awhp,
                            pv_turnkey_cost=capex_info["pv_turnkey_cost"],
                            inverter_replacement_cost=capex_info["inverter_replacement_cost"],
                            ess_replacement_cost=capex_info["ess_replacement_cost"],
                            awhp_replacement_cost=capex_info["awhp_replacement_cost"],
                        )

                        # Verify component sum equals net capex within 1 KRW
                        comp_diff = capex_info["component_sum_difference"]
                        is_sum_ok = capex_info["is_sum_consistent"]

                        # Assemble results row
                        row_dict = {
                            "scenario_id": scenario_id,
                            "house_model": h_name,
                            "occupants": occ,
                            "house_occupants_label": f"{h_name} ({occ}인)",
                            "heating_package": heat_pkg,
                            "occupancy_rate": occ_rate,
                            "occupancy_rate_pct": f"{int(occ_rate*100)}%",
                            "target_model": target,
                            "with_subsidy": with_sub,
                            "pv_capacity_kw": round(pv_kw, 2),
                            "ess_capacity_kwh": round(ess_kwh, 2),
                            # Granular CAPEX components
                            "capex_pv_turnkey_krw": capex_info["pv_turnkey_cost"],
                            "capex_inverter_note": capex_info["inverter_capex_note"],
                            "capex_inverter_krw": capex_info["inverter_capex_amount"],
                            "capex_ess_krw": capex_info["ess_cost"],
                            "capex_awhp_krw": capex_info["awhp_turnkey_cost"],
                            "capex_grid_electrical_krw": capex_info["total_grid_electrical_cost"],
                            "subsidy_pv_krw": capex_info["pv_subsidy"],
                            "subsidy_awhp_sensitivity_krw": capex_info["awhp_subsidy_sensitivity"],
                            "gross_capex_krw": capex_info["gross_capex"],
                            "net_capex_krw": capex_info["net_capex"],
                            "net_capex_awhp70_krw": capex_info["net_capex_awhp70"],
                            "capex_sum_consistent": is_sum_ok,
                            "capex_sum_diff": comp_diff,
                            # Energy & Operating Costs
                            "grid_import_kwh": round(grid_import_kwh, 1),
                            "grid_export_kwh": round(grid_export_kwh, 1),
                            "billed_kwh": round(billed_kwh, 1),
                            "alt_electric_bill_krw": round(alt_elec_cost, 0),
                            "alt_propane_kg": round(alt_propane_kg, 1),
                            "alt_gas_bill_krw": round(alt_gas_cost, 0),
                            "alt_total_energy_cost_krw": alt_total_cost,
                            "baseline_total_energy_cost_krw": base_total_cost,
                            "annual_savings_y1_krw": annual_savings_y1,
                            # Financial Metrics
                            "payback_years": cf_res["payback_years"],
                            "payback_period_str": cf_res["payback_period_str"],
                            "payback_reason_code": cf_res["reason_code"],
                            "net_savings_25y_krw": cf_res["net_savings_25y"],
                            "net_savings_100y_krw": cf_res["net_savings_100y"],
                            # Near zero specific
                            "status_near_zero": status_near_zero,
                            "required_capex_for_3y_krw": req_capex_3y,
                            "required_discount_rate_pct": req_discount_pct,
                            # Cashflow array for charting
                            "cumulative_cashflow_100y": cf_res["cumulative_cashflow_100y"],
                        }

                        results_all_rows.append(row_dict)

                        # Energy comparison row
                        energy_comp_rows.append({
                            "scenario_id": scenario_id,
                            "house_occupants_label": f"{h_name} ({occ}인)",
                            "heating_package": heat_pkg,
                            "occupancy_rate_pct": f"{int(occ_rate*100)}%",
                            "target_model": target,
                            "with_subsidy": "보조금 반영" if with_sub else "보조금 미반영",
                            "baseline_import_kwh": round(base_data["grid_import_kwh"], 1),
                            "baseline_electric_bill_krw": base_data["electric_bill_krw"],
                            "baseline_propane_kg": base_data["propane_kg"],
                            "baseline_gas_bill_krw": base_data["gas_bill_krw"],
                            "baseline_total_energy_cost_krw": base_data["total_energy_cost_krw"],
                            "alt_import_kwh": round(grid_import_kwh, 1),
                            "alt_export_kwh": round(grid_export_kwh, 1),
                            "alt_billed_kwh": round(billed_kwh, 1),
                            "alt_electric_bill_krw": round(alt_elec_cost, 0),
                            "alt_propane_kg": round(alt_propane_kg, 1),
                            "alt_gas_bill_krw": round(alt_gas_cost, 0),
                            "alt_total_energy_cost_krw": alt_total_cost,
                            "annual_savings_krw": annual_savings_y1,
                        })

                        scenario_id += 1

    # 70 cases zero energy minimality validation
    print("Validating 70 Zero Energy cases for zero grid import and minimality across 10 seeds (42..51)...")
    ze_minimality_rows = []
    pv_deg_factor = 0.995 ** 24
    soh_eol = 0.70
    rte = 0.90
    eff_d = np.sqrt(rte)
    single_module_usable_kwh = 9.6 * soh_eol * 1.0 * eff_d

    # Pre-cache load profiles for seeds 42..51 across the 35 (h_name, occ, occ_rate) combinations
    seed_list = list(range(42, 52))
    multi_seed_load_cache = {}
    for pair in house_occupant_pairs:
        h_name = pair["house"]
        occ = pair["occupants"]
        h_cfg = config_values["houses"][h_name]
        for occ_rate in occupancy_rates:
            ld = load_cache[(h_name, occ, occ_rate)]
            p_cool_elec = np.where(ld["q_cool_kw"] > 0, ld["q_cool_kw"] / cop_cool_std, 0.0)
            
            # Base seed 42
            base_gas = baseline_cache[(h_name, occ, occ_rate)]["p_elec_total_kw"]
            base_awhp = awhp_load_cache[(h_name, occ, occ_rate)]["p_total_elec"]
            gas_loads = [base_gas]
            awhp_loads = [base_awhp]
            
            # Additional seeds 43..51
            for s in seed_list[1:]:
                m_s = OccupancyTUSModel(
                    kosis_dir=kosis_dir,
                    load_config=config_values["load"],
                    house_config=h_cfg,
                    weather_df=weather_df,
                    occupants=occ,
                    seed=s,
                )
                res_s = m_s.simulate_year(occupancy_rate=occ_rate)
                # Gas boiler electricity: seed base load + cooling
                p_gas_s = res_s["total_elec_base_load_kw_15min"] + p_cool_elec
                gas_loads.append(p_gas_s)
                # AWHP electricity: seed base load + AWHP HVAC load
                p_awhp_s = awhp_load_cache[(h_name, occ, occ_rate)]["p_awhp_elec"] + res_s["total_elec_base_load_kw_15min"]
                awhp_loads.append(p_awhp_s)
                
            multi_seed_load_cache[(h_name, occ, occ_rate, "가스보일러")] = gas_loads
            multi_seed_load_cache[(h_name, occ, occ_rate, "AWHP")] = awhp_loads

    for pair in house_occupant_pairs:
        h_name = pair["house"]
        occ = pair["occupants"]
        for heat_pkg in heating_packages:
            for occ_rate in occupancy_rates:
                ze_res = ze_sizing_cache[(h_name, occ, heat_pkg, occ_rate)]
                pv_kw = ze_res["pv_capacity_kw"]
                ess_mod = ze_res["ess_modules"]
                ess_kwh = ze_res["ess_capacity_kwh"]
                max_daily_load = float(ze_res["max_daily_load_kwh"])

                loads_10 = multi_seed_load_cache[(h_name, occ, occ_rate, heat_pkg)]

                # Base run (Seed 42)
                unmet_base, lol_base, _ = fast_simulate_offgrid(
                    p_load_kw=loads_10[0],
                    p_pv_kw=p_pv1_kw * pv_kw * pv_deg_factor,
                    ess_kwh=ess_kwh,
                    soc_min=0.0,
                    soc_max=1.0,
                    soh_eol=soh_eol,
                    rte=rte,
                )
                is_zero_grid = (unmet_base <= 1e-4 and lol_base <= 1e-4)

                # Check ESS - 1 module start condition constraint
                # Constraint: usable_ess >= max_daily_load
                usable_ess_minus = (ess_mod - 1) * single_module_usable_kwh
                ess_minus_limited_by_start = (ess_mod <= 1) or (usable_ess_minus < max_daily_load - 1e-4)

                # Evaluate across all 10 seeds (42..51)
                lol_pv_minus_list = []
                lol_ess_minus_list = []

                for p_load_s in loads_10:
                    # PV - 0.5 kW
                    if pv_kw > 0.5:
                        _, lol_pv_s, _ = fast_simulate_offgrid(
                            p_load_kw=p_load_s,
                            p_pv_kw=p_pv1_kw * (pv_kw - 0.5) * pv_deg_factor,
                            ess_kwh=ess_kwh,
                            soc_min=0.0,
                            soc_max=1.0,
                            soh_eol=soh_eol,
                            rte=rte,
                        )
                    else:
                        lol_pv_s = 10.0
                    lol_pv_minus_list.append(lol_pv_s)

                    # ESS - 1 module
                    if not ess_minus_limited_by_start:
                        _, lol_ess_s, _ = fast_simulate_offgrid(
                            p_load_kw=p_load_s,
                            p_pv_kw=p_pv1_kw * pv_kw * pv_deg_factor,
                            ess_kwh=(ess_mod - 1) * 9.6,
                            soc_min=0.0,
                            soc_max=1.0,
                            soh_eol=soh_eol,
                            rte=rte,
                        )
                    else:
                        lol_ess_s = 0.0
                    lol_ess_minus_list.append(lol_ess_s)

                max_lol_pv_minus = max(lol_pv_minus_list)
                max_lol_ess_minus = max(lol_ess_minus_list)

                # Determination rule (Requirement 3):
                # 1. If ESS -1 module violates start condition -> "시작 조건 제한"
                # 2. Else if lol_pv_minus > 0 or lol_ess_minus > 0 -> "PASS"
                # 3. Else -> "FAIL"
                if ess_minus_limited_by_start:
                    status_str = "시작 조건 제한"
                    is_minimal = True
                    is_passed = is_zero_grid
                elif (max_lol_pv_minus > 0.0) or (max_lol_ess_minus > 0.0):
                    status_str = "PASS"
                    is_minimal = True
                    is_passed = is_zero_grid
                else:
                    status_str = "FAIL"
                    is_minimal = False
                    is_passed = False

                ze_minimality_rows.append({
                    "house_name": h_name,
                    "occupants": occ,
                    "heat_pkg": heat_pkg,
                    "occupancy_rate": occ_rate,
                    "max_daily_load_kwh": round(max_daily_load, 1),
                    "pv_kw": round(float(pv_kw), 1),
                    "ess_modules": int(ess_mod),
                    "ess_kwh": round(float(ess_kwh), 1),
                    "unmet_base_kwh": round(float(unmet_base), 1),
                    "lol_base_hours": round(float(lol_base), 1),
                    "lol_pv_minus_hours": round(float(max_lol_pv_minus), 1),
                    "lol_ess_minus_hours": round(float(max_lol_ess_minus), 1),
                    "is_zero_grid": is_zero_grid,
                    "is_minimal": is_minimal,
                    "is_passed": is_passed,
                    "status": status_str,
                })

    df_results = pd.DataFrame(results_all_rows)
    df_energy_comp = pd.DataFrame(energy_comp_rows)

    rep_key = ("MONO Core 54", 2, 1.00)
    rep_load_data = load_cache.get(rep_key, {})

    metadata = {
        "load_mode": load_mode,
        "load_mode_detail": load_mode_detail,
        "tus_fit": tus_fit_meta,
        "kosis_validation": kosis_val_meta,
        "appliance_calibration_errors": appliance_err_meta,
        "lifetimes": lifetimes_cfg,
        "ze_sizing_cache": ze_sizing_cache,
        "zb_sizing_cache": zb_sizing_cache,
        "nz_sizing_cache": nz_sizing_cache,
        "load_cache": load_cache,
        "awhp_load_cache": awhp_load_cache,
        "baseline_cache": baseline_cache,
        "dates": dates,
        "p_pv1_kw": p_pv1_kw,
        "ze_minimality_rows": ze_minimality_rows,
    }

    return df_results, df_energy_comp, df_ze_sizing, metadata
