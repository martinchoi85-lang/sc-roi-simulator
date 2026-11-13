"""테스트용 MOCK report_data.json 생성기 (숫자는 의미 없음, 렌더링 확인 전용)."""
import json, math, random, sys

random.seed(7)
HP = [("C54_1", "MONO Core 54", 1), ("C54_2", "MONO Core 54", 2), ("C72_1", "MONO Core 72", 1),
      ("C72_2", "MONO Core 72", 2), ("C72_3", "MONO Core 72", 3), ("D45_1", "DUO Max 45", 1), ("D45_2", "DUO Max 45", 2)]
HEAT = ["gas", "awhp"]; OCC = [100, 70, 50, 30, 15]; TGT = ["nz", "zb", "ze"]; SUB = ["none", "pv2026"]
ENDUSE = ["heating", "dhw", "cooling", "cooking", "laundry", "dishwasher", "fridge", "lighting", "plug", "vent_standby"]
LIFE = {"inverter": 12, "ess": 10, "awhp": 15, "pv": 25}
UNIT = {"inverter": 250000, "ess": 1775200, "awhp": 14000000, "pv": 1513667}


def cumflow(net, benefit, pv, ess, heat):
    reps, cum, out = [], -net, [round(-net)]
    for y in range(1, 101):
        cost = 0
        for item, life in LIFE.items():
            if y > 1 and (y - 1) % life == 0:
                if item == "awhp" and heat != "awhp": continue
                if item == "ess" and ess == 0: continue
                if item in ("pv", "inverter") and pv == 0: continue
                k = {"inverter": max(750000, UNIT[item] * pv), "ess": UNIT[item] * ess, "awhp": UNIT[item], "pv": UNIT[item] * pv}[item]
                reps.append({"year": y, "item": item, "krw": round(k)}); cost += k
        age = (y - 1) % 25
        cum += benefit * (0.995 ** age if pv else 1) - cost
        out.append(round(cum))
    return out, reps


def payback(cf):
    if cf[-1] < 0: return None
    last = 0
    for y in range(1, 101):
        if cf[y - 1] < 0 <= cf[y]: last = y - 1 + (-cf[y - 1]) / (cf[y] - cf[y - 1])
    return round(last, 1)


