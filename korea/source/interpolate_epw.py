"""Interpolator for Climate.OneBuilding Chuncheon 471010 EPW to 15-minute resolution.
Interpolates the official 8,760-hour EPW dataset to 35,040 15-minute steps.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pvlib
from pvlib import solarposition


def interpolate_epw_to_15min(epw_path: Path, output_csv_path: Path):
    data, meta = pvlib.iotools.read_epw(epw_path)
    lat = meta["latitude"]
    lon = meta["longitude"]
    tz = "Asia/Seoul"

    # Create target 15-minute DatetimeIndex for 2026 (365 days x 96 steps = 35,040)
    target_dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:45:00", freq="15min", tz=tz)
    n_target = len(target_dates)

    # Standardize EPW index to 2026 hourly timestamps
    # EPW hours are 1 to 24 (hour ending), map to standard start of hour
    hourly_dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:00:00", freq="h", tz=tz)
    df_hourly = data.iloc[:8760].copy()
    df_hourly.index = hourly_dates

    # Reindex to 15-min and interpolate
    # Temperature, wind, humidity: cubic spline or pchip
    df_15min = df_hourly.reindex(hourly_dates.union(target_dates))

    temp_air_15 = df_15min["temp_air"].interpolate(method="time").reindex(target_dates)
    wind_speed_15 = df_15min["wind_speed"].interpolate(method="time").reindex(target_dates)
    rel_hum_15 = df_15min["relative_humidity"].interpolate(method="time").reindex(target_dates)

    # Solar position for solar elevation clipping
    solpos = solarposition.get_solarposition(target_dates, lat, lon)
    elev = solpos["elevation"].values
    sun_up = elev > 0

    # Solar irradiance interpolation: linear with solar elevation envelope
    ghi_15 = df_15min["ghi"].interpolate(method="time").reindex(target_dates).values.copy()
    dni_15 = df_15min["dni"].interpolate(method="time").reindex(target_dates).values.copy()
    dhi_15 = df_15min["dhi"].interpolate(method="time").reindex(target_dates).values.copy()

    # Zero out when sun is down
    ghi_15[~sun_up] = 0.0
    dni_15[~sun_up] = 0.0
    dhi_15[~sun_up] = 0.0

    # Energy preservation check: scale slightly so annual GHI exactly matches hourly EPW
    annual_ghi_hourly = data["ghi"].sum() / 1000.0  # kWh/m2
    annual_ghi_15min_raw = np.sum(ghi_15) * 0.25 / 1000.0
    if annual_ghi_15min_raw > 0:
        scale_factor = annual_ghi_hourly / annual_ghi_15min_raw
        ghi_15 *= scale_factor
        dni_15 *= scale_factor
        dhi_15 *= scale_factor

    df_out = pd.DataFrame({
        "timestamp": target_dates.strftime("%Y-%m-%d %H:%M:%S"),
        "temp_air": np.round(temp_air_15.values, 2),
        "ghi": np.round(ghi_15, 1),
        "dni": np.round(dni_15, 1),
        "dhi": np.round(dhi_15, 1),
        "wind_speed": np.round(wind_speed_15.values, 2),
        "relative_humidity": np.round(rel_hum_15.values, 1),
    })

    df_out.to_csv(output_csv_path, index=False)
    print(f"Successfully interpolated EPW to 15-min CSV: {output_csv_path} ({len(df_out)} rows)")
    print(f"Annual GHI: {np.sum(df_out['ghi']) * 0.25 / 1000.0:.2f} kWh/m2")


if __name__ == "__main__":
    epw = Path("d:/Projects/smart-cottage-roi/korea/source/KOR_KW_Chuncheon.471010_TMYx.2009-2023.epw")
    out = Path("d:/Projects/smart-cottage-roi/korea/source/tmy_chuncheon_471010_15min.csv")
    interpolate_epw_to_15min(epw, out)
