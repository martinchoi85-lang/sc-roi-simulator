"""미국 ATUS 원자료 → 한국 엔진(KOSIS 2024 형식) 입력표 변환.

엔진(engine/occupancy_tus.py)이 읽는 표를 같은 열 구조로 만든다:
  T1(취업자 평일 일), T2(취업자 이동 92), T3(취업자 여가 8/미디어 82), T4(취업자 교제 7),
  P/H/CR/V/MV(15세 이상 전체), M(15세 이상, 7개 시간대, 대분류 1~9 + 세부 411/413/421/422/824/825).
값 = 30분 구간 동안 해당 활동에 쓴 시간 비율(%) (가중 평균, KOSIS 행동비율과 같은 정의).
또한 엔진 상수(취업자 행위자비율, 주말 근무 비율)와 '집 밖' 검증 곡선(TEWHERE)을 country_params.json에 저장.

사용: python -m simulator.precompute.atus_to_kosis <atus 압축해제 폴더> <출력 폴더> [--state 6] [--years 2015-2019,2022-2025]
"""
import sys, json, argparse
from pathlib import Path
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--state", type=int, default=6, help="GESTFIPS (6=California, 0=전국)")
ap.add_argument("--years", default="2015-2019,2022-2025")
a = ap.parse_args()
src, out = Path(a.src), Path(a.out); out.mkdir(parents=True, exist_ok=True)
years = set()
for part in a.years.split(","):
    lo, hi = part.split("-"); years |= set(range(int(lo), int(hi) + 1))

# ---------- 응답자 ----------
resp = pd.read_csv(src / "atusresp_0325.dat", usecols=["TUCASEID", "TUYEAR", "TUDIARYDAY", "TRHOLIDAY", "TELFS", "TUFNWGTP", "TU20FWGT"], dtype={"TUCASEID": str})
resp = resp[resp.TUYEAR.isin(years) & (resp.TRHOLIDAY != 1)]
resp["w"] = np.where(resp.TU20FWGT > 0, resp.TU20FWGT, resp.TUFNWGTP)
rost = pd.read_csv(src / "atusrost_0325.dat", dtype={"TUCASEID": str})
rost = rost[rost.TULINENO == 1][["TUCASEID", "TEAGE", "TESEX"]]
resp = resp.merge(rost, on="TUCASEID")
if a.state:
    keep = set()
    for ch in pd.read_csv(src / "atuscps_0325.dat", usecols=["TUCASEID", "TULINENO", "GESTFIPS"], dtype={"TUCASEID": str}, chunksize=2_000_000):
        ch = ch[(ch.TULINENO == 1) & (ch.GESTFIPS == a.state)]; keep |= set(ch.TUCASEID)
    resp = resp[resp.TUCASEID.isin(keep)]
resp = resp[resp.TEAGE >= 15]
resp["emp"] = resp.TELFS.isin([1, 2])
resp["dt"] = np.where(resp.TUDIARYDAY == 7, "토요일", np.where(resp.TUDIARYDAY == 1, "일요일", "평일"))
resp["sex"] = np.where(resp.TESEX == 1, "남자", "여자")
print("응답자", len(resp), "취업자", int(resp.emp.sum()), flush=True)

