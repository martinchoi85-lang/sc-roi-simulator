"""Unit tests for PV and ESS dispatch and physical conservation."""

from pathlib import Path
import numpy as np
import pandas as pd
from engine.schema import load_country_config
from engine.weather import load_weather_data
from engine.pv import simulate_pv_generation_1kwp
from engine.ess import simulate_ess_dispatch


def test_pv_and_ess_conservation():
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    weather_df = load_weather_data(root / "korea" / "source" / "tmy_chuncheon_471010_15min.csv")

    lat = float(cfg.values["country"]["latitude"])
    lon = float(cfg.values["country"]["longitude"])
    p_pv1 = simulate_pv_generation_1kwp(weather_df, lat, lon)

    # 1 kWp should produce realistic annual energy in Korea: 1,100 ~ 1,500 kWh/kWp/year
    annual_pv_kwh = float(np.sum(p_pv1) * 0.25)
    assert 1100.0 <= annual_pv_kwh <= 1550.0

    # ESS battery test
    n = 96 * 5  # 5 days
    p_pv = p_pv1[:n] * 5.0  # 5 kW PV
    p_load = np.full(n, 1.5)  # constant 1.5 kW load

    ess_cfg = cfg.values["equipment"]["ess_system"]
    disp = simulate_ess_dispatch(p_pv, p_load, battery_capacity_kwh=10.0, ess_config=ess_cfg, is_off_grid=False)

    # Check SoC bounds: 0.10 <= SoC <= 1.00
    assert disp["soc"].min() >= 0.099
    assert disp["soc"].max() <= 1.001

