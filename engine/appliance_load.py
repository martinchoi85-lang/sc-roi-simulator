"""Appliance, lighting, and baseload electrical profile generator using appliance event models.

Reflects house-specific configurations and appliance event schedules.
Deterministic +/-15min random shift with fixed seed while strictly preserving total annual energy.
"""

from typing import Dict, Tuple, Optional, Any
import numpy as np


def calculate_appliance_load(
    occupants: int,
    is_occupied_day: np.ndarray,
    load_config: Dict[str, Any],
    house_config: Optional[Dict[str, Any]] = None,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, np.ndarray]]:
    """Calculates 15-minute appliance power profiles (kW) and heat gains (W) over 35,040 steps.

    Accounts for:
    - Continuous standby power (active on both occupied & vacant days)
    - Refrigerator continuous + compressor cycle (active on both occupied & vacant days)
    - House-specific continuous appliances: Water purifier, ERV (active on all days if included)
    - House-specific active appliances on occupied days only:
        * Induction (Breakfast, Lunch, Dinner cooking windows)
        * Dishwasher (Post-dinner washing window)
        * Washing machine / WashTower (Morning laundry/drying window)
        * Lightwave oven (Evening cooking window)
        * Floor area dependent lighting (Sunset ~ Bedtime: 18:00 ~ 23:30)
        * Person-dependent active plug loads (Morning 06:30~08:30 & Evening 18:00~23:00)

    Returns:
        (total_p_appliance_kw, internal_heat_gain_w, end_use_breakdown_dict)
    """
    n = 35040
    dt_h = 0.25

    appliances = []
    floor_area = 54.0
    if house_config:
        floor_area = float(house_config.get("floor_area", 54.0))
        inc_app = house_config.get("included_appliances", [])
        if isinstance(inc_app, dict) and "value" in inc_app:
            appliances = inc_app["value"]
        elif isinstance(inc_app, list):
            appliances = inc_app

    rng = np.random.RandomState(seed)
    day_shifts = rng.choice([-1, 0, 1], size=(365, 8))  # separate shifts for different events

    # 1. Base Standby Power (active 24/7)
    # Default household baseline standby 10W
    p_standby_kw = np.full(n, 0.010, dtype=float)

    # 2. Refrigerator (active 24/7, 312 kWh/year = 0.8548 kWh/day)
    # Base fan/control 20W + compressor 15-min cycle every hour (0.06247 kW extra)
    fridge_daily_kwh = 312.0 / 365.0
    fridge_base_w = 0.020
    comp_extra_kw = (fridge_daily_kwh - (fridge_base_w * 24.0)) / (24.0 * dt_h)
    p_fridge_day = np.full(96, fridge_base_w, dtype=float)
    p_fridge_day[::4] += comp_extra_kw  # 1 step (15 min) every hour
    p_fridge_kw = np.tile(p_fridge_day, 365)

    # 3. Water Purifier (if included, DUO Max: 146 kWh/year = 0.40 kWh/day)
    p_purifier_kw = np.zeros(n, dtype=float)
    if "water_purifier" in appliances:
        purifier_base_kw = 0.010
        purifier_extra_kw = (0.40 - (purifier_base_kw * 24.0)) / (12.0 * dt_h)
        purifier_day = np.full(96, purifier_base_kw, dtype=float)
        purifier_day[::8] += purifier_extra_kw  # cycle every 2 hours
        p_purifier_kw = np.tile(purifier_day, 365)

    # 4. ERV (if included, DUO Max: 30W continuous = 0.72 kWh/day)
    p_erv_kw = np.zeros(n, dtype=float)
    if "erv" in appliances:
        p_erv_kw = np.full(n, 0.030, dtype=float)

    # 5. Active Cooking: Induction & Lightwave Oven (Occupied days only)
    p_induction_kw = np.zeros(n, dtype=float)
    p_oven_kw = np.zeros(n, dtype=float)

    has_induction = "induction" in appliances or (not house_config)
    has_oven = "lightwave_oven" in appliances

    # Induction: Breakfast 0.30 kWh, Lunch 0.35 kWh, Dinner 0.5007 kWh (Total 1.1507 kWh/day = 420 kWh/yr)
    # Step indices: Breakfast 30 (07:30), Lunch 49 (12:15), Dinner 77-78 (19:15-19:45)
    for day in range(365):
        if is_occupied_day[day]:
            sh = day_shifts[day]
            day_slice = slice(day * 96, (day + 1) * 96)

            if has_induction:
                ind_prof = np.zeros(96, dtype=float)
                # Breakfast: 0.30 kWh in 15 min (1.20 kW)
                ind_prof[30 + sh[0]] += 0.30 / dt_h
                # Lunch: 0.35 kWh in 15 min (1.40 kW)
                ind_prof[49 + sh[1]] += 0.35 / dt_h
                # Dinner: 0.5007 kWh in 30 min (step 1: 1.40 kW, step 2: 0.6028 kW)
                ind_prof[77 + sh[2]] += 0.35 / dt_h
                ind_prof[78 + sh[2]] += 0.1507 / dt_h
                p_induction_kw[day_slice] = ind_prof

            if has_oven:
                # Oven: 0.2603 kWh in 15 min (1.0412 kW) at 18:45 (step 75)
                ov_prof = np.zeros(96, dtype=float)
                ov_prof[75 + sh[3]] += 0.2603 / dt_h
                p_oven_kw[day_slice] = ov_prof

    p_cooking_kw = p_induction_kw + p_oven_kw

    # 6. Dishwasher (Occupied days only: 185 kWh/yr = 0.5068 kWh/day)
    # Evening washing 20:30~21:30 (steps 82-85)
    p_dishwasher_kw = np.zeros(n, dtype=float)
    if "dishwasher" in appliances:
        for day in range(365):
            if is_occupied_day[day]:
                sh = day_shifts[day][4]
                dw_prof = np.zeros(96, dtype=float)
                # 4 steps: 0.22 kW, 0.15 kW, 0.08 kW, 0.0568 kW
                dw_prof[82 + sh] += 0.22 / dt_h
                dw_prof[83 + sh] += 0.15 / dt_h
                dw_prof[84 + sh] += 0.08 / dt_h
                dw_prof[85 + sh] += 0.0568 / dt_h
                p_dishwasher_kw[day * 96 : (day + 1) * 96] = dw_prof

    # 7. Laundry: Washing Machine (9kg) or WashTower (Occupied days only)
    p_laundry_kw = np.zeros(n, dtype=float)
    has_washtower = "washtower" in appliances
    has_washing = ("washing_machine" in appliances) and (not has_washtower)

    for day in range(365):
        if is_occupied_day[day]:
            sh = day_shifts[day][5]
            lau_prof = np.zeros(96, dtype=float)
            if has_washtower:
                # WashTower: 0.9452 kWh/day (세탁 0.3562 kWh + 건조 0.589 kWh, 09:15~11:00, 7 steps)
                # Steps 37-39 (세탁 45분): 0.3562 / (3 * 0.25) = 0.4749 kW
                # Steps 40-43 (건조 60분): 0.589 / (4 * 0.25) = 0.589 kW
                for s in range(37, 40):
                    lau_prof[s + sh] += 0.4749
                for s in range(40, 44):
                    lau_prof[s + sh] += 0.589
            elif has_washing:
                # Washing machine: 0.3562 kWh/day (09:15~10:00, 3 steps)
                for s in range(37, 40):
                    lau_prof[s + sh] += 0.4749
            p_laundry_kw[day * 96 : (day + 1) * 96] = lau_prof

    # 8. Person-dependent Plug Loads (Occupied days only: 0.90 kWh/(person*day))
    # Morning 06:30~08:30 (8 steps: 26 to 33, 25% energy)
    # Evening 18:00~23:00 (20 steps: 72 to 91, 75% energy)
    daily_plug_kwh = occupants * float(load_config.get("base_plug_load_per_person_day", 0.90))
    p_plug_kw = np.zeros(n, dtype=float)
    p_morn_plug = (0.25 * daily_plug_kwh / 8.0) / dt_h
    p_eve_plug = (0.75 * daily_plug_kwh / 20.0) / dt_h

    for day in range(365):
        if is_occupied_day[day]:
            sh = day_shifts[day][6]
            plug_prof = np.zeros(96, dtype=float)
            for s in range(26, 34):
                plug_prof[s + sh] += p_morn_plug
            for s in range(72, 92):
                plug_prof[s + sh] += p_eve_plug
            p_plug_kw[day * 96 : (day + 1) * 96] = plug_prof

    # 9. Lighting (Occupied days only: area * 4.3452 / 365 kWh/day)
    # Sunset to Bedtime: 18:00 ~ 23:30 (22 steps: 72 to 93)
    lighting_annual_per_m2 = float(load_config.get("lighting_annual_kwh_per_m2", 4.3452))
    daily_lighting_kwh = floor_area * (lighting_annual_per_m2 / 365.0)
    p_light_step = (daily_lighting_kwh / 22.0) / dt_h
    p_lighting_kw = np.zeros(n, dtype=float)

    for day in range(365):
        if is_occupied_day[day]:
            sh = day_shifts[day][7]
            light_prof = np.zeros(96, dtype=float)
            for s in range(72, 94):
                light_prof[s + sh] += p_light_step
            p_lighting_kw[day * 96 : (day + 1) * 96] = light_prof

    # Combined ventilation & standby
    p_base_vent_kw = p_standby_kw + p_purifier_kw + p_erv_kw

    # Total appliance load (kW)
    total_p_appliance_kw = (
        p_cooking_kw
        + p_dishwasher_kw
        + p_laundry_kw
        + p_fridge_kw
        + p_lighting_kw
        + p_plug_kw
        + p_base_vent_kw
    )

    # Internal heat gain to building indoor space: approx 85% sensible heat
    internal_heat_gain_w = total_p_appliance_kw * 1000.0 * 0.85

    breakdown = {
        "cooking_kw": p_cooking_kw + p_dishwasher_kw,  # 취사 (인덕션 + 오븐 + 식기세척기)
        "laundry_kw": p_laundry_kw,                    # 세탁·건조
        "fridge_kw": p_fridge_kw,                      # 냉장
        "lighting_kw": p_lighting_kw,                  # 조명
        "plug_kw": p_plug_kw,                          # 기타 가전 (TV/PC 플러그)
        "base_vent_kw": p_base_vent_kw,                # 환기·대기 (ERV + 정수기 + 대기)
    }

    return total_p_appliance_kw, internal_heat_gain_w, breakdown