# ---------- 활동 → 분 단위 코드 ----------
CAT = {  # 6자리 TRCODEP 접두어 규칙 (위에서부터 먼저 맞는 것)
}
def classify(code):
    c = code.zfill(6); t1, t2 = c[:2], c[:4]
    sub = {}
    if t1 == "01" or t1 == "11" or t1 == "50": major = "1"
    elif t1 == "05": major = "2"
    elif t1 == "06": major = "3"
    elif t1 in ("02", "07", "08", "09", "10"): major = "4"
    elif t1 in ("03", "04"): major = "5"
    elif t1 == "15": major = "6"
    elif t1 in ("14", "16") or t2 in ("1201", "1202"): major = "7"
    elif t1 in ("12", "13"): major = "8"
    elif t1 == "18": major = "9"
    else: major = "1"
    tags = {major}
    if t2 == "0101": tags.add("11")
    if t2 == "0102": tags.add("14")
    if t2 == "0202": tags.add("41")
    if c in ("020201", "020202"): tags.add("411")
    if c == "020203": tags.add("413")
    if c in ("020102", "020104"): tags.add("42")
    if c == "020102": tags.add("421")
    if c == "020104": tags.add("422")
    if c == "020101" or t2 == "0203": tags.add("43")
    if c[:4] == "1203" and c in ("120303", "120304", "120305", "120306", "120307", "120308"): tags.add("82")
    if c in ("120303", "120304", "120305"): tags.add("824")
    if c in ("120307", "120308"): tags.add("825")
    if t2 == "1805": tags.add("92")
    if t2 == "1806": tags.add("93")
    return tags

TAGS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "14", "41", "411", "413", "42", "421", "422", "43", "82", "824", "825", "92", "93"]
TI = {t: i for i, t in enumerate(TAGS)}
ids = set(resp.TUCASEID)
acts = []
for ch in pd.read_csv(src / "atusact_0325.dat", usecols=["TUCASEID", "TUACTDUR24", "TUCUMDUR24", "TRCODEP", "TEWHERE"], dtype={"TUCASEID": str, "TRCODEP": str}, chunksize=2_000_000):
    acts.append(ch[ch.TUCASEID.isin(ids)])
acts = pd.concat(acts)
print("활동 행", len(acts), flush=True)
code_tags = {c: classify(c) for c in acts.TRCODEP.unique()}

rid = {k: i for i, k in enumerate(resp.TUCASEID)}
N = len(resp)
slots = np.zeros((N, 48, len(TAGS)), dtype=np.float32)   # 30분 구간별 분(minutes)
away = np.zeros((N, 48), dtype=np.float32)
for r in acts.itertuples(index=False):
    i = rid[r.TUCASEID]; dur = int(r.TUACTDUR24); end = int(r.TUCUMDUR24); st = end - dur
    if dur <= 0: continue
    m = (np.arange(st, end) + 240) % 1440            # 일지 04:00 시작 → 시각(분)
    s = m // 30
    cnt = np.bincount(s, minlength=48)
    for t in code_tags[r.TRCODEP]: slots[i, :, TI[t]] += cnt
    # 집 밖: TEWHERE가 1(집) 이외의 장소로 기록된 경우 (-1/미기록은 집으로 간주; 이동 18은 집 밖)
    if (r.TEWHERE not in (1, -1, -2, -3)) or r.TRCODEP.zfill(6)[:2] == "18": away[i] += cnt
slots /= 30.0; away /= 30.0

w = resp.w.to_numpy(); emp = resp.emp.to_numpy(); dts = resp.dt.to_numpy(); sex = resp.sex.to_numpy()
SLOT_START = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
M7 = [("10", "새벽 00:00~05:59", 0, 12), ("20", "아침 06:00~08:59", 12, 18), ("30", "오전 09:00~11:59", 18, 24), ("40", "점심 12:00~13:59", 24, 28),
      ("50", "오후 14:00~17:59", 28, 36), ("60", "저녁 18:00~20:59", 36, 42), ("70", "밤 21:00~23:59", 42, 48)]
DAYCODE = {"평일": "A1", "토요일": "A2", "일요일": "A3"}

def wmean(mask):
    ww = w[mask]; return (slots[mask] * ww[:, None, None]).sum(0) / ww.sum() * 100.0, int(mask.sum())