scen, energy, sid = [], [], 0
for hp, house, n in HP:
    for heat in HEAT:
        for occ in OCC:
            f = occ / 100
            base_kwh = (1800 + 900 * n) * (0.3 + 0.7 * f)
            prop_kg = (330 + 60 * n) * (0.25 + 0.75 * f)
            awhp_kwh = base_kwh + 2600 * (0.3 + 0.7 * f)
            for sub in SUB:
                rows = {"baseline": (0, 0, base_kwh, prop_kg), "awhp_only": (0, 0, awhp_kwh, 0)}
                for h in HEAT:
                    load = base_kwh if h == "gas" else awhp_kwh
                    for t, (pvk, ess) in {"nz": (1.5 + 0.5 * n * f, 0), "zb": (load / 1250, 9.6), "ze": (12 + 4 * n + (8 if h == "awhp" else 0), 38.4 + (28.8 if h == "awhp" else 0))}.items():
                        rows[f"{h}_{t}"] = (round(pvk * 2) / 2, ess, load, prop_kg if h == "gas" else 0)
                for case, (pvk, ess, load, kg) in rows.items():
                    gen = pvk * 1180
                    billed = max(0, load - gen) if not case.endswith("ze") else 0
                    imp = load * 0.65 if not case.endswith("ze") else 0
                    fixed = 12 * 910 * 1.127
                    var = billed * 150
                    if any(e["hp"] == hp and e["occ"] == occ and e["sub"] == sub and e["case"] == case for e in energy): continue
                    energy.append({"hp": hp, "occ": occ, "sub": sub, "case": case, "pv_kw": pvk, "ess_kwh": ess,
                                   "import_kwh": round(imp), "export_kwh": round(max(0, gen - load * 0.35)), "billed_kwh": round(billed),
                                   "elec_fixed_krw": round(fixed if not case.endswith("ze") else 0), "elec_variable_krw": round(var),
                                   "propane_kg": round(kg), "gas_krw": round(kg * 2812.26)})
                for t in TGT:
                    pvk, ess, load, kg = rows[f"{heat}_{t}"]
                    e_base = next(e for e in energy if e["hp"] == hp and e["occ"] == occ and e["sub"] == sub and e["case"] == "baseline")
                    e_alt = next(e for e in energy if e["hp"] == hp and e["occ"] == occ and e["sub"] == sub and e["case"] == f"{heat}_{t}")
                    tot = lambda e: e["elec_fixed_krw"] + e["elec_variable_krw"] + e["gas_krw"]
                    benefit = tot(e_base) - tot(e_alt)
                    cap = {"pv": round(pvk * 1513667), "ess": round(ess * 1775200), "awhp": 14000000 if heat == "awhp" else 0,
                           "grid": 306000 + (121000 * max(0, pvk - 5) if pvk > 5 else 0),
                           "pv_subsidy": -round(2650000 * min(pvk, 3) / 3) if sub == "pv2026" and pvk <= 3 else 0}
                    cap["net"] = sum(cap.values())
                    cf, reps = cumflow(cap["net"], benefit, pvk, ess, heat)
                    pb = payback(cf) if benefit > 0 else None
                    s = {"id": sid, "hp": hp, "heat": heat, "occ": occ, "target": t, "sub": sub, "pv_kw": pvk, "ess_kwh": ess,
                         "ess_modules": int(round(ess / 9.6)), "capex": cap, "annual_benefit_krw": round(benefit),
                         "var_bill_saving_pct": round(100 * (1 - e_alt["elec_variable_krw"] / max(1, e_base["elec_variable_krw"])), 1),
                         "cum25_krw": cf[25], "payback_years": pb,
                         "payback_reason": None if pb is not None else ("no_benefit" if benefit <= 0 else "over_100y"),
                         "replacements": reps, "cum_cashflow": cf}
                    if t == "nz":
                        s["nz_required_capex_krw"] = round(max(0, 3 * benefit))
                        s["nz_required_cut_pct"] = round(100 * (1 - max(0, 3 * benefit) / cap["net"]), 1)
                    if t == "zb":
                        s["zb_payback_ess"] = {k: (round(pb * m, 1) if pb and pb * m <= 100 else None) for k, m in (("low", 0.55), ("central", 1), ("high", 1.05))}
                    scen.append(s); sid += 1


def day(kind, hp_n, heat):
    kw = {k: [0.0] * 96 for k in ENDUSE}
    persons = []
    for p in range(hp_n):
        st = []
        lv, rt, wk, sl = (31 + random.randint(-3, 3), 76 + random.randint(-4, 6), 26, 93) if kind != "weekend" else (60, 66, 34, 96)
        for i in range(96):
            st.append(2 if i < wk or i >= sl else (0 if (lv <= i < rt and (kind != "weekend" or random.random() < 1)) else 1))
        persons.append(st)
    for i in range(96):
        home = sum(1 for s in persons if s[i] == 1)
        cold = 1.6 if kind == "peak" else 0.8
        kw["heating"][i] = (cold * (1.2 if home else 0.6) if heat == "awhp" else 0.05) + random.random() * 0.1
        kw["fridge"][i] = 0.12 if (i % 4) < 2 else 0.03
        kw["vent_standby"][i] = 0.04
        kw["lighting"][i] = 0.15 * home if (i < 30 or i > 72) else 0
        kw["plug"][i] = 0.1 * home + (0.3 if home and 76 < i < 92 else 0)
    for i in (28, 29, 78, 79, 80):
        kw["cooking"][i] = 2.0 * (0.6 + random.random() * 0.4)
    for i in (84, 85, 86, 87):
        kw["dishwasher"][i] = 1.4
    if kind != "weekday":
        for i in (40, 41, 42): kw["laundry"][i] = 1.5
    for i in (27, 88):
        kw["dhw"][i] = 3.5 if heat == "awhp" else 0.05
    return {k: [round(v, 3) for v in a] for k, a in kw.items()}, persons


