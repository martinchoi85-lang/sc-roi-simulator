"""Climate.OneBuilding EPW(또는 zip)를 엔진용 15분 CSV로 변환 (기존 korea/source/interpolate_epw.py 함수 재사용).
사용: python -m simulator.precompute.prepare_weather <epw 또는 zip 경로> <출력 csv 경로>
예:   python -m simulator.precompute.prepare_weather korea/source/KOR_JN_Gwangju.471560_TMYx.2009-2023.zip korea/source/tmy_gwangju_471560_15min.csv
"""
import sys, zipfile, tempfile, importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ie", ROOT / "korea" / "source" / "interpolate_epw.py")
ie = importlib.util.module_from_spec(spec); spec.loader.exec_module(ie)
src, out = Path(sys.argv[1]), Path(sys.argv[2])
if src.suffix.lower() == ".zip":
    td = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(src) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".epw")][0]; z.extract(name, td); src = td / name
import pvlib
_, meta = pvlib.iotools.read_epw(src)
print("EPW 위치:", meta.get("city"), meta["latitude"], meta["longitude"], "→ precompute.py REGIONS의 lat/lon과 맞는지 확인")
ie.interpolate_epw_to_15min(src, out)
print("저장:", out)
