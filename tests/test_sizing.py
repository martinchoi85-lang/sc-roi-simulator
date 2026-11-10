"""Unit tests for system sizing targets (v9)."""

from pathlib import Path
import numpy as np
import pandas as pd
from engine.schema import load_country_config
from engine.weather import load_weather_data
from engine.pv import simulate_pv_generation_1kwp
from engine.sizing import size_zero_energy


def test_zero_energy_sizing_v9():
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    weather_df = load_weather_data(root / "korea" / "source" / "tmy_chuncheon_471010_15min.csv")
    dates = pd.DatetimeIndex(weather_df["timestamp"])

    lat = float(cfg.values["country"]["latitude"])
    lon = float(cfg.values["country"]["longitude"])
    tz = str(cfg.values["country"].get("timezone", "Asia/Seoul"))
    p_pv1 = simulate_pv_generation_1kwp(weather_df, lat, lon, timezone=tz)

    p_load = np.full(35040, 1.5)  # constant 1.5 kW load
    capex_cfg = cfg.values["capex"]
    subsidy_cfg = cfg.values["subsidy"]

    res = size_zero_energy(
        p_load_kw=p_load,
        p_pv1_kw=p_pv1,
        dates=dates,
        capex_config=capex_cfg,
        subsidy_config=subsidy_cfg,
        heating_package="가스보일러",
        with_subsidy=False,
    )

    assert res["pv_capacity_kw"] > 0.0
    assert res["ess_capacity_kwh"] > 0.0
    assert res["ess_modules"] >= res["min_modules_constraint"]
    assert res["unmet_kwh"] <= 0.001
    assert res["lol_hours"] <= 0.001
    assert "search_curve" in res
    assert len(res["sample_soc_7d"]) == 7 * 96
