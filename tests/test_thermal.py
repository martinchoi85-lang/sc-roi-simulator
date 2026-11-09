"""Unit tests for 5R1C thermal model and freeze protection."""

from pathlib import Path
import numpy as np
import pandas as pd
from engine.schema import load_country_config
from engine.thermal_5r1c import simulate_thermal_5r1c


def test_thermal_and_freeze_prevention():
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    house_cfg = cfg.values["houses"]["MONO Core 54"]

    n = 96 * 10  # 10 days
    # Extreme sub-zero ambient temp (-15 C)
    temp_air = np.full(n, -15.0)
    ghi = np.zeros(n)
    presence = np.zeros(n)
    internal_gain = np.full(n, 50.0)

    # 10 days completely unoccupied
    is_occ_day = np.zeros(10, dtype=bool)

    t_in, q_heat_kw, q_cool_kw = simulate_thermal_5r1c(
        house_cfg, temp_air, ghi, presence, internal_gain, is_occ_day
    )

    # Freeze protection threshold is 8.0 C
    # Indoor temp should not drop below 8.0 C (with tiny numerical epsilon)
    assert t_in.min() >= 7.95
    # Heating power must be generated to maintain 8.0 C
    assert q_heat_kw.sum() > 0.0
    # No cooling during vacancy
    assert q_cool_kw.sum() == 0.0

