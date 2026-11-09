# LG Smart Cottage ROI Simulation & Physical Validation Report

## 1. 2026-02-03 (Day 34) 저조도 원인 및 PV 모델 검증
- **GHI 1.18 kWh/m² 오표기 원인 규명**:
  * 기존 보고서의 GHI 1.18은 실제 일사량이 아니라, `sizing.py`에서 `crit_ghi_kwh_m2 = crit_pv1_kwh / (0.21 * 0.86) = 0.2137 / 0.1806 = 1.18`로 잘못 역산된 코드 표기 버그였음.
  * 춘천 TMYx 공식 EPW 기상 데이터 상 2026-02-03의 실제 일사량 합계는 **GHI = 0.2465 kWh/m²** (DNI = 0.0, 산란광 DHI = 0.2465 kWh/m²)로 연중 최저 일사 강설일임.
  * 경사면 일사량 POA = 0.2379 kWh/m², DC 발전량 = 0.2562 kWh (외기온 1.5°C 저온 효율 상승 반영), 인버터(97%) 및 BOS 손실(14%) 후 최종 AC 발전량 = **0.2137 kWh**.
  * 실제 발전 비율: 1kWp 발전량 / GHI = 0.2137 / 0.2465 = **86.7%** (정상 성능비 PR 범위).
- **인버터 최소 동작값·tare 손실·시간 보간·적설·클리핑 가정 점검**:
  * 인버터 모델: Tare 손실(야간 대기전력) 및 최소 동작 컷오프는 1kWp 정규화 시 왜곡을 방지하기 위해 0으로 처리하였으며, 실제 시스템 인버터 부하율(33kW PV 기준 정오 발전 1.5kW / 3kW 인버터 = 부하율 50%)에서 97% 고효율 구간에서 정상 동작함을 확인.
  * 15분 단위 상세 내역은 `korea/output/debug_day34.csv`로 저장 완료.

## 2. 일별 GHI 대비 1kWp 발전량 비율 분포 및 하위 10일
- **연간 일별 발전 비율 (1kWp AC kWh / GHI kWh/m²) 통계 분포**:
  * 평균: 0.9481, 표준편차: 0.1911
  * 최소값: 0.6970, 25% 분위: 0.7855, 중간값: 0.8948, 75% 분위: 1.0724, 최대값: 1.4301

- **발전 비율 하위 10일 (하계 고온 및 고태양고도 경사각 불일치)**:
| 순위 | 날짜 | GHI (kWh/m²/day) | 1kWp AC 발전 (kWh/day) | 발전 비율 (AC/GHI) | 비고 |
|---|---|---|---|---|---|
| 1 | 2026-06-30 | 6.164 | 4.296 | 0.6970 | 하계 고온 모듈 손실 |
| 2 | 2026-06-23 | 4.469 | 3.141 | 0.7029 | 하계 고온 모듈 손실 |
| 3 | 2026-06-22 | 6.526 | 4.589 | 0.7033 | 하계 고온 모듈 손실 |
| 4 | 2026-06-29 | 6.388 | 4.532 | 0.7094 | 하계 고온 모듈 손실 |
| 5 | 2026-06-11 | 7.104 | 5.051 | 0.7111 | 하계 고온 모듈 손실 |
| 6 | 2026-06-15 | 6.129 | 4.370 | 0.7129 | 하계 고온 모듈 손실 |
| 7 | 2026-06-06 | 7.830 | 5.634 | 0.7195 | 하계 고온 모듈 손실 |
| 8 | 2026-06-19 | 7.229 | 5.206 | 0.7202 | 하계 고온 모듈 손실 |
| 9 | 2026-06-04 | 7.450 | 5.367 | 0.7204 | 하계 고온 모듈 손실 |
| 10 | 2026-06-27 | 6.870 | 4.985 | 0.7255 | 하계 고온 모듈 손실 |

## 3. 주택 모델별 부하 사양 비교 (면적 연동 조명 및 인원 연동 사용량)
| 주택 모델 | 바닥면적 (m²) | 조명 부하 (kWh/년) | 조명 부하 (kWh/일) | 인원 수 (인) | 인원 연동 플러그 (kWh/일) | 포함 가전 목록 | 상시 전력 (W) | 100% 이용률 일 부하 (가스 케이스, kWh/일) |
|---|---|---|---|---|---|---|---|---|
| MONO Core 54 | 54.0 | 234.6 | 0.64 | 2 | 1.80 | 냉장고, 세탁기, 인덕션 | 80.0 | 5.87 |
| DUO Max 45 | 45.4 | 197.3 | 0.54 | 2 | 1.80 | 워시타워 컴팩트, 식기세척기, 인덕션, 광파오븐, 정수기, ERV, 냉장고 | 126.7 | 8.24 |
| MONO Core 72 | 72.9 | 316.8 | 0.87 | 3 | 2.70 | 냉장고, 워시타워, 인덕션, 식기세척기 | 80.0 | 8.09 |
- **동일 결과 원인 및 수정 결과**: 기존에 가전 부하를 가구원수(2인) 단일 변수로만 산정하여 Core 54와 DUO Max 45의 가스 케이스 부하가 동일하게 산출되었으나, 주택별 가전 목록(워시타워, 식기세척기, 광파오븐, 정수기, ERV) 및 면적 연동 조명을 분리 반영하여 Core 54(5.87 kWh/일)와 DUO Max(8.24 kWh/일)의 결과가 명확히 분리됨.

