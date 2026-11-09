"""Domestic Hot Water (DHW) thermal demand model."""

from typing import Dict, Tuple
import numpy as np


def calculate_dhw_load(
    occupants: int,
    is_occupied_day: np.ndarray,
    load_config: Dict,
) -> np.ndarray:
    """Calculates 15-minute DHW thermal load profile (kW thermal) over 35,040 timesteps.

    DHW occurs only on occupied days.
    """
    n = 35040
    liters_per_person = float(load_config["dhw_consumption_per_person_day"])
    t_inlet = float(load_config["dhw_inlet_water_temp"])
    t_target = float(load_config["dhw_target_water_temp"])

    # Specific heat of water: 4.186 kJ/(kg*K) = 0.0011628 kWh/(kg*K)
    delta_t = max(0.0, t_target - t_inlet)
    daily_energy_kwh = occupants * liters_per_person * 0.0011628 * delta_t

    # Diurnal hourly fractions (summing to 1.0)
    hourly_distribution = np.zeros(24)
    # Morning showers / washing: 07:00 - 09:00
    hourly_distribution[7] = 0.20
    hourly_distribution[8] = 0.20
    # Mid-day cleaning / dishes: 12:00 - 13:00
    hourly_distribution[12] = 0.10
    # Evening showers / baths: 19:00 - 22:00
    hourly_distribution[19] = 0.15
    hourly_distribution[20] = 0.20
    hourly_distribution[21] = 0.15

    # 15-minute distribution per day (96 steps)
    daily_profile_15min_kw = np.repeat(hourly_distribution / 4.0, 4) * daily_energy_kwh / 0.25

    # Tile over 365 days, zeroing out unoccupied days
    q_dhw_kw = np.zeros(n, dtype=float)
    for day in range(365):
        if is_occupied_day[day]:
            q_dhw_kw[day * 96 : (day + 1) * 96] = daily_profile_15min_kw

    return q_dhw_kw

