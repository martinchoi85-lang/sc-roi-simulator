"""Climate.OneBuilding EPW(또는 zip)를 엔진용 15분 CSV로 변환 (korea/source/interpolate_epw.py 로직 재사용, 시간대만 인자로).
EPW는 현지 표준시(서머타임 없음)이므로 tz에는 고정 오프셋을 쓴다: 한국 Asia/Seoul, LA Etc/GMT+8, 멜버른 Etc/GMT-10.
사용: python -m simulator.precompute.prepare_weather <epw|zip> <출력 csv> [tz]
"""
import sys, zipfile, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
src, out = Path(sys.argv[1]), Path(sys.argv[2]); tz = sys.argv[3] if len(sys.argv) > 3 else "Asia/Seoul"
if src.suffix.lower() == ".zip":
    td = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(src) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".epw")][0]; z.extract(name, td); src = td / name
code = (ROOT / "korea" / "source" / "interpolate_epw.py").read_text(encoding="utf-8")
code = code.replace('tz = "Asia/Seoul"', f'tz = "{tz}"').split('if __name__ == "__main__":')[0]
ns = {}; exec(compile(code, "interpolate_epw.py", "exec"), ns)
import pvlib
_, meta = pvlib.iotools.read_epw(src)
print("EPW 위치:", meta.get("city"), meta["latitude"], meta["longitude"], "TZ", meta.get("TZ"), "→ 사용 tz", tz)
ns["interpolate_epw_to_15min"](src, out)