profiles, ze = {}, {}
for hp, house, n in HP:
    for heat in HEAT:
        key = f"{hp}|{heat}"
        days = {}
        for kind, label, date in (("weekday", "평일 샘플", "2026-03-11"), ("weekend", "주말 샘플", "2026-03-14"), ("peak", "최대 부하일", "2026-01-25")):
            kw, persons = day(kind, n, heat)
            days[kind] = {"date": date, "label": label, "kw": kw, "persons": persons}
        hm = [[round(max(0.1, (1.5 if heat == "awhp" else 0.4) * (1 + math.cos(2 * math.pi * d / 365)) * 0.6 + (0.8 if h in (7, 19, 20) else 0.2) * random.random()), 2) for h in range(24)] for d in range(365)]
        daily = [round(sum(r), 1) for r in hm]
        week_total = [round(sum(days["weekday"]["kw"][k][i % 96] for k in ENDUSE) * (0.8 + 0.4 * random.random()), 2) for i in range(672)]
        homec = [sum(1 for s in days["weekday"]["persons"] if s[i % 96] != 0) for i in range(672)]
        tot = lambda d: [sum(d["kw"][k][i] for k in ENDUSE) for i in range(96)]
        bw = tot(days["weekday"]); be = tot(days["weekend"])
        bands = {dt: {"p10": [round(x * 0.6, 2) for x in b], "p50": [round(x, 2) for x in b], "p90": [round(x * 1.6, 2) for x in b]} for dt, b in (("weekday", bw), ("saturday", be), ("sunday", be))}
        profiles[key] = {"occ_basis": 100, "days": days, "week": {"start_date": "2026-03-09", "kw_total": week_total, "home_count": homec},
                         "hourly_heatmap": hm, "bands": bands, "daily_kwh": daily}
        pv = next(s["pv_kw"] for s in scen if s["hp"] == hp and s["heat"] == heat and s["target"] == "ze" and s["occ"] == 100 and s["sub"] == "none")
        ze[key] = {"search": [{"modules": m, "min_pv_kw": round(pv + 6 - 1.5 * (m - 4), 1), "capex_krw": round((pv + 6 - 1.5 * (m - 4)) * 1513667 + m * 9.6 * 1775200)} for m in range(4, 13)],
                   "daily": {"load_kwh": daily, "pv_kwh": [round(pv * 0.88 * (2.2 + 2.3 * math.sin(math.pi * d / 365)) * (0.2 + 0.8 * random.random()), 1) for d in range(365)], "ess_usable_kwh": round(38.4 * 0.7 * 0.9 * 0.949, 1)},
                   "soc7": {"start_date": "2026-01-31", "soc_pct": [round(40 + 40 * math.sin(i / 50), 1) for i in range(672)], "pv_kw": [round(max(0, pv * 0.5 * math.sin(math.pi * ((i % 96) - 30) / 40)) * (0.1 if 300 < i < 400 else 1), 2) if 30 < i % 96 < 70 else 0 for i in range(672)], "load_kw": week_total}}

curves = []
for c in ("sleep", "away", "cook", "media"):
    for dt in ("weekday", "saturday", "sunday"):
        tgt = [round(max(0, {"sleep": 90 * (1 if (i < 12 or i > 45) else 0.05), "away": 70 * (1 if 17 < i < 38 and dt == "weekday" else 0.2), "cook": 8 * (1 if i in (13, 14, 36, 37) else 0.1), "media": 20 * (1 if 38 < i < 46 else 0.15)}[c] + random.uniform(-2, 2)), 1) for i in range(48)]
        curves.append({"curve": c, "daytype": dt, "target": tgt, "sim": [round(max(0, x + random.uniform(-1.2, 1.2)), 1) for x in tgt], "mae": round(random.uniform(0.1, 0.7), 2)})