def table(name, acts_, pop, days=("평일", "토요일", "일요일"), level=None):
    rows = []
    for d in days:
        for sx in ("남자", "여자"):
            mask = (dts == d) & (sex == sx) & pop
            v, n = wmean(mask)
            for a_ in acts_:
                for k in range(48):
                    rows.append([name, DAYCODE[d], d, "S1" if sx == "남자" else "S2", sx, "", a_, a_, "대" if len(a_) == 1 else "중", k, SLOT_START[k], SLOT_START[k], round(float(v[k, TI[a_]]), 2)])
    df = pd.DataFrame(rows, columns=["table", "day_code", "day_name", "sex_code", "sex_name", "emp_name", "act_code", "act_name", "act_level", "slot_code", "slot_name", "slot_start", "value"])
    df.to_csv(out / f"{name}_2024.csv", index=False, encoding="utf-8-sig")

allp = np.ones(N, bool)
table("T1", ["2"], emp, days=("평일",))
table("T2", ["92"], emp)
table("T3", ["8", "82"], emp)
table("T4", ["7"], emp)
table("P", ["1", "11", "14"], allp)
table("H", ["4", "41", "42", "43"], allp)
table("CR", ["5"], allp)
table("V", ["6"], allp)
table("MV", ["9", "92", "93"], allp)
rows = []
for d in ("평일", "토요일", "일요일"):
    for sx in ("남자", "여자"):
        v, n = wmean((dts == d) & (sex == sx))
        for code, iname, s0, s1 in M7:
            for a_ in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "411", "413", "421", "422", "824", "825", "92"]:
                rows.append(["M", DAYCODE[d], d, "", sx, "", a_, a_, "대" if len(a_) == 1 else "소", code, iname, iname[3:8], round(float(v[s0:s1, TI[a_]].mean()), 2)])
pd.DataFrame(rows, columns=["table", "day_code", "day_name", "sex_code", "sex_name", "emp_name", "act_code", "act_name", "act_level", "slot_code", "slot_name", "slot_start", "value"]).to_csv(out / "M_2024.csv", index=False, encoding="utf-8-sig")

# ---------- 엔진 상수 ----------
def part(mask, tag, minutes=5):
    did = slots[mask][:, :, TI[tag]].sum(1) * 30 >= minutes; ww = w[mask]; return float((did * ww).sum() / ww.sum())
cp = {
    "w_part_rate": {sx: part(emp & (dts == "평일") & (sex == sx), "2") for sx in ("남자", "여자")},
    "c_part_rate": {sx: part(emp & (dts == "평일") & (sex == sx), "92") for sx in ("남자", "여자")},
    "p_work_weekend": {"saturday": part(emp & (dts == "토요일"), "2", 60), "sunday": part(emp & (dts == "일요일"), "2", 60)},
    "n_resp": {d: {sx: int(((dts == d) & (sex == sx) & emp).sum()) for sx in ("남자", "여자")} for d in ("평일", "토요일", "일요일")},
}
# 검증용: 취업자의 실제 '집 밖' 비율 곡선(TEWHERE 기반), 수면 곡선
val = {}
for d in ("평일", "토요일", "일요일"):
    mask = emp & (dts == d); ww = w[mask]
    val[d] = {"away": ((away[mask] * ww[:, None]).sum(0) / ww.sum()).round(4).tolist(),
              "sleep": ((slots[mask][:, :, TI["11"]] * ww[:, None]).sum(0) / ww.sum()).round(4).tolist()}
cp["validation_curves_employed"] = val
cp["source"] = {"survey": "BLS ATUS multi-year 2003-2025 (atusact/atusresp/atusrost/atuscps-0325)", "state_fips": a.state, "years": sorted(years),
                "population": "15세 이상, 공휴일 제외, 가중치 TU20FWGT(2020~)/TUFNWGTP", "time_basis": "현지 시각(일지 04:00 시작을 0시 기준으로 변환)"}
(out / "country_params.json").write_text(json.dumps(cp, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: cp[k] for k in ("w_part_rate", "c_part_rate", "p_work_weekend", "n_resp")}, ensure_ascii=False))
# 대분류 합 점검
M = pd.read_csv(out / "M_2024.csv"); g = M[M.act_level == "대"].groupby(["day_name", "sex_name", "slot_name"]).value.sum()
print("M 대분류 합 범위", round(g.min(), 2), round(g.max(), 2))