## 4. 12개 Critical Day 및 Zero Energy 사이징 검증
- 탐색 기준: 365일 전체 탐색 PV = max_d(일 부하 kWh / 1kWp 발전량 kWh).
- 성능 기준: PV 25년 차 계수 0.995^24, ESS 사용 가능 용량 70%.
| 주택 모델 | 난방 패키지 | EV | Critical Day | 일사량 GHI (kWh/m²/day) | 부하 (kWh) | 1kWp 발전 (kWh) | 초기 PV (kW) | 초기 ESS (kWh) | 최종 PV (kW) | 최종 ESS (kWh) | 인버터 필요 (kW) | 부족량 (kWh) | LOL (시간) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MONO Core 54 | PV+ESS+가스보일러 | 0대 | 2026-02-03 (Day 34) | 0.25 | 6.54 | 0.21 | 31.0 | 9.6 | 31.0 | 19.2 | 3.0 | 0.000000 | 0.0 |
| MONO Core 54 | PV+ESS+가스보일러 | 1대 | 2026-02-03 (Day 34) | 0.25 | 13.46 | 0.21 | 63.0 | 19.2 | 65.0 | 19.2 | 7.3 | 0.000000 | 0.0 |
| MONO Core 54 | PV+ESS+AWHP | 0대 | 2026-02-03 (Day 34) | 0.25 | 15.68 | 0.21 | 73.5 | 48.0 | 73.5 | 57.6 | 5.4 | 0.000000 | 0.0 |
| MONO Core 54 | PV+ESS+AWHP | 1대 | 2026-02-03 (Day 34) | 0.25 | 22.60 | 0.21 | 106.0 | 57.6 | 106.0 | 57.6 | 8.9 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+가스보일러 | 0대 | 2026-02-03 (Day 34) | 0.25 | 9.14 | 0.21 | 43.0 | 9.6 | 43.0 | 28.8 | 3.0 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+가스보일러 | 1대 | 2026-02-03 (Day 34) | 0.25 | 16.06 | 0.21 | 75.5 | 19.2 | 75.5 | 28.8 | 7.4 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+AWHP | 0대 | 2026-02-03 (Day 34) | 0.25 | 20.58 | 0.21 | 96.5 | 57.6 | 96.5 | 76.8 | 6.2 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+AWHP | 1대 | 2026-02-03 (Day 34) | 0.25 | 27.51 | 0.21 | 129.0 | 67.2 | 129.0 | 76.8 | 9.3 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+가스보일러 | 0대 | 2026-02-03 (Day 34) | 0.25 | 9.13 | 0.21 | 43.0 | 9.6 | 43.0 | 19.2 | 3.0 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+가스보일러 | 1대 | 2026-02-03 (Day 34) | 0.25 | 16.05 | 0.21 | 75.5 | 19.2 | 75.5 | 28.8 | 7.4 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+AWHP | 0대 | 2026-02-03 (Day 34) | 0.25 | 17.35 | 0.21 | 81.5 | 48.0 | 81.5 | 57.6 | 3.8 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+AWHP | 1대 | 2026-02-03 (Day 34) | 0.25 | 24.27 | 0.21 | 114.0 | 57.6 | 114.0 | 57.6 | 8.8 | 0.000000 | 0.0 |

## 5. 전 케이스 무정전(Zero Loss of Load) 검증
- 전 케이스 연간 부족량 최대값: `0.000000 kWh`
- 전 이용률(100%, 70%, 50%, 30%, 10%, 5%) LOL = 0 여부: `True` (전 시나리오 0.0 시간 충족)
- 기존 최대 부하일 방식 대비 성능:
  * 기존 방식 적용 시 12개 케이스 연간 정전 시간(LOL) 범위: 622.0 ~ 3,419.8 시간/년 발생.
  * 신규 365일 Critical Day 및 정상상태 모듈 탐색 방식 적용 시: 12개 케이스 전수 연간 LOL = 0.0 시간 달성.

