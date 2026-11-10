"""Occupancy calendar generator for Second-Home Smart Cottage (v9).

Rules:
- 2026 Calendar with Korean official public holidays (holidays.KR).
- Public holidays apply Sunday profile.
- Occupied day selection priority:
  1. Saturdays, Sundays, and public holidays.
  2. Fridays and days preceding public holidays (if not in 1).
  3. Mondays and days succeeding public holidays (if not in 1, 2).
  4. Other weekdays.
- Within each priority group, select evenly spaced across the year (no seasonal bias).
- Target occupied days = round(365 * occupancy_rate).
- On occupied weekdays, residents commute (commuter weekday profile).
- Arrival/departure partial presence ignored (ASSUMPTION).
- Unoccupied days: Continuous base load (fridge, water purifier, ERV, standby) only.
"""

from datetime import timedelta
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import holidays


def get_korea_2026_holidays() -> holidays.HolidayBase:
    """Returns official Korean holidays for 2026."""
    return holidays.KR(years=2026)


def select_evenly_spaced(items: List[int], k: int) -> List[int]:
    """Selects k items from a list evenly distributed across indices."""
    n = len(items)
    if k <= 0 or n == 0:
        return []
    if k >= n:
        return list(items)
    if k == 1:
        return [items[n // 2]]
    # Pick evenly spaced indices
    selected_indices = np.round(np.linspace(0, n - 1, k)).astype(int)
    # Deduplicate while preserving order if any collision
    seen = set()
    result = []
    for idx in selected_indices:
        if idx not in seen:
            seen.add(idx)
            result.append(items[idx])
    # If deduplication dropped any, fill greedily from nearest available
    if len(result) < k:
        for i in range(n):
            if i not in seen:
                result.append(items[i])
                seen.add(i)
                if len(result) == k:
                    break
    result.sort()
    return result


def generate_occupancy_calendar(
    occupancy_rate: float,
    dates: Optional[pd.DatetimeIndex] = None,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Generates a 365-day boolean array and profile types.

    Args:
        occupancy_rate: Fraction in [0.15, 0.30, 0.50, 0.70, 1.00]
        dates: 35,040 15-minute DatetimeIndex for 2026. If None, generated.

    Returns:
        (is_occupied_day_365, is_occupied_15min, day_types_365)
        day_types_365 elements are: 'weekday', 'saturday', 'sunday' (holidays mapped to sunday)
    """
    daily_dates = pd.date_range("2026-01-01", "2026-12-31", freq="D")
    total_days = len(daily_dates)  # 365
    target_occupied_days = int(round(total_days * occupancy_rate))

    kr_holidays = get_korea_2026_holidays()

    # Determine day types for each day
    day_types = []
    bucket1 = []  # Saturday, Sunday, Public Holiday
    bucket2 = []  # Friday or Day before holiday
    bucket3 = []  # Monday or Day after holiday
    bucket4 = []  # Other weekdays

    for i, d in enumerate(daily_dates):
        date_obj = d.date()
        is_holiday = date_obj in kr_holidays
        weekday = d.weekday()  # Mon=0, ..., Sun=6

        if is_holiday or weekday == 6:
            day_types.append("sunday")
        elif weekday == 5:
            day_types.append("saturday")
        else:
            day_types.append("weekday")

        # Prioritization
        if weekday in (5, 6) or is_holiday:
            bucket1.append(i)
        else:
            # Check if eve of holiday or Friday
            next_date = date_obj + timedelta(days=1)
            prev_date = date_obj - timedelta(days=1)
            is_eve = next_date in kr_holidays
            is_post = prev_date in kr_holidays

            if weekday == 4 or is_eve:
                bucket2.append(i)
            elif weekday == 0 or is_post:
                bucket3.append(i)
            else:
                bucket4.append(i)

    # Select target_occupied_days following priority 1 -> 2 -> 3 -> 4
    selected_day_indices = []
    remaining = target_occupied_days

    for bucket in [bucket1, bucket2, bucket3, bucket4]:
        if remaining <= 0:
            break
        if len(bucket) <= remaining:
            selected_day_indices.extend(bucket)
            remaining -= len(bucket)
        else:
            chosen = select_evenly_spaced(bucket, remaining)
            selected_day_indices.extend(chosen)
            remaining = 0
            break

    is_occupied_day = np.zeros(total_days, dtype=bool)
    is_occupied_day[selected_day_indices] = True

    if dates is None:
        dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:45:00", freq="15min")

    day_indices = dates.dayofyear.values - 1
    # Handle leap year edge cases safely though 2026 is 365 days
    day_indices = np.clip(day_indices, 0, total_days - 1)
    is_occupied_15min = is_occupied_day[day_indices]

    return is_occupied_day, is_occupied_15min, day_types
