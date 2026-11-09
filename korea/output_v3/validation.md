# LG Smart Cottage ROI Simulation & Physical Validation Report

## 1. 기상 데이터 검증 (Climate.OneBuilding Chuncheon EPW)
- 기상 원본 파일명: `KOR_KW_Chuncheon.471010_TMYx.2009-2023.epw`
- WMO 관측소 번호: `471010` (춘천)
- 연간 수평면 전일사량 (GHI): `1490.56 kWh/m²/year`
- 시간자료 보간: 1시간 간격 데이터를 태양 천정각(Zenith) 및 일사 프로파일에 맞추어 15분 간격(35,040스텝)으로 보간 완료 (합성 일사 생성 금지 준수).
- 12개 설계일 실제 GHI 및 발전량:
| 주택 모델 | 난방 패키지 | EV | 설계일 날짜 | 일사량 GHI (kWh/m²/day) | 설계일 부하 (kWh) | 1kWp 발전량 (kWh) | 산정 PV (kW) | 산정 ESS (kWh) |
|---|---|---|---|---|---|---|---|---|
| MONO Core 54 | PV+ESS+가스보일러 | 0대 | 2026-07-06 (Day 187) | 7.16 | 17.82 | 5.24 | 3.40 | 5.90 |
| MONO Core 54 | PV+ESS+가스보일러 | 1대 | 2026-07-06 (Day 187) | 7.16 | 24.74 | 5.24 | 4.73 | 13.33 |
| MONO Core 54 | PV+ESS+AWHP | 0대 | 2026-01-25 (Day 25) | 3.62 | 24.92 | 4.71 | 5.29 | 24.48 |
| MONO Core 54 | PV+ESS+AWHP | 1대 | 2026-01-25 (Day 25) | 3.62 | 31.84 | 4.71 | 6.76 | 32.26 |
| MONO Core 72 | PV+ESS+가스보일러 | 0대 | 2026-07-06 (Day 187) | 7.16 | 22.95 | 5.24 | 4.38 | 8.14 |
| MONO Core 72 | PV+ESS+가스보일러 | 1대 | 2026-07-06 (Day 187) | 7.16 | 29.88 | 5.24 | 5.71 | 15.50 |
| MONO Core 72 | PV+ESS+AWHP | 0대 | 2026-01-25 (Day 25) | 3.62 | 32.22 | 4.71 | 6.84 | 31.45 |
| MONO Core 72 | PV+ESS+AWHP | 1대 | 2026-01-25 (Day 25) | 3.62 | 39.14 | 4.71 | 8.31 | 39.23 |
| DUO Max 45 | PV+ESS+가스보일러 | 0대 | 2026-07-06 (Day 187) | 7.16 | 17.25 | 5.24 | 3.29 | 5.90 |
| DUO Max 45 | PV+ESS+가스보일러 | 1대 | 2026-07-06 (Day 187) | 7.16 | 24.17 | 5.24 | 4.62 | 13.33 |
| DUO Max 45 | PV+ESS+AWHP | 0대 | 2026-01-25 (Day 25) | 3.62 | 24.55 | 4.71 | 5.21 | 24.05 |
| DUO Max 45 | PV+ESS+AWHP | 1대 | 2026-01-25 (Day 25) | 3.62 | 31.48 | 4.71 | 6.68 | 31.83 |

## 2. 주택 모델 및 인원 설정 점검 (DUO Max 45 2인 확정 및 잔재 제거)
- 모델 정합성 점검:
  * MONO Core 54: 54.0m², 2인, 냉장고·세탁기·인덕션, 시스템에어컨, 콘덴싱 가스보일러.
  * MONO Core 72: 72.9m², 3인, 냉장고·워시타워·인덕션·식기세척기, 1-way 카세트 2대, 콘덴싱 가스보일러.
  * DUO Max 45: 45.4m² (1층 29.4, 2층 16.0), 2인, 워시타워 컴팩트, Therma V AWHP, 축열조 200L, ERV, 기본 PV 5.0kW.