## 6. CAPEX 정합성 및 내역 검증
- PV 턴키 = 용량 비례 (1,513,667원/kW) 정합성: `True` (오차: 0.50원)
- 지상 추가비 적용 건수: `0건` (요구사항에 따라 지상 추가비 삭제 및 PLACEHOLDER 0원 처리)
- AWHP 턴키 총액: 14,000,000원 (주요설비 12,000,000원 + 전기·기타 2,000,000원).
- ESS 단가: NREL 해외 기준 환율 1,400원/USD 적용 (Low 396,200 / Central 1,775,200 / High 1,871,800 원/kWh).
- 분전반 개체비(450,000원), 내선공사비(300,000원/kW), 인버터 교체비: PLACEHOLDER 적용.

## 7. 수전 피크 및 계약전력 검증
- 전 케이스 최대 수전 kW 분포: 최소값 0.00 kW, 25% 분위 0.00 kW, 중간값 2.10 kW, 75% 분위 7.38 kW, 최대값 9.26 kW.
- 상위 5개 최대 수전 피크 케이스:
  1. 9.26 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  2. 9.26 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  3. 9.26 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  4. 9.26 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  5. 9.26 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `70%`

## 8. PLACEHOLDER 및 UNVERIFIED 항목 전체 목록
### PLACEHOLDER 항목 (13개):
- `capex.fx_krw_per_usd`: status=PLACEHOLDER
- `capex.ground_mount_pv.threshold_kw`: status=PLACEHOLDER
- `capex.ground_mount_pv.excess_cost_per_kw`: status=PLACEHOLDER
- `capex.replacements.inverter_replacement_min_krw`: status=PLACEHOLDER
- `capex.replacements.inverter_replacement_per_kw`: status=PLACEHOLDER
- `capex.grid_connection.distribution_board_cost`: status=PLACEHOLDER
- `capex.grid_connection.wiring_expansion_cost_per_kw`: status=PLACEHOLDER
- `subsidy.ess_subsidy.unit_rate_per_kwh`: status=PLACEHOLDER
- `subsidy.ess_subsidy.max_cap`: status=PLACEHOLDER
- `load.erv_continuous_power`: status=PLACEHOLDER
- `load.ev_charge_start_hour`: status=PLACEHOLDER
- `equipment.awhp_system.nominal_heating_capacity_kw`: status=PLACEHOLDER
- `equipment.awhp_system.max_heating_capacity_kw`: status=PLACEHOLDER

### UNVERIFIED 항목 (28개):
- `houses.MONO Core 72.appliances_desc`: status=UNVERIFIED
- `houses.MONO Core 72.included_appliances`: status=UNVERIFIED
- `houses.DUO Max 45.base_pv_capacity_kw`: status=UNVERIFIED
- `tariff.super_user_rate`: status=UNVERIFIED
- `capex.pv_system.unit_cost_per_kw.low`: status=UNVERIFIED
- `capex.pv_system.unit_cost_per_kw.central`: status=UNVERIFIED
- `capex.pv_system.unit_cost_per_kw.high`: status=UNVERIFIED
- `capex.ess_system.min_module_kwh`: status=UNVERIFIED
- `capex.ess_system.unit_cost_usd_per_kwh.low`: status=UNVERIFIED
- `capex.ess_system.unit_cost_usd_per_kwh.central`: status=UNVERIFIED
- `capex.ess_system.unit_cost_usd_per_kwh.high`: status=UNVERIFIED
- `capex.ess_system.unit_cost_per_kwh.low`: status=UNVERIFIED
- `capex.ess_system.unit_cost_per_kwh.central`: status=UNVERIFIED
- `capex.ess_system.unit_cost_per_kwh.high`: status=UNVERIFIED
- `capex.awhp_system.turnkey_installation_cost.low`: status=UNVERIFIED
- `capex.awhp_system.turnkey_installation_cost.central`: status=UNVERIFIED
- `capex.awhp_system.turnkey_installation_cost.high`: status=UNVERIFIED
- `capex.awhp_system.breakdown_major_equipment`: status=UNVERIFIED
- `capex.awhp_system.breakdown_electric_and_other`: status=UNVERIFIED
- `capex.replacements.ess_replacement_unit_cost_per_kwh`: status=UNVERIFIED
- `subsidy.pv_subsidy.unit_rate_under_3kw`: status=UNVERIFIED
- `subsidy.pv_subsidy.standard_3kw_amount`: status=UNVERIFIED
- `subsidy.pv_subsidy.national_subsidy_3kw`: status=UNVERIFIED
- `subsidy.pv_subsidy.chuncheon_subsidy_3kw`: status=UNVERIFIED
- `subsidy.awhp_subsidy.sensitivity_rate_70pct`: status=UNVERIFIED
- `subsidy.awhp_subsidy.sensitivity_max_amount_krw`: status=UNVERIFIED
- `load.standby_power`: status=UNVERIFIED
- `equipment.awhp_system.cop_a2_w55`: status=UNVERIFIED
