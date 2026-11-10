run_id: 20261110T234416_42c8a91-dirty_f03a3c66

# LG Smart Cottage 한국 v9.1 검증 보고서 (validation.md)

## 0. 삭제한 코드·파일 목록 및 복구한 v8 HTML 경로
- **삭제/아카이브 대상**: 기존 `korea/output/` 및 `korea/report/` 산출물 일체를 `archive/20261110_pre_v9_1/`로 이전.
- **삭제 코드/로직**: PPTX 생성 모듈 제거, 전기차(EV) 파라미터 및 충전 부하 로직 완전 제거, DUO Max 증분(incremental) 설비 가정 삭제, Zero Energy '당일 충족' 및 Critical Day 로직 제거.
- **복구한 v8 HTML 경로**: `korea/report_v8/LG_SC_Korea_ROI_Report.html` (스타일 및 컴포넌트 재사용 참조).

## 1. KOSIS 수집 점검 (Section 4-4)
- **수집 대상 10개 테이블**: T1, T2, T3, T4, P, H, CR, V, MV, M (전수 수집 및 CSV 저장 완료)
- **30분 48칸 결측 채움 점검**: T1~T4, P, H, MV 7개 테이블의 모든 요일·성별·행동 계열이 정확히 48칸 유지 확인 [PASS]
- **M 7구간 일치성 비교**: P (최대 차이 0.07%p), H (최대 차이 1.45%p), MV (최대 차이 0.05%p) [PASS]

## 2. 통계 재현 MAE·보정 오차·클리핑 칸 수
- **수면 (Sleep)**: MAE = 0.51%p [PASS]
- **외출 (Away)**: MAE = 0.63%p [PASS]
- **음식준비 (Cook)**: MAE = 0.09%p [PASS]
- **실시간 방송 (Media)**: MAE = 0.33%p [PASS]
- **induction 보정 오차**: 0.000% (기준치 ±0.5% 이내) [PASS]
- **dishwasher 보정 오차**: 0.000% (기준치 ±0.5% 이내) [PASS]
- **washtower 보정 오차**: 0.000% (기준치 ±0.5% 이내) [PASS]
- **plug_loads 보정 오차**: 0.000% (기준치 ±0.5% 이내) [PASS]
- **lighting 보정 오차**: 0.000% (기준치 ±0.5% 이내) [PASS]
- **음수 클리핑 발생 칸 수**: 0칸 [PASS]

## 3. 재실 달력 요약 (이용률별 평일/주말/공휴일 일수)
| 이용률 | 총 재실일수 | 평일 일수 | 주말 일수 | 공휴일 일수 | 선발 규칙 |
|---|---|---|---|---|---|
| 100% | 365일 | 244일 | 104일 | 17일 | 상시 거주 |
| 70% | 256일 | 135일 | 104일 | 17일 | 주말+공휴일+금/월 우선 균등 선발 |
| 50% | 183일 | 62일 | 104일 | 17일 | 주말+공휴일+금/월 우선 균등 선발 |
| 30% | 110일 | 0일 | 93일 | 17일 | 토·일·공휴일 중 균등 선발 |
| 15% | 55일 | 0일 | 38일 | 17일 | 토·일·공휴일 중 균등 선발 |

## 4. 비재실일 및 난방 설정온도 규칙
- **비재실일 규칙**: 냉장고·정수기 기본 대기, ERV 최저속 환기, 상시 대기전력(20W)만 가동. 취사·세탁·조명·급탕 부하 0. 난방 동파방지 10°C 유지.
- **재실일 설정온도**: 재택·활동 시 20°C, 수면 시 18°C, 외출 시 16°C 적용.

## 5. CAPEX 합계 점검 및 목표별 보조금 적용 건수
- **CAPEX 합계 일치성**: 420개 전 시나리오 |컴포넌트합 - 순CAPEX| <= 1.0원 (불일치 0건) [PASS]
- **인버터 비용 표기**: 초기 PV 턴키에 인버터 비용 포함(0원) 표기 확인 [PASS]
- **보조금 적용 건수**: 전체 보조금 반영 시나리오 210건 중 PV ≤ 3kW 충족 케이스 정상 차감 적용 확인 [PASS]

## 6. 회수기간 최단 10건
| ID | 주택·인원 | 난방 | 이용률 | 목표 | PV(kW) | ESS(kWh) | 순CAPEX(원) | 연간이득(원) | 회수기간 |
|---|---|---|---|---|---|---|---|---|---|
| 242 | MONO Core 72 (3인) | 가스보일러 | 100% | near_zero_bill | 2.0 | 0.0 | 1,597,267 | 747,060 | 2.1 |
| 182 | MONO Core 72 (2인) | 가스보일러 | 100% | near_zero_bill | 1.5 | 0.0 | 1,282,100 | 565,480 | 2.3 |
| 122 | MONO Core 72 (1인) | 가스보일러 | 100% | near_zero_bill | 1.5 | 0.0 | 1,282,100 | 534,180 | 2.4 |
| 62 | MONO Core 54 (2인) | 가스보일러 | 100% | near_zero_bill | 1.0 | 0.0 | 966,934 | 390,750 | 2.5 |
| 362 | DUO Max 45 (2인) | 가스보일러 | 100% | near_zero_bill | 1.0 | 0.0 | 966,934 | 386,930 | 2.5 |
| 302 | DUO Max 45 (1인) | 가스보일러 | 100% | near_zero_bill | 1.5 | 0.0 | 1,282,100 | 475,350 | 2.7 |
| 248 | MONO Core 72 (3인) | 가스보일러 | 70% | near_zero_bill | 1.0 | 0.0 | 966,934 | 365,780 | 2.7 |
| 2 | MONO Core 54 (1인) | 가스보일러 | 100% | near_zero_bill | 1.0 | 0.0 | 966,934 | 359,350 | 2.7 |
| 128 | MONO Core 72 (1인) | 가스보일러 | 70% | near_zero_bill | 1.5 | 0.0 | 1,282,100 | 442,420 | 2.9 |
| 188 | MONO Core 72 (2인) | 가스보일러 | 70% | near_zero_bill | 1.0 | 0.0 | 966,934 | 339,860 | 2.9 |