data = {
    "schema_version": "sc-report-1", "run_id": "MOCK-20261111",
    "meta": {"country": "korea", "location": "춘천", "weather_source": "Climate.OneBuilding 춘천 TMYx 2009-2023 (WMO 471010)", "annual_ghi_kwh_m2": 1490.6, "created_at": "2026-11-11", "is_mock": True},
    "load_mode_detail": "KOSIS 2024 생활시간조사의 취업자 시간대별 행동비율과 10세 이상 행동비율을 결합한 통계 기반 확률 시뮬레이션(실측 아님).",
    "dims": {"house_persons": [{"id": hp, "house": h, "persons": n, "label": f"{h} · {n}인"} for hp, h, n in HP],
             "heating": [{"id": "gas", "label": "가스보일러(프로판)"}, {"id": "awhp", "label": "AWHP"}], "occupancy": OCC,
             "targets": [{"id": "nz", "label": "Near zero"}, {"id": "zb", "label": "Zero bill"}, {"id": "ze", "label": "Zero energy"}],
             "subsidy": [{"id": "none", "label": "보조금 없음"}, {"id": "pv2026", "label": "2026 PV 보조금"}]},
    "constants": {"ess_module_kwh": 9.6, "pv_unit_krw_per_kw": 1513667, "awhp_capex_krw": 14000000, "propane_krw_per_kg": 2812.26,
                  "tariff_300kwh_krw": 57760, "ess_soh_eol": 0.7, "ess_soc_window": 0.9, "ess_rte": 0.9, "pv_degradation_per_year": 0.005,
                  "horizon_years": 100, "pv_subsidy_krw_3kw": 2650000, "pv_subsidy_max_kw": 3.0},
    "scenarios": scen, "energy": energy,
    "lifetimes": [{"item": "pv", "label": "PV 모듈", "years": 25, "basis": "제조사 보증", "status": "VERIFIED", "note": "한화큐셀 출력보증 25년 (참고: 제품보증 12년, HD현대 출력보증 30년)"},
                  {"item": "inverter", "label": "인버터", "years": 12, "basis": "추정", "status": "ASSUMPTION", "note": "참고: 주택지원사업 시공기업 무상 하자보증 3년"},
                  {"item": "ess", "label": "ESS", "years": 10, "basis": "추정", "status": "PLACEHOLDER", "note": "10년 차 SOH 70%, SoC 창 90%, RTE 90%"},
                  {"item": "awhp", "label": "AWHP", "years": 15, "basis": "추정", "status": "ASSUMPTION", "note": "민감도 10년·20년"}],
    "profiles": profiles,
    "tus": {"person_days": 2000, "lambda": 0.08, "away_episodes_weekday_mean": 1.4, "fit": curves,
            "leave_hist": [round(max(0, 18 * math.exp(-((i - 15) ** 2) / 3)), 1) for i in range(48)],
            "return_hist": [round(max(0, 12 * math.exp(-((i - 37) ** 2) / 6)), 1) for i in range(48)]},
    "appliances": [{"hp": "C54_2", "name": nm, "rated_kw": r, "cycle_min": c, "annual_target_kwh": a, "annual_sim_kwh": round(a * random.uniform(0.997, 1.003), 1), "status": "UNVERIFIED"}
                   for nm, r, c, a in (("냉장고", 0.12, 0, 312), ("인덕션", 2.0, 17, 420), ("세탁기", 0.5, 45, 130), ("TV·플러그", 0.4, 200, 657), ("조명", 0.15, 0, 234.6))],
    "seed_range": [{"hp": hp, "heat": h, "pv_min": 12 + n, "pv_max": 16 + n, "ess_min": 38.4, "ess_max": 48.0, "capex_min": 6.0e7, "capex_max": 7.2e7} for hp, _, n in HP for h in HEAT],
    "kappa_sens": [{"kappa": k, "values": {"연간 사용량 kWh (Core 72·3인·AWHP·100%)": round(5200 * (1 + (0.5 - k) * 0.1)), "Near zero 최단 회수기간(년)": round(2.1 + (0.5 - k), 1)}} for k in (0.3, 0.5, 0.7)],
    "ze": ze,
    "sensitivities": [{"group": "외피 법정기준", "case": "MONO Core 72 · 3인 · AWHP · Zero bill · 100%", "base": 60.1, "sens": 52.3},
                      {"group": "AWHP 보조금 70%", "case": "MONO Core 72 · 3인 · AWHP · Near zero · 100%", "base": 20.1, "sens": 15.7},
                      {"group": "AWHP 수명 10년", "case": "MONO Core 72 · 3인 · AWHP · Near zero · 100%", "base": 20.1, "sens": None},
                      {"group": "AWHP 수명 20년", "case": "MONO Core 72 · 3인 · AWHP · Near zero · 100%", "base": 20.1, "sens": 17.9}],
    "inputs": [{"group": "요금", "name": "한전 주택용 저압 누진요금", "value": "910/1,600/7,300원 · 120.0/214.6/307.3원/kWh", "unit": "", "status": "VERIFIED", "source": "한전 요금표"},
               {"group": "연료", "name": "일반프로판 단가", "value": "2,812.26", "unit": "원/kg", "status": "VERIFIED", "source": "오피넷 2026-10 4주"},
               {"group": "설비", "name": "ESS 단가(Central)", "value": "1,775,200", "unit": "원/kWh", "status": "UNVERIFIED", "source": "NREL Q1 2021, 환율 1,400"},
               {"group": "설비", "name": "환율", "value": "1,400", "unit": "원/USD", "status": "PLACEHOLDER", "source": "-"},
               {"group": "부하", "name": "난방 설정온도", "value": "20/18/16/10", "unit": "°C", "status": "ASSUMPTION", "source": "재택/수면/외출/비재실"}],
    "limits": ["부하는 실측이 아닌 통계 기반 시뮬레이션이다.", "ESS 단가는 해외(NREL) 기준 범위값이다.", "기상은 TMY(대표 기상년) 1년을 100년 동안 반복한다.", "3kW 초과 PV 단가는 3kW 상한 단가의 비례 가정이다."],
}

