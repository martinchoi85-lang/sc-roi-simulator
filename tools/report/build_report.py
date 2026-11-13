"""report_data.json + report_template.html + echarts.min.js -> 단일 HTML 보고서 (schema sc-report-2).

사용법: python build_report.py <report_data.json> <출력.html> [--template ...] [--echarts ...]
- 템플릿(문구·차트)은 수정하지 않는다. 숫자·문장은 모두 report_data.json에서 온다.
- [FAIL]: 형식 오류. HTML을 만들지 않고 종료 코드 1.
- [WARN]: HTML은 만들지만 계산 결과를 다시 확인해야 하는 항목(물리·상식 점검).
"""
import argparse, json, math, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
SCHEMA = "sc-report-2"
TOP = ["schema_version", "run_id", "meta", "load_mode_detail", "dims", "constants", "scenarios", "energy",
       "lifetimes", "profiles", "tus", "appliances", "seed_range", "kappa_sens", "ze", "sensitivities", "inputs", "limits"]
SC_KEYS = ["id", "hp", "heat", "occ", "target", "sub", "pv_kw", "ess_kwh", "ess_modules", "capex", "annual_benefit_krw",
           "var_bill_saving_pct", "cum25_krw", "payback_years", "payback_reason", "replacements", "cum_cashflow"]
EN_KEYS = ["hp", "occ", "sub", "case", "pv_kw", "ess_kwh", "import_kwh", "export_kwh", "billed_kwh", "elec_fixed_krw",
           "elec_variable_krw", "propane_kg", "gas_krw", "enduse_kwh", "heat_th_kwh", "pv_gen_kwh", "monthly"]
CASES = ["baseline", "awhp_only", "gas_nz", "gas_zb", "gas_ze", "awhp_nz", "awhp_zb", "awhp_ze"]
STATUS = {"VERIFIED", "UNVERIFIED", "PLACEHOLDER", "ASSUMPTION"}
ENDUSE = ["heating", "cooling", "dhw", "cooking", "laundry", "dishwasher", "fridge", "lighting", "plug", "vent_standby"]
BASIS = {"제조사 보증", "공공·법정", "업계 통상", "추정"}


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def person_flags(states, weekday):
    """개인 하루 상태(96칸, 0=외출 1=재택 2=수면)의 상식 점검. 문제 문자열 목록을 돌려준다."""
    f = []
    sleep_h = sum(1 for s in states if s == 2) / 4
    if not 4 <= sleep_h <= 12: f.append(f"수면 {sleep_h:.1f}시간")
    if weekday and any(states[i] == 0 for i in range(4, 16)): f.append("평일 01~04시 외출")
    blocks = sum(1 for i in range(1, 96) if states[i] == 2 and states[i - 1] != 2) + (1 if states[0] == 2 else 0)
    if states[0] == 2 and states[95] == 2: blocks -= 1
    if blocks > 3: f.append(f"수면 구간 {blocks}개")
    return f


