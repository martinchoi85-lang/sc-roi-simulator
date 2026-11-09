"""Unit tests for weather dataset loading and validation."""

from pathlib import Path
import pytest
from engine.weather import load_weather_data


def test_weather_loading():
    root = Path(__file__).resolve().parent.parent
    weather_path = root / "korea" / "source" / "tmy_chuncheon_471010_15min.csv"
    df = load_weather_data(weather_path)

    # 365 days * 24 hours * 4 steps = 35,040
    assert len(df) == 35040
    assert "temp_air" in df.columns
    assert "ghi" in df.columns
    assert "dni" in df.columns
    assert "dhi" in df.columns
    assert "wind_speed" in df.columns

    # Check physical ranges
    assert df["temp_air"].min() >= -30.0
    assert df["temp_air"].max() <= 45.0
    assert df["ghi"].min() >= 0.0
    assert df["ghi"].max() <= 1200.0
    assert df["wind_speed"].min() >= 0.0

