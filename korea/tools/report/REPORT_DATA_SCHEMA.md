# report_data.json 데이터 계약 (schema_version = "sc-report-2")

보고서 HTML은 `report_template.html`(고정)과 이 JSON으로만 만들어진다. 계산 코드는 이 형식의 JSON만 출력하고 HTML·차트·문장은 만들지 않는다.
단위: 금액 원(정수), 전력 kW, 전력량 kWh, 회수기간 년(소수 1자리), 비율 %(0~100), 온도 °C. NaN·Infinity·999 같은 내부값 금지(없으면 `null`).
`make_mock_data.py`가 같은 구조의 예시를 만든다(값은 가짜). `build_report.py`가 형식을 검사하고 [FAIL]이면 HTML을 만들지 않는다. [WARN]은 계산 결과를 다시 봐야 하는 물리·상식 점검이다.

## 1. 최상위
schema_version, run_id, meta{country, location, weather_source, annual_ghi_kwh_m2, created_at, is_mock:false}, load_mode_detail(문장), dims, constants, scenarios, energy, lifetimes, profiles, tus, appliances, seed_range, kappa_sens, ze, sensitivities, inputs, limits

dims (순서 고정)
- house_persons: `[{"id":"C54_1","house":"MONO Core 54","persons":1,"label":"MONO Core 54 · 1인"}, …]` id = C54_1, C54_2, C72_1, C72_2, C72_3, D45_1, D45_2
- heating: gas, awhp / occupancy: [100,70,50,30,15] / targets: nz, zb, ze / subsidy: none, pv2026

constants
- ess_module_kwh, pv_unit_krw_per_kw, awhp_capex_krw, propane_krw_per_kg, propane_mj_per_kg, tariff_300kwh_krw, ess_soh_eol, ess_soc_window, ess_rte, pv_degradation_per_year, horizon_years, pv_subsidy_krw_3kw, pv_subsidy_max_kw
- replacement_rule: 교체비 산정 규칙 문장(설비별 교체 단가 기준·보조금 재지급 여부). 예: "ESS는 배터리 팩만 교체(NREL ATB 2030 396,200원/kWh), 인버터·AWHP·PV는 현재 단가, 보조금 재지급 없음"
- boiler_avoided_cost_included: true/false (AWHP 케이스에서 기존 보일러 구입·교체비 절감을 반영했는지)
- ess_price_cases: `[{"id":"low"|"central"|"high"|"specific", "label", "krw_per_kwh", "usd_per_kwh"(없으면 null), "status", "source"}]` low·central·high 필수, specific은 확인된 실제 사례가 있을 때 추가

## 2. scenarios (420행)
id, hp, heat, occ, target, sub, pv_kw, ess_kwh, ess_modules,
capex{pv, ess, awhp, grid, pv_subsidy(음수), awhp_subsidy(음수, 민감도만), net} (net = 나머지 합, 오차 ≤1원),
annual_benefit_krw, var_bill_saving_pct, cum25_krw, payback_years(또는 null), payback_reason(null/"over_100y"/"no_benefit"),
replacements[{year, item:"pv"|"inverter"|"ess"|"awhp", krw}], cum_cashflow[101]
- target=nz: nz_required_capex_krw(=3×연간 이득), nz_required_cut_pct(0 미만이면 0)
- target=zb: zb_payback_ess{price_case_id: 회수기간 또는 null} (ess_price_cases의 모든 id),
  zb_breakeven_ess_krw_per_kwh = 회수기간 ≤ 25년이 되는 최대 ESS 단가(원/kWh). ESS 단가 0원이어도 25년 초과면 null

## 3. energy (1년 차, 7 × 5 × 2 × case 8 = 560행)
case: baseline(가스보일러+계통), awhp_only(AWHP, PV·ESS 없음), gas_nz, gas_zb, gas_ze, awhp_nz, awhp_zb, awhp_ze. baseline·awhp_only는 두 보조금 행에 같은 값.

