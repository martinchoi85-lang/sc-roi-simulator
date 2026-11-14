"""SC ROI 시뮬레이터 1단계 사전계산.

기존 v10 엔진(engine/)의 Step1(재실·가전, KOSIS TUS) + Step2(5R1C 열, 가스보일러/AWHP, 급탕)
로직을 그대로 호출해 (모델 × 거주자 × 이용률) 조합별 1년 시간별 용도별 에너지를 만든다.
AWHP 유/무 두 경우를 한 조합 파일에 함께 저장한다(설치 전 = 가스보일러 기준안 필요).

사용:
  python -m simulator.precompute.precompute --region kr_central [--jobs 2] [--only "MONO Core 72|3|1.0"]
출력: simulator/data/<region>/meta.js, simulator/data/<region>/c_<key>.js
"""
import argparse, base64, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.schema import load_country_config
from engine.weather import load_weather_data
from engine.occupancy_tus import OccupancyTUSModel
from engine.thermal_5r1c import simulate_thermal_5r1c
from engine.heat_pump import (generate_event_based_dhw, simulate_dhw_tank_reheat,
                              simulate_awhp_space_heating_with_capacity_bound)
from engine.pv import simulate_pv_generation_1kwp
from engine import passive_climate
USE_PASSIVE = True  # v2: 수직창 일사·차양·창문 환기 (engine/passive_climate.py). False면 v10과 동일

REGIONS = {
    "kr_central": {"label": "한국 중부 · 춘천", "country_dir": "korea",
                   "weather": "korea/source/tmy_chuncheon_471010_15min.csv",
                   "lat": 37.9025, "lon": 127.7358, "tz": "Asia/Seoul",
                   "weather_src": "Climate.OneBuilding 춘천 471010 TMYx 2009-2023"},
    "kr_south": {"label": "한국 남부 · 광주", "country_dir": "korea",
                 "weather": "korea/source/tmy_gwangju_471560_15min.csv",
                 "lat": 35.1731, "lon": 126.8917, "tz": "Asia/Seoul",
                 "weather_src": "Climate.OneBuilding 광주 471560 TMYx 2009-2023"},
}
HOUSES = ["MONO Core 54", "MONO Core 72", "DUO Max 45"]
HOUSE_KEY = {"MONO Core 54": "C54", "MONO Core 72": "C72", "DUO Max 45": "D45"}
OCCS = [1, 2, 3]
RATES = [1.0, 0.7, 0.5, 0.3, 0.1]
DT = 0.25

# 채널 정의(시간별 kWh, 가스는 kg). 순서 = 바이너리 순서
CHANNELS = [
    ("cook", "조리"), ("laundry", "세탁·식세기"), ("plug", "가전·플러그"), ("light", "조명"),
    ("fridge", "냉장고·환기·대기"),
    ("cool_base", "냉방(기준안 에어컨)"),
    ("gas_heat_kg", "난방 프로판(kg)"), ("gas_dhw_kg", "급탕 프로판(kg)"),
    ("heat_th_base", "난방 열(kWh_th, 기준안)"), ("dhw_th", "급탕 열(kWh_th)"),
    ("aw_heat", "AWHP 난방 전력"), ("aw_backup", "AWHP 보조히터 전력"), ("aw_dhw", "AWHP 급탕 전력"),
    ("aw_cool", "냉방(AWHP 케이스)"), ("aw_standby", "AWHP 대기전력"),
    ("t_in_base", "실내온도 기준안(°C)"), ("t_in_aw", "실내온도 AWHP(°C)"), ("t_set", "설정온도(°C)"),
]


def hourly_sum(x):
    return np.asarray(x, dtype=float).reshape(8760, 4).sum(axis=1) * DT

def hourly_mean(x):
    return np.asarray(x, dtype=float).reshape(8760, 4).mean(axis=1)

def _v(x, d):
    return float(x.get("value", d)) if isinstance(x, dict) else float(x if x is not None else d)


