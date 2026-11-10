"""Heating, cooling, and DHW equipment simulation with HM091HF performance model."""

from typing import Dict, Any, Tuple, Optional
import numpy as np


def calculate_hm091hf_cop(
    temp_air: np.ndarray,
    water_temp: float,
    awhp_cfg: Dict[str, Any],
) -> np.ndarray:
    """Calculates AWHP COP for HM091HF based on ambient temperature and leaving water temperature.

    Specifications:
    - Official (VERIFIED): A7/W35 4.7, A2/W35 3.7, A-7/W35 2.7, A7/W55 3.3, A-7/W55 2.2.
    - Estimated (UNVERIFIED): A2/W55 2.75.
    - For T_air < -7C: W35 is linearly extrapolated using A2~A-7 slope (0.111/C).
      W55 is calculated as W35 * 0.815.
    - COP lower bound: 1.0.
    - Leaving water temp is linearly interpolated between W35 and W55.
    """
    t = np.atleast_1d(np.asarray(temp_air, dtype=float))

    c_a7_w35 = float(awhp_cfg.get("cop_a7_w35", 4.7))
    c_a2_w35 = float(awhp_cfg.get("cop_a2_w35", 3.7))
    c_am7_w35 = float(awhp_cfg.get("cop_am7_w35", 2.7))

    c_a7_w55 = float(awhp_cfg.get("cop_a7_w55", 3.3))
    c_a2_w55 = float(awhp_cfg.get("cop_a2_w55", 2.75))
    c_am7_w55 = float(awhp_cfg.get("cop_am7_w55", 2.2))

    slope_extrap = float(awhp_cfg.get("extrapolation_slope_under_am7", 0.111))
    w55_factor = float(awhp_cfg.get("w55_factor_under_am7", 0.815))
    cop_min = float(awhp_cfg.get("cop_lower_bound", 1.0))

    # W35 profile
    cop_w35 = np.zeros_like(t)
    mask_under_am7 = t < -7.0
    mask_am7_to_a2 = (t >= -7.0) & (t <= 2.0)
    mask_a2_to_a7 = (t > 2.0) & (t <= 7.0)
    mask_above_a7 = t > 7.0

    cop_w35[mask_under_am7] = c_am7_w35 + slope_extrap * (t[mask_under_am7] - (-7.0))
    cop_w35[mask_am7_to_a2] = c_am7_w35 + (t[mask_am7_to_a2] - (-7.0)) * ((c_a2_w35 - c_am7_w35) / (2.0 - (-7.0)))
    cop_w35[mask_a2_to_a7] = c_a2_w35 + (t[mask_a2_to_a7] - 2.0) * ((c_a7_w35 - c_a2_w35) / (7.0 - 2.0))
    cop_w35[mask_above_a7] = c_a7_w35

    # W55 profile
    cop_w55 = np.zeros_like(t)
    cop_w55[mask_under_am7] = cop_w35[mask_under_am7] * w55_factor
    cop_w55[mask_am7_to_a2] = c_am7_w55 + (t[mask_am7_to_a2] - (-7.0)) * ((c_a2_w55 - c_am7_w55) / (2.0 - (-7.0)))
    cop_w55[mask_a2_to_a7] = c_a2_w55 + (t[mask_a2_to_a7] - 2.0) * ((c_a7_w55 - c_a2_w55) / (7.0 - 2.0))
    cop_w55[mask_above_a7] = c_a7_w55

    # Water temp linear interpolation between 35C and 55C
    frac = (water_temp - 35.0) / (55.0 - 35.0)
    frac = np.clip(frac, 0.0, 1.0)
    cop = cop_w35 + frac * (cop_w55 - cop_w35)

    return np.maximum(cop_min, cop)


