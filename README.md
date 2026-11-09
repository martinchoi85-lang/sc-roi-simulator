# LG Smart Cottage (SC) PV / ESS / AWHP ROI Engine

LG Smart Cottage의 태양광(PV), 에너지저장장치(ESS), 공기대물 히트펌프(AWHP) 시스템 도입에 따른 25년 현금흐름 및 투자회수기간(ROI)을 산출하는 국가 공통 분석 엔진입니다.

국가 공통 핵심 엔진은 `engine/`에 위치하며, 국가별 고유 파라미터는 `config/` YAML과 `engine/tariffs/` 플러그인으로 분리되어 있습니다. 본 단계에서는 **korea** 파이프라인이 구현되어 있습니다.

---

## 1. 프로젝트 구조

```text
smart-cottage-roi/
├─ run.py                     # 실행 진입점 (python run.py --country korea)
├─ requirements.txt           # Python 의존성 패키지
├─ README.md                  # 프로젝트 안내서
├─ engine/
│  ├─ schema.py               # config 로드·검증, 단위/출처/상태 메타데이터 필수 검사
│  ├─ weather.py              # 15분 단위 365일 TMY 기상 데이터 로더
│  ├─ occupancy.py            # 이용률별 주말·성수기 중심 통계 재실 달력 (최대 부하일 고정)
│  ├─ appliance_load.py       # 대기전력, 냉장고, 가전 플러그 전력 및 내부 발열
│  ├─ thermal_5r1c.py         # ISO 13790 기반 5R1C 동적 건물 열평형 (동파방지 포함)
│  ├─ dhw.py                  # 급탕(DHW) 열부하 산출
│  ├─ ev.py                   # EV 충전 전력 (이용률 연동 및 심야 완속 충전)
│  ├─ heat_pump.py            # AWHP 외기온별 COP 곡선 vs 가스보일러 프로판 비용
│  ├─ pv.py                   # pvlib 기반 경사면 일사 및 1kWp AC 발전량 프로파일
│  ├─ ess.py                  # DoD, 효율, C-rate 반영 배터리 자가소비/오프그리드 디스패치
│  ├─ capex.py                # 항목별 CAPEX 분해 및 보조금, 장기 교체비용(11년/13년)
│  ├─ sizing.py               # zero_energy / zero_bill / near_zero_bill 사이징 알고리즘
│  ├─ cashflow.py             # 25년 단순 현금흐름, PV 감쇄, 교체주기, 손익분기 회수기간
│  ├─ scenarios.py            # 432개 전수 시나리오 파이프라인 러너
│  ├─ report.py               # 결과 요약, 물리 검증서, 차트 및 프로파일 생성기
│  └─ tariffs/
│     ├─ base.py              # 국가 요금제 추상 인터페이스
│     └─ korea.py             # 한전 주택용 누진제, monthly_net / tou_slot_net 상계
├─ tests/                     # pytest 단위 및 통합 테스트 스위트
├─ australia/                 # 폴더 구조 유지
├─ california/                # 폴더 구조 유지
└─ korea/
   ├─ source/                 # 원본 TMY 기상 데이터 CSV (로컬 읽기 전용)
   ├─ config/                 # 모든 파라미터가 {value, unit, source, grade, status} 보유
   │  ├─ country.yaml         # 입지, 시간대, 통화, 시나리오 축
   │  ├─ houses.yaml          # 주택 모델별 외피/지붕 스펙
   │  ├─ tariff.yaml          # 한전 전기요금 및 프로판 단가
   │  ├─ capex.yaml           # 설비별 CAPEX 단가 및 교체 비율
   │  ├─ subsidy.yaml         # 신재생/친환경 보조금
   │  ├─ load.yaml            # 가전 기저부하, EV 충전, 재실 스케줄
   │  └─ equipment.yaml       # PV/ESS/AWHP/보일러 장비 성능 계수
   ├─ assets/                 # 컬러 팔레트 등 입력 자산
   ├─ output/                 # 계산 CSV, 15분 프로파일, 차트, 검증 파일
   └─ report/                 # (향후 보고서용)
```

---

## 2. 설치 및 실행 방법

### 1) 가상환경 및 의존성 설치
```bash
pip install -r requirements.txt
```

### 2) 한국 시나리오 ROI 계산 실행
```bash
python run.py --country korea
```

### 3) 단위 및 정합성 테스트 실행
```bash
python -m pytest tests/
```

---

## 3. 핵심 시뮬레이션 및 사이징 규칙

1. **시뮬레이션 해상도**: 15분 해상도, 365일 (35,040 타임스텝).
2. **시나리오 매트릭스 (총 432개)**:
   - 주택 3종: `MONO Core 54` (2인), `MONO Core 72` (3인), `DUO Max 45` (2인)
   - 패키지 2종: `PV+ESS+가스보일러`, `PV+ESS+AWHP`
   - EV 2종: `0대`, `1대`
   - 이용률 6종: `100%`, `70%`, `50%`, `30%`, `10%`, `5%`
   - 목표 모델 3종: `zero_energy`, `zero_bill`, `near_zero_bill`
   - 보조금 2종: `있음(True)`, `없음(False)`
3. **목표 모델별 사이징 알고리즘**:
   - `zero_energy`: 계통 미연계(오프그리드). 100% 이용률 부하 기준 설계일 일일 발전량 = 당일 전체 부하. TMY 당일 및 월평균 2종 각각 회수기간 산출. ESS는 일일 최대 누적 부족량(DoD, 왕복효율 반영)으로 산출. 이용률별 실제 부하 기준 전력 부족 시간(loss of load hours) 출력.
   - `zero_bill`: 한전 기본요금을 제외한 변동요금이 0이 되는 최소 PV 탐색. ESS는 최소 상용 모듈(5 kWh) 고정.
   - `near_zero_bill`: PV 0.5kW 단위 탐색, ESS 최소 모듈 고정. 회수기간 3년 이내에서 잔여 변동요금이 최소인 조합 선택. (해가 없으면 `no_solution`, 최단 회수기간, 3년 달성에 필요한 CAPEX 출력).
   - 지붕 상한은 제거(부지 내 지상 설치 공간 충분 가정)하고 지상 설치비는 PLACEHOLDER로 유지.
4. **25년 현금흐름**:
   - 할인율 0% (단순 회수기간).
   - PV 연간 감쇄율 0.5%/년.
   - ESS: 10년 차 용량 70%까지 선형 감소, 11년 차 1회 교체.
   - 인버터: 13년 차 1회 교체.
   - 25년 내 미회수 시 `">25"` 표기.
5. **데이터 메타데이터 및 PLACEHOLDER 규칙**:
   - 모든 config 입력값은 `value`, `unit`, `source`, `grade`, `status` 필드를 보유.
   - 미확보 값은 `status: PLACEHOLDER`로 명시되며 결과 테이블 및 요약서에 추적 현황이 출력됨.

