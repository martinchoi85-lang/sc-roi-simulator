# SC ROI 시뮬레이터

조건을 바꿔 가며 ROI를 바로 확인하는 화면. 한국 v10 엔진(`engine/`)을 재사용한다.
지역별 원자료·가공 방법·요금은 [`docs/지역별_데이터_노트.md`](docs/지역별_데이터_노트.md) 참고.

## 구조
- `precompute/precompute.py` — 1단계 사전계산. 조합(모델 3 × 거주자 1~3 × 이용률 5)별 1년 시간별 용도별 에너지를 `data/<region>/c_<모델>_<인원>_<이용률>.js`로 저장(지역당 45조합, 조합당 약 6~7초). `--max N`으로 나눠 실행(이미 있는 조합은 건너뜀), `--index-only`로 index.json만 재생성.
  - 지역: `kr_central`, `kr_south`, `us_la`, `au_mel` (REGIONS 사전).
  - 열모델 v2(`engine/passive_climate.py`)를 기본 사용(`USE_PASSIVE = True`).
- `precompute/prepare_weather.py` — EPW/zip → 15분 기상 CSV (시간대 인자).
- `precompute/atus_to_kosis.py` — 미국 ATUS 원자료 → KOSIS 형식 표 + country_params.json.
- `precompute/au_from_abs.py` — 캘리포니아 표 모양 + ABS TUS 2024 총량 → 호주 표.
- `web/engine.js` — 2·3단계 계산(PV·ESS 디스패치, 열화·교체, HEMS, 누진·구간·단일·TOU(N구간·하루 한도) 요금, 상계·FIT·TOU·매전 없음, 통화 환산, 20년 현금흐름, 자립률·Zero Energy·Zero Bill 판정, Zero Energy 최소 ESS 탐색 `minEssForZero`). 브라우저·Node 공용.
  - 에너지 자립률(대표) = 1 − 계통 수전 ÷ 사용, 연간 발전 상쇄율 = PV 발전 ÷ 사용. ESS 시작 SOC = 1년 차 조건으로 한 해를 미리 돌린 연말 SOC.
- `web/index.html, app.js, style.css, defaults.js` — 화면. `defaults.js`에 기본값·단가·요금 프리셋.
- `build.py` — `dist/SC_ROI_Simulator/` 배포본과 zip. index.html 더블클릭으로 오프라인 실행.

## 테스트
```
# 2·3단계: JS 엔진 ↔ 독립 Python 기준 구현 (한국 5 + LA 4 + 멜버른 4 시나리오 × 최대 20년, KPI·Zero 판정 포함)
node simulator/tests/run_js.js > /tmp/js.json && python simulator/tests/reference.py /tmp/js.json

# v10 회귀: 엔진 옵션을 끈 상태에서 v10 기준값(tests/v10_regression.json, 35조합) 재현
python simulator/tests/test_v10_regression.py 5

# 한전 누진 요금 대조
node simulator/tests/bill_js.js > /tmp/bill.json   # 이후 engine/tariffs/korea.py와 비교
```
v10 결과 캐시(`korea/cache`)와 리포트 산출물은 2026-11-14에 삭제했다. 회귀 기준값은 `tests/v10_regression.json`에 남겨 두었다.

## 지역 추가 절차
1. EPW zip을 `<country>/source/`에 넣고 `python -m simulator.precompute.prepare_weather <zip> <csv> <tz>`
2. 생활시간 표가 KOSIS 형식이 아니면 변환(`atus_to_kosis.py` 참고) → `<country>/source/tus_kosis/` + `country_params.json`
3. `precompute.py` REGIONS에 항목 추가(위경도, tz, kosis_dir, holidays, cooling_months)
4. `python -m simulator.precompute.precompute --region <id> --jobs 2`
5. `web/defaults.js`에 지역·요금 프리셋 추가 → `python simulator/build.py`
6. `docs/지역별_데이터_노트.md` 갱신

## 검증 기록
- 1단계: v10과 겹치는 28조합 전부 0.1% 이내(열모델 v2 적용 전), 엔진 옵션을 끄면 v10과 차이 0.
- 누진 요금: `engine/tariffs/korea.py`와 51,900건 원 단위 일치(300kWh = 57,760원).
- 2·3단계: JS ↔ Python 13개 시나리오(매전 없음, 4구간 TOU·하루 한도, SCE PRIME 포함) × 최대 20년 최대 차이 약 6e-7원. 자립률·수전일 수·Zero Bill 변동요금도 대조(2026-11-17).
- 미국 생활 패턴: 주말 '집 밖' 비율 ATUS 장소 기록과 MAE 3~4%p.
