"""Weather data loader and validator."""

from pathlib import Path
from typing import Union
import pandas as pd
import numpy as np


def load_weather_data(weather_path: Union[str, Path]) -> pd.DataFrame:
    """Loads and validates the 15-minute 1-year TMY meteorological dataset.

    Returns a DataFrame with 35,040 rows and columns:
    ['timestamp', 'temp_air', 'ghi', 'dni', 'dhi', 'wind_speed', 'relative_humidity']
    """
    path = Path(weather_path)
    if not path.exists():
        raise FileNotFoundError(f"Weather dataset file not found: {path}")

    df = pd.read_csv(path)
    required_cols = {"timestamp", "temp_air", "ghi", "dni", "dhi", "wind_speed", "relative_humidity"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Weather file missing columns: {missing}")

    if len(df) != 35040:
        raise ValueError(f"Weather dataset must have exactly 35,040 timesteps (15-min x 365 days), got {len(df)}")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