def check(d):
    E, W = [], []
    err, warn = E.append, W.append
    for k in TOP:
        if k not in d: err(f"최상위 키 누락: {k}")
    if E: return E, W
    if d["schema_version"] != SCHEMA: err(f"schema_version은 '{SCHEMA}'이어야 함")
    dm, C = d["dims"], d["constants"]
    hps = [h["id"] for h in dm["house_persons"]]; heats = [h["id"] for h in dm["heating"]]
    tg = [t["id"] for t in dm["targets"]]; subs = [s["id"] for s in dm["subsidy"]]; occ = dm["occupancy"]
    if heats != ["gas", "awhp"]: err("dims.heating id는 ['gas','awhp']")
    if tg != ["nz", "zb", "ze"]: err("dims.targets id는 ['nz','zb','ze']")
    # constants
    pcs = C.get("ess_price_cases")
    if not isinstance(pcs, list) or not pcs: err("constants.ess_price_cases 누락"); pcs = []
    pids = [p.get("id") for p in pcs]
    for need in ("low", "central", "high"):
        if need not in pids: err(f"ess_price_cases에 '{need}' 없음")
    for p_ in pcs:
        if not num(p_.get("krw_per_kwh")) or p_.get("status") not in STATUS or "label" not in p_:
            err(f"ess_price_cases 항목 형식 오류: {p_.get('id')}")
    for k in ("ess_module_kwh", "propane_mj_per_kg", "horizon_years"):
        if not num(C.get(k)): err(f"constants.{k} 누락")
    if not isinstance(C.get("replacement_rule"), str) or not C["replacement_rule"]: err("constants.replacement_rule(교체비 산정 규칙 문장) 누락")
    if "boiler_avoided_cost_included" not in C: err("constants.boiler_avoided_cost_included 누락(true/false)")
    # scenarios
    exp = len(hps) * len(heats) * len(occ) * len(tg) * len(subs)
    if len(d["scenarios"]) != exp: err(f"scenarios 개수 {len(d['scenarios'])} != {exp}")
    seen = set()
    for s in d["scenarios"]:
        miss = [k for k in SC_KEYS if k not in s]
        if miss: err(f"scenario {s.get('id')} 키 누락 {miss}"); continue
        key = (s["hp"], s["heat"], s["occ"], s["target"], s["sub"])
        if key in seen: err(f"scenario 중복 {key}")
        seen.add(key)
        if s["hp"] not in hps or s["heat"] not in heats or s["occ"] not in occ or s["target"] not in tg or s["sub"] not in subs:
            err(f"scenario {s['id']} 차원 값이 dims에 없음")
        c = s["capex"]
        if "net" not in c: err(f"scenario {s['id']} capex.net 누락")
        elif abs(sum(v for k, v in c.items() if k != "net") - c["net"]) > 1: err(f"scenario {s['id']} CAPEX 합계 불일치")
        if len(s["cum_cashflow"]) != 101: err(f"scenario {s['id']} cum_cashflow 길이 101 아님")
        p = s["payback_years"]
        if p is None and s["payback_reason"] not in ("over_100y", "no_benefit"): err(f"scenario {s['id']} payback null인데 reason 없음")
        if p is not None and not (0 <= p <= 100): err(f"scenario {s['id']} payback 범위 밖 {p}")
    # 민감도 단조성: 이득만 늘리는 민감도(보일러 회피비용·AWHP 보조금)는 회수기간을 늘릴 수 없다
    for r in d["sensitivities"]:
        if any(w in r.get("group", "") for w in ("보일러 회피", "AWHP 보조금")):
            b_, s_ = r.get("base"), r.get("sens")
            if b_ is not None and (s_ is None or s_ > b_ + 0.05):
                err(f"민감도 단조성 위반: {r['group']} / {r['case']} 기준 {b_} → 민감도 {s_}")
        if s["target"] == "nz" and ("nz_required_capex_krw" not in s or "nz_required_cut_pct" not in s): err(f"scenario {s['id']} nz_required_* 누락")
        if s["target"] == "zb":
            z = s.get("zb_payback_ess") or {}
            for pid in pids:
                if pid not in z: err(f"scenario {s['id']} zb_payback_ess.{pid} 누락")
            if "zb_breakeven_ess_krw_per_kwh" not in s: err(f"scenario {s['id']} zb_breakeven_ess_krw_per_kwh 누락(null 허용)")
        for r in s["replacements"]:
            if r.get("item") not in ("pv", "inverter", "ess", "awhp"): err(f"scenario {s['id']} replacements.item 오류")
        for k, v in s.items():
            if isinstance(v, float) and not math.isfinite(v): err(f"scenario {s['id']} {k}에 NaN/Inf")
    # energy
    ek = {}
    for e in d["energy"]:
        miss = [k for k in EN_KEYS if k not in e]
        if miss: err(f"energy {e.get('hp')}/{e.get('case')} 키 누락 {miss}"); continue
        kk = (e["hp"], e["occ"], e["sub"], e["case"])
        if kk in ek: err(f"energy 행 중복 {kk}")
        ek[kk] = e
        eu = e["enduse_kwh"]
        if set(eu) != set(ENDUSE) or not all(num(v) for v in eu.values()): err(f"energy {kk} enduse_kwh 키는 {ENDUSE} 전부(숫자)")
        if set(e["heat_th_kwh"]) != {"heating", "dhw", "cooling"}: err(f"energy {kk} heat_th_kwh 키는 heating/dhw/cooling")
        m = e["monthly"]
        if any(len(m.get(k, [])) != 12 for k in ("consumption_kwh", "pv_kwh", "bill_krw")): err(f"energy {kk} monthly 배열 길이 12 아님")
        elif sum(eu.values()) > 0 and abs(sum(m["consumption_kwh"]) - sum(eu.values())) > 0.01 * sum(eu.values()) + 1:
            err(f"energy {kk} 월별 소비 합 {sum(m['consumption_kwh']):.0f} ≠ 용도별 합 {sum(eu.values()):.0f}")
        MK = ("import_kwh", "export_kwh", "carry_in_kwh", "billed_kwh", "bill_krw")
        if any(len(m.get(k, [])) != 12 for k in MK): err(f"energy {kk} monthly에 {MK} 각 12개월 필요")
        else:
            tot_bill = e["elec_fixed_krw"] + e["elec_variable_krw"]
            if abs(sum(m["bill_krw"]) - tot_bill) > 120: err(f"energy {kk} 월 요금 합 {sum(m['bill_krw'])} ≠ 연간 전기요금 {tot_bill}")
            if abs(sum(m["billed_kwh"]) - e["billed_kwh"]) > 12: err(f"energy {kk} 월 과금 kWh 합 ≠ billed_kwh")
            for i in range(12):
                net = m["import_kwh"][i] - m["export_kwh"][i] - m["carry_in_kwh"][i]
                if abs(max(0, net) - m["billed_kwh"][i]) > 1: err(f"energy {kk} {i+1}월 과금 kWh ≠ max(0, 수전−역송−이월)"); break
                cout = max(0, -net)
                if i < 11 and abs(cout - m["carry_in_kwh"][i + 1]) > 1: err(f"energy {kk} {i+1}월 이월 연결 오류"); break
                if i == 11 and abs(cout - m["carry_in_kwh"][0]) > 1 and not (cout > m["carry_in_kwh"][0] and sum(m["import_kwh"]) <= sum(m["export_kwh"])):
                    err(f"energy {kk} 12월 말 이월 ≠ 1월 초 이월(연간 잉여가 없는데 정상상태 아님)"); break
            if sum(m["import_kwh"]) - sum(m["export_kwh"]) >= -1 and min(m["carry_in_kwh"]) > 1:
                warn(f"energy {kk} 연간 잉여가 없는데 이월 잔고가 1년 내내 {min(m['carry_in_kwh']):.0f} kWh 이상 남음(정상상태 초기값 확인)")
            cv = m["consumption_kwh"]; mean = sum(cv) / 12
            if mean > 0 and max(cv) - min(cv) > 0.1 * mean and len(set(m["bill_krw"])) == 1 and e["billed_kwh"] > 0:
                warn(f"energy {kk} 월 소비는 다른데 월 요금이 12개월 모두 같음")
        gas = e["case"] == "baseline" or e["case"].startswith("gas")
        if gas and eu.get("heating", 0) + eu.get("dhw", 0) > 400:
            warn(f"가스 케이스 {kk} 난방+급탕 전력 {eu['heating'] + eu['dhw']:.0f} kWh (보일러 보조전력만 있어야 함)")
        if not gas and e["propane_kg"] > 0: warn(f"AWHP 케이스 {kk} 프로판 {e['propane_kg']} kg")
        h_ = e["heat_th_kwh"]; th = h_["heating"] + h_["dhw"]
        if gas and e["propane_kg"] > 0:
            eff = th / (e["propane_kg"] * d["constants"]["propane_mj_per_kg"] / 3.6)
            if not 0.6 <= eff <= 1.08: warn(f"가스 케이스 {kk} 보일러 효율 {eff:.0%} (열량÷프로판 순발열량)")
        if not gas and eu["heating"] + eu["dhw"] > 0:
            cop = th / (eu["heating"] + eu["dhw"])
            if not 1.5 <= cop <= 5.5: warn(f"AWHP 케이스 {kk} 연평균 COP {cop:.2f}")
    for h in hps:
        for o in occ:
            for sb in subs:
                for cs in CASES:
                    if (h, o, sb, cs) not in ek: err(f"energy 행 누락 {(h, o, sb, cs)}")
                b, a = ek.get((h, o, sb, "baseline")), ek.get((h, o, sb, "awhp_only"))
                if b and a and sum(a["enduse_kwh"].values()) < sum(b["enduse_kwh"].values()):
                    warn(f"{h}/{o}%: AWHP 케이스 전력 소비가 가스 케이스보다 작음")
    # 연간 이득 = 기준안 총에너지비용 − 대안 총에너지비용 (1년 차), 현금흐름 1년 차와 일치
    tot = lambda e: e["elec_fixed_krw"] + e["elec_variable_krw"] + e["gas_krw"]
    nb = 0
    for s in d["scenarios"]:
        b_ = ek.get((s["hp"], s["occ"], s["sub"], "baseline")); a_ = ek.get((s["hp"], s["occ"], s["sub"], f"{s['heat']}_{s['target']}"))
        if not b_ or not a_: continue
        if a_["pv_kw"] != s["pv_kw"] or abs(a_["ess_kwh"] - s["ess_kwh"]) > 0.01:
            err(f"scenario {s['id']} PV·ESS가 energy 행과 다름"); continue
        diff = tot(b_) - tot(a_)
        if abs(s["annual_benefit_krw"] - diff) > 10:
            nb += 1
            if nb <= 10: err(f"scenario {s['id']} 연간 이득 {s['annual_benefit_krw']} ≠ 기준안−대안 에너지비용 {diff}")
        rep1 = sum(r["krw"] for r in s["replacements"] if r["year"] == 1)
        y1 = s["cum_cashflow"][1] - s["cum_cashflow"][0] + rep1
        if abs(y1 - s["annual_benefit_krw"]) > max(10, 0.001 * abs(s["annual_benefit_krw"])):
            warn(f"scenario {s['id']} 현금흐름 1년 차 증가 {y1} ≠ 연간 이득 {s['annual_benefit_krw']}")
    if nb > 10: err(f"연간 이득 불일치 총 {nb}건")
    for l in d["lifetimes"]:
        if l.get("status") not in STATUS: err(f"lifetimes status 오류 {l.get('item')}")
        if l.get("basis") not in BASIS: err(f"lifetimes basis는 {sorted(BASIS)} 중 하나: {l.get('basis')}")
    for r in d["inputs"]:
        if r.get("status") not in STATUS: err(f"inputs status 오류 {r.get('name')}")
    # profiles
    pflag = 0
    for h in hps:
        for ht in heats:
            k = f"{h}|{ht}"
            P = d["profiles"].get(k)
            if not P: err(f"profiles['{k}'] 누락"); continue
            days = P.get("days") or {}
            if "peak" not in days: err(f"profiles['{k}'].days.peak 누락")
            for dk_, dd in days.items():
                if not all(x in dd for x in ("date", "label", "kw", "persons")): err(f"profiles['{k}'].days.{dk_} 키 누락"); continue
                if set(dd["kw"]) - set(ENDUSE): err(f"profiles['{k}'].{dk_} 알 수 없는 용도 {set(dd['kw']) - set(ENDUSE)}")
                if any(len(v) != 96 for v in dd["kw"].values()): err(f"profiles['{k}'].{dk_} kw 길이 96 아님")
                for t in ("t_out", "t_in", "t_set"):
                    if t in dd and len(dd[t]) != 96: err(f"profiles['{k}'].{dk_}.{t} 길이 96 아님")
                for st in dd["persons"]:
                    if len(st) != 96 or any(x not in (0, 1, 2) for x in st): err(f"profiles['{k}'].{dk_} persons 형식 오류"); break
                    fl = person_flags(st, "weekday" in dk_)
                    if fl: pflag += 1; warn(f"대표일 {k}/{dk_} 거주자 일과 비현실: {', '.join(fl)}")
                if ht == "gas" and max(dd["kw"].get("heating", [0]) + dd["kw"].get("dhw", [0])) > 0.5:
                    warn(f"가스 케이스 {k}/{dk_} 난방·급탕 전력 최대 {max(dd['kw'].get('heating', [0]) + dd['kw'].get('dhw', [0])):.2f} kW")
                if "cooling" in dd["kw"]:
                    away = [i for i in range(96) if all(p[i] == 0 for p in dd["persons"]) and dd["kw"]["cooling"][i] > 0.05]
                    if away: warn(f"{k}/{dk_} 전원 외출 중 냉방 {len(away)}칸")
            W_ = P.get("week") or {}
            n = len(W_.get("home_count", []))
            if n != 672: err(f"profiles['{k}'].week.home_count 길이 672 아님")
            if "kw" in W_:
                if any(len(v) != n for v in W_["kw"].values()) or set(W_["kw"]) - set(ENDUSE): err(f"profiles['{k}'].week.kw 형식 오류")
            elif len(W_.get("kw_total", [])) != n: err(f"profiles['{k}'].week에 kw(용도별) 또는 kw_total 필요")
            for t in ("t_out", "t_in", "t_set"):
                if t in W_ and len(W_[t]) != n: err(f"profiles['{k}'].week.{t} 길이 오류")
            if len(P["hourly_heatmap"]) != 365 or any(len(r) != 24 for r in P["hourly_heatmap"]): err(f"profiles['{k}'].hourly_heatmap 365x24 아님")
            if len(P["daily_kwh"]) != 365: err(f"profiles['{k}'].daily_kwh 길이 365 아님")
            for b in ("weekday", "saturday", "sunday"):
                if any(len(P["bands"][b][q]) != 96 for q in ("p10", "p50", "p90")): err(f"profiles['{k}'].bands.{b} 길이 오류")
            # ze
            Z = d["ze"].get(k)
            if not Z: err(f"ze['{k}'] 누락"); continue
            S_ = Z.get("search") or []
            if not S_: err(f"ze['{k}'].search 비어 있음")
            for r in S_:
                if not isinstance(r.get("modules"), int) or not (r.get("min_pv_kw") is None or num(r.get("min_pv_kw"))) or not (r.get("capex_krw") is None or num(r.get("capex_krw"))):
                    err(f"ze['{k}'].search 항목 형식 오류 {r}"); break
            sel = next((s for s in d["scenarios"] if s["hp"] == h and s["heat"] == ht and s["occ"] == 100 and s["target"] == "ze" and s["sub"] == subs[0]), None)
            if sel and S_ and sel["ess_modules"] not in [r.get("modules") for r in S_]: warn(f"ze['{k}'] 선택 모듈 수 {sel['ess_modules']}가 search에 없음")
            if len(Z["daily"]["load_kwh"]) != 365 or len(Z["daily"]["pv_kwh"]) != 365: err(f"ze['{k}'].daily 길이 오류")
            Q = Z.get("soc7") or {}
            if not all(len(Q.get(x, [])) == 672 for x in ("soc_pct", "pv_kw", "load_kw")): err(f"ze['{k}'].soc7 배열 길이 672 아님")
            elif not isinstance(Q.get("basis"), dict) or not num(Q.get("soc_floor_pct")): err(f"ze['{k}'].soc7.basis / soc_floor_pct 누락")
            elif Z.get("minimality") not in ("start_constraint", "pass") and min(Q["soc_pct"]) > Q["soc_floor_pct"] + 5:
                warn(f"ze['{k}'] 7일 최저 SoC {min(Q['soc_pct']):.1f}% > 하한 {Q['soc_floor_pct']}%+5 → 구간 선정 또는 조합 최소성 확인")
    # tus
    tu = d["tus"]
    for f in tu.get("fit", []):
        if len(f["target"]) != 48 or len(f["sim"]) != 48: err(f"tus.fit {f['curve']}/{f['daytype']} 길이 48 아님")
    for k in ("leave_hist", "return_hist"):
        if len(tu.get(k, [])) != 48: err(f"tus.{k} 길이 48 아님")
    spd = tu.get("sample_person_days") or []
    if len(spd) < 12: err("tus.sample_person_days 12개 이상 필요")
    bad = 0
    for r in spd:
        if len(r.get("states", [])) != 96: err("tus.sample_person_days.states 길이 96 아님"); break
        if person_flags(r["states"], r.get("daytype") == "weekday"): bad += 1
    if bad: warn(f"표본 거주자-일 {bad}/{len(spd)}개가 상식 점검 위반(수면 4~12시간, 평일 01~04시 외출 없음, 수면 구간 ≤3)")
    sh = tu.get("sleep_dur_hist") or {}
    if "edges_h" not in sh or any(len(v) != len(sh["edges_h"]) - 1 for k, v in sh.items() if k != "edges_h"): err("tus.sleep_dur_hist 형식 오류")
    for r in tu.get("realism", []):
        if not all(x in r for x in ("metric", "daytype", "sim", "kosis", "unit")): err("tus.realism 항목 키 누락"); break
    if not tu.get("realism"): err("tus.realism 비어 있음")
    # appliances
    for a in d["appliances"]:
        if num(a.get("annual_target_kwh")) and a["annual_target_kwh"] > 0 and abs(a["annual_sim_kwh"] / a["annual_target_kwh"] - 1) > 0.005:
            warn(f"가전 보정 오차 > 0.5%: {a['hp']} {a['name']} {a['annual_sim_kwh']} / {a['annual_target_kwh']}")
    txt = json.dumps(d, ensure_ascii=False)
    for w in ("999.0", "상사", "보고 요령", "어필"):
        if w in txt: err(f"금지 문자열 발견: {w}")
    return E, W


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out")
    ap.add_argument("--template", default=str(HERE / "report_template.html"))
    ap.add_argument("--echarts", default=str(HERE / "echarts.min.js"))
    a = ap.parse_args()
    d = json.load(open(a.data, encoding="utf-8"))
    errs, warns = check(d)
    for w in warns[:60]: print("[WARN]", w)
    if len(warns) > 60: print(f"[WARN] … 외 {len(warns) - 60}건")
    if errs:
        print(f"[FAIL] 스키마 오류 {len(errs)}건 (HTML 생성 안 함)")
        for e in errs[:60]: print(" -", e)
        sys.exit(1)
    tpl = pathlib.Path(a.template).read_text(encoding="utf-8")
    ech = pathlib.Path(a.echarts).read_text(encoding="utf-8")
    js = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    assert tpl.count("/*__ECHARTS__*/") == 1 and tpl.count("/*__DATA__*/null") == 1, "템플릿 자리표시자 오류"
    pathlib.Path(a.out).write_text(tpl.replace("/*__ECHARTS__*/", ech).replace("/*__DATA__*/null", js), encoding="utf-8")
    print(f"[OK] {a.out} run_id={d['run_id']} WARN {len(warns)}건")


if __name__ == "__main__":
    main()
