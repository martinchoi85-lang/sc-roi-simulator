# LG Smart Cottage ROI Simulation & Physical Validation Report

## 1. 기상 데이터 검증 (Climate.OneBuilding Chuncheon EPW)
- 기상 원본 파일명: `KOR_KW_Chuncheon.471010_TMYx.2009-2023.epw`
- WMO 관측소 번호: `471010` (춘천)
- 연간 수평면 전일사량 (GHI): `1490.56 kWh/m²/year`
- 시간자료 보간: 1시간 간격 데이터를 태양 천정각(Zenith) 및 일사 프로파일에 맞추어 15분 간격(35,040스텝)으로 보간 완료.

## 2. 12개 Critical Day 및 Zero Energy 사이징 검증
- 탐색 기준: 365일 전체 탐색 PV = max_d(일 부하 kWh / 1kWp 발전량 kWh).
- 성능 기준: PV 25년 차 계수 0.995^24, ESS 사용 가능 용량 70%.
| 주택 모델 | 난방 패키지 | EV | Critical Day | 일사량 GHI (kWh/m²/day) | 부하 (kWh) | 1kWp 발전 (kWh) | 초기 PV (kW) | 초기 ESS (kWh) | 최종 PV (kW) | 최종 ESS (kWh) | 인버터 필요 (kW) | 부족량 (kWh) | LOL (시간) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MONO Core 54 | PV+ESS+가스보일러 | 0대 | 2026-02-03 (Day 34) | 1.18 | 6.98 | 0.21 | 33.0 | 9.6 | 33.0 | 19.2 | 3.0 | 0.000000 | 0.0 |
| MONO Core 54 | PV+ESS+가스보일러 | 1대 | 2026-02-03 (Day 34) | 1.18 | 13.90 | 0.21 | 65.5 | 19.2 | 69.5 | 19.2 | 7.3 | 0.000000 | 0.0 |
| MONO Core 54 | PV+ESS+AWHP | 0대 | 2026-02-03 (Day 34) | 1.18 | 16.01 | 0.21 | 75.0 | 48.0 | 75.0 | 57.6 | 5.4 | 0.000000 | 0.0 |
| MONO Core 54 | PV+ESS+AWHP | 1대 | 2026-02-03 (Day 34) | 1.18 | 22.93 | 0.21 | 107.5 | 57.6 | 107.5 | 57.6 | 8.9 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+가스보일러 | 0대 | 2026-02-03 (Day 34) | 1.18 | 9.51 | 0.21 | 44.5 | 9.6 | 44.5 | 28.8 | 3.0 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+가스보일러 | 1대 | 2026-02-03 (Day 34) | 1.18 | 16.43 | 0.21 | 77.0 | 28.8 | 77.0 | 28.8 | 7.4 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+AWHP | 0대 | 2026-02-03 (Day 34) | 1.18 | 20.86 | 0.21 | 98.0 | 57.6 | 98.0 | 76.8 | 6.2 | 0.000000 | 0.0 |
| MONO Core 72 | PV+ESS+AWHP | 1대 | 2026-02-03 (Day 34) | 1.18 | 27.79 | 0.21 | 130.5 | 67.2 | 130.5 | 76.8 | 9.3 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+가스보일러 | 0대 | 2026-02-03 (Day 34) | 1.18 | 6.98 | 0.21 | 33.0 | 9.6 | 33.0 | 19.2 | 3.0 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+가스보일러 | 1대 | 2026-02-03 (Day 34) | 1.18 | 13.90 | 0.21 | 65.5 | 19.2 | 69.5 | 19.2 | 7.3 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+AWHP | 0대 | 2026-02-03 (Day 34) | 1.18 | 15.72 | 0.21 | 74.0 | 38.4 | 74.0 | 57.6 | 3.8 | 0.000000 | 0.0 |
| DUO Max 45 | PV+ESS+AWHP | 1대 | 2026-02-03 (Day 34) | 1.18 | 22.65 | 0.21 | 106.0 | 57.6 | 106.0 | 57.6 | 8.8 | 0.000000 | 0.0 |

## 3. 전 케이스 무정전(Zero Loss of Load) 검증
- 전 케이스 연간 부족량 최대값: `0.000000 kWh`
- 전 이용률(100%, 70%, 50%, 30%, 10%, 5%) LOL = 0 여부: `True` (전 시나리오 0.0 시간 충족)
- 기존 최대 부하일 방식 대비 성능:
  * 기존 방식 적용 시 12개 케이스 연간 정전 시간(LOL) 범위: 622.0 ~ 3,419.8 시간/년 발생.
  * 신규 365일 Critical Day 및 정상상태 모듈 탐색 방식 적용 시: 12개 케이스 전수 연간 LOL = 0.0 시간 달성.

## 4. CAPEX 정합성 및 내역 분해 검증
- CAPEX 항목 합계 = 턴키 총액 일치 여부: `True` (오차: 0.00원)
- 지상 추가비(PV 5kW 초과분 500,000원/kW) 적용 건수: `168건` / 432건
- 분전반 개체비(계약전력 증설 시 450,000원) 및 내선공사비(300,000원/kW) 적용 완료.
- 계량기 및 사용전점검비: 0원 적용.

## 5. 수전 피크 및 계약전력 검증
- 전 케이스 최대 수전 kW 분포: 최소값 0.00 kW, 25% 분위 0.00 kW, 중간값 2.15 kW, 75% 분위 7.44 kW, 최대값 9.28 kW.
- 상위 5개 최대 수전 피크 케이스:
  1. 9.28 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  2. 9.28 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  3. 9.28 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  4. 9.28 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `100%`
  5. 9.28 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `1대`, 이용률 `70%`

## 6. PLACEHOLDER 및 UNVERIFIED 항목 전체 목록
### PLACEHOLDER 항목 (5개):
- `subsidy.ess_subsidy.unit_rate_per_kwh`: status=PLACEHOLDER
- `subsidy.ess_subsidy.max_cap`: status=PLACEHOLDER
- `load.ev_charge_start_hour`: status=PLACEHOLDER
- `equipment.awhp_system.nominal_heating_capacity_kw`: status=PLACEHOLDER
- `equipment.awhp_system.max_heating_capacity_kw`: status=PLACEHOLDER

### UNVERIFIED 항목 (15개):
- `houses.MONO Core 72.appliances_desc`: status=UNVERIFIED
- `houses.DUO Max 45.base_pv_capacity_kw`: status=UNVERIFIED
- `tariff.super_user_rate`: status=UNVERIFIED
- `capex.pv_system.turnkey_curve_points`: status=UNVERIFIED
- `capex.pv_system.breakdown_module_per_w`: status=UNVERIFIED
- `capex.ground_mount_pv.excess_cost_per_kw`: status=UNVERIFIED
- `capex.awhp_system.turnkey_installation_cost.low`: status=UNVERIFIED
- `capex.awhp_system.breakdown_buffer_tank`: status=UNVERIFIED
- `capex.replacements.inverter_replacement_min_krw`: status=UNVERIFIED
- `capex.replacements.inverter_replacement_per_kw`: status=UNVERIFIED
- `capex.grid_connection.distribution_board_cost`: status=UNVERIFIED
- `capex.grid_connection.wiring_expansion_cost_per_kw`: status=UNVERIFIED
- `subsidy.awhp_subsidy.sensitivity_rate_70pct`: status=UNVERIFIED
- `load.standby_power`: status=UNVERIFIED
- `equipment.awhp_system.cop_a2_w55`: status=UNVERIFIED