| 키 | 내용 |
|---|---|
| pv_kw, ess_kwh | 조합(baseline·awhp_only는 0) |
| import_kwh, export_kwh, billed_kwh | 수전, 역송, 월 합산 상계 후 과금 전력량 |
| elec_fixed_krw | 각 월 사용량 0일 때의 청구액 합(기본요금+그 부가세·기금). 계통 계약 없는 Zero energy는 0 |
| elec_variable_krw | 연간 전기요금 − elec_fixed_krw |
| propane_kg, gas_krw | 연간 프로판 kg, 요금 |
| enduse_kwh | 연간 **전력** 소비 용도별 {heating, cooling, dhw, cooking, laundry, dishwasher, fridge, lighting, plug, vent_standby} 10개 모두. 가스 케이스의 heating·dhw는 보일러 보조전력(펌프·팬)만 |
| heat_th_kwh | 공급 열량 {heating, dhw, cooling} (kWh_th) |
| pv_gen_kwh | 연간 PV 발전량 |
| monthly | {consumption_kwh, pv_kwh, import_kwh, export_kwh, carry_in_kwh(그달 시작 시 이월 잉여), billed_kwh(=max(0, 수전−역송−이월)), bill_krw(그달 청구액)} 각 12개월. 12월 말 이월 = 1월 carry_in(정상상태). bill_krw 합 = elec_fixed_krw + elec_variable_krw(±120원). consumption 합 = enduse 합 |

## 4. lifetimes
`[{"item":"pv"|"inverter"|"ess"|"awhp","label","years","basis","status","note"}]` basis ∈ 제조사 보증 / 공공·법정 / 업계 통상 / 추정

## 5. profiles (키 "<hp>|<heat>", 14개, 이용률 100%·기본 시드)
- days: {키: {date, label, rule, kw{용도:[96]}, persons[[96]…], t_out[96], t_in[96], t_set[96]}}, day_order: 키 순서 목록
  - 권장 키: winter_weekday, winter_weekend, summer_weekday, summer_weekend, peak(필수)
  - rule: 그날을 고른 기준 문장(예: "12~2월 평일 중 일 사용량이 중앙값 ±10% 이내이고 재실 패턴이 가장 전형적인 날")
  - persons 값: 0 외출, 1 재택(활동), 2 수면
  - t_set: 그 시각의 난방 또는 냉방 설정온도(운전 안 하면 null 대신 해당 시각 실내온도와 같은 값)
- week: {start_date(월요일), kw{용도:[672]}, home_count[672], t_out[672], t_in[672], t_set[672]} 겨울 연속 7일
- hourly_heatmap[365][24] 시간 평균 kW, bands{weekday,saturday,sunday}{p10,p50,p90}[96], daily_kwh[365]

## 6. tus (재실 달력과 무관한 별도 시뮬레이션)
- person_days, lambda(해당 없으면 null), away_episodes_weekday_mean
- fit[{curve: sleep|away|cook|media, daytype: weekday|saturday|sunday, target[48], sim[48], mae}]
- leave_hist[48], return_hist[48]: 평일 첫 외출·마지막 귀가 30분 칸 비율(%)
- sample_person_days[{daytype, sex:"M"|"F", states[96]}]: 평일·토·일 × 남녀 × 5명 = 30개 무작위 추출(골라내기 금지)
- sleep_dur_hist{edges_h[k+1], weekday[k], weekend[k]}: 하루 수면 시간 분포(%)
- realism[{metric, daytype, sim, kosis, unit:"min"}]: 시뮬레이션 개인 하루 평균 vs KOSIS 평균시간(취업자). 최소 수면·일·이동 × 평일/토/일

## 7. 보정·민감도
- appliances[{hp, name, rated_kw, cycle_min(상시 0), annual_target_kwh, annual_sim_kwh, status}]: 주택·인원별 실제 탑재 가전 전부. annual_sim_kwh는 시뮬레이션 합계(목표 복사 금지)
- seed_range[{hp, heat, pv_min, pv_max, ess_min, ess_max, capex_min, capex_max}]
- kappa_sens[{kappa, values{"열 제목(단위)": 숫자|null}}]

## 8. ze (키 "<hp>|<heat>", 14개, 이용률 100%)
- search[{modules(int), min_pv_kw(없으면 null), capex_krw(없으면 null)}]: 탐색한 모든 모듈 수. 비어 있으면 FAIL
- daily{load_kwh[365], pv_kwh[365](선택 PV의 수명 말기 일 발전), ess_usable_kwh}
- minimality: "pass"(PV −0.5kW·ESS −1모듈 모두 LOL>0) / "start_constraint"(ESS −1모듈이 시작 조건 위반) / "fail"
- soc7{start_date, soc_pct[672], pv_kw[672], load_kw[672], soc_floor_pct, basis{seed, pv_factor, soh, rule}}
  - 선택 조합을 수명 말기 조건(pv_factor, soh)과 사이징을 결정한 시드로 1년 운전하고, SoC가 연중 최저가 되는 시점을 포함한 7일
  - 최소 조합이면 최저 SoC가 하한(soc_floor_pct)에 닿아야 한다. 닿지 않으면 WARN

## 9. 기타
- sensitivities[{group, case, base, sens}] 회수기간 또는 null
- inputs[{group, name, value(문자열), unit, status, source}]
- limits[문장]
