"""시뮬레이터 배포본 만들기: simulator/dist/SC_ROI_Simulator/ (+ zip).
- data/<region>/ 에 meta.js 와 45개 조합 파일이 모두 있는 지역만 '사용 가능'으로 regions.js에 기록
- index.html을 더블클릭하면 인터넷 없이 열린다(데이터를 <script>로 읽으므로 file:// 에서도 동작)
사용: python simulator/build.py
"""
import json, shutil, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
DIST = HERE / "dist" / "SC_ROI_Simulator"

def main():
    avail = {}
    for d in sorted((HERE / "data").iterdir()):
        if d.is_dir() and (d / "meta.js").exists() and len(list(d.glob("c_*.js"))) == 45:
            avail[d.name] = True
    ver = "KR-v1 " + datetime.date.today().isoformat()
    (HERE / "data" / "regions.js").write_text(f"window.SCREGIONS={json.dumps(avail)};window.SCREGIONS_VER={json.dumps(ver)};\n", encoding="utf-8")
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    for f in ["index.html", "style.css", "engine.js", "defaults.js", "app.js"]:
        shutil.copy2(HERE / "web" / f, DIST / f)
    (DIST / "data").mkdir()
    shutil.copy2(HERE / "data" / "regions.js", DIST / "data" / "regions.js")
    for r in avail:
        shutil.copytree(HERE / "data" / r, DIST / "data" / r, ignore=shutil.ignore_patterns("index.json"))
    z = shutil.make_archive(str(HERE / "dist" / "SC_ROI_Simulator"), "zip", HERE / "dist", "SC_ROI_Simulator")
    print("사용 가능 지역:", list(avail), "| 배포본:", DIST, "| zip:", z)

if __name__ == "__main__":
    main()