def run_combo(args):
    region, h_name, occ, rate = args
    reg = REGIONS[region]
    cfg = load_country_config(ROOT / reg["country_dir"]).values
    weather_df = load_weather_data(ROOT / reg["weather"])
    kosis_dir = ROOT / reg["country_dir"] / "source" / "kosis"
    h_cfg = cfg["houses"][h_name]
    equip = cfg["equipment"]; tariff = cfg["tariff"]
    t0 = time.perf_counter()
    pas = passive_climate.make_passive(weather_df, reg["lat"], reg["lon"], reg["tz"]) if USE_PASSIVE else None

    # ---- Step1 (pipeline.run_step1_load 와 동일) ----
    model = OccupancyTUSModel(kosis_dir=kosis_dir, load_config=cfg["load"], house_config=h_cfg,
                              weather_df=weather_df, occupants=occ, seed=42)
    tus = model.simulate_year(occupancy_rate=rate)
    q_occ_w = tus["occupants_active_15min"] * 80.0
    sleeping = (np.array(tus["persons_state_15min"]) == 2).sum(axis=0).astype(float)
    t_in_base, q_heat_kw, q_cool_kw, t_set = simulate_thermal_5r1c(
        house_config=h_cfg, temp_air=weather_df["temp_air"].values, ghi=weather_df["ghi"].values,
        occupant_presence=tus["is_occupied_15min"].astype(float), internal_heat_gain_w=q_occ_w,
        is_occupied_day=tus["is_occupied_day_365"], heat_setpoint_schedule=tus["heat_setpoint_15min"],
        occupants_active=tus["occupants_active_15min"], occupants_sleeping=sleeping, passive=pas)

    # ---- Step2 (pipeline.run_step2_thermal 와 동일) ----
    cop_cool = _v(equip["awhp_system"].get("cop_cool_nominal", 4.4), 4.4)
    boiler_eff = _v(equip.get("gas_boiler", {}).get("thermal_efficiency", equip.get("gas_boiler", {}).get("efficiency", 0.9)), 0.9)
    kwh_per_kg = _v(tariff.get("lpg_net_heating_value_mj_per_kg", 46.3), 46.3) / 3.6
    dhw_l = generate_event_based_dhw(occupants=occ, is_occupied_15min=tus["is_occupied_15min"],
                                     occupants_active_15min=tus["occupants_active_15min"],
                                     is_occupied_day_365=tus["is_occupied_day_365"], seed=42)
    q_dhw_kw = dhw_l * 4.186 * 40.0 / 3600.0 / DT
    p_cool_base = np.where(q_cool_kw > 0, q_cool_kw / cop_cool, 0.0)

    tank = _v(equip["awhp_system"].get("dhw_tank_volume_liters", 200.0), 200.0)
    p_dhw_aw, _, _ = simulate_dhw_tank_reheat(dhw_draw_liters=dhw_l, temp_air=weather_df["temp_air"].values,
                                              awhp_cfg=equip["awhp_system"], tank_volume_liters=tank,
                                              supply_water_temp=55.0, dt_hours=DT)
    aw = simulate_awhp_space_heating_with_capacity_bound(
        house_config=h_cfg, temp_air=weather_df["temp_air"].values, ghi=weather_df["ghi"].values,
        occupant_presence=tus["is_occupied_15min"].astype(float), internal_heat_gain_w=q_occ_w,
        is_occupied_day=tus["is_occupied_day_365"], heat_setpoint_schedule=tus["heat_setpoint_15min"],
        occupants_active=tus["occupants_active_15min"], occupants_sleeping=sleeping,
        awhp_cfg=equip["awhp_system"], dt_sec=900.0, passive=pas)
    standby_kw = _v(equip["awhp_system"].get("standby_power_w", 10.0), 10.0) / 1000.0

    ap = tus["appliance_15min"]
    ch = {
        "cook": hourly_sum(ap["cooking"]),
        "laundry": hourly_sum(np.asarray(ap["dishwasher"]) + np.asarray(ap["laundry"])),
        "plug": hourly_sum(ap["plug"]),
        "light": hourly_sum(ap["lighting"]),
        "fridge": hourly_sum(np.asarray(ap["fridge"]) + np.asarray(ap["vent_standby"])),
        "cool_base": hourly_sum(p_cool_base),
        "gas_heat_kg": hourly_sum(q_heat_kw) / (boiler_eff * kwh_per_kg),
        "gas_dhw_kg": hourly_sum(q_dhw_kw) / (boiler_eff * kwh_per_kg),
        "heat_th_base": hourly_sum(q_heat_kw),
        "dhw_th": hourly_sum(q_dhw_kw),
        "aw_heat": hourly_sum(aw["p_comp_kw"]) if "p_comp_kw" in aw else hourly_sum(aw["p_heating_total_kw"]),
        "aw_backup": hourly_sum(aw["p_backup_kw"]) if "p_backup_kw" in aw else np.zeros(8760),
        "aw_dhw": hourly_sum(p_dhw_aw),
        "aw_cool": hourly_sum(aw["p_cooling_kw"]),
        "aw_standby": np.full(8760, standby_kw),
        "t_in_base": hourly_mean(t_in_base),
        "t_in_aw": hourly_mean(aw["t_indoor"]),
        "t_set": hourly_mean(aw["t_set"]),
    }
    # 정합성: 앱 채널 합 = 기존 base_elec 합, AWHP 난방 comp+backup = p_heating_total
    base_sum = float(np.sum(tus["total_elec_base_load_kw_15min"]) * DT)
    app_sum = sum(float(ch[k].sum()) for k in ["cook", "laundry", "plug", "light", "fridge"])
    heat_tot = float(np.sum(aw["p_heating_total_kw"]) * DT)
    states = np.array(tus["persons_state_15min"]).reshape(occ, 8760, 4)
    # 시간 대표 상태: 4칸 중 최빈(동률이면 앞쪽)
    pst = np.zeros((occ, 8760), dtype=np.uint8)
    for s in (0, 1, 2):
        cnt = (states == s).sum(axis=2)
        if s == 0:
            best = cnt.copy(); pst[:] = 0
        else:
            m = cnt > best; pst[m] = s; best = np.where(m, cnt, best)

    # 양자화 Uint16 (채널별 scale)
    mats, scales = [], []
    for k, _ in CHANNELS:
        a = ch[k].astype(float)
        if k.startswith("t_"):
            off = -40.0; sc = 100.0 / 1.0  # 0.01°C, offset -40
            q = np.clip(np.round((a - off) * sc), 0, 65535)
            scales.append([sc, off])
        else:
            mx = float(a.max()) if a.max() > 0 else 1.0
            sc = 65535.0 / mx
            q = np.clip(np.round(a * sc), 0, 65535)
            scales.append([sc, 0.0])
        mats.append(q.astype("<u2"))
    blob = np.concatenate(mats).tobytes() + pst.tobytes() + np.asarray(tus["is_occupied_day_365"], dtype=np.uint8).tobytes()

    key = f"{HOUSE_KEY[h_name]}_{occ}_{int(round(rate*100))}"
    summ = {k: round(float(ch[k].sum()), 3) for k, _ in CHANNELS if not k.startswith("t_")}
    rec = {"key": key, "house": h_name, "occ": occ, "rate": rate,
           "scales": scales, "occupied_days": int(np.sum(tus["is_occupied_day_365"])),
           "summary": summ,
           "check": {"app_sum": round(app_sum, 3), "base_elec_sum": round(base_sum, 3),
                     "aw_heat_total": round(heat_tot, 3),
                     "aw_heat_split": round(float(ch["aw_heat"].sum() + ch["aw_backup"].sum()), 3),
                     "unmet_hours": round(float(aw.get("unmet_hours", 0.0)), 1)},
           "sec": round(time.perf_counter() - t0, 1)}
    out = ROOT / "simulator" / "data" / region
    out.mkdir(parents=True, exist_ok=True)
    b64 = base64.b64encode(blob).decode()
    (out / f"c_{key}.js").write_text(
        "SCDATA.add(" + json.dumps(rec, ensure_ascii=False) + ',"' + b64 + '");\n', encoding="utf-8")
    return rec


