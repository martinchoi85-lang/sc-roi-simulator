"""Unit tests for occupancy schedule generation (v9)."""

import pandas as pd
from engine.occupancy import generate_occupancy_calendar


def test_occupancy_days_exact_round():
    """Verifies that occupied days exactly match round(365 * occupancy_rate)."""
    occupancy_rates = [1.00, 0.70, 0.50, 0.30, 0.15]
    expected_days = [365, 255, 182, 110, 55]

    for occ_rate, exp in zip(occupancy_rates, expected_days):
        is_occ_day, is_occ_15min, day_types = generate_occupancy_calendar(occ_rate)
        assert is_occ_day.sum() == exp
        assert is_occ_day.sum() == round(365 * occ_rate)
        assert len(is_occ_15min) == 35040
        assert len(day_types) == 365
