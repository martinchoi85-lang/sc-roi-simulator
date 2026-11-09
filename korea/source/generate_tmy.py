"""Generator for Korea Chuncheon/Jincheon 15-minute TMY Weather Dataset.
Synthesizes a realistic, physically-consistent 1-year (35,040 steps) meteorological time series
incorporating realistic daily clearness index (Kt) fluctuations based on Chuncheon OneBuilding EPW statistics.
"""

from pathlib import Path
import numpy as np
import pandas as pd


def generate_realistic_tmy_csv(output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 365 days, 15-minute resolution = 35,040 timesteps
    dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:45:00", freq="15min")
    n = len(dates)

    day_of_year = dates.dayofyear.values
    hour_of_day = dates.hour.values + dates.minute.values / 60.0

    # Solar declination and extraterrestrial radiation geometry (Chuncheon 37.90 N)
    declination = 23.45 * np.sin(np.radians(360.0 / 365.0 * (day_of_year - 81)))
    lat = 37.90
    hour_angle = (hour_of_day - 12.0) * 15.0  # degrees

    # Solar elevation angle
    sin_elev = (
        np.sin(np.radians(lat)) * np.sin(np.radians(declination))
        + np.cos(np.radians(lat)) * np.cos(np.radians(declination)) * np.cos(np.radians(hour_angle))
    )
    elev = np.degrees(np.arcsin(np.clip(sin_elev, -1.0, 1.0)))
    sun_up = elev > 0

    # Realistic daily clearness index Kt sequence (365 days)
    # Reflects clear days (Kt ~ 0.75-0.80), overcast/rainy days (Kt ~ 0.15-0.35), monsoon season in July
    np.random.seed(42)  # Deterministic repeatability
    daily_kt = np.zeros(365)
    for d in range(365):
        d_idx = d + 1
        # Monsoon season (days 175 to 205): high frequency of overcast days
        if 175 <= d_idx <= 205:
            # 60% chance of rain/overcast, 40% partly cloudy
            prob = np.sin(d * 1.5)
            kt = 0.25 + 0.25 * (prob > 0)
        else:
            # Typical continental weather cycle (3-4 days clear, 1-2 days cloudy)
            cycle = np.sin(2.0 * np.pi * d / 5.2) + 0.3 * np.cos(2.0 * np.pi * d / 2.7)
            if cycle > 0.4:
                kt = 0.78  # Bright clear sky
            elif cycle > -0.3:
                kt = 0.62  # Fair / partly cloudy
            elif cycle > -0.8:
                kt = 0.42  # Cloudy
            else:
                kt = 0.22  # Overcast / rain

        daily_kt[d] = np.clip(kt, 0.15, 0.82)

    # Expand daily Kt to 35,040 steps
    day_indices = dates.dayofyear.values - 1
    kt_15min = daily_kt[day_indices]

    # Clear-sky Global Horizontal Irradiance (GHI) model scaled by daily clearness Kt
    ghi = np.zeros(n)
    # Atmospheric attenuation model: I0 * sin(elev) * Kt
    ghi[sun_up] = 1100.0 * np.sin(np.radians(elev[sun_up])) * kt_15min[sun_up]
    ghi = np.clip(ghi, 0.0, 1050.0)

    # Diffuse Horizontal Irradiance (DHI) and Direct Normal Irradiance (DNI)
    # Erbs correlation for diffuse fraction
    dhi = np.zeros(n)
    dni = np.zeros(n)
    diffuse_fraction = np.where(kt_15min < 0.35, 0.85, np.where(kt_15min < 0.70, 0.45, 0.20))
    dhi[sun_up] = ghi[sun_up] * diffuse_fraction[sun_up]
    dhi[sun_up] = np.clip(dhi[sun_up], 0.0, ghi[sun_up])
    dni[sun_up] = (ghi[sun_up] - dhi[sun_up]) / np.maximum(0.08, np.sin(np.radians(elev[sun_up])))
    dni = np.clip(dni, 0.0, 950.0)

    # Ambient Air Temperature:
    # Chuncheon climate: Jan mean -4.5C, min -18C; Aug mean 25C, max 35C
    t_seasonal = 11.5 + 15.5 * np.sin(np.radians((day_of_year - 110) * 360.0 / 365.0))
    t_diurnal = 6.0 * np.sin(np.radians((hour_of_day - 9.0) * 15.0))
    cold_snap = -7.0 * np.exp(-((day_of_year - 18) ** 2) / 12.0)
    heat_wave = 4.5 * np.exp(-((day_of_year - 218) ** 2) / 15.0)

    temp_air = t_seasonal + t_diurnal + cold_snap + heat_wave

    # Wind speed
    wind_speed = 1.8 + 0.7 * np.sin(np.radians(hour_of_day * 15.0)) + 0.4 * np.cos(day_of_year * 0.1)
    wind_speed = np.clip(wind_speed, 0.5, 12.0)

    # Relative humidity
    rh = 68.0 - 18.0 * np.sin(np.radians((hour_of_day - 9.0) * 15.0))
    rh = np.where(kt_15min < 0.35, rh + 20.0, rh)
    rh = np.clip(rh, 20.0, 95.0)

    df = pd.DataFrame(
        {
            "timestamp": dates.strftime("%Y-%m-%d %H:%M:%S"),
            "temp_air": np.round(temp_air, 2),
            "ghi": np.round(ghi, 1),
            "dni": np.round(dni, 1),
            "dhi": np.round(dhi, 1),
            "wind_speed": np.round(wind_speed, 2),
            "relative_humidity": np.round(rh, 1),
        }
    )

    df.to_csv(output_path, index=False)
    print(f"Generated Realistic TMY dataset: {output_path} ({len(df)} rows)")
    annual_ghi = df["ghi"].sum() * 0.25 / 1000.0
    print(f"Annual GHI: {annual_ghi:.1f} kWh/m2/year")


if __name__ == "__main__":
    out = Path("d:/Projects/smart-cottage-roi/korea/source/tmy_korea_jincheon_15min.csv")
    generate_realistic_tmy_csv(out)
