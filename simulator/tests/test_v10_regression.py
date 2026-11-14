"""v10 회귀 검증: 엔진 옵션(passive, country_params)을 끈 상태에서 v10 연간 합계를 재현하는지 확인.
사용: python simulator/tests/test_v10_regression.py [조합 수, 기본 3]"""
import sys, json, builtins, typing
from pathlib import Path
import numpy as np
builtins.Tuple = typing.Tuple
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from engine.schema import load_country_config
from engine.weather import load_weather_data
from engine.occupancy_tus import OccupancyTUSModel
from engine.thermal_5r1c import simulate_thermal_5r1c
ref = json.loads((Path(__file__).parent / "v10_regression.json").read_text(encoding="utf-8"))
cfg = load_country_config(ROOT / "korea").values
w = load_weather_data(ROOT / "korea/source/tmy_chuncheon_471010_15min.csv")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3; bad = 0
for c in ref["combos"][:n]:
    h = cfg["houses"][c["house"]]
    t = OccupancyTUSModel(kosis_dir=ROOT / "korea/source/kosis", load_config=cfg["load"], house_config=h, weather_df=w, occupants=c["occ"], seed=42).simulate_year(occupancy_rate=c["rate"])
    sl = (np.array(t["persons_state_15min"]) == 2).sum(0).astype(float)
    ti, qh, qc, ts = simulate_thermal_5r1c(house_config=h, temp_air=w.temp_air.values, ghi=w.ghi.values, occupant_presence=t["is_occupied_15min"].astype(float),
        internal_heat_gain_w=t["occupants_active_15min"] * 80.0, is_occupied_day=t["is_occupied_day_365"], heat_setpoint_schedule=t["heat_setpoint_15min"],
        occupants_active=t["occupants_active_15min"], occupants_sleeping=sl)
    ok = int(t["is_occupied_day_365"].sum()) == c["occupied_days"] and abs(float(ti.max()) - c["t_indoor_max_base"]) < 1e-3
    bad += not ok; print(c["house"], c["occ"], c["rate"], "OK" if ok else "MISMATCH")
print("불일치", bad); sys.exit(1 if bad else 0)