def calculate_hm091hf_max_capacity(
    temp_air: np.ndarray,
    water_temp: float,
    cop: np.ndarray,
    awhp_cfg: Dict[str, Any],
) -> np.ndarray:
    """Calculates maximum thermal heating capacity (kW) for Therma V HM091HF UB40.

    Rules:
    - W35 capacity ceiling = 9.0 kW
    - W55 capacity ceiling = 8.0 kW (A-7/W55 rated 8.0kW, A7/W55 5.5kW is test point, not max cap)
    - Linear interpolation between W35 and W55 for leaving water temperature.
    - Max thermal output = min(water_temp_capacity_ceiling, cop * max_electric_input_kw)
      where max_electric_input_kw = 3.91 kW (17A @ 230V).
    """
    frac = np.clip((water_temp - 35.0) / (55.0 - 35.0), 0.0, 1.0)
    w35_cap = float(awhp_cfg.get("max_heating_capacity_w35_kw", 9.0))
    w55_cap = float(awhp_cfg.get("max_heating_capacity_w55_kw", 8.0))
    cap_water = w35_cap - frac * (w35_cap - w55_cap)

    max_elec_kw = float(awhp_cfg.get("max_electric_input_kw", 3.91))
    cap_elec = cop * max_elec_kw
    return np.minimum(cap_water, cap_elec)