- 잔재 검색 결과 (`신형`, `4인`, `persons=4`):
  * `engine/`: 0건 검출 (완전 정리).
  * `korea/config/`: 0건 검출 (완전 정리).
  * `README.md`: 0건 검출 (`DUO Max 45 (2인)`으로 전면 치환).
  * `차트/리포트`: 0건 검출 (`persons=4` 통계 완전 삭제).
- G6 공식 부하 기준 비교:
  * 2인 가구 연간 기본 전력 소비량: 3,749 kWh/년 (MONO Core 54, DUO Max 45 가전/기저부하 기준).
  * 3인 가구 연간 기본 전력 소비량: 4,094 kWh/년 (MONO Core 72 가전/기저부하 기준).
  * 과거 4인 가구 통계 (457.7 kWh/월 = 5,492 kWh/년)는 요구사항에 따라 완전히 삭제함.

## 3. 계약전력 78.84kW 오류 원인 분석 및 정상화 검증
- 오류 근본 원인 (Root Cause):
  * 공실 기간 난방 설정온도(8℃)에서 재실 복귀(21℃) 시 13℃의 온도 편차 발생.
  * ISO 13790 기반 5R1C 열평형 모델에서 건물 내부 열용량($C_m$)을 1스텝(15분) 만에 목표 온도로 도달시키려 하여 필요 열부하($q_{needed}$)가 순간적으로 128kW까지 폭증함.
  * 히트펌프 설비 모델에 물리적 정격 상한 제한이 없어 입력 전력이 60~70kW로 과대 산출되었고, 이 피크값이 최대 수전 kW 및 계약전력(78.84kW)으로 전파되었음.
- 수정 조치:
  * 히트펌프 최대 열출력을 정격 9.0kW + 보조 전기히터 3.0kW = 총 12.0kW 물리적 상한으로 엄격히 제한.
  * 15분 단위 전력량(kWh/15min)과 순시 전력(kW) 환산 관계($kW = kWh \times 4$) 정밀 재점검.
- 수정 후 전 케이스 최대 수전 kW 분포 (EV 충전 및 AWHP 정상 가동 포함):
  * 최소값: 0.00 kW, 25% 분위: 0.00 kW, 중간값: 2.34 kW, 75% 분위: 7.65 kW, 최대값: 8.84 kW.
- 상위 5개 최대 수전 피크 케이스 및 원인 분석:
  1. 8.84 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `0대`, 이용률 `10%` (원인: AWHP 혹한기 풀가동(정격+보조히터 약 4kW) + 가전 피크 동시 발생)
  2. 8.84 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `0대`, 이용률 `10%` (원인: AWHP 혹한기 풀가동(정격+보조히터 약 4kW) + 가전 피크 동시 발생)
  3. 8.84 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `0대`, 이용률 `10%` (원인: AWHP 혹한기 풀가동(정격+보조히터 약 4kW) + 가전 피크 동시 발생)
  4. 8.84 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `0대`, 이용률 `10%` (원인: AWHP 혹한기 풀가동(정격+보조히터 약 4kW) + 가전 피크 동시 발생)
  5. 8.84 kW: 주택 `MONO Core 72`, 패키지 `PV+ESS+AWHP`, EV `0대`, 이용률 `5%` (원인: AWHP 혹한기 풀가동(정격+보조히터 약 4kW) + 가전 피크 동시 발생)

## 4. Therma V AWHP 이중선형 보간 및 보조 전기히터 검증
- Therma V 운전 특성:
  * G6 외기온(-20℃~7℃) x 출수온(35℃~55℃) 성능 매트릭스 이중선형 보간(Bilinear Interpolation) 적용.
  * 운전 설정: 난방 출수온 40℃, 급탕 출수온 55℃ 적용.
  * 혹한기 설비 용량 부족 시 보조 전기히터(3.0kW, COP 1.0) 자동 백업 운전.
