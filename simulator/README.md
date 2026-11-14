# SC ROI 시뮬레이터

상사가 직접 조건을 바꿔 가며 ROI를 확인하는 화면. 한국 v10 엔진(`engine/`)을 그대로 재사용한다.

## 구조
- `precompute/precompute.py` — 1단계 사전계산. v10 Step1(KOSIS 재실·가전) + Step2(5R1C, 가스보일러/AWHP, 급탕)를 조합별로 호출해 1년 시간별 용도별 에너지를 `data/<region>/c_<모델>_<인원>_<이용률>.js`로 저장(45조합, 조합당 약 6초). `--max N`으로 나눠 실행 가능(이미 있는 조합은 건너뜀).
- `precompute/prepare_weather.py` — EPW/zip → 15분 기상 CSV.
- `web/engine.js` — 2·3단계 계산(PV·ESS 디스패치, 열화·교체, HEMS, 누진/TOU, 상계/FIT/TOU 매전, 20년 현금흐름). 브라우저·Node 공용.
- `web/index.html, app.js, style.css, defaults.js` — 화면. `defaults.js`에 기본값·단가·요금 프리셋.
- `tests/` — `run_js.js`(JS 실행) ↔ `reference.py`(독립 Python 기준 구현) 교차검증, `bill_js.js`(누진 요금 대조).
- `build.py` — `dist/SC_ROI_Simulator/` 배포본과 zip 생성. index.html 더블클릭으로 오프라인 실행.

## 검증 (2026-11-14)
- 1단계: v10과 겹치는 28조합 전부 기준안 전력·프로판·AWHP 전력 0.1% 이내 일치.
- 누진 요금: `engine/tariffs/korea.py`와 51,900개 경우 원 단위 일치(300kWh = 57,760원).
- 2·3단계: JS ↔ Python 기준 구현, 4개 시나리오 × 20년 최대 차이 5e-7원.

## 지역 추가 절차 (예: 한국 남부 광주)
1. EPW zip을 `korea/source/`에 넣고 `python -m simulator.precompute.prepare_weather <zip> korea/source/tmy_gwangju_471560_15min.csv`
2. `python -m simulator.precompute.precompute --region kr_south --jobs 2`
3. `python simulator/build.py` → regions.js에 자동 등록

## 테스트
```
node simulator/tests/run_js.js > /tmp/js.json && python simulator/tests/reference.py /tmp/js.json
```
