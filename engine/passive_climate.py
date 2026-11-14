"""수동형 실내 기후 제어(시뮬레이터 v2 옵션). v10 계산에는 쓰지 않는다(passive=None이면 기존과 동일).

- 창 일사: 수평 GHI 대신 벽면(수직) 창 일사. 방향 비율은 가정(도면 없음).
- 차양: 실내 > t_shade 이면 일사 취득 × shading_fc (실내 블라인드 수준).
- 창문 환기: 재실자(활동·수면)가 있고 실내 > t_vent, 외기 < 실내 − 1°C 이면 환기 ach_open 회/h 추가.
보정 근거: PHI 과열 빈도 기준(25°C 초과 ≤ 10%, 권장 < 5%)을 비냉방기(10~5월) 재택 시간에 적용.
"""
import numpy as np
import pandas as pd

DEFAULT = {"orient_shares": {180: 0.5, 90: 0.2, 270: 0.2, 0: 0.1},
           "shading_fc": 0.6, "t_shade": 24.0, "ach_open": 2.0, "t_vent": 23.0}


def window_irradiance(weather_df, lat, lon, tz, shares=None):
    import pvlib
    shares = shares or DEFAULT["orient_shares"]
    times = pd.DatetimeIndex(weather_df["timestamp"])
    times = times.tz_localize(tz) if times.tz is None else times.tz_convert(tz)
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    out = np.zeros(len(times))
    for az, s in shares.items():
        r = pvlib.irradiance.get_total_irradiance(90, az, sp["apparent_zenith"].values, sp["azimuth"].values,
                                                  weather_df["dni"].values, weather_df["ghi"].values, weather_df["dhi"].values)
        out += s * np.nan_to_num(np.asarray(r["poa_global"]))
    return out


def make_passive(weather_df, lat, lon, tz, **over):
    p = dict(DEFAULT); p.update(over)
    p["window_irr"] = window_irradiance(weather_df, lat, lon, tz, p["orient_shares"])
    return p


def step(p, i, t_curr, t_amb, q_nosol_i, q_sol_full_i, home_i, h_tot, room_volume, c_m, dt_sec):
    """한 스텝의 (t_free, heat_gain_factor) 반환."""
    h = h_tot
    if home_i and t_curr > p["t_vent"] and t_amb < t_curr - 1.0:
        h = h_tot + 1200.0 * room_volume * p["ach_open"] / 3600.0
    q_g = q_nosol_i + q_sol_full_i * (p["shading_fc"] if t_curr > p["t_shade"] else 1.0)
    dec = np.exp(-dt_sec * h / c_m)
    t_inf = t_amb + q_g / h
    return t_inf + (t_curr - t_inf) * dec, h / (1.0 - dec)