def write_meta(region):
    reg = REGIONS[region]
    cfg = load_country_config(ROOT / reg["country_dir"]).values
    w = load_weather_data(ROOT / reg["weather"])
    pv1 = simulate_pv_generation_1kwp(w, reg["lat"], reg["lon"], tilt=25.0, azimuth=180.0,
                                      timezone=reg["tz"], pv_equipment_config=cfg["equipment"]["pv_system"])
    meta = {"region": region, "label": reg["label"], "weather_src": reg["weather_src"],
            "channels": CHANNELS,
            "pv1kw_kwh": [round(x, 4) for x in hourly_sum(pv1)],
            "temp_out": [round(x, 2) for x in hourly_mean(w["temp_air"].values)],
            "ghi_wh": [round(x, 1) for x in hourly_mean(w["ghi"].values)],
            "pv1kw_annual": round(float(hourly_sum(pv1).sum()), 1),
            "year_start": "2026-01-01", "thermal": ("v2 수동형 제어: " + json.dumps({k: v for k, v in passive_climate.DEFAULT.items()}, ensure_ascii=False)) if USE_PASSIVE else "v10"}
    out = ROOT / "simulator" / "data" / region
    out.mkdir(parents=True, exist_ok=True)
    (out / "meta.js").write_text("SCDATA.meta(" + json.dumps(meta, ensure_ascii=False) + ");\n", encoding="utf-8")
    return meta["pv1kw_annual"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="kr_central")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", default=None)
    ap.add_argument("--max", type=int, default=999, help="이번 실행에서 계산할 최대 조합 수")
    ap.add_argument("--index-only", action="store_true")
    a = ap.parse_args()
    out = ROOT / "simulator" / "data" / a.region
    if a.index_only:
        build_index(a.region); return
    print("PV 1kW 연간 kWh:", write_meta(a.region), flush=True)
    combos = [(a.region, h, o, r) for h in HOUSES for o in OCCS for r in RATES]
    if a.only:
        h, o, r = a.only.split("|"); combos = [(a.region, h, int(o), float(r))]
    else:
        combos = [c for c in combos if not (out / f"c_{HOUSE_KEY[c[1]]}_{c[2]}_{int(round(c[3]*100))}.js").exists()][:a.max]
    recs = []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for rec in ex.map(run_combo, combos):
            print(rec["key"], rec["sec"], "s", rec["check"], flush=True); recs.append(rec)
    print("DONE", len(recs), "남은 조합:", 45 - len(list(out.glob("c_*.js"))))
    build_index(a.region)


def build_index(region):
    out = ROOT / "simulator" / "data" / region
    recs = []
    for f in sorted(out.glob("c_*.js")):
        t = f.read_text(encoding="utf-8"); j = t[len("SCDATA.add("):t.index(',"')]
        r = json.loads(j); recs.append({k: r[k] for k in ("key", "house", "occ", "rate", "occupied_days", "summary", "check")})
    (out / "index.json").write_text(json.dumps({"region": region, "combos": recs}, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
