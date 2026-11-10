"""Domestic Hot Water (DHW) thermal demand model."""

from typing import Dict
import numpy as np


def calculate_dhw_load(
    occupants: int,
    is_occupied_day: np.ndarray,
    load_config: Dict,
    seed: int = 42,
) -> np.ndarray:
    """Calculates 15-minute DHW thermal load profile (kW thermal) over 35,040 timesteps.

    DHW occurs only on occupied days, concentrated in morning and evening shower windows.
    Applies deterministic +/-15min random shift with fixed seed while strictly preserving total energy.
    """
    n = 35040
    liters_per_person = float(load_config["dhw_consumption_per_person_day"])
    t_inlet = float(load_config["dhw_inlet_water_temp"])
    t_target = float(load_config["dhw_target_water_temp"])

    # Specific heat of water: 4.186 kJ/(kg*K) = 0.0011628 kWh/(kg*K)
    delta_t = max(0.0, t_target - t_inlet)
    daily_energy_kwh = occupants * liters_per_person * 0.0011628 * delta_t

    # Morning shower: 07:00 - 08:30 (6 steps, indices 28 to 33), 50% of energy
    # Evening shower: 20:00 - 21:30 (6 steps, indices 80 to 85), 50% of energy
    morning_steps = list(range(28, 34))  # 6 steps
    evening_steps = list(range(80, 86))  # 6 steps

    p_morning = (0.50 * daily_energy_kwh / len(morning_steps)) / 0.25
    p_evening = (0.50 * daily_energy_kwh / len(evening_steps)) / 0.25

    rng = np.random.RandomState(seed)
    day_shifts_m = rng.choice([-1, 0, 1], size=365)
    day_shifts_e = rng.choice([-1, 0, 1], size=365)

    q_dhw_kw = np.zeros(n, dtype=float)

    for day in range(365):
        if is_occupied_day[day]:
            day_profile = np.zeros(96, dtype=float)
            shift_m = int(day_shifts_m[day])
            shift_e = int(day_shifts_e[day])

            for s in morning_steps:
                day_profile[s + shift_m] += p_morning

            for s in evening_steps:
                day_profile[s + shift_e] += p_evening

            q_dhw_kw[day * 96 : (day + 1) * 96] = day_profile

    return q_dhw_kw