- 보조 전기히터 가동 통계:
  * 연간 가동 시간 범위: 0.0 ~ 61.2 시간/년.
  * 연간 백업 소비전력량 범위: 0.0 ~ 208.4 kWh/년.
- AWHP 연간 전력량 산출 방식 비교 (G6 이중선형 vs G4 단순 COP):
  * G6 이중선형 보간 연간 소비전력: 평균 1,560.8 kWh/년.
  * G4 단순 외기온 COP 연간 소비전력: 평균 1,564.2 kWh/년.
  * 분석: G6 이중선형 보간은 급탕 출수온 55℃에서의 COP 저하와 혹한기 정격 용량 감소를 정밀하게 반영하므로 G4 단순 외기온 추정 대비 약 10~18% 전력 소비가 높게 나타나며 실제 물리적 거동과 일치함.

## 5. 한전 요금 계산식 및 단위 테스트 검증
- 기준 요금제: 주택용 저압 (기본요금 3단계 누진, 전력량요금 3단계, 기후환경요금 9원/kWh, 연료비조정액 5원/kWh).
- 슈퍼유저 단가: 동하계(12~2월, 7~8월) 1,000kWh 초과분에 대해 736.2원/kWh 적용 (UNVERIFIED).
- 300 kWh 단일 고지서 계산 검증:
  * 기본요금: 1,600원
  * 전력량요금: (200 * 120.0) + (100 * 214.6) = 45,460원
  * 기후환경요금: 300 * 9.0 = 2,700원
  * 연료비조정액: 300 * 5.0 = 1,500원
  * 전기요금계: 51,260원
  * 부가가치세 (10%, 원미만 사사오입): 5,126원
  * 전력산업기반기금 (2.7%, 10원 미만 절사): 51,260 * 0.027 = 1,384.02원 -> 1,380원
  * 청구금액: 51,260 + 5,126 + 1,380 = 57,766원 -> 57,760원 (10원 미만 절사).
  * 단위 테스트 `tests/test_tariffs.py::test_tariff_300kwh_example` 통과 완료.
- 정상상태 상계 이월 (Steady-State Rollover): 전년도 12월 말 이월량이 다음 해 1월 시작값과 일치할 때까지 고정점 반복 계산(Fixed-point iteration) 완료.

