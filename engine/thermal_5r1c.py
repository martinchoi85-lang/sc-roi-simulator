"""5R1C dynamic thermal network model with physical heating capacity bounds.

Calculates 15-minute sensible heating and cooling demand, accounting for:
- Envelope conduction (walls, roof, floor, windows)
- Infiltration and ventilation air exchange
- Solar heat gains through windows
- Internal heat gains (occupants, plug loads, lighting)
- Indoor setpoint control with freeze-protection setback during vacancy
- Physical equipment heating/cooling capacity constraints (prevents unphysical peak spikes)
"""

from typing import Dict, Tuple
import numpy as np


def simulate_thermal_5r1c(
    house_config: Dict,
    temp_air: np.ndarray,
    ghi: np.ndarray,
    occupant_presence: np.ndarray,
    internal_heat_gain_w: np.ndarray,
    is_occupied_day: np.ndarray,
    dt_sec: float = 900.0,  # 15 minutes
    max_heating_capacity_kw: float = 12.0,  # 9kW AWHP + 3kW backup heater
    max_cooling_capacity_kw: float = 8.0,
    heat_setpoint_schedule: np.ndarray = None,
    occupants_active: np.ndarray = None,
    occupants_sleeping: np.ndarray = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Simulates 15-minute building thermal dynamics over 35,040 timesteps.

    Cooling rules:
    - Only operated 6/1 ~ 9/30 (days 151 to 272). Outside this period, no mechanical cooling.
    - Setpoints: home-active 26°C, sleep 27°C, away / unoccupied day stopped.
    - Heating setpoints: 20/18/16/10°C from schedule.
    - t_set returns active setpoint during HVAC operation, or indoor temp when free-floating.

    Returns:
        (t_indoor, q_heat_kw, q_cool_kw, t_set)
    """
    n = len(temp_air)
    floor_area = float(house_config["floor_area"])
    roof_area = float(house_config["roof_area"])
    window_area = float(house_config["window_area"])

    # Wall area from config or estimated from perimeter
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
    c_internal = float(house_config["c_internal"])  # J/(m2*K)
    infiltration_ach = float(house_config["infiltration_ach"])

    setpoint_heat_occ = float(house_config.get("setpoint_heat_occupied", 20.0).get("value", 20.0) if isinstance(house_config.get("setpoint_heat_occupied", 20.0), dict) else house_config.get("setpoint_heat_occupied", 20.0))
    setpoint_freeze = float(house_config.get("setpoint_heat_unoccupied", 10.0).get("value", 10.0) if isinstance(house_config.get("setpoint_heat_unoccupied", 10.0), dict) else house_config.get("setpoint_heat_unoccupied", 10.0))

    # Lumped conductance H_tr (W/K)
    h_tr = (
        u_wall * wall_net_area
        + u_roof * roof_area
        + u_floor * floor_area
        + u_window * window_area
    )

    # Infiltration/ventilation H_ve (W/K)
    room_volume = floor_area * 2.6
    h_ve = 1200.0 * room_volume * (infiltration_ach / 3600.0)

    h_tot = h_tr + h_ve
    c_m = c_internal * floor_area  # J/K
    tau = c_m / h_tot  # seconds

    f_frame = 0.85
    q_sol = ghi * window_area * shgc * f_frame

    occupants = float(house_config["occupants"])
    q_occ = occupant_presence * occupants * 80.0
    q_gains = q_sol + q_occ + internal_heat_gain_w

    day_indices = np.arange(n) // 96
    day_occupied_15min = is_occupied_day[day_indices]

    t_indoor = np.zeros(n, dtype=float)
    q_heat_kw = np.zeros(n, dtype=float)
    q_cool_kw = np.zeros(n, dtype=float)
    t_set = np.zeros(n, dtype=float)

    decay = np.exp(-dt_sec / tau)
    heat_gain_factor = h_tot / (1.0 - decay)

    max_heat_w = max_heating_capacity_kw * 1000.0
    max_cool_w = max_cooling_capacity_kw * 1000.0

    t_curr = 20.0

    for i in range(n):
        t_amb = temp_air[i]
        q_g = q_gains[i]
        t_inf = t_amb + q_g / h_tot
        t_free = t_inf + (t_curr - t_inf) * decay

        d_idx = day_indices[i]
        is_occ = day_occupied_15min[i]

        # Heating setpoint
        if heat_setpoint_schedule is not None:
            t_set_heat = float(heat_setpoint_schedule[i])
        else:
            t_set_heat = setpoint_heat_occ if is_occ else setpoint_freeze

        # Cooling setpoint & allowance: only 6/1 ~ 9/30 (days 151 to 272 inclusive)
        is_cooling_season = (151 <= d_idx <= 272)
        allow_cooling = False
        t_set_cool = 40.0

        if is_cooling_season and is_occ:
            act_n = float(occupants_active[i]) if occupants_active is not None else (1.0 if occupant_presence[i] > 0 else 0.0)
            sleep_n = float(occupants_sleeping[i]) if occupants_sleeping is not None else 0.0

            if act_n > 0:
                allow_cooling = True
                t_set_cool = 26.0
            elif sleep_n > 0:
                allow_cooling = True
                t_set_cool = 27.0
            else:
                allow_cooling = False
                t_set_cool = 40.0

        # Thermal response and setpoint resolution
        if t_free < t_set_heat:
            # Heating demand
            q_needed_w = (t_set_heat - t_free) * heat_gain_factor
            q_actual_w = min(q_needed_w, max_heat_w)
            q_heat_kw[i] = q_actual_w / 1000.0
            t_curr = t_free + (q_actual_w / heat_gain_factor)
            t_set[i] = t_set_heat

        elif allow_cooling and (t_free > t_set_cool):
            # Cooling demand
            q_needed_w = (t_free - t_set_cool) * heat_gain_factor
            q_actual_w = min(q_needed_w, max_cool_w)
            q_cool_kw[i] = q_actual_w / 1000.0
            t_curr = t_free - (q_actual_w / heat_gain_factor)
            t_set[i] = t_set_cool

        else:
            t_curr = t_free
            # Unoperated: set to current indoor temperature
            t_set[i] = t_curr

        t_indoor[i] = t_curr

    return t_indoor, q_heat_kw, q_cool_kw, t_set
