"""Photovoltaic (PV) power generation modeling using pvlib."""

from typing import Dict
import numpy as np
import pandas as pd
import pvlib
from pvlib import solarposition, irradiance, pvsystem


def simulate_pv_generation_1kwp(
    weather_df: pd.DataFrame,
    latitude: float,
    longitude: float,
    tilt: float = 25.0,
    azimuth: float = 180.0,
    timezone: str = "Asia/Seoul",
    pv_equipment_config: Dict = None,
) -> np.ndarray:
    """Calculates 15-minute AC power output profile (kW) for a normalized 1 kWp PV system.

    Args:
        weather_df: Weather DataFrame with ['timestamp', 'temp_air', 'ghi', 'dni', 'dhi', 'wind_speed']
        latitude: Site latitude (deg)
        longitude: Site longitude (deg)
        tilt: Surface tilt angle (deg)
        azimuth: Surface azimuth angle (deg, 180 = South)
        timezone: Local timezone name (default: 'Asia/Seoul')
        pv_equipment_config: PV parameters dictionary

    Returns:
        p_pv_1kwp_kw array of shape (35040,)
    """
    times = pd.DatetimeIndex(weather_df["timestamp"])
    if times.tz is None:
        times = times.tz_localize(timezone)
    else:
        times = times.tz_convert(timezone)
    temp_air = weather_df["temp_air"].values
    wind_speed = weather_df["wind_speed"].values
    ghi = weather_df["ghi"].values
    dni = weather_df["dni"].values
    dhi = weather_df["dhi"].values

    # Solar position
    solpos = solarposition.get_solarposition(times, latitude, longitude)
    apparent_zenith = solpos["apparent_zenith"].values
    solar_azimuth = solpos["azimuth"].values

    # Total in-plane irradiance (POA: Plane of Array)
    poa_irradiance = irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        solar_zenith=apparent_zenith,
        solar_azimuth=solar_azimuth,
        dni=dni,
        ghi=ghi,
        dhi=dhi,
    )
    poa_global = poa_irradiance["poa_global"]
    if hasattr(poa_global, "values"):
        poa_global = poa_global.values
    poa_global = np.nan_to_num(poa_global, nan=0.0)
    poa_global = np.clip(poa_global, 0.0, 1400.0)

    # Cell temperature model (King model / open rack standard)
    # T_cell = T_air + POA * exp(-a - b * wind_speed)
    # Default open_rack_glass_glass: a = -3.47, b = -0.0594
    t_cell = pvsystem.temperature.sapm_cell(
        poa_global, temp_air, wind_speed, a=-3.47, b=-0.0594, deltaT=3.0
    )

    # Temperature coefficient of power
    gamma_pdc = -0.0035
    inverter_eff = 0.97
    bos_loss = 0.14
    if pv_equipment_config:
        gamma_pdc = float(pv_equipment_config.get("temp_coefficient_power", -0.0035))
        inverter_eff = float(pv_equipment_config.get("inverter_efficiency", 0.97))
        bos_loss = float(pv_equipment_config.get("bos_loss_factor", 0.14))

    # DC power generation for 1 kWp (Pdc0 = 1.0 kW at 1000 W/m2 and 25C)
    # Pdc = Pdc0 * (poa_global / 1000.0) * (1 + gamma_pdc * (t_cell - 25.0))
    p_dc_kw = 1.0 * (poa_global / 1000.0) * (1.0 + gamma_pdc * (t_cell - 25.0))
    p_dc_kw = np.clip(p_dc_kw, 0.0, None)

    # AC power after inverter efficiency and system losses (soiling, wiring mismatch)
    p_ac_kw = p_dc_kw * inverter_eff * (1.0 - bos_loss)
    return np.round(p_ac_kw, 5)
