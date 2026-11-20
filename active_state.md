# active_state — PC 간 작업 상태 (마지막 갱신: 2026-11-20, mini PC)

이 저장소는 메인 PC(martin85pc, `D:\Projects\smart-cottage-roi-simulator`)와 mini PC(desktop-3kg17jf, `C:\Users\MartinChoi\Documents\WorkSpace\sc_roi`)에서 번갈아 작업한다.
**다른 PC에서 작업을 시작하기 전에 이 파일부터 읽는다.** pull/merge 전에 `git fetch` 후 `git show origin/simulator:active_state.md`로 최신 내용을 확인한다.

## ⚠ 메인 PC에서 먼저 확인할 것 (충돌 가능성)

mini PC에서 2026-11-20에 아래 기능을 구현해 push했다(기준 커밋 0857516 = 수정 3).

| 커밋 | 내용 | 바뀐 파일 |
|---|---|---|
| a597dae | HEMS TOU 부하 이동, N년 차 월별 차트(표시 연도 슬라이더), 자가소비율 KPI | `simulator/web/engine.js`, `app.js`, `index.html`, `style.css`, `defaults.js`, `simulator/tests/reference.py`, `cases.json`, `simulator/data/regions.js`, `simulator/dist/SC_ROI_Simulator/*` |
| (이 파일과 같은 커밋) | 입력 패널 고정(좌측만 따로 스크롤), '1년 데이터' 탭 HEMS 조작부·'HEMS 변화' 히트맵 | 위 web 파일, dist, 이 파일 |

메인 PC에서 같은 기능(N년 차 월별 차트, HEMS 부하 이동)을 **따로 구현했을 수도 있다**. 그렇다면 같은 파일을 서로 다르게 고쳤으므로 병합 충돌이 난다.

### 확인 순서 (메인 PC)
1. `git status` — 커밋 안 한 변경이 있으면 먼저 정리(커밋 또는 `git stash`).
2. `git fetch origin`
3. `git log --oneline origin/simulator..simulator` — 메인 PC에만 있는 커밋 목록.
   - **비어 있으면**: 메인 PC에 새 작업 없음 → `git pull --ff-only origin simulator`로 끝.
   - **있으면**: 각 커밋이 무엇인지 확인. `git diff --stat 0857516 simulator`로 바뀐 파일을 본다.
4. 메인 PC 커밋이 **수정 4(precompute·`engine/*.py`·`simulator/data/**`)만** 건드렸다면: `git merge origin/simulator`. 충돌은 `simulator/dist/SC_ROI_Simulator/*`와 `simulator/data/regions.js`에서만 날 수 있음 → 아무 쪽이나 고른 뒤 `python simulator/build.py`로 다시 만들면 해결(아래 줄바꿈 주의).
5. 메인 PC 커밋이 **`simulator/web/*` (특히 engine.js·app.js)를 건드렸다면**: 같은 기능을 두 번 구현했을 가능성이 크다. **병합하지 말고 멈춰서 Claude에게 두 구현을 비교시킨다**(`git diff 0857516 simulator -- simulator/web` 와 `git diff 0857516 origin/simulator -- simulator/web`). 어느 쪽을 남길지는 사용자가 결정.
6. 병합 후 반드시: `node simulator/tests/run_js.js > js.json && python simulator/tests/reference.py js.json` → "최대 절대 차이" 1e-3 미만(현재 7.5e-8, 21개 시나리오). 그다음 `python simulator/build.py`.

### 줄바꿈 함정
- git의 `simulator/dist/SC_ROI_Simulator/data/**` 데이터팩은 CRLF, `simulator/data/**` 원본은 LF. build.py 뒤 185개 파일이 줄바꿈만 바뀌어 보이면 `git checkout -- simulator/dist/SC_ROI_Simulator/data` 후 `cp simulator/data/regions.js simulator/dist/SC_ROI_Simulator/data/`. 단, 수정 4로 데이터팩 내용이 실제로 바뀌었으면 이 되돌리기를 하면 안 됨(그때는 `git diff --ignore-cr-at-eol --stat`로 실제 변경을 확인).

## 현재 브랜치 상태 (2026-11-20 mini PC 기준)
- `origin/simulator`: 0857516 → a597dae → (이번 커밋). push는 사용자가 함(`git push origin simulator` + `git push origin simulator:main`).
- mini PC의 버린 노트 커밋 edf0156은 로컬 브랜치 `backup/mini-edf0156-20261120`에만 보관(push 안 함).
- 수정 4(`claude/SC_IDE_수정4_상식점검2_프롬프트.md`, 프로젝트 문서)는 원격에 없음 — 메인 PC에서 실행했는지 미확인.

## 이번에 구현한 동작 요약 (중복 구현 비교용)
- **HEMS 부하 이동** (`engine.js` `hemsShift`·`hemsLoad`·`yearCost`): TOU 요금제 + HEMS + '부하 이동' 체크일 때, 같은 날 안에서 세탁·식세기(7~22시, 시간당 2.0kWh 이하)와 AWHP 급탕(하루 상한 기본 1.5kWh, 압축기 3.91kW 이하)을 계통 수전분이 있는 가장 비싼 시간 → 가장 싼 시간(PV 잉여 시간은 매전 가치)으로 옮김. 달마다 1년 차 정상 상태 전기 비용이 줄어드는 달에만 적용. 그 뒤 계절별 절감률.
- **N년 차 월별 차트**: `simulate()`가 연도별 `years[i].mon`(pv, imp, exp, curt, billB, billA, expInc, gasB, gasA) 저장, UI 슬라이더 `[data-yr]`.
- **KPI**: `kpi.selfCons`(자가소비율) 추가.
- **화면**: 좌측 입력 패널 `position:sticky`(따로 스크롤), '1년 데이터' 탭에 HEMS 조작부(시뮬레이터 탭과 같은 값, `syncTwins`)와 'HEMS 변화' 히트맵, `simulate()` 결과 `hemsView`.
