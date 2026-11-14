"""호주(멜버른) 생활시간 입력표: 미국 캘리포니아 ATUS 시간대 곡선 '모양' + 호주 ABS TUS 2024 '하루 총량'.

- ABS 공개표에는 시간대별 자료가 근무(Table 14.1, 1시간 단위)뿐이다 → 근무 곡선은 ABS 값을 직접 쓴다.
- 나머지 활동은 캘리포니아 곡선 × (ABS 하루 평균 분 ÷ 캘리포니아 하루 평균 분), 평일/주말·성별로 보정.
- 엔진 상수: 평일 출근 비율 = 평일 근무 참여율(전체) ÷ 취업자 비율(Table 2.1 인구), 주말 근무 비율 동일 방식.
사용: python -m simulator.precompute.au_from_abs <캘리포니아 tus_kosis 폴더> <ABS tus 폴더> <출력 폴더>
"""
import sys, json, datetime
from pathlib import Path
import numpy as np, pandas as pd, openpyxl
ca, absdir, out = map(Path, sys.argv[1:4]); out.mkdir(parents=True, exist_ok=True)

def mins(x): return x.total_seconds() / 60 if isinstance(x, datetime.timedelta) else float(x)
# --- ABS Table 4.1: 전체 인구 하루 평균 분 (평일 M,F,P / 주말 M,F,P) ---
ws = openpyxl.load_workbook(absdir / "TUSDC04.xlsx", read_only=True)["Table 4.1"]
A = {}
for r in ws.iter_rows(values_only=True):
    if r and isinstance(r[0], str) and len([x for x in r if x is not None]) >= 19:
        v = [x for x in r if x is not None]; A[v[0].strip()] = [mins(x) for x in v[13:19]]
def g(name, day, sex):  # day: 평일/주말, sex: 남자/여자
    k = (0 if day == "평일" else 3) + (0 if sex == "남자" else 1); return A[name][k]
TRAVEL = ["Travel related to personal care for self", "Travel related to own employment", "Travel related to own education", "Travel related to domestic activities",
          "Travel related to looking after children", "Travel related to caring and support for adult", "Travel related to volunteering", "Travel related to free time"]
SOC = ["Talking and socialising (in person)", "Phone, video calls and texting", "Prayer and religion"]
def target(tag, d, s):
    G = lambda n: g(n, d, s)
    return {
        "1": G("Personal care for self") - G("Travel related to personal care for self"), "11": G("Sleeping"), "14": G("Personal hygiene and care"),
        "2": G("Employment activities(c)") - G("Travel related to own employment"), "92": G("Travel related to own employment"), "93": G("Travel related to own education"),
        "3": G("Education activities(c)") - G("Travel related to own education"),
        "4": G("Domestic activities(c)") - G("Travel related to domestic activities"),
        "41": G("Cooking and food/drink preparation"), "411": G("Cooking and food/drink preparation"), "413": G("Cooking and food/drink preparation"),
        "42": G("Housework"), "421": G("Housework"), "422": G("Housework"), "43": G("Housework"),
        "5": G("Looking after children (14 years and under)(c)") - G("Travel related to looking after children") + G("Caring and support (15 years and over)") - G("Travel related to caring and support for adult"),
        "6": G("Volunteering"), "7": sum(G(n) for n in SOC),
        "8": G("Free time activities(c)") - sum(G(n) for n in SOC) - G("Travel related to free time"),
        "82": G("Watching TV or streaming") + G("Checking emails, social media, browsing") + G("Playing video or mobile games"),
        "824": G("Watching TV or streaming"), "825": G("Checking emails, social media, browsing") + G("Playing video or mobile games"),
        "9": sum(G(n) for n in TRAVEL)}[tag]

