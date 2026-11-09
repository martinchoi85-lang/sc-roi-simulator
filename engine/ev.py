"""Electric Vehicle (EV) charging load model."""

from typing import Dict
import numpy as np


def calculate_ev_load(
    has_ev: int,
    occupancy_rate: float,
    is_occupied_day: np.ndarray,
    load_config: Dict,
) -> np.ndarray:
    """Calculates 15-minute EV charging power profile (kW electrical) over 35,040 timesteps.

    Args:
        has_ev: 0 or 1
        occupancy_rate: Fraction (0.05 to 1.0)
        is_occupied_day: 365-day boolean array
        load_config: Configuration dictionary

    Returns:
        p_ev_kw array of shape (35040,)
    """
    n = 35040
    p_ev_kw = np.zeros(n, dtype=float)

    if has_ev == 0:
        return p_ev_kw

    annual_base_mileage = float(load_config["ev_annual_base_mileage_km"])
    efficiency = float(load_config["ev_efficiency_km_per_kwh"])
    charge_start_hour = int(load_config["ev_charge_start_hour"])
    charger_power = float(load_config["ev_charger_power_kw"])

    occupied_days_count = int(np.sum(is_occupied_day))
    if occupied_days_count == 0:
        return p_ev_kw

    # Mileage linked to occupancy rate
    actual_annual_mileage = annual_base_mileage * occupancy_rate
    daily_mileage = actual_annual_mileage / occupied_days_count
    daily_energy_needed_kwh = daily_mileage / efficiency

    # Charging duration in hours and 15-min intervals
    charge_duration_hours = daily_energy_needed_kwh / charger_power
    intervals_needed = int(np.ceil(charge_duration_hours / 0.25))

    start_interval_in_day = charge_start_hour * 4  # e.g., 23 * 4 = 92

    for day in range(365):
        if is_occupied_day[day]:
            remaining_kwh = daily_energy_needed_kwh
            # Charge starting at 23:00 (wrap around to early morning if needed)
            for step in range(intervals_needed):
                curr_step_in_day = (start_interval_in_day + step) % 96
                # Next day index if wrapped
                actual_day = day if (start_interval_in_day + step) < 96 else min(364, day + 1)
                global_idx = actual_day * 96 + curr_step_in_day

                step_energy = min(charger_power * 0.25, remaining_kwh)
                step_power = step_energy / 0.25
                p_ev_kw[global_idx] += step_power
                remaining_kwh -= step_energy
                if remaining_kwh <= 1e-4:
                    break

    return p_ev_kw

