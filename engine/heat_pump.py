"""Heating, cooling, and DHW equipment simulation with HM091HF performance model."""

from typing import Dict, Any, Tuple, Optional, Union
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
    t_indoor: Optional[np.ndarray] = None,
    t_set_heat: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Calculates 15-minute electrical demand, backup heater usage, and fuel consumption.

    Rules (SPEC v9.1 & update):
    - Standard system air conditioner with identical efficiency (COP 4.40) across baseline and all alternatives.
    - AWHP electric backup heater operates ONLY when indoor temperature is below (t_set_heat - 1.5°C).

    Returns:
        Dict with electrical profiles, backup heater metrics, and propane usage.
    """
    n = len(temp_air)
    awhp_cfg = equipment_config["awhp_system"]

    # All alternatives and baseline use the same standard system air conditioner (COP 4.40)
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

        # Space heating split between AWHP and backup heater
        q_heat_awhp = np.minimum(q_heat_kw, max_cap_heat)
        q_heat_rem = np.maximum(0.0, q_heat_kw - max_cap_heat)

        # Backup heater constraint: operates ONLY when indoor temp < t_set_heat - 1.5°C
        if t_indoor is not None and t_set_heat is not None:
            allow_backup = (t_indoor < (t_set_heat - 1.5))
        else:
            allow_backup = np.ones(n, dtype=bool)

        q_heat_backup = np.where(allow_backup, np.minimum(q_heat_rem, max_backup_cap), 0.0)
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


def mains_water_temp_daily(temp_air: np.ndarray, latitude: float) -> np.ndarray:
    """Calculates daily mains water temperature according to EnergyPlus Site:WaterMainsTemperature correlation (Burch & Christensen, NREL).

    T_mains = (T_out_avg + 6°F) + ratio * (delta_T_maxdiff * 1.8 / 2) * sin(0.986 * (day - 15 - lag) - 90°)
    ratio = 0.4 + 0.01 * (T_out_avg_F - 44)
    lag = 35 - 1.0 * (T_out_avg_F - 44)
    Southern hemisphere (latitude < 0) shifts phase by 182 days.
    Lower bound: 4.0 °C.
    """
    temp_arr = np.asarray(temp_air, dtype=float)
    daily_temp = temp_arr.reshape(365, -1).mean(axis=1)
    t_avg = float(daily_temp.mean())
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    m_starts = np.cumsum([0] + month_days[:-1])
    m_ends = np.cumsum(month_days)
    monthly_means = [float(daily_temp[s:e].mean()) for s, e in zip(m_starts, m_ends)]
    max_diff = max(monthly_means) - min(monthly_means)

    t_avg_f = t_avg * 1.8 + 32.0
    ratio = 0.4 + 0.01 * (t_avg_f - 44.0)
    lag = 35.0 - 1.0 * (t_avg_f - 44.0)
    if latitude < 0:
        lag -= 182.0

    days = np.arange(1, 366)
    angle_deg = 0.986 * (days - 15.0 - lag) - 90.0
    angle_rad = np.radians(angle_deg)
    t_mains_f = (t_avg_f + 6.0) + ratio * (max_diff * 1.8 / 2.0) * np.sin(angle_rad)
    t_mains_c = (t_mains_f - 32.0) / 1.8
    return np.maximum(4.0, t_mains_c)


def generate_event_based_dhw(
    occupants: int,
    is_occupied_15min: np.ndarray,
    occupants_active_15min: np.ndarray,
    is_occupied_day_365: np.ndarray,
    seed: int = 42,
    use_dhw_v2: bool = False,
    persons_state_15min: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Generates 15-minute event-based domestic hot water draw profile.

    Rules:
    - 75 L per occupant per occupied day (0 L on unoccupied days).
    - Divided into discrete events per person:
      - 1 shower event: 50 L
      - 2 basin/sink events: 15 L, 10 L
    - Events occur ONLY when occupant is at home and active (state == 1).
    - Event timing weighted by daily active schedule.
    - Preserves exact 75 L/person/occupied day (+-0.0% error).
    """
    n_steps = len(is_occupied_15min)
    dhw_draw_liters = np.zeros(n_steps, dtype=float)
    rng = np.random.default_rng(seed)

    steps_per_day = 96
    for d in range(365):
        if not is_occupied_day_365[d]:
            continue
        s_idx = d * steps_per_day
        e_idx = s_idx + steps_per_day

        day_active = (occupants_active_15min[s_idx:e_idx] >= 1.0) & (is_occupied_15min[s_idx:e_idx] == 1)
        active_indices = np.where(day_active)[0]
        if len(active_indices) == 0:
            day_occ = (is_occupied_15min[s_idx:e_idx] == 1)
            active_indices = np.where(day_occ)[0]
        if len(active_indices) == 0:
            continue

        if not use_dhw_v2:
            for p in range(occupants):
                weights = np.ones(len(active_indices), dtype=float)
                for idx_pos, step_in_day in enumerate(active_indices):
                    if 24 <= step_in_day <= 36:  # Morning peak 6:00~9:00
                        weights[idx_pos] = 3.0
                    elif 76 <= step_in_day <= 92:  # Evening peak 19:00~23:00
                        weights[idx_pos] = 4.0
                    elif 44 <= step_in_day <= 56:  # Lunch 11:00~14:00
                        weights[idx_pos] = 1.5
                weights /= weights.sum()

                chosen_indices = rng.choice(active_indices, size=3, replace=True, p=weights)
                dhw_draw_liters[s_idx + chosen_indices[0]] += 50.0
                dhw_draw_liters[s_idx + chosen_indices[1]] += 15.0
                dhw_draw_liters[s_idx + chosen_indices[2]] += 10.0
        else:
            for p in range(occupants):
                if persons_state_15min is not None and len(persons_state_15min) > p:
                    p_active = (persons_state_15min[p, s_idx:e_idx] == 1) & (is_occupied_15min[s_idx:e_idx] == 1)
                    p_indices = np.where(p_active)[0]
                else:
                    p_indices = np.array([], dtype=int)

                cand_indices = p_indices if len(p_indices) > 0 else active_indices

                # 샤워 50L 가중: 06–09시 3, 18–23시 4, 그 밖 0.3
                weights_shower = np.full(len(cand_indices), 0.3, dtype=float)
                for idx_pos, step_in_day in enumerate(cand_indices):
                    if 24 <= step_in_day <= 36:  # 06:00~09:00
                        weights_shower[idx_pos] = 3.0
                    elif 72 <= step_in_day <= 92:  # 18:00~23:00
                        weights_shower[idx_pos] = 4.0
                weights_shower /= weights_shower.sum()

                # 세면 15L·10L는 지금 가중 그대로
                weights_basin = np.ones(len(cand_indices), dtype=float)
                for idx_pos, step_in_day in enumerate(cand_indices):
                    if 24 <= step_in_day <= 36:  # Morning peak 6:00~9:00
                        weights_basin[idx_pos] = 3.0
                    elif 76 <= step_in_day <= 92:  # Evening peak 19:00~23:00
                        weights_basin[idx_pos] = 4.0
                    elif 44 <= step_in_day <= 56:  # Lunch 11:00~14:00
                        weights_basin[idx_pos] = 1.5
                weights_basin /= weights_basin.sum()

                chosen_shower = rng.choice(cand_indices, p=weights_shower)
                chosen_basin = rng.choice(cand_indices, size=2, replace=True, p=weights_basin)
                dhw_draw_liters[s_idx + chosen_shower] += 50.0
                dhw_draw_liters[s_idx + chosen_basin[0]] += 15.0
                dhw_draw_liters[s_idx + chosen_basin[1]] += 10.0

    return dhw_draw_liters


