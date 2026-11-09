"""Appliance, lighting, and baseload electrical profile generator reflecting house-specific configurations."""

from typing import Dict, Tuple, Optional
import numpy as np


def calculate_appliance_load(
    occupants: int,
    is_occupied_day: np.ndarray,
    load_config: Dict,
    house_config: Optional[Dict] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculates 15-minute baseload and plug load power (kW) and heat gains (W).

    Accounts for:
    - Continuous standby power (always active, vacant & occupied)
    - Refrigerator continuous baseline (always active)
    - House-specific continuous appliances (Water purifier, ERV)
    - House-specific active appliances on occupied days (Washing machine, WashTower, Induction, Dishwasher, Oven)
    - Floor area dependent lighting load (occupied days)
    - Person-dependent active plug loads (occupied days)

    Returns:
        (p_appliance_kw, internal_heat_gain_w)
    """
    n = 35040
    standby_w = float(load_config.get("standby_power", 45.0))
    fridge_w = float(load_config.get("fridge_continuous_power", 35.0))

    base_w = standby_w + fridge_w

    appliances = []
    floor_area = 54.0
    if house_config:
        floor_area = float(house_config.get("floor_area", 54.0))
        inc_app = house_config.get("included_appliances", [])
        if isinstance(inc_app, dict) and "value" in inc_app:
            appliances = inc_app["value"]
        elif isinstance(inc_app, list):
            appliances = inc_app

        if "water_purifier" in appliances:
            base_w += float(load_config.get("water_purifier_continuous_power", 16.7))
        if "erv" in appliances:
            base_w += float(load_config.get("erv_continuous_power", 30.0))

    p_base_kw = base_w / 1000.0

    # Occupied-day active load calculation
    if house_config and len(appliances) > 0:
        daily_app_kwh = 0.0
        if "washing_machine" in appliances:
            daily_app_kwh += float(load_config.get("washing_machine_daily_kwh", 0.3562))
        if "washtower" in appliances:
            daily_app_kwh += float(load_config.get("washtower_daily_kwh", 0.9452))
        if "induction" in appliances:
            daily_app_kwh += float(load_config.get("induction_daily_kwh", 1.1507))
        if "dishwasher" in appliances:
            daily_app_kwh += float(load_config.get("dishwasher_daily_kwh", 0.5068))
        if "lightwave_oven" in appliances:
            daily_app_kwh += float(load_config.get("lightwave_oven_daily_kwh", 0.2603))

        # Area-dependent lighting (kWh/day)
        lighting_annual_per_m2 = float(load_config.get("lighting_annual_kwh_per_m2", 4.3452))
        daily_lighting_kwh = floor_area * (lighting_annual_per_m2 / 365.0)

        # Person-dependent general plug load (kWh/day)
        plug_per_person = float(load_config.get("base_plug_load_per_person_day", 0.90))
        daily_plug_kwh = occupants * plug_per_person

        daily_active_kwh = daily_app_kwh + daily_lighting_kwh + daily_plug_kwh
    else:
        # Fallback to generic per-person estimate
        plug_kwh_per_person = float(load_config.get("base_plug_load_per_person_day", 2.2))
        daily_active_kwh = occupants * plug_kwh_per_person

    # Diurnal normalized distribution for active appliances & lighting (summing to 1.0)
    hourly_dist = np.array([
        0.015, 0.010, 0.010, 0.010, 0.010, 0.015,  # 00-06
        0.035, 0.060, 0.055, 0.035, 0.035, 0.045,  # 06-12
        0.050, 0.040, 0.040, 0.050, 0.065, 0.085,  # 12-18
        0.115, 0.125, 0.105, 0.080, 0.055, 0.025,  # 18-24
    ])

    daily_active_profile_15min_kw = np.repeat(hourly_dist / 4.0, 4) * daily_active_kwh / 0.25

    p_appliance_kw = np.full(n, p_base_kw, dtype=float)

    for day in range(365):
        if is_occupied_day[day]:
            p_appliance_kw[day * 96 : (day + 1) * 96] += daily_active_profile_15min_kw

    # Internal heat gain to indoor space: approx 85% sensible heat
    internal_heat_gain_w = p_appliance_kw * 1000.0 * 0.85

    return p_appliance_kw, internal_heat_gain_w