def simulate_hvac_and_dhw(
    heating_package: str,
    q_heat_kw: np.ndarray,
    q_cool_kw: np.ndarray,
    q_dhw_kw: np.ndarray,
    temp_air: np.ndarray,
    equipment_config: Dict[str, Any],
    tariff_config: Dict[str, Any],
    dt_hours: float = 0.25,
    house_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculates 15-minute electrical demand, backup heater usage, and fuel consumption.

    Args:
        heating_package: 'PV+ESS+가스보일러' or 'PV+ESS+AWHP'
        q_heat_kw: 15-min space heating load (kW thermal)
        q_cool_kw: 15-min space cooling load (kW thermal)
        q_dhw_kw: 15-min DHW load (kW thermal)
        temp_air: 15-min outdoor ambient temperature (C)
        equipment_config: Equipment configuration parameters
        tariff_config: Tariff configuration parameters
        dt_hours: Timestep in hours (0.25)
        house_config: House model configuration (to check uses_awhp_cooling)

    Returns:
        Dict with electrical profiles, backup heater metrics, and propane usage.
    """
    n = len(temp_air)
    awhp_cfg = equipment_config["awhp_system"]

    # Cooling efficiency & capacity logic
    # DUO Max AWHP case uses Therma V (A35/W7 EER 2.6, 5.5kW cap)
    # Core 54, 72 and DUO Max gas boiler maintain standard system air conditioner (COP 4.40)
    uses_awhp_cooling = False
    if house_config:
        inc_cool = house_config.get("uses_awhp_cooling", False)
        if isinstance(inc_cool, dict):
            uses_awhp_cooling = bool(inc_cool.get("value", False))
        else:
            uses_awhp_cooling = bool(inc_cool)

    is_awhp = "AWHP" in heating_package

    if uses_awhp_cooling and is_awhp:
        eer_cool = float(awhp_cfg.get("therma_v_cooling_eer", 2.6))
        cap_cool_kw = float(awhp_cfg.get("therma_v_cooling_capacity_kw", 5.5))
        q_cool_served = np.minimum(q_cool_kw, cap_cool_kw)
        p_cool_kw = np.where(q_cool_served > 0, q_cool_served / eer_cool, 0.0)
    else:
        cop_cool = float(awhp_cfg.get("cop_cool_nominal", 4.40))
        p_cool_kw = np.where(q_cool_kw > 0, q_cool_kw / cop_cool, 0.0)

    if "가스보일러" in heating_package:
        boiler_eff = float(equipment_config["gas_boiler"]["thermal_efficiency"])
        lpg_heat_val = float(tariff_config["lpg_heating_value_kwh_per_kg"])
        lpg_unit_price = float(tariff_config["lpg_unit_price"])

        p_hvac_kw = p_cool_kw.copy()

        total_thermal_kwh = float(np.sum(q_heat_kw + q_dhw_kw) * dt_hours)
        propane_kwh = total_thermal_kwh / boiler_eff
        propane_kg = propane_kwh / lpg_heat_val
        propane_cost = propane_kg * lpg_unit_price

        return {
            "p_hvac_kw": p_hvac_kw,
            "p_heating_kw": np.zeros_like(p_hvac_kw),
            "p_cooling_kw": p_cool_kw,
            "p_dhw_kw": np.zeros_like(p_hvac_kw),
            "propane_kwh": propane_kwh,
            "propane_kg": propane_kg,
            "propane_cost": propane_cost,
            "backup_heater_hours": 0.0,
            "backup_heater_kwh": 0.0,
            "annual_awhp_actual_kwh": 0.0,
        }

    else:
        # AWHP Case with HM091HF model
        max_backup_cap = float(awhp_cfg.get("backup_heater_capacity_kw", 3.0))
        standby_w = float(awhp_cfg.get("standby_power_w", 10.0))
        p_standby_kw = standby_w / 1000.0

        # Space heating at water temp 40C
        t_water_heat = float(awhp_cfg.get("heating_leaving_water_temp", 40.0))
        cop_heat = calculate_hm091hf_cop(temp_air, t_water_heat, awhp_cfg)
        max_cap_heat = calculate_hm091hf_max_capacity(temp_air, t_water_heat, cop_heat, awhp_cfg)

        # Space heating split between AWHP and backup heater (max 3kW)
        q_heat_awhp = np.minimum(q_heat_kw, max_cap_heat)
        q_heat_rem = np.maximum(0.0, q_heat_kw - max_cap_heat)
        q_heat_backup = np.minimum(q_heat_rem, max_backup_cap)
        p_heat_awhp = np.where(q_heat_awhp > 0, q_heat_awhp / cop_heat, 0.0)
        p_heat_backup = q_heat_backup / 1.0  # Electric backup COP = 1.0

        # DHW at water temp 55C
        t_water_dhw = float(awhp_cfg.get("dhw_leaving_water_temp", 55.0))
        cop_dhw = calculate_hm091hf_cop(temp_air, t_water_dhw, awhp_cfg)
        max_cap_dhw = calculate_hm091hf_max_capacity(temp_air, t_water_dhw, cop_dhw, awhp_cfg)

        q_dhw_awhp = np.minimum(q_dhw_kw, max_cap_dhw)
        q_dhw_rem = np.maximum(0.0, q_dhw_kw - max_cap_dhw)
        q_dhw_backup = np.minimum(q_dhw_rem, max_backup_cap)
        p_dhw_awhp = np.where(q_dhw_awhp > 0, q_dhw_awhp / cop_dhw, 0.0)
        p_dhw_backup = q_dhw_backup / 1.0

        # Reflect standby power 10W (0.01kW) continuously into AWHP load
        p_hvac_kw = p_cool_kw + p_heat_awhp + p_heat_backup + p_dhw_awhp + p_dhw_backup + p_standby_kw

        backup_power = p_heat_backup + p_dhw_backup
        backup_heater_hours = float(np.sum(backup_power > 0) * dt_hours)
        backup_heater_kwh = float(np.sum(backup_power) * dt_hours)
        annual_awhp_actual_kwh = float(np.sum(p_hvac_kw) * dt_hours)

        return {
            "p_hvac_kw": p_hvac_kw,
            "p_heating_kw": p_heat_awhp + p_heat_backup,
            "p_cooling_kw": p_cool_kw,
            "p_dhw_kw": p_dhw_awhp + p_dhw_backup,
            "propane_kwh": 0.0,
            "propane_kg": 0.0,
            "propane_cost": 0.0,
            "backup_heater_hours": backup_heater_hours,
            "backup_heater_kwh": backup_heater_kwh,
            "annual_awhp_actual_kwh": annual_awhp_actual_kwh,
        }