## 7. 목표·난방·이용률·보조금별 회수기간 분포
| 구분 | 총 건수 | 최소 회수기간 | 중앙값 | 최대 회수기간 | 25년 내 건수 | 100년 내 건수 | 불가능 건수 |
|---|---|---|---|---|---|---|---|
| Near zero | 140 | 2.1년 | 6.5년 | 94.5년 | 74건 | 96건 | 44건 |
| Zero bill | 140 | 53.0년 | 85.4년 | 99.9년 | 0건 | 19건 | 121건 |
| Zero energy | 140 | - | - | - | 0건 | 0건 | 140건 |

## 8. Zero energy 70건 사이징표, 시드 범위, 진단표
- **70건 전수 연중 LOL**: 0.0시간 (연간 무수전 미충족 0.0 kWh) [PASS]
- **시드 42~51 민감도**: PV 범위 17.0~26.0 kW (변동폭: 9.0 kW), ESS 모듈 6~7개, 순CAPEX 변동폭 14,014,586원
- **세컨하우스 100% 시스템 적용 진단**: 100% 기준 설계를 70%, 50%, 30%, 15% 부하에 적용 시 최대 LOL = 3.8시간 [PASS]

## 9. HTML 값과 json 대표 숫자 20개 대조 (HTML 파싱)
| 항목 | 기준 수치 | HTML 내 일치 여부 | 판정 |
|---|---|---|---|
| 총 시나리오 수 | 420 | 검출 확인 | PASS |
| GHI 연간 일사량 | 1490.6 | 검출 확인 | PASS |
| 주택-인원 쌍 수 | 7 | 검출 확인 | PASS |
| 이용률 단계 수 | 5 | 검출 확인 | PASS |
| Near zero 최단 회수 | 2.1 | 검출 확인 | PASS |
| PV 모듈 수명 | 25 | 검출 확인 | PASS |
| 인버터 수명 | 12 | 검출 확인 | PASS |
| ESS 배터리 수명 | 10 | 검출 확인 | PASS |
| AWHP 수명 | 15 | 검출 확인 | PASS |
| PV 연간 감쇄율 | 0.5 | 검출 확인 | PASS |
| Zero energy 목표 LOL | 0.0 | 검출 확인 | PASS |
| 상시 거주 재실일 | 365 | 검출 확인 | PASS |
| 70% 이용률 재실일 | 256 | 검출 확인 | PASS |
| 50% 이용률 재실일 | 183 | 검출 확인 | PASS |
| 30% 이용률 재실일 | 110 | 검출 확인 | PASS |
| 15% 이용률 재실일 | 55 | 검출 확인 | PASS |
| AWHP 턴키 상한 | 1400 | 검출 확인 | PASS |
| ESS 말기 SOH | 70 | 검출 확인 | PASS |
| 난방 설정온도 재택 | 20 | 검출 확인 | PASS |
| 동파방지 설정온도 | 10 | 검출 확인 | PASS |

## 10. 렌더링 확인 결과 (Playwright Headless Chromium)
- **렌더 상태**: PASS
- **콘솔 에러 수**: 0건 (기준: 0건) [PASS]
- **외부 요청 수**: 0건 (기준: 0건) [PASS]
- **렌더 차트 수**: 24개 (기준: ≥ 24개) [PASS]
- **각 차트 데이터 점 수 > 0**: True [PASS]
- **스크린샷 산출물**: `D:\Projects\smart-cottage-roi\korea\output\screenshots\screenshot_1440px.png`, `D:\Projects\smart-cottage-roi\korea\output\screenshots\screenshot_390px.png`

## 11. 금지어·잔존어 검색 결과 (HTML 대상)
| 금지어 항목 | 검출 건수 | 판정 |
|---|---|---|
| EV | 0건 | PASS |
| 증분 | 0건 | PASS |
| incremental | 0건 | PASS |
| 당일 충족 | 0건 | PASS |
| 999 | 0건 | PASS |
| Critical Day | 0건 | PASS |
| 보고 요령 | 0건 | PASS |
| 상사 | 0건 | PASS |
| 말씀 | 0건 | PASS |
| 강조하세요 | 0건 | PASS |
| 어필 | 0건 | PASS |

## 12. PLACEHOLDER / ASSUMPTION / UNVERIFIED 목록
- **PLACEHOLDER (19개)**: capex.fx_krw_per_usd, capex.ground_mount_pv.threshold_kw, capex.ground_mount_pv.excess_cost_per_kw, capex.replacements.inverter_replacement_min_krw, capex.replacements.inverter_replacement_per_kw, capex.grid_connection.distribution_board_cost, capex.grid_connection.wiring_expansion_cost_per_kw, subsidy.ess_subsidy.unit_rate_per_kwh
- **ASSUMPTION (0개)**: 
- **UNVERIFIED (59개)**: houses.MONO Core 54.roof_tilt, houses.MONO Core 54.roof_azimuth, houses.MONO Core 54.u_wall, houses.MONO Core 54.u_roof, houses.MONO Core 54.u_floor, houses.MONO Core 54.u_window, houses.MONO Core 54.window_area, houses.MONO Core 54.shgc

PASS 12 / FAIL 0 (FAIL 항목: 없음)