# ===== sc-report-2 확장 (MOCK) =====
data["schema_version"] = "sc-report-2"
C = data["constants"]
C.update({"replacement_rule": "MOCK: 교체 시점에는 현재 단가로 교체비가 발생하고 보조금은 다시 지급되지 않는다.", "propane_mj_per_kg": 46.3, "boiler_avoided_cost_included": False, "ess_price_cases": [
    {"id": "low", "label": "Low (NREL)", "usd_per_kwh": 283, "krw_per_kwh": 396200, "status": "UNVERIFIED", "source": "NREL 범위 하단, 환율 1,400원/USD"},
    {"id": "central", "label": "Central (NREL)", "usd_per_kwh": 1268, "krw_per_kwh": 1775200, "status": "UNVERIFIED", "source": "NREL Q1 2021, 환율 1,400원/USD"},
    {"id": "high", "label": "High (NREL)", "usd_per_kwh": 1337, "krw_per_kwh": 1871800, "status": "UNVERIFIED", "source": "NREL 범위 상단, 환율 1,400원/USD"},
    {"id": "specific", "label": "Specific (MOCK 사례)", "usd_per_kwh": None, "krw_per_kwh": 1100000, "status": "PLACEHOLDER", "source": "MOCK: 실제 판매·설치 사례 단가 자리"}]})
for s_ in scen:
    if s_["target"] == "zb":
        c_ = s_["zb_payback_ess"].get("central")
        s_["zb_payback_ess"]["specific"] = round(c_ * 0.8, 1) if c_ else None
        s_["zb_breakeven_ess_krw_per_kwh"] = 250000 if s_["occ"] == 100 else None
