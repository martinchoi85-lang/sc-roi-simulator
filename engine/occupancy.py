"""Occupancy calendar and diurnal schedule generator.

Rule-based statistical occupancy:
- No personas.
- Days allocated prioritized by:
  1. Annual peak load day (always forced to be occupied).
  2. Peak season weekends (Summer July/August, Autumn foliage October).
  3. Regular weekends (Saturdays, Sundays).
  4. Peak season weekdays.
  5. Regular weekdays.
- Diurnal profile represents aggregate presence.
"""

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd


def generate_occupancy_calendar(
    occupancy_rate: float,
    dates: pd.DatetimeIndex,
    peak_months: Optional[List[int]] = None,
    forced_peak_day: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generates a 365-day boolean array and a 35,040-step 15-minute presence array.

    Args:
        occupancy_rate: Fraction in [0.05, 0.10, 0.30, 0.50, 0.70, 1.00]
        dates: 35,040 DatetimeIndex
        peak_months: Months considered peak season (default: [7, 8, 10])
        forced_peak_day: Day of year (1-365) to strictly force as occupied.

    Returns:
        (is_occupied_day_365, is_occupied_15min)
    """
    if peak_months is None:
        peak_months = [7, 8, 10]

    # Daily level representation
    daily_dates = pd.date_range("2026-01-01", "2026-12-31", freq="D")
    total_days = len(daily_dates)  # 365
    target_occupied_days = int(round(total_days * occupancy_rate))

    # Priority score for each day of year
    # Higher score gets selected first
    scores = np.zeros(total_days, dtype=float)

    for i, d in enumerate(daily_dates):
        is_weekend = d.weekday() >= 5  # Sat=5, Sun=6
        is_peak = d.month in peak_months

        score = 0.0
        if is_peak and is_weekend:
            score = 100.0
        elif is_weekend:
            score = 75.0
        elif is_peak:
            score = 50.0
        else:
            score = 20.0

        # Add minor deterministic dispersion across months to avoid big contiguous blocks
        score += (d.day % 7) * 0.1
        scores[i] = score

    # Forced peak day gets maximum priority
    if forced_peak_day is not None and 1 <= forced_peak_day <= total_days:
        scores[forced_peak_day - 1] = 1000.0

    # Select top target_occupied_days
    ranked_indices = np.argsort(scores)[::-1]
    selected_indices = set(ranked_indices[:target_occupied_days])

    # Ensure forced peak day is occupied even if target_occupied_days is 0
    if forced_peak_day is not None and 1 <= forced_peak_day <= total_days:
        selected_indices.add(forced_peak_day - 1)

    is_occupied_day = np.zeros(total_days, dtype=bool)
    for idx in selected_indices:
        is_occupied_day[idx] = True

    # Expand to 35,040 15-minute steps (96 steps per day)
    # Diurnal occupant presence factor on occupied days:
    # 00:00 - 06:30 : sleeping (full presence 1.0)
    # 06:30 - 08:30 : morning active (1.0)
    # 08:30 - 17:30 : day outdoor/work (partial presence 0.35)
    # 17:30 - 23:00 : evening active (1.0)
    # 23:00 - 24:00 : sleeping (1.0)
    hour = dates.hour.values + dates.minute.values / 60.0
    diurnal_presence = np.where((hour >= 8.5) & (hour < 17.5), 0.35, 1.0)

    # Day index for each 15-min step
    day_indices = dates.dayofyear.values - 1
    day_occupied_expanded = is_occupied_day[day_indices]

    occupant_presence_15min = np.where(day_occupied_expanded, diurnal_presence, 0.0)

    return is_occupied_day, occupant_presence_15min

