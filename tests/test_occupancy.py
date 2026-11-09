"""Unit tests for occupancy schedule generation."""

import numpy as np
import pandas as pd
from engine.occupancy import generate_occupancy_calendar


def test_occupancy_peak_day_forced():
    dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:45:00", freq="15min")
    forced_day = 218  # August peak heat wave day

    for occ_rate in [0.05, 0.10, 0.30, 0.50, 0.70, 1.00]:
        is_occ_day, occ_presence = generate_occupancy_calendar(
            occupancy_rate=occ_rate,
            dates=dates,
            peak_months=[7, 8, 10],
            forced_peak_day=forced_day,
        )

        assert len(is_occ_day) == 365
        assert len(occ_presence) == 35040
        # Peak day MUST be occupied
        assert is_occ_day[forced_day - 1] is np.True_ or is_occ_day[forced_day - 1] == True

        # Check total occupied days is close to target
        expected_days = round(365 * occ_rate)
        assert abs(int(np.sum(is_occ_day)) - expected_days) <= 1