WM = [1.45, 1.3, 1.05, .85, .7, .75, .95, 1.0, .75, .8, 1.05, 1.35]; WS = [.6, .75, 1.0, 1.15, 1.25, 1.1, .95, 1.0, 1.0, .95, .7, .55]
for e in energy:
    aw = e["case"].startswith("awhp"); f = 0.3 + 0.7 * e["occ"] / 100; n_ = int(e["hp"][-1])
    eu = {"cooling": 260 * f, "cooking": 420 * f, "laundry": 150 * f, "dishwasher": 185 * f, "fridge": 312, "lighting": 230 * f,
          "plug": 330 * n_ * f, "vent_standby": 700, "heating": (2400 if aw else 60) * f, "dhw": (500 + 250 * n_ if aw else 30) * f}
    e["enduse_kwh"] = {k: round(v) for k, v in eu.items()}
    tot = sum(e["enduse_kwh"].values())
    e["heat_th_kwh"] = {"heating": round(7200 * f), "dhw": round((1300 + 650 * n_) * f), "cooling": round(260 * f * 3.3)}
    e["pv_gen_kwh"] = round(e["pv_kw"] * 1250)
    if not aw and e["propane_kg"] > 0:
        th_ = e["heat_th_kwh"]["heating"] + e["heat_th_kwh"]["dhw"]; k_ = e["propane_kg"] * 46.3 / 3.6 * 0.88 / th_
        e["heat_th_kwh"]["heating"] = round(e["heat_th_kwh"]["heating"] * k_); e["heat_th_kwh"]["dhw"] = round(e["heat_th_kwh"]["dhw"] * k_)
    cons = [round(tot * w / sum(WM)) for w in WM]; cons[-1] += tot - sum(cons)
    pvm = [round(e["pv_gen_kwh"] * w / sum(WS)) for w in WS]
    imp = [round(c - min(c, p) * 0.35) for c, p in zip(cons, pvm)]; exp_ = [round(p - min(c, p) * 0.35) for c, p in zip(cons, pvm)]
    zeroE = e["case"].endswith("_ze")
    if zeroE: imp = [0] * 12; exp_ = [0] * 12
    carry = 0
    for _ in range(30):  # 정상상태: 12월 말 이월 = 1월 초 이월(연간 잉여면 계속 누적)
        cin = []; bil = []
        for i in range(12):
            cin.append(carry); net = imp[i] - exp_[i] - carry; bil.append(max(0, net)); carry = max(0, -net)
        if sum(imp) <= sum(exp_) or carry == cin[0]: break
    def kbill(kwh, mon):
        t1, t2 = (300, 450) if mon in (7, 8) else (200, 400)
        base = 910 if kwh <= t1 else 1600 if kwh <= t2 else 7300
        en = min(kwh, t1) * 120 + max(0, min(kwh, t2) - t1) * 214.6 + max(0, kwh - t2) * 307.3 + kwh * 14
        return int(((base + en) * 1.127) // 10 * 10)
    bills = [0 if zeroE else kbill(bil[i], i + 1) for i in range(12)]
    e["elec_fixed_krw"] = 0 if zeroE else sum(kbill(0, i + 1) for i in range(12)); e["elec_variable_krw"] = sum(bills) - e["elec_fixed_krw"]
    e["billed_kwh"] = sum(bil); e["import_kwh"] = sum(imp); e["export_kwh"] = sum(exp_)
    e["monthly"] = {"consumption_kwh": cons, "pv_kwh": pvm, "import_kwh": imp, "export_kwh": exp_, "carry_in_kwh": cin, "billed_kwh": bil, "bill_krw": bills}

def tday(base, amp=5):
    return [round(base + amp * math.sin(math.pi * (i / 4 - 9) / 12), 1) for i in range(96)]
def setp(persons, summer):
    out = []
    for i in range(96):
        act = any(p[i] == 1 for p in persons); slp = any(p[i] == 2 for p in persons)
        out.append((26 if act else 27 if slp else None) if summer else (20 if act else 18 if slp else 16))
    return out
for key, P in profiles.items():
    D0 = P["days"]; new = {}
    for nk, src, lbl, date, season in (("winter_weekday", "weekday", "겨울 평일", "2026-01-14", "w"), ("winter_weekend", "weekend", "겨울 주말", "2026-01-17", "w"),
                                       ("summer_weekday", "weekday", "여름 평일", "2026-07-15", "s"), ("summer_weekend", "weekend", "여름 주말", "2026-07-18", "s"),
                                       ("peak", "peak", "최대 부하일", "2026-01-25", "p")):
        d = json.loads(json.dumps(D0[src])); d["label"] = lbl; d["date"] = date; d["rule"] = "MOCK"
        if season == "s":
            d["kw"]["heating"] = [0] * 96
            d["kw"]["cooling"] = [round(0.7 if 40 < i < 90 and any(p[i] == 1 for p in d["persons"]) else 0, 3) for i in range(96)]
            d["t_out"] = tday(27); ts = setp(d["persons"], True)
            d["t_in"] = [round(t if t else min(31, d["t_out"][i] + 1.5), 1) for i, t in enumerate(ts)]; d["t_set"] = [t if t else 30 for t in ts]
        else:
            d["kw"]["cooling"] = [0] * 96
            d["t_out"] = tday(-12 if season == "p" else -5); d["t_set"] = setp(d["persons"], False)
            d["t_in"] = [round(t - 0.3 + 0.3 * math.sin(i / 5), 1) for i, t in enumerate(d["t_set"])]
        new[nk] = d
    P["days"] = new; P["day_order"] = list(new)
    W = P["week"]; wk = {k: [] for k in ENDUSE}
    for dd in range(7):
        src = new["winter_weekday"] if dd < 5 else new["winter_weekend"]
        for k in ENDUSE: wk[k] += [round(v * (0.85 + 0.3 * random.random()), 3) for v in src["kw"][k]]
    W["kw"] = wk; W.pop("kw_total", None)
    W["t_out"] = [round(-4 + 5 * math.sin(math.pi * ((i % 96) / 4 - 9) / 12) + random.uniform(-.5, .5), 1) for i in range(672)]
    W["t_set"] = [(20 if 7 <= (i % 96) / 4 < 23 else 18) if W["home_count"][i] > 0 else 16 for i in range(672)]
    W["t_in"] = [round(t - 0.4 + 0.3 * math.sin(i / 5), 1) for i, t in enumerate(W["t_set"])]

def pday(dt):
    if dt == "weekday": w = random.randint(23, 28); lv = w + random.randint(3, 6); rt = random.randint(70, 82); b = random.randint(89, 95)
    else: w = random.randint(29, 38); lv = random.randint(48, 60); rt = lv + random.randint(8, 22); b = random.randint(91, 95)
    return [2 if (i < w or i >= b) else 0 if lv <= i < rt else 1 for i in range(96)]
data["tus"]["sample_person_days"] = [{"daytype": dt, "sex": sx, "states": pday(dt)} for dt in ("weekday", "saturday", "sunday") for sx in ("M", "F") for _ in range(5)]
data["tus"]["sleep_dur_hist"] = {"edges_h": [4, 5, 6, 7, 8, 9, 10, 11, 12], "weekday": [2, 8, 22, 34, 24, 8, 2, 0], "weekend": [1, 3, 12, 27, 31, 18, 6, 2]}
data["tus"]["realism"] = [{"metric": m_, "daytype": dt, "sim": sv, "kosis": kv, "unit": "min"} for m_, dt, sv, kv in
                          (("수면", "weekday", 452, 455), ("수면", "sunday", 531, 524), ("일", "weekday", 498, 505), ("이동", "weekday", 92, 88))]
for k_, Z in ze.items():
    Z["soc7"]["basis"] = {"seed": 47, "pv_factor": 0.887, "soh": 0.7, "rule": "수명 말기 조건·사이징 결정 시드로 1년 운전, 연중 최저 충전 상태 포함 7일"}
    Z["soc7"]["soc_floor_pct"] = 5.0; Z["soc7"]["soc_pct"] = [max(5.0, v) for v in Z["soc7"]["soc_pct"]]
data["appliances"] = [dict(a, hp=hp_) for hp_, _, _ in HP for a in data["appliances"]]
json.dump(data, open(sys.argv[1] if len(sys.argv) > 1 else "report_data.mock.json", "w"), ensure_ascii=False)
print("ok", len(scen), len(energy))