# --- 캘리포니아 표 읽기, 전체 인구 기준 하루 분(M 표의 7구간 평균×구간 길이) ---
M = pd.read_csv(ca / "M_2024.csv")
BLK = {"새벽 00:00~05:59": 12, "아침 06:00~08:59": 6, "오전 09:00~11:59": 6, "점심 12:00~13:59": 4, "오후 14:00~17:59": 8, "저녁 18:00~20:59": 6, "밤 21:00~23:59": 6}
def ca_min(tag, d, s, src=None):
    if tag == "82" and src is None: return ca_min("824", d, s) + ca_min("825", d, s)
    if src is not None:  # 30분 표(P/H/MV 등)
        sub = src[(src.day_name == d) & (src.sex_name == s) & (src.act_code.astype(str) == tag)]
        return sub.value.sum() / 100 * 30
    sub = M[(M.day_name == d) & (M.sex_name == s) & (M.act_code.astype(str) == tag)]
    return sum(r.value / 100 * 30 * BLK[r.slot_name] for r in sub.itertuples())
TAB = {n: pd.read_csv(ca / f"{n}_2024.csv") for n in ["T1", "T2", "T3", "T4", "P", "H", "CR", "V", "MV"]}
SRC_FOR = {"11": "P", "14": "P", "1": "P", "41": "H", "42": "H", "43": "H", "4": "H", "5": "CR", "6": "V", "9": "MV", "92": "MV", "93": "MV", "8": "T3", "82": "T3", "7": "T4"}

factors = {}
def fac(tag, d, s):
    dd = "평일" if d == "평일" else "주말"
    key = (tag, dd, s)
    if key not in factors:
        if d == "평일":
            cm = ca_min(tag, "평일", s, None if tag not in SRC_FOR or SRC_FOR[tag].startswith("T") else TAB[SRC_FOR[tag]])
        else:
            cm = np.mean([ca_min(tag, x, s, None if tag not in SRC_FOR or SRC_FOR[tag].startswith("T") else TAB[SRC_FOR[tag]]) for x in ("토요일", "일요일")])
        factors[key] = float(np.clip(target(tag, dd, s) / cm, 0.2, 5.0)) if cm > 0.5 else 1.0
    return factors[key]

# --- ABS Table 14.1: 근무자 시간대별 근무 참여율 → 30분 근무 시간 비율 ---
ws = openpyxl.load_workbook(absdir / "TUSDC14.xlsx", read_only=True)["Table 14.1"]
rows = [r for r in ws.iter_rows(values_only=True) if r and isinstance(r[0], str) and ("AM–" in r[0] or "PM–" in r[0])]
H14 = {"평일": {"남자": [r[1] for r in rows], "여자": [r[2] for r in rows]}, "주말": {"남자": [r[4] for r in rows], "여자": [r[5] for r in rows]}}
PER_PART = {"평일": {"남자": target("2", "평일", "남자"), "여자": target("2", "평일", "여자")}}
# 근무자 1인 근무 분(ABS Table 4.1 참여자 평균): 평일 M/F, 주말 M/F
ws4 = openpyxl.load_workbook(absdir / "TUSDC04.xlsx", read_only=True)["Table 4.1"]
for r in ws4.iter_rows(values_only=True):
    if r and r[0] == "Paid work and employment":
        v = [x for x in r if x is not None]; PP = [mins(x) for x in v[7:13]]; PR = [float(x) for x in v[1:7]]
WORKER_MIN = {"평일": {"남자": PP[0], "여자": PP[1]}, "주말": {"남자": PP[3], "여자": PP[4]}}
PART_ALL = {"평일": {"남자": PR[0] / 100, "여자": PR[1] / 100}, "주말": {"남자": PR[3] / 100, "여자": PR[4] / 100}}
def work_curve(dd, s):  # 근무자의 30분 근무 시간 비율(0~1)
    p = np.array(H14[dd][s], float) / 100; k = WORKER_MIN[dd][s] / (p.sum() * 60)
    return np.repeat(np.clip(p * k, 0, 1), 2)

# --- 취업자 비율 (Table 2.1 인구 '000) ---
ws2 = openpyxl.load_workbook(absdir / "TUSDC02.xlsx", read_only=True)["Table 2.1"]
pop = {}; cur = None
for r in ws2.iter_rows(values_only=True):
    v = [x for x in r if x is not None]
    if not v: continue
    if v[0] in ("Employed full-time", "Employed part-time") and len(v) >= 11: pop.setdefault(cur, 0); pop[cur] = pop.get(cur, 0) + float(v[-1])
    if isinstance(v[0], str) and v[0].startswith("Total males"): pop["남자_tot"] = float(v[-1]); cur = "여자"
    if isinstance(v[0], str) and v[0].startswith("Total females"): pop["여자_tot"] = float(v[-1]); cur = "persons"
    if cur is None and v[0] == "Labour force status(b)": pass