def simulate_dhw_tank_reheat(
    dhw_draw_liters: np.ndarray,
    temp_air: np.ndarray,
    awhp_cfg: Dict[str, Any],
    tank_volume_liters: float = 200.0,
    supply_water_temp: float = 55.0,
    mains_water_temp: Union[float, np.ndarray] = 15.0,
    dt_hours: float = 0.25,
    use_tank_v2: bool = False,
    ua_tank_w_per_k: float = 1.35,
    t_ambient_tank: float = 20.0,
    hysteresis_fraction: float = 0.3,
    return_details: bool = False,
) -> Union[Tuple[np.ndarray, np.ndarray, float], Tuple[np.ndarray, np.ndarray, float, Dict[str, Any]]]:
    """Simulates AWHP DHW storage tank reheat dynamics.

    Rules:
    - Tank volume: config or 200L PLACEHOLDER.
    - Draws deplete hot water, adding to reheat energy deficit:
      Q_deficit += Draw_L * 4.186 * (55 - 15) / 3600 [kWh_th].
    - AWHP reheats at maximum heating capacity at W55:
      Q_cap_15m = max_cap_dhw(T_air) * dt_hours [kWh_th].
    - Reheat delivered = min(Q_deficit, Q_cap_15m).
    - Gas case has 0 electric power (handled separately).

    Returns:
        (p_dhw_elec_kw, q_dhw_th_kw, annual_dhw_elec_kwh)
    """
    n = len(dhw_draw_liters)
    p_dhw_elec = np.zeros(n, dtype=float)
    q_dhw_th = np.zeros(n, dtype=float)

    cop_dhw = calculate_hm091hf_cop(temp_air, supply_water_temp, awhp_cfg)
    max_cap_dhw = calculate_hm091hf_max_capacity(temp_air, supply_water_temp, cop_dhw, awhp_cfg)

    if not use_tank_v2:
        mains_t = float(mains_water_temp) if isinstance(mains_water_temp, (int, float)) else float(mains_water_temp[0])
        delta_t = supply_water_temp - mains_t
        kwh_per_liter = 4.186 * delta_t / 3600.0

        q_deficit_kwh = 0.0
        for i in range(n):
            draw_l = dhw_draw_liters[i]
            if draw_l > 0:
                q_deficit_kwh += draw_l * kwh_per_liter

            if q_deficit_kwh > 1e-4:
                cap_kwh = max_cap_dhw[i] * dt_hours
                q_reheat_kwh = min(q_deficit_kwh, cap_kwh)
                q_deficit_kwh -= q_reheat_kwh

                q_th_kw = q_reheat_kwh / dt_hours
                p_elec_kw = q_th_kw / max(1.0, cop_dhw[i])

                q_dhw_th[i] = q_th_kw
                p_dhw_elec[i] = p_elec_kw

        annual_dhw_elec_kwh = float(np.sum(p_dhw_elec) * dt_hours)
        return p_dhw_elec, q_dhw_th, annual_dhw_elec_kwh

    # v2: Hysteresis (0.3 of tank capacity) + Standby loss (UA * 35K * 0.25h)
    if isinstance(mains_water_temp, (int, float)):
        tm_arr = np.full(n, float(mains_water_temp))
    else:
        tm_arr = np.asarray(mains_water_temp, dtype=float)
        if len(tm_arr) == 365:
            tm_arr = np.repeat(tm_arr, n // 365)

    standby_loss_kwh = ua_tank_w_per_k * (supply_water_temp - t_ambient_tank) * dt_hours / 1000.0
    D = 0.0
    is_reheating = False
    reheat_starts = 0

    for i in range(n):
        tm = tm_arr[i]
        draw_l = dhw_draw_liters[i]
        use_kwh = draw_l * 4.186 * (supply_water_temp - tm) / 3600.0
        D += use_kwh + standby_loss_kwh
        c_tank = tank_volume_liters * 4.186 * (supply_water_temp - tm) / 3600.0

        if not is_reheating:
            if D >= hysteresis_fraction * c_tank:
                is_reheating = True
                reheat_starts += 1

        if is_reheating:
            cap_kwh = max_cap_dhw[i] * dt_hours
            q_reheat_kwh = min(D, cap_kwh)
            D -= q_reheat_kwh

            q_th_kw = q_reheat_kwh / dt_hours
            p_elec_kw = q_th_kw / max(1.0, cop_dhw[i])

            q_dhw_th[i] = q_th_kw
            p_dhw_elec[i] = p_elec_kw

            if D <= 1e-6:
                D = max(0.0, D)
                is_reheating = False

    annual_dhw_elec_kwh = float(np.sum(p_dhw_elec) * dt_hours)
    if return_details:
        details = {
            "reheat_starts": reheat_starts,
            "reheat_hours": float((p_dhw_elec > 0).sum() * dt_hours),
            "annual_standby_loss_kwh_th": float(standby_loss_kwh * n),
            "final_deficit_kwh": float(D),
        }
        return p_dhw_elec, q_dhw_th, annual_dhw_elec_kwh, details
    return p_dhw_elec, q_dhw_th, annual_dhw_elec_kwh


def simulate_awhp_space_heating_with_capacity_bound(
    house_config: Dict[str, Any],
    temp_air: np.ndarray,
    ghi: np.ndarray,
    occupant_presence: np.ndarray,
    internal_heat_gain_w: np.ndarray,
    is_occupied_day: np.ndarray,
    heat_setpoint_schedule: np.ndarray,
    occupants_active: np.ndarray,
    occupants_sleeping: np.ndarray,
    awhp_cfg: Dict[str, Any],
    dt_sec: float = 900.0,
    passive: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Simulates 5R1C space heating with HM091HF maximum capacity bound and 3kW backup heater.

    Rules:
    - 15-minute supplied heating heat <= HM091HF datasheet maximum capacity (interpolated by ambient temp at W40).
    - Deficit beyond maximum capacity is handled by electric backup heater (<= 3 kW).
    - Backup heater operates ONLY when indoor temp < (setpoint - 1.5°C).
    - If capacity is still deficient, indoor temperature drops below setpoint (unmet hours tracked).
    - Tracks:
      - 15-minute maximum heating power (kW)
      - Compressor share (kW) and backup heater share (kW) at peak time
      - Unmet heating hours (hours indoor temp < setpoint - 0.1°C)
    """
    n = len(temp_air)
    dt_h = dt_sec / 3600.0

    floor_area = float(house_config["floor_area"])
    roof_area = float(house_config["roof_area"])
    window_area = float(house_config["window_area"])

    if "gross_wall_area" in house_config:
        wall_net_area = max(10.0, float(house_config["gross_wall_area"]) - window_area)
    else:
        perimeter = 4.0 * np.sqrt(floor_area)
        wall_net_area = max(10.0, (perimeter * 2.8) - window_area)

    u_wall = float(house_config["u_wall"])
    u_roof = float(house_config["u_roof"])
    u_floor = float(house_config["u_floor"])
    u_window = float(house_config["u_window"])
    shgc = float(house_config["shgc"])
    c_internal = float(house_config["c_internal"])
    infiltration_ach = float(house_config["infiltration_ach"])

    h_tr = (u_wall * wall_net_area + u_roof * roof_area + u_floor * floor_area + u_window * window_area)
    room_volume = floor_area * 2.6
    h_ve = 1200.0 * room_volume * (infiltration_ach / 3600.0)
    h_tot = h_tr + h_ve
    c_m = c_internal * floor_area
    tau = c_m / h_tot

    f_frame = 0.85
    q_sol = ghi * window_area * shgc * f_frame
    occupants = float(house_config.get("occupants", 2))
    q_occ = occupant_presence * occupants * 80.0
    q_gains = q_sol + q_occ + internal_heat_gain_w

    day_indices = np.arange(n) // 96
    day_occupied_15min = is_occupied_day[day_indices]

    decay = np.exp(-dt_sec / tau)
    heat_gain_factor = h_tot / (1.0 - decay)

    t_water_heat = float(awhp_cfg.get("heating_leaving_water_temp", 40.0))
    cop_heat = calculate_hm091hf_cop(temp_air, t_water_heat, awhp_cfg)
    max_cap_heat_kw = calculate_hm091hf_max_capacity(temp_air, t_water_heat, cop_heat, awhp_cfg)
    max_backup_kw = float(awhp_cfg.get("backup_heater_capacity_kw", 3.0))
    cop_cool_std = float(awhp_cfg.get("cop_cool_nominal", 4.40))

    t_indoor = np.zeros(n, dtype=float)
    q_heat_awhp_kw = np.zeros(n, dtype=float)
    q_heat_backup_kw = np.zeros(n, dtype=float)
    p_comp_kw = np.zeros(n, dtype=float)
    p_backup_kw = np.zeros(n, dtype=float)
    q_cool_kw = np.zeros(n, dtype=float)
    p_cool_kw = np.zeros(n, dtype=float)
    t_set = np.zeros(n, dtype=float)
    unmet_step_mask = np.zeros(n, dtype=bool)

    # Warm-up preconditioning using December (day 334 to 364, timesteps 32064 to n)
    # to establish realistic winter dynamic thermal equilibrium at start of year (Jan 1 00:00).
    dec_start_idx = 334 * 96
    t_curr = 20.0
    if passive is not None:
        from engine import passive_climate as _pc
        _sol_full = passive["window_irr"] * window_area * shgc * f_frame
        _q_nosol = q_gains - q_sol
        _home = (occupants_active + occupants_sleeping) > 0

    def _free(i, t_curr):
        if passive is None:
            t_inf = temp_air[i] + q_gains[i] / h_tot
            return t_inf + (t_curr - t_inf) * decay, heat_gain_factor
        return _pc.step(passive, i, t_curr, temp_air[i], _q_nosol[i], _sol_full[i], _home[i], h_tot, room_volume, c_m, dt_sec)

    for i in range(dec_start_idx, n):
        t_amb = temp_air[i]
        t_free, hgf = _free(i, t_curr)
        d_idx = day_indices[i]
        is_occ = day_occupied_15min[i]
        t_set_heat = float(heat_setpoint_schedule[i]) if heat_setpoint_schedule is not None else (20.0 if is_occ else 10.0)

        if t_free < t_set_heat:
            q_needed_w = (t_set_heat - t_free) * hgf
            q_needed_kw = max(0.0, q_needed_w / 1000.0)
            cap_awhp = max_cap_heat_kw[i]
            q_awhp = min(q_needed_kw, cap_awhp)
            t_temp = t_free + (q_awhp * 1000.0) / hgf
            if t_temp < (t_set_heat - 1.5):
                q_deficit = q_needed_kw - q_awhp
                q_backup = min(q_deficit, max_backup_kw)
            else:
                q_backup = 0.0
            q_actual_kw = q_awhp + q_backup
            t_curr = t_free + (q_actual_kw * 1000.0) / hgf
        else:
            t_curr = t_free

    for i in range(n):
        t_amb = temp_air[i]
        t_free, hgf = _free(i, t_curr)

        d_idx = day_indices[i]
        is_occ = day_occupied_15min[i]

        t_set_heat = float(heat_setpoint_schedule[i]) if heat_setpoint_schedule is not None else (20.0 if is_occ else 10.0)

        # Cooling
        is_cooling_season = (151 <= d_idx <= 272) if (passive is None or passive.get('cooling_doy') is None) else bool(passive['cooling_doy'][d_idx])
        allow_cooling = False
        t_set_cool = 40.0

        if is_cooling_season and is_occ:
            act_n = float(occupants_active[i]) if occupants_active is not None else 1.0
            sleep_n = float(occupants_sleeping[i]) if occupants_sleeping is not None else 0.0
            if act_n > 0:
                allow_cooling = True
                t_set_cool = 26.0
            elif sleep_n > 0:
                allow_cooling = True
                t_set_cool = 27.0

        # Heating demand
        if t_free < t_set_heat:
            t_set[i] = t_set_heat
            q_needed_w = (t_set_heat - t_free) * hgf
            q_needed_kw = max(0.0, q_needed_w / 1000.0)

            # AWHP Compressor
            cap_awhp = max_cap_heat_kw[i]
            q_awhp = min(q_needed_kw, cap_awhp)

            # Temp achieved with AWHP alone
            t_temp = t_free + (q_awhp * 1000.0) / hgf

            # Backup heater rule: operates ONLY when indoor temp < (setpoint - 1.5°C)
            if t_temp < (t_set_heat - 1.5):
                q_deficit = q_needed_kw - q_awhp
                q_backup = min(q_deficit, max_backup_kw)
            else:
                q_backup = 0.0

            q_actual_kw = q_awhp + q_backup
            t_curr = t_free + (q_actual_kw * 1000.0) / hgf

            # Track unmet heating hours
            if t_curr < (t_set_heat - 0.1):
                unmet_step_mask[i] = True

            q_heat_awhp_kw[i] = q_awhp
            q_heat_backup_kw[i] = q_backup
            p_comp_kw[i] = q_awhp / cop_heat[i] if q_awhp > 0 else 0.0
            p_backup_kw[i] = q_backup / 1.0

        elif allow_cooling and (t_free > t_set_cool):
            t_set[i] = t_set_cool
            q_needed_w = (t_free - t_set_cool) * hgf
            q_actual_w = min(q_needed_w, 8000.0)
            q_cool_kw[i] = q_actual_w / 1000.0
            p_cool_kw[i] = q_cool_kw[i] / cop_cool_std
            t_curr = t_free - (q_actual_w / hgf)

        else:
            t_curr = t_free
            t_set[i] = t_curr

        t_indoor[i] = t_curr

    p_heating_total_kw = p_comp_kw + p_backup_kw
    peak_idx = int(np.argmax(p_heating_total_kw))
    max_heating_power_kw = float(p_heating_total_kw[peak_idx])
    comp_share_kw = float(p_comp_kw[peak_idx])
    backup_share_kw = float(p_backup_kw[peak_idx])
    unmet_hours = float(np.sum(unmet_step_mask) * dt_h)

    return {
        "t_indoor": t_indoor,
        "t_set": t_set,
        "q_heat_awhp_kw": q_heat_awhp_kw,
        "q_heat_backup_kw": q_heat_backup_kw,
        "q_heat_total_kw": q_heat_awhp_kw + q_heat_backup_kw,
        "p_comp_kw": p_comp_kw,
        "p_backup_kw": p_backup_kw,
        "p_heating_total_kw": p_heating_total_kw,
        "q_cool_kw": q_cool_kw,
        "p_cooling_kw": p_cool_kw,
        "max_heating_power_kw": max_heating_power_kw,
        "peak_time_index": peak_idx,
        "peak_comp_share_kw": comp_share_kw,
        "peak_backup_share_kw": backup_share_kw,
        "unmet_hours": unmet_hours,
        "backup_heater_hours": float(np.sum(p_backup_kw > 0) * dt_h),
        "backup_heater_kwh": float(np.sum(p_backup_kw) * dt_h),
    }
