"""Unit tests for system sizing targets."""

from pathlib import Path
import numpy as np
import pandas as pd
from engine.schema import load_country_config
from engine.weather import load_weather_data
from engine.pv import simulate_pv_generation_1kwp
from engine.sizing import size_zero_energy


def test_zero_energy_sizing():
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    weather_df = load_weather_data(root / "korea" / "source" / "tmy_chuncheon_471010_15min.csv")
    dates = pd.DatetimeIndex(weather_df["timestamp"])

    lat = float(cfg.values["country"]["latitude"])
    lon = float(cfg.values["country"]["longitude"])
    tz = str(cfg.values["country"].get("timezone", "Asia/Seoul"))
    p_pv1 = simulate_pv_generation_1kwp(weather_df, lat, lon, timezone=tz)

    p_load = np.full(35040, 2.0)
    all_loads = [p_load]
    house_cfg = cfg.values["houses"]["MONO Core 54"]
    equip_cfg = cfg.values["equipment"]
    capex_cfg = cfg.values["capex"]

    res = size_zero_energy(
        p_load_100_kw=p_load,
        all_occupancy_loads=all_loads,
        p_pv1_kw=p_pv1,
        dates=dates,
        house_config=house_cfg,
        equipment_config=equip_cfg,
        capex_config=capex_cfg,
        design_margin=1.0,
    )

    assert res["pv_capacity_kw"] > 0.0
    assert res["ess_capacity_kwh"] > 0.0
    assert "critical_day" in res
    assert "inverter_required_kw" in res
    assert res["final_max_unmet_kwh"] <= 0.001