# 첫 섹션(남자) 처리: 위 루프는 Total males 이전을 cur=None으로 모음
E = {"남자": pop[None] / pop["남자_tot"], "여자": pop["여자"] / pop["여자_tot"]}
w_part = {s: PART_ALL["평일"][s] / E[s] for s in E}
p_we = float(np.mean([PART_ALL["주말"][s] / E[s] for s in E]))
c_part = {s: (target("92", "평일", s) / 1440 * 0 + 0) for s in E}  # 아래에서 대체
# 출퇴근 참여율: ABS 'Travel related to own employment' 평일 참여율 ÷ 취업자 비율
for r in ws4.iter_rows(values_only=True):
    if r and isinstance(r[0], str) and r[0].strip() == "Travel related to own employment":
        v = [x for x in r if x is not None]; c_part = {"남자": float(v[1]) / 100 / E["남자"], "여자": float(v[2]) / 100 / E["여자"]}

# --- 표 쓰기 ---
def scale_table(name, df):
    df = df.copy()
    for (d, s, a_), idx in df.groupby(["day_name", "sex_name", "act_code"]).groups.items():
        a_ = str(a_)
        if name == "T1" and a_ == "2":
            df.loc[idx, "value"] = np.round(work_curve("평일", s) * w_part[s] * 100, 2); continue
        f = fac(a_, d, s)
        df.loc[idx, "value"] = np.round(np.clip(df.loc[idx, "value"] * f, 0, 100), 2)
    df.to_csv(out / f"{name}_2024.csv", index=False, encoding="utf-8-sig")
for n, df in TAB.items(): scale_table(n, df)
# M: 대분류 보정 후 구간별 합 100으로 정규화, 근무(2)는 ABS 곡선 × 전체 참여율
M2 = M.copy()
for (d, s, a_), idx in M2.groupby(["day_name", "sex_name", "act_code"]).groups.items():
    a_ = str(a_); dd = "평일" if d == "평일" else "주말"
    if a_ == "2":
        wc = work_curve(dd, s) * PART_ALL[dd][s] * 100
        M2.loc[idx, "value"] = [round(float(wc[s0:s0 + n].mean()), 2) for s0, n in [(0, 12), (12, 6), (18, 6), (24, 4), (28, 8), (36, 6), (42, 6)]]
    else:
        M2.loc[idx, "value"] = M2.loc[idx, "value"] * fac(a_, d, s)
maj = M2.act_level == "대"
tot = M2[maj].groupby(["day_name", "sex_name", "slot_name"]).value.transform("sum")
M2.loc[maj, "value"] = np.round(M2.loc[maj, "value"] / tot * 100, 2)
M2.to_csv(out / "M_2024.csv", index=False, encoding="utf-8-sig")
cp = {"w_part_rate": w_part, "c_part_rate": c_part, "p_work_weekend": {"saturday": p_we, "sunday": p_we},
      "employment_ratio": E, "scale_factors": {f"{k[0]}|{k[1]}|{k[2]}": round(v, 3) for k, v in sorted(factors.items())},
      "source": {"shape": "BLS ATUS 캘리포니아(2015-2019, 2022-2025) 시간대 곡선", "totals": "ABS How Australians Use Their Time 2024, TUSDC04 Table 4.1(하루 평균), TUSDC14 Table 14.1(근무 시간대), TUSDC02 Table 2.1(취업자 수)",
                 "note": "ABS는 토·일을 나누지 않아 주말 값을 토·일에 같이 적용"}}
(out / "country_params.json").write_text(json.dumps(cp, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: cp[k] for k in ("w_part_rate", "c_part_rate", "p_work_weekend", "employment_ratio")}, ensure_ascii=False))
print("보정계수 예:", {k: v for k, v in cp["scale_factors"].items() if k.split("|")[0] in ("11", "2", "82", "41", "9", "92")})