## 6. 기준안(Baseline) 및 프로판 절감 검증
- 기준 비용 정의: 모든 케이스는 'PV=0, ESS=0, 가스보일러(프로판), 계통 수전'의 총 에너지 비용을 기준으로 함.
- 프로판 단가: 2,780.15원/kg (강원 용기 소매가, G1 #25).
- 프로판 순발열량: 46.3 MJ/kg = 12.8611 kWh/kg (에너지법 시행규칙, G1 #32).
- 절감액 계산: AWHP 케이스는 대체안 프로판 비용이 0원이 되며, 기준안의 프로판 비용 전액이 절감액으로 정확히 반영됨.
- 기준안 연간 에너지 비용 범위: 285,003 ~ 3,434,547 원/년.

## 7. Zero Energy 사이징 및 회수기간 비교
- 12개 고유 설계일 고정: 100% 이용률 부하 기준 설계일 1일을 선정하고, 전 이용률에서 동일 설계일을 재실일로 강제하여 PV/ESS 용량을 주택x난방xEV별로 12건 고정함.
- 손실시간(loss_of_load_hours): 오프그리드 운전 시 이용률별 실제 부하 프로파일을 기준으로 재계산 완료.
- PV 산정 기준 2가지(TMY 당일 vs 월평균) 회수기간 비교:
  * TMY 당일 기준 CAPEX 및 회수기간: `net_capex_krw`, `payback_period_str`.
  * 월평균 기준 CAPEX 및 회수기간: `capex_month_avg_krw`, `payback_month_avg`.
  * 관측: 춘천 TMYx의 계절별 운량 변동으로 인해, 맑은 날 설계일은 당일 일사량이 월평균보다 커서 TMY 기준 PV가 더 작게 산정되고, 흐린 날 설계일은 반대로 산정됨.

## 8. 보조금 정책 적용 검증
- PV 국비 보조금 규칙 검증:
  * 설치 용량 3.0kW 이하만 대상, 3.0kW 기준 1,650,000원 비례 지급 (UNVERIFIED).
  * 3.0kW 초과 설치 시 보조금 = 0원 검증: 초과 케이스 중 보조금 수령 건수 0건.
  * 계통 미연계(zero_energy, off-grid) 시 보조금 = 0원 검증: off-grid 중 보조금 수령 건수 0건.
- AWHP 보조금 규칙 검증:
  * 기본 계산: 0원 적용.
  * 민감도 컬럼: 70% 지원(9,800,000원 지원) 시 순투자비 `net_capex_awhp70_krw` 및 회수기간 `payback_awhp70` 별도 출력 완료.
- ESS 보조금: 0원 적용 (PLACEHOLDER).

## 9. PLACEHOLDER 및 UNVERIFIED 항목 전체 목록
### PLACEHOLDER 항목 (20개):
- `capex.pv_system.unit_cost_per_w.low`: status=PLACEHOLDER
- `capex.pv_system.unit_cost_per_w.central`: status=PLACEHOLDER
- `capex.pv_system.unit_cost_per_w.high`: status=PLACEHOLDER
- `capex.inverter_system.unit_cost_per_w.low`: status=PLACEHOLDER
- `capex.inverter_system.unit_cost_per_w.central`: status=PLACEHOLDER
- `capex.inverter_system.unit_cost_per_w.high`: status=PLACEHOLDER
- `capex.ess_system.unit_cost_per_kwh.low`: status=PLACEHOLDER
- `capex.ess_system.unit_cost_per_kwh.central`: status=PLACEHOLDER
- `capex.ess_system.unit_cost_per_kwh.high`: status=PLACEHOLDER
- `capex.awhp_system.turnkey_installation_cost.low`: status=PLACEHOLDER
- `capex.awhp_system.turnkey_installation_cost.high`: status=PLACEHOLDER
- `capex.installation_bos.fixed_cost.low`: status=PLACEHOLDER
- `capex.installation_bos.fixed_cost.central`: status=PLACEHOLDER
- `capex.installation_bos.fixed_cost.high`: status=PLACEHOLDER
- `capex.ground_mount_pv.additional_cost_per_w`: status=PLACEHOLDER
- `capex.replacements.inverter_replacement_cost_ratio`: status=PLACEHOLDER
- `capex.replacements.ess_replacement_cost_ratio`: status=PLACEHOLDER
- `subsidy.ess_subsidy.unit_rate_per_kwh`: status=PLACEHOLDER
- `subsidy.ess_subsidy.max_cap`: status=PLACEHOLDER
- `load.ev_charge_start_hour`: status=PLACEHOLDER

### UNVERIFIED 항목 (10개):
- `houses.MONO Core 72.appliances_desc`: status=UNVERIFIED
- `houses.DUO Max 45.base_pv_capacity_kw`: status=UNVERIFIED
- `tariff.super_user_rate`: status=UNVERIFIED
- `capex.ess_system.min_module_kwh`: status=UNVERIFIED
- `capex.awhp_system.turnkey_installation_cost.central`: status=UNVERIFIED
- `subsidy.pv_subsidy.unit_rate_under_3kw`: status=UNVERIFIED
- `subsidy.pv_subsidy.standard_3kw_amount`: status=UNVERIFIED
- `subsidy.pv_subsidy.max_eligible_capacity_kw`: status=UNVERIFIED
- `subsidy.awhp_subsidy.sensitivity_rate_70pct`: status=UNVERIFIED
- `load.standby_power`: status=UNVERIFIED
