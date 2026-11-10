"""Builds single standalone HTML report: korea/report/LG_SC_Korea_ROI_Report.html

Features:
- Pure offline single file (no external CDN, embedded SVG charts and JS).
- Full compliance with LGE brand palette tokens.
- Top executive summary fitting desktop fold without vertical scroll.
- Collapsible detailed sections (1-12) and bottom limitations section.
- Section 4: 3-house peak day profile tab selector with actual sized PV & ESS.
- Section 5: Critical day 15-day window daily GHI and 15-min load/PV/SoC time series.
- Section 6: Zero energy 12 cases comparing Daily PV criteria vs Minimal Cost reference.
- Section 9: Heatmap with target model switch (Zero Bill default, Near Zero, Zero Energy).
- Section 10: AWHP 70% sensitivity table with actual calculated payback reductions.
- Mandatory note: 'Therma V 값은 EU 모델 HM091HF UB40 기준이며 A-7 미만은 추정'
- Badges applied item-by-item instead of entire section headers.
- Dark / Light mode toggle + prefers-color-scheme.
- Print stylesheet auto-expanding all details.
"""

import json
from pathlib import Path


def generate_html_report(project_root: Path):
    korea_dir = project_root / "korea"
    report_dir = korea_dir / "report"
    data_path = report_dir / "report_data.json"

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Serialize data into embedded JSON for interactive JS
    json_data_str = json.dumps(data, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LG Smart Cottage Korea ROI 분석 보고서</title>
  <style>
    :root {{
      --lge-red: #A50034;
      --lge-active-red: #FD312E;
      --lge-dark: #000000;
      --lge-gray: #707070;
      --lge-warm-gray: #F0ECE4;
      --lge-white: #FFFFFF;

      --bg-primary: #FFFFFF;
      --bg-surface: #F8F7F4;
      --bg-card: #FFFFFF;
      --border-color: #E2DFD8;
      --border-subtle: #EDEAE3;
      --text-primary: #111111;
      --text-secondary: #555555;
      --text-muted: #707070;
      --table-header-bg: #F0ECE4;
      --table-hover-bg: #F7F5F0;
      --badge-verified-bg: #A50034;
      --badge-verified-txt: #FFFFFF;
      --badge-unverified-bg: #707070;
      --badge-unverified-txt: #FFFFFF;
      --badge-placeholder-bg: #EAE6DE;
      --badge-placeholder-txt: #222222;
      --chart-grid: #E8E6E0;
      --chart-axis: #707070;
      --chart-bg: #FFFFFF;
    }}

    [data-theme="dark"] {{
      --bg-primary: #121212;
      --bg-surface: #1A1A1A;
      --bg-card: #222222;
      --border-color: #333333;
      --border-subtle: #2A2A2A;
      --text-primary: #F5F5F5;
      --text-secondary: #CCCCCC;
      --text-muted: #999999;
      --table-header-bg: #2A2A2A;
      --table-hover-bg: #2C2C2C;
      --badge-verified-bg: #A50034;
      --badge-verified-txt: #FFFFFF;
      --badge-unverified-bg: #555555;
      --badge-unverified-txt: #FFFFFF;
      --badge-placeholder-bg: #3A3A3A;
      --badge-placeholder-txt: #E0E0E0;
      --chart-grid: #333333;
      --chart-axis: #999999;
      --chart-bg: #1A1A1A;
    }}

    @media (prefers-color-scheme: dark) {{
      :root:not([data-theme="light"]) {{
        --bg-primary: #121212;
        --bg-surface: #1A1A1A;
        --bg-card: #222222;
        --border-color: #333333;
        --border-subtle: #2A2A2A;
        --text-primary: #F5F5F5;
        --text-secondary: #CCCCCC;
        --text-muted: #999999;
        --table-header-bg: #2A2A2A;
        --table-hover-bg: #2C2C2C;
        --badge-verified-bg: #A50034;
        --badge-verified-txt: #FFFFFF;
        --badge-unverified-bg: #555555;
        --badge-unverified-txt: #FFFFFF;
        --badge-placeholder-bg: #3A3A3A;
        --badge-placeholder-txt: #E0E0E0;
        --chart-grid: #333333;
        --chart-axis: #999999;
        --chart-bg: #1A1A1A;
      }}
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html, body {{
      overflow-x: hidden;
      max-width: 100vw;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.5;
      padding: 0;
      margin: 0;
      font-size: 13.5px;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px 24px;
      width: 100%;
      box-sizing: border-box;
    }}

    /* Top Executive Summary (Fit Desktop Fold) */
    .hero-summary {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 18px 22px;
      margin-bottom: 22px;
    }}

    .brand-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid var(--lge-red);
      padding-bottom: 10px;
      margin-bottom: 14px;
    }}

    .brand-title h1 {{
      font-size: 21px;
      font-weight: 700;
      color: var(--lge-red);
      letter-spacing: -0.5px;
      margin-bottom: 3px;
    }}

    .brand-title p {{
      font-size: 12.5px;
      color: var(--text-secondary);
    }}

    .theme-toggle-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 5px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }}

    /* Findings Grid: 5 Cards */
    .findings-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }}

    .finding-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-top: 3px solid var(--lge-red);
      border-radius: 5px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
    }}

    .finding-card h3 {{
      font-size: 12.5px;
      font-weight: 700;
      color: var(--lge-red);
      margin-bottom: 5px;
      line-height: 1.3;
    }}

    .finding-card p {{
      font-size: 11.5px;
      color: var(--text-secondary);
      line-height: 1.4;
      flex: 1;
    }}

    /* Representative Table in Hero */
    .hero-table-wrapper {{
      margin-bottom: 12px;
      overflow-x: auto;
    }}

    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
      text-align: left;
      background: var(--bg-card);
    }}

    table.data-table th, table.data-table td {{
      padding: 7px 10px;
      border: 1px solid var(--border-color);
    }}

    table.data-table th {{
      background-color: var(--table-header-bg);
      font-weight: 600;
      color: var(--text-primary);
    }}

    table.data-table tr:hover {{
      background-color: var(--table-hover-bg);
    }}

    .notices-box {{
      background: var(--bg-card);
      border-left: 3px solid var(--lge-gray);
      padding: 8px 14px;
      font-size: 11.5px;
      color: var(--text-secondary);
      line-height: 1.5;
    }}

    .notices-box strong {{
      color: var(--text-primary);
    }}

    /* Collapsible Sections */
    details.accordion-section {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      margin-bottom: 12px;
      overflow: hidden;
    }}

    summary.section-header {{
      background: var(--bg-surface);
      padding: 12px 16px;
      font-size: 14.5px;
      font-weight: 700;
      color: var(--text-primary);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      user-select: none;
      border-bottom: 1px solid transparent;
      transition: background 0.2s;
    }}

    summary.section-header:hover {{
      background: var(--border-subtle);
    }}

    details[open] > summary.section-header {{
      border-bottom: 1px solid var(--border-color);
      color: var(--lge-red);
    }}

    .section-content {{
      padding: 16px 18px;
    }}

    /* Status Badges */
    .badge {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: 600;
      line-height: 1.2;
      white-space: nowrap;
    }}

    .badge-verified {{
      background: var(--badge-verified-bg);
      color: var(--badge-verified-txt);
    }}

    .badge-unverified {{
      background: var(--badge-unverified-bg);
      color: var(--badge-unverified-txt);
    }}

    .badge-placeholder {{
      background: var(--badge-placeholder-bg);
      color: var(--badge-placeholder-txt);
    }}

    /* Button Toggles */
    .btn-toggle {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 5px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: all 0.2s;
    }}

    .btn-toggle:hover {{
      border-color: var(--lge-red);
    }}

    .btn-toggle.active {{
      background: var(--lge-red);
      color: var(--lge-white);
      border-color: var(--lge-red);
      font-weight: 700;
    }}

    .controls-bar {{
      display: flex;
      gap: 8px;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }}

    @media (max-width: 900px) {{
      .findings-grid {{
        grid-template-columns: 1fr;
      }}
      .brand-header {{
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }}
      .container {{
        padding: 12px 14px;
      }}
    }}

    /* Print auto-expand */
    @media print {{
      body {{ font-size: 10pt; }}
      details {{ display: block !important; }}
      details[open] summary, details summary {{ display: block !important; font-weight: bold; page-break-after: avoid; }}
      .section-content {{ display: block !important; }}
      .theme-toggle-btn, .controls-bar button {{ display: none !important; }}
    }}
  </style>
</head>
<body>
  <div class="container">

    <!-- Top Executive Summary -->
    <div class="hero-summary">
      <div class="brand-header">
        <div class="brand-title">
          <h1>LG Smart Cottage Korea ROI 분석 보고서</h1>
          <p>분석 범위: 대한민국 강원도 춘천시 (37.88°N, 127.73°E), 3개 주택 모델(MONO Core 54, 72, DUO Max 45), 432개 시나리오 전수 분석</p>
        </div>
        <button class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()">다크모드 전환</button>
      </div>

      <!-- 5 Key Findings -->
      <div class="findings-grid">
        <div class="finding-card">
          <h3>01. 3년 회수 및 최단 회수</h3>
          <p id="findingSummary1">로딩 중...</p>
        </div>
        <div class="finding-card">
          <h3>02. Zero Energy 기준 비교</h3>
          <p id="findingSummary2">로딩 중...</p>
        </div>
        <div class="finding-card">
          <h3>03. Zero Bill ESS 단가 영향</h3>
          <p id="findingSummary3">로딩 중...</p>
        </div>
        <div class="finding-card">
          <h3>04. 프로판 비용 제거 효과</h3>
          <p id="findingSummary4">로딩 중...</p>
        </div>
        <div class="finding-card">
          <h3>05. 이용률 및 보조금 분석</h3>
          <p id="findingSummary5">로딩 중...</p>
        </div>
      </div>

      <!-- 1 Representative Summary Table (6 rows x 3 target models) -->
      <div class="hero-table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th rowspan="2">주택 모델</th>
              <th rowspan="2">난방 패키지</th>
              <th colspan="2" style="text-align: center; border-bottom: none;">Zero Energy (당일 PV 충족 기준)</th>
              <th colspan="2" style="text-align: center; border-bottom: none;">Zero Bill (변동요금 0원)</th>
              <th colspan="2" style="text-align: center; border-bottom: none;">Near Zero (3년 회수 불가, 최단 회수)</th>
            </tr>
            <tr>
              <th style="text-align: right;">투자비 (Central)</th>
              <th style="text-align: center;">회수기간</th>
              <th style="text-align: right;">투자비 (Central)</th>
              <th style="text-align: center;">회수기간</th>
              <th style="text-align: right;">투자비 (Central)</th>
              <th style="text-align: center;">회수기간</th>
            </tr>
          </thead>
          <tbody id="heroTableBody">
            <!-- Rendered by JS -->
          </tbody>
        </table>
      </div>

      <!-- Required Notices Box -->
      <div class="notices-box">
        <strong>보고 시 필수 유의사항:</strong>
        1) 부하는 실측이 아닌 ISO 13790 기반 5R1C 동적 열평형 및 가전 스케줄 시뮬레이션 데이터입니다.
        2) ESS 단가는 국내 시장 미성숙으로 NREL 미국 벤치마크 범위값($1,268/kWh, 환율 1,400원/$)을 적용하였습니다.
        3) 기상 데이터는 Climate.OneBuilding TMYx(2009-2023) 춘천 표준기상데이터(연간 GHI 1,490.6 kWh/m²) 기준입니다.
        4) Therma V 값은 EU 모델 HM091HF UB40 기준이며 A-7 미만은 추정입니다.
      </div>
    </div>

    <!-- Collapsible Section 1: 모델 정의와 계산 기준 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>1. 모델 정의 및 계산 기준</span>
      </summary>
      <div class="section-content">
        <table class="data-table" style="margin-bottom: 12px;">
          <thead>
            <tr>
              <th>주택 모델</th>
              <th>연면적</th>
              <th>거주 인원</th>
              <th>가전 패키지</th>
              <th>대기전력</th>
              <th>난방 / 냉방 설비</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>MONO Core 54</strong></td>
              <td>54.0 m²</td>
              <td>2인</td>
              <td>냉장고, 세탁기(9kg), 인덕션</td>
              <td>60.0 W</td>
              <td>시스템에어컨 (COP 4.40) / 가스보일러 or AWHP</td>
            </tr>
            <tr>
              <td><strong>MONO Core 72</strong></td>
              <td>72.9 m²</td>
              <td>3인</td>
              <td>냉장고, 워시타워, 인덕션, 식기세척기 (가정)</td>
              <td>60.0 W</td>
              <td>시스템에어컨 (COP 4.40) / 가스보일러 or AWHP</td>
            </tr>
            <tr>
              <td><strong>DUO Max 45</strong></td>
              <td>45.4 m² (복층)</td>
              <td>2인</td>
              <td>워시타워 컴팩트, 식기세척기, 인덕션, 광파오븐, 정수기, ERV, 냉장고</td>
              <td>106.7 W</td>
              <td>AWHP 시 Therma V 냉방(EER 2.6, 5.5kW) / 가스 시 에어컨(4.40)</td>
            </tr>
          </tbody>
        </table>
        <p style="font-size: 12px; color: var(--text-secondary);">
          * <strong>계산 기준:</strong> Zero Energy는 연간 부족량(LOL)=0.0h 무수전 오프그리드 기준. Zero Bill은 계통연계 연간 변동요금 0원(기본요금·세금 별도) 상계 기준. Near Zero는 3년 회수 불가 조건 하 최단 회수 조합. 가스 케이스는 전력 기준이며 일반프로판(LPG) 연료비는 별도 합산됩니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 2: 전기요금과 상계 제도 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>2. 전기요금 누진 구조 및 상계·이월 지침</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 12px;">한국전력공사 주택용 저압 요금표 및 소규모 신·재생에너지 상계 지침(제18조)을 적용하였습니다.</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 14px;">
          <div>
            <h4 style="margin-bottom: 6px; font-size: 13px;">한전 주택용 저압 누진 요금표 (2026) <span class="badge badge-verified">공식 확인</span></h4>
            <table class="data-table">
              <thead>
                <tr>
                  <th>구간 (비하계 기준)</th>
                  <th>기본요금 (원/호)</th>
                  <th>전력량요금 (원/kWh)</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>1구간 (200 kWh 이하)</td>
                  <td>910원</td>
                  <td>120.0원</td>
                </tr>
                <tr>
                  <td>2구간 (201 ~ 400 kWh)</td>
                  <td>1,600원</td>
                  <td>214.6원</td>
                </tr>
                <tr>
                  <td>3구간 (400 kWh 초과)</td>
                  <td>7,300원</td>
                  <td>307.3원</td>
                </tr>
              </tbody>
            </table>
            <p style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">* 하계(7~8월)는 1구간 300kWh, 2구간 450kWh까지 확대 적용. 기후환경요금 9원/kWh, 연료비조정액 +5원/kWh 별도.</p>
          </div>
          <div>
            <h4 style="margin-bottom: 6px; font-size: 13px;">표준 300 kWh 월 청구금액 계산 검증</h4>
            <table class="data-table">
              <tbody>
                <tr><td>기본요금 (2단계)</td><td style="text-align: right;">1,600원</td></tr>
                <tr><td>전력량요금 (200k×120원 + 100k×214.6원)</td><td style="text-align: right;">45,460원</td></tr>
                <tr><td>기후환경요금 (300k × 9원) + 연료비조정액 (+5원)</td><td style="text-align: right;">4,200원</td></tr>
                <tr><td>전기요금계</td><td style="text-align: right;"><strong>51,260원</strong></td></tr>
                <tr><td>부가가치세 (10%) + 전력산업기반기금 (2.7%)</td><td style="text-align: right;">6,500원</td></tr>
                <tr style="background: var(--table-header-bg);"><td><strong>최종 청구금액 (10원 미만 절사)</strong></td><td style="text-align: right;"><strong>57,760원</strong></td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <p style="font-size: 12px; color: var(--text-secondary);">
          * <strong>상계 및 이월:</strong> 한전 지침 제18조에 의거, 월간 잉여 발전량은 당월 수전량과 1:1 상계된 후 잔여 잉여량은 다음 달로 <strong>무기한 누적 이월(소멸 없음)</strong> 처리됩니다. <span class="badge badge-verified">공식 확인</span>
        </p>
      </div>
    </details>

    <!-- Collapsible Section 3: 설치비 및 단가 근거 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>3. 설치비(CAPEX) 및 단가 산정 근거</span>
      </summary>
      <div class="section-content">
        <table class="data-table">
          <thead>
            <tr>
              <th>구분</th>
              <th>적용 단가 (Central)</th>
              <th>적용 범위 (Low ~ High)</th>
              <th>출처 및 산출 근거</th>
              <th>상태 뱃지</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>태양광 (PV ≤3kW)</strong></td>
              <td>1,513,667원/kW</td>
              <td>110만 ~ 200만원/kW</td>
              <td>2026 신재생에너지보급 주택지원 3kW 상한액(4,541,000원) 비례 산출</td>
              <td><span class="badge badge-verified">공식 확인</span></td>
            </tr>
            <tr>
              <td><strong>태양광 (PV >3kW)</strong></td>
              <td>1,513,667원/kW</td>
              <td>110만 ~ 200만원/kW</td>
              <td>3kW 초과 단가 단순 비례 적용 (지상 추가비 0원 반영)</td>
              <td><span class="badge badge-unverified">미검증</span></td>
            </tr>
            <tr>
              <td><strong>ESS 시스템</strong></td>
              <td>1,775,200원/kWh</td>
              <td>39.6만 ~ 187.2만원/kWh</td>
              <td>NREL Q1 2021 Benchmark ($1,268/kWh, 환율 1,400원/$ 해외 벤치마크)</td>
              <td><span class="badge badge-unverified">미검증</span></td>
            </tr>
            <tr>
              <td><strong>AWHP (Therma V)</strong></td>
              <td>14,000,000원</td>
              <td>1,400만원 고정</td>
              <td>난방전기화사업 기준 사업비 상한: 주요설비 1,200만 원 + 전기·기타 200만 원 (출처: 한국냉난방공조신문 2026-09 기사)</td>
              <td><span class="badge badge-unverified">미검증</span></td>
            </tr>
            <tr>
              <td><strong>일반프로판 (LPG)</strong></td>
              <td>2,812.26원/kg</td>
              <td>-</td>
              <td>한국석유공사 오피넷 일반프로판 전국 평균 (2026년 10월 4주)</td>
              <td><span class="badge badge-verified">공식 확인</span></td>
            </tr>
            <tr>
              <td><strong>인버터 교체비</strong></td>
              <td>250,000원/kW (최소 75만)</td>
              <td>-</td>
              <td>13년 차 인버터 교체비 가정치</td>
              <td><span class="badge badge-placeholder">(가정)</span></td>
            </tr>
            <tr>
              <td><strong>지상 설치비</strong></td>
              <td>0원 (5kW 초과분)</td>
              <td>-</td>
              <td>분석 지침에 따라 지상 추가 시공비 0원 적용 (부지 매입비 별도)</td>
              <td><span class="badge badge-placeholder">(가정)</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <!-- Collapsible Section 4: 부하 패턴 15분 차트 (3개 주택 탭 전환) -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>4. 주택 모델별 연간 최대 부하일 15분 프로파일</span>
      </summary>
      <div class="section-content">
        <div class="controls-bar">
          <span style="font-weight: 600;">주택 모델 선택:</span>
          <button class="btn-toggle active" id="btnTabCore54" onclick="switchPeakTab('MONO Core 54')">MONO Core 54</button>
          <button class="btn-toggle" id="btnTabCore72" onclick="switchPeakTab('MONO Core 72')">MONO Core 72</button>
          <button class="btn-toggle" id="btnTabDuoMax" onclick="switchPeakTab('DUO Max 45')">DUO Max 45</button>
        </div>
        <p id="peakChartTitle" style="font-weight: 700; color: var(--lge-red); margin-bottom: 8px;">조건 로딩 중...</p>
        <div id="chartProfilesContainer">
          <!-- SVG rendered by JS -->
        </div>
        <p style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">
          * 부하는 5R1C 시뮬레이션 기반 <span class="badge badge-placeholder">(가정)</span>이며, PV 발전량은 해당 주택 케이스의 실제 산정 용량을 적용하였습니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 5: Critical Day 분석 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>5. Critical Day (2026-02-03) 및 전후 7일 분석</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 8px;">
          춘천 TMYx 연중 최저 일사 강설일인 <strong>2026-02-03 (Day 34, GHI 0.25 kWh/m²)</strong>과 전후 7일간(총 15일)의 일별 일사량 및 15분 시계열 변화입니다.
        </p>
        <div id="chartCriticalDailyContainer" style="margin-bottom: 14px;">
          <!-- Daily GHI SVG rendered by JS -->
        </div>
        <div id="chartCritical15mContainer">
          <!-- 15-min Series SVG rendered by JS -->
        </div>
        <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
          * <strong>피크데이 방식과의 차이:</strong> 기존 단일 피크일 기준 사이징 시 동계 저조도 기간 동안 수백~수천 시간의 정전(LOL)이 발생하지만, 본 분석의 365일 연계 시뮬레이션은 12개 케이스 전수 연간 LOL = 0.0시간을 달성합니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 6: Zero Energy 상세 표 (당일 PV 충족 vs 최소비용) -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>6. Zero Energy (오프그리드 무수전) 12개 케이스 상세 분석</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 10px; font-size: 12.5px;">
          본문 표의 <strong>"당일 PV 충족 기준"</strong>과 <strong>"ESS 보완 최소비용 조합"</strong>을 나란히 비교합니다. 둘 다 TMY 기준 연간 무수전(LOL = 0.0시간)을 달성하지만, 2026-02-03 하루의 극저일사가 두 방식 간 큰 용량 격차를 만듭니다.
        </p>
        <div class="hero-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th rowspan="2">주택 모델</th>
                <th rowspan="2">난방</th>
                <th rowspan="2">EV</th>
                <th colspan="4" style="text-align: center; border-bottom: none;">당일 PV 충족 기준 (본문값)</th>
                <th colspan="3" style="text-align: center; border-bottom: none;">ESS 보완 최소비용 조합 (참고값)</th>
                <th rowspan="2" style="text-align: center;">필요부지<br>(5m²/kW)</th>
                <th rowspan="2" style="text-align: center;">정전시간<br>(LOL)</th>
              </tr>
              <tr>
                <th>감쇄전 PV</th>
                <th>감쇄후 PV</th>
                <th>ESS 용량</th>
                <th>CAPEX</th>
                <th>최적 PV</th>
                <th>최적 ESS</th>
                <th>최소 CAPEX</th>
              </tr>
            </thead>
            <tbody id="zeTableBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
        <p style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">
          * 감쇄 계수: 25년 차 0.995^24 = 0.886654 적용. 회수기간은 전 케이스 >25년입니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 7: Zero Bill 분석 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>7. Zero Bill (변동요금 0원, 기본요금·세금 별도) Low / Central / High 분석</span>
        <span class="badge badge-unverified">미검증 (ESS 단가)</span>
      </summary>
      <div class="section-content">
        <div class="hero-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>주택 모델</th>
                <th>난방 패키지</th>
                <th>PV 용량</th>
                <th>ESS 용량</th>
                <th>CAPEX (Low)</th>
                <th>CAPEX (Central)</th>
                <th>CAPEX (High)</th>
                <th>회수기간 (Low)</th>
                <th>회수기간 (Central)</th>
                <th>회수기간 (High)</th>
              </tr>
            </thead>
            <tbody id="zbTableBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
      </div>
    </details>

    <!-- Collapsible Section 8: Near Zero Bill 분석 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>8. Near Zero (3년 회수 불가, 최단 회수 조합) 및 3년 달성 필요 CAPEX</span>
      </summary>
      <div class="section-content">
        <div class="hero-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>주택 모델</th>
                <th>난방 패키지</th>
                <th>PV 용량</th>
                <th>ESS 용량</th>
                <th>실제 CAPEX</th>
                <th>현재 회수기간</th>
                <th>3년 달성 필요 CAPEX</th>
                <th>CAPEX 인하 필요액</th>
                <th>인하율 (%)</th>
              </tr>
            </thead>
            <tbody id="nzTableBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
      </div>
    </details>

    <!-- Collapsible Section 9: 이용률별 회수기간 히트맵 (모델 전환 지원) -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>9. 이용률(점유율)별 회수기간 히트맵 및 보조금 전환</span>
      </summary>
      <div class="section-content">
        <div class="controls-bar">
          <span style="font-weight: 600;">목표 모델:</span>
          <button class="btn-toggle active" id="btnModelZb" onclick="switchHeatmapModel('zero_bill')">Zero Bill (기본)</button>
          <button class="btn-toggle" id="btnModelNz" onclick="switchHeatmapModel('near_zero_bill')">Near Zero</button>
          <button class="btn-toggle" id="btnModelZe" onclick="switchHeatmapModel('zero_energy')">Zero Energy</button>

          <span style="font-weight: 600; margin-left: 16px;">보조금 조건:</span>
          <button class="btn-toggle active" id="btnSubFalse" onclick="switchHeatmapSub(false)">보조금 미적용 (기본)</button>
          <button class="btn-toggle" id="btnSubTrue" onclick="switchHeatmapSub(true)">2026 보조금 적용 (265만원)</button>
        </div>
        <p style="font-size: 11.5px; color: var(--text-muted); margin-bottom: 6px;">
          * <strong>표시 기준:</strong> EV 0대, Central 비용 tier, 투자비 회수기간(년, 25년 초과 시 >25년 표시). 보조금은 PV 3kW 이하에만 적용.
        </p>
        <div class="hero-table-wrapper">
          <table class="data-table" id="heatmapTable">
            <thead>
              <tr>
                <th>주택 모델</th>
                <th>난방 패키지</th>
                <th style="text-align: center;">100% (상시)</th>
                <th style="text-align: center;">70% (주 5일)</th>
                <th style="text-align: center;">50% (격주)</th>
                <th style="text-align: center;">30% (주말)</th>
                <th style="text-align: center;">10% (월 3일)</th>
                <th style="text-align: center;">5% (연휴)</th>
              </tr>
            </thead>
            <tbody id="heatmapTableBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
      </div>
    </details>

    <!-- Collapsible Section 10: 보조금 및 AWHP 70% 민감도 분석 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>10. 보조금 정책 및 AWHP 70% 민감도 분석</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 10px;">
          2026 주택지원 국비(165만원, <span class="badge badge-verified">공식 확인</span>) 및 춘천시 시비 하한(100만원, <span class="badge badge-verified">공식 확인</span>) 적용 현황과, 온난지역·실거주 가상 시나리오(AWHP 70% 지원, 980만원) 민감도 실제 분석 결과입니다.
        </p>
        <div class="hero-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>주택 모델</th>
                <th>목표 모델</th>
                <th>기준 CAPEX (무보조)</th>
                <th>기준 회수기간</th>
                <th>AWHP 70% 적용 CAPEX</th>
                <th>AWHP 70% 적용 회수기간</th>
                <th>회수기간 단축 효과</th>
              </tr>
            </thead>
            <tbody id="subsidyTableBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
        <p style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">
          * 각주: 춘천시 안내문은 2025년 단가 기준(총공사비 4,930,000원, 공단 1,790,000원)이며, 본 보고서는 2026 공고 단가(총공사비 4,541,000원, 공단 1,650,000원) + 춘천 시비 1,000,000원을 적용하였습니다. AWHP 70% 보조금은 춘천시에는 적용되지 않는 가상 정책 민감도입니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 11: 전체 432개 시나리오 인터랙티브 테이블 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>11. 전체 432개 시나리오 결과 브라우저</span>
      </summary>
      <div class="section-content">
        <div style="display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;">
          <select id="filterHouse" onchange="filterScenarios()" style="padding: 5px 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary);">
            <option value="">전체 주택 모델</option>
            <option value="MONO Core 54">MONO Core 54</option>
            <option value="MONO Core 72">MONO Core 72</option>
            <option value="DUO Max 45">DUO Max 45</option>
          </select>
          <select id="filterHeat" onchange="filterScenarios()" style="padding: 5px 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary);">
            <option value="">전체 난방 패키지</option>
            <option value="가스보일러">가스보일러</option>
            <option value="AWHP">AWHP</option>
          </select>
          <select id="filterTarget" onchange="filterScenarios()" style="padding: 5px 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary);">
            <option value="">전체 목표 모델</option>
            <option value="zero_energy">Zero Energy</option>
            <option value="zero_bill">Zero Bill</option>
            <option value="near_zero_bill">Near Zero</option>
          </select>
          <select id="filterOcc" onchange="filterScenarios()" style="padding: 5px 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary);">
            <option value="">전체 이용률</option>
            <option value="1.0">100%</option>
            <option value="0.7">70%</option>
            <option value="0.5">50%</option>
            <option value="0.3">30%</option>
            <option value="0.1">10%</option>
            <option value="0.05">5%</option>
          </select>
          <span id="scenarioCountLabel" style="font-size: 12px; color: var(--text-secondary); align-self: center;"></span>
        </div>
        <div class="hero-table-wrapper" style="max-height: 400px; overflow-y: auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>주택 모델</th>
                <th>난방</th>
                <th>EV</th>
                <th>이용률</th>
                <th>목표 모델</th>
                <th>보조금</th>
                <th>PV (kW)</th>
                <th>ESS (kWh)</th>
                <th>부지 (m²)</th>
                <th>CAPEX (원)</th>
                <th>회수기간</th>
              </tr>
            </thead>
            <tbody id="allScenariosBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
      </div>
    </details>

    <!-- Collapsible Section 12: DUO Max 45 증분 투자 분석 (72건) -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>12. [부록] DUO Max 45 증분 투자(Incremental) 분석 (72건)</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 12px;">
          DUO Max 45의 경우 <strong>루프탑 기본 PV 5kW 및 AWHP 완제품 기본 탑재</strong>를 전제로 하여, 추가 PV·ESS 증설 비용 및 추가 절감액만으로 산출한 증분 회수기간(Incremental ROI) 분석 결과입니다.
        </p>
        <div class="hero-table-wrapper" style="max-height: 350px; overflow-y: auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>이용률</th>
                <th>EV</th>
                <th>목표 모델</th>
                <th>보조금</th>
                <th>총 PV (kW)</th>
                <th>총 ESS (kWh)</th>
                <th>증분 CAPEX (원)</th>
                <th>증분 회수기간</th>
              </tr>
            </thead>
            <tbody id="duoIncBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
      </div>
    </details>

    <!-- Bottom Limitations & Next Steps Section -->
    <details class="accordion-section" style="border-top: 2px solid var(--lge-gray);">
      <summary class="section-header">
        <span>데이터 한계, PLACEHOLDER / UNVERIFIED 전체 목록 및 향후 확장 계획</span>
        <span class="badge badge-placeholder">필독 사항</span>
      </summary>
      <div class="section-content">
        <h4 style="font-size: 13px; color: var(--lge-red); margin-bottom: 8px;">분석 가정 및 데이터 한계점</h4>
        <ul style="margin-left: 20px; margin-bottom: 16px; font-size: 12.5px; color: var(--text-secondary);">
          <li><strong>부하 모델링:</strong> 실제 계측 데이터가 아닌 ISO 13790 기반 5R1C 동적 시뮬레이션 및 표준 가전 소비전력 스케줄을 사용하였습니다.</li>
          <li><strong>ESS 비용:</strong> 국내 가정용 소용량 ESS 시장 미성숙으로 NREL 미국 벤치마크 데이터를 환율 1,400원/$으로 단순 환산하여 적용하였습니다.</li>
          <li><strong>PV 설치비:</strong> 3kW 초과 설비에 대해 정부 공고 3kW 단가를 단순 비례 적용하였으며, 토목·기초 공사비 및 부지 매입비는 반영되지 않았습니다.</li>
          <li><strong>동계 성능:</strong> Therma V HM091HF UB40의 A-7℃ 미만 성능은 선형 외삽 추정치이며 실제 혹한기 서리(Defrost) 손실은 추가 검증이 필요합니다.</li>
        </ul>

        <h4 style="font-size: 13px; color: var(--lge-red); margin-bottom: 8px;">PLACEHOLDER 및 UNVERIFIED 항목 요약</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
          <div>
            <h5 style="font-size: 12px; margin-bottom: 4px;">주요 PLACEHOLDER 항목:</h5>
            <ul style="font-size: 12px; margin-left: 18px; color: var(--text-secondary);">
              <li>환율 가정 (1,400 KRW/USD)</li>
              <li>지상 설치 추가비 (0원 가정)</li>
              <li>인버터 교체비 (25만원/kW) 및 13년 차 교체 주기</li>
              <li>가정용 ESS 보조금 단가 및 상한 (미반영)</li>
              <li>ERV 전열교환기 연속 소비전력 (30W)</li>
            </ul>
          </div>
          <div>
            <h5 style="font-size: 12px; margin-bottom: 4px;">주요 UNVERIFIED 항목:</h5>
            <ul style="font-size: 12px; margin-left: 18px; color: var(--text-secondary);">
              <li>가구원수별 전력량 3,749/4,094kWh (KESIS 자료와 유사 수준, 정확한 표 미특정)</li>
              <li>Therma V A-7℃ 미만 성능 기울기 외삽값</li>
              <li>NREL ESS 배터리팩 및 시공 단가</li>
              <li>AWHP 사업비 상한 (1,400만원) 세부 내역</li>
            </ul>
          </div>
        </div>

        <h4 style="font-size: 13px; color: var(--lge-red); margin-bottom: 8px;">다음 단계: 글로벌 국가 확장 로드맵</h4>
        <p style="font-size: 12.5px; color: var(--text-secondary);">
          본 ROI 엔진은 다국가 확장 구조로 설계되었습니다.
          <strong>호주(Australia)</strong>의 경우 높은 일사량과 실시간 도매요금 연동(NEM) 구조를 반영하며,
          <strong>미국 캘리포니아(California)</strong>의 경우 NEM 3.0(Net Billing Tariff) 요금제 및 높은 피크 전기요금(Super Peak) 하에서의 ESS 경제성을 검증할 예정입니다.
        </p>
      </div>
    </details>

  </div>

  <script>
    // Embedded Complete Report Data
    const REPORT_DATA = {json_data_str};

    // Format KRW
    function formatKRW(val) {{
      if (val === null || val === undefined || isNaN(val)) return "-";
      const v = Number(val);
      if (Math.abs(v) >= 100000000) return (v / 100000000).toFixed(1) + "억원";
      if (Math.abs(v) >= 10000) return Math.round(v / 10000).toLocaleString() + "만원";
      return Math.round(v).toLocaleString() + "원";
    }}

    // Format Payback
    function formatPB(val) {{
      if (val === null || val === undefined || isNaN(val) || val >= 999.0 || val < 0) return ">25년";
      return Number(val).toFixed(1) + "년";
    }}

    // Theme Toggle
    function toggleTheme() {{
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      document.getElementById("themeToggleBtn").innerText = next === "dark" ? "라이트모드 전환" : "다크모드 전환";
      renderPeakDayChart();
      renderCriticalDailyChart();
      renderCritical15mChart();
    }}

    // Populate Findings Text
    function populateFindings() {{
      REPORT_DATA.key_findings.forEach(f => {{
        const el = document.getElementById("findingSummary" + f.id);
        if (el) el.innerText = f.summary;
      }});
    }}

    // Render Representative Table in Hero
    function renderHeroTable() {{
      const tbody = document.getElementById("heroTableBody");
      tbody.innerHTML = "";
      REPORT_DATA.representative_table.forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${{r.house_model}}</strong></td>
          <td>${{r.heating_package}}</td>
          <td style="text-align: right;">${{r.zero_energy.capex_str}}</td>
          <td style="text-align: center; font-weight: 600; color: ${{r.zero_energy.payback_years < 25 ? 'var(--lge-red)' : 'var(--text-muted)'}};">${{r.zero_energy.payback_str}}</td>
          <td style="text-align: right;">${{r.zero_bill.capex_str}}</td>
          <td style="text-align: center; font-weight: 600; color: ${{r.zero_bill.payback_years < 25 ? 'var(--lge-red)' : 'var(--text-muted)'}};">${{r.zero_bill.payback_str}}</td>
          <td style="text-align: right;">${{r.near_zero_bill.capex_str}}</td>
          <td style="text-align: center; font-weight: 600; color: ${{r.near_zero_bill.payback_years < 25 ? 'var(--lge-red)' : 'var(--text-muted)'}};">${{r.near_zero_bill.payback_str}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Section 4: Peak Day Profiles Tab Logic
    let currentPeakHouse = "MONO Core 54";
    function switchPeakTab(hm) {{
      currentPeakHouse = hm;
      document.getElementById("btnTabCore54").classList.toggle("active", hm === "MONO Core 54");
      document.getElementById("btnTabCore72").classList.toggle("active", hm === "MONO Core 72");
      document.getElementById("btnTabDuoMax").classList.toggle("active", hm === "DUO Max 45");
      renderPeakDayChart();
    }}

    function renderPeakDayChart() {{
      const container = document.getElementById("chartProfilesContainer");
      const p = REPORT_DATA.peak_day_profiles[currentPeakHouse];
      if (!p) return;

      document.getElementById("peakChartTitle").innerText = p.condition_title;

      const w = 900;
      const h = 260;
      const padL = 50;
      const padR = 20;
      const padT = 30;
      const padB = 40;

      const maxVal = Math.max(6.0, ...p.load_kw, ...p.pv_kw);
      const n = p.load_kw.length; // 96

      function getX(i) {{ return padL + (i / (n - 1)) * (w - padL - padR); }}
      function getY(val) {{ return h - padB - (val / maxVal) * (h - padT - padB); }}

      let pathLoad = `M ${{getX(0)}} ${{getY(p.load_kw[0])}}`;
      let pathPv = `M ${{getX(0)}} ${{getY(p.pv_kw[0])}}`;
      for (let i = 1; i < n; i++) {{
        pathLoad += ` L ${{getX(i)}} ${{getY(p.load_kw[i])}}`;
        pathPv += ` L ${{getX(i)}} ${{getY(p.pv_kw[i])}}`;
      }}

      let svg = `
        <svg viewBox="0 0 ${{w}} ${{h}}" style="width: 100%; height: auto; display: block;">
          <!-- Grid Lines -->
          <line x1="${{padL}}" y1="${{getY(0)}}" x2="${{w - padR}}" y2="${{getY(0)}}" stroke="var(--chart-axis)" stroke-width="1"/>
          <line x1="${{padL}}" y1="${{getY(2)}}" x2="${{w - padR}}" y2="${{getY(2)}}" stroke="var(--chart-grid)" stroke-dasharray="3,3"/>
          <line x1="${{padL}}" y1="${{getY(4)}}" x2="${{w - padR}}" y2="${{getY(4)}}" stroke="var(--chart-grid)" stroke-dasharray="3,3"/>
          <line x1="${{padL}}" y1="${{getY(6)}}" x2="${{w - padR}}" y2="${{getY(6)}}" stroke="var(--chart-grid)" stroke-dasharray="3,3"/>

          <!-- Y Axis Labels -->
          <text x="${{padL - 8}}" y="${{getY(0) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">0 kW</text>
          <text x="${{padL - 8}}" y="${{getY(2) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">2 kW</text>
          <text x="${{padL - 8}}" y="${{getY(4) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">4 kW</text>
          <text x="${{padL - 8}}" y="${{getY(6) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">6 kW</text>

          <!-- X Axis Labels (Every 3 hours) -->
          ${{[0, 12, 24, 36, 48, 60, 72, 84, 95].map(idx => `
            <text x="${{getX(idx)}}" y="${{h - padB + 16}}" font-size="11" fill="var(--chart-axis)" text-anchor="middle">${{p.times[idx]}}</text>
          `).join('')}}

          <!-- Paths -->
          <path d="${{pathLoad}}" fill="none" stroke="var(--lge-dark)" stroke-width="2.5" />
          <path d="${{pathPv}}" fill="none" stroke="var(--lge-red)" stroke-width="2" />

          <!-- Title & Legend -->
          <circle cx="${{w - 280}}" cy="14" r="5" fill="var(--lge-dark)"/>
          <text x="${{w - 270}}" y="18" font-size="11" fill="var(--text-primary)">부하 (kW)</text>
          <line x1="${{w - 180}}" y1="14" x2="${{w - 160}}" y2="14" stroke="var(--lge-red)" stroke-width="2"/>
          <text x="${{w - 154}}" y="18" font-size="11" fill="var(--text-primary)">PV 발전 (${{p.actual_pv_kw.toFixed(2)}}kW)</text>
        </svg>
      `;
      container.innerHTML = svg;
    }}

    // Section 5: Critical Day Daily GHI Bar Chart
    function renderCriticalDailyChart() {{
      const container = document.getElementById("chartCriticalDailyContainer");
      const list = REPORT_DATA.critical_window_daily;
      if (!list || list.length === 0) return;

      const w = 900;
      const h = 180;
      const padL = 50;
      const padR = 20;
      const padT = 25;
      const padB = 30;

      const maxGhi = Math.max(5.0, ...list.map(d => d.ghi_kwh_m2));
      const n = list.length;
      const barW = ((w - padL - padR) / n) * 0.65;

      function getBarX(i) {{ return padL + (i + 0.175) * ((w - padL - padR) / n); }}
      function getY(val) {{ return h - padB - (val / maxGhi) * (h - padT - padB); }}

      let svg = `
        <svg viewBox="0 0 ${{w}} ${{h}}" style="width: 100%; height: auto; display: block;">
          <line x1="${{padL}}" y1="${{getY(0)}}" x2="${{w - padR}}" y2="${{getY(0)}}" stroke="var(--chart-axis)" stroke-width="1"/>
          <text x="${{padL - 8}}" y="${{getY(0) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">0.0</text>
          <text x="${{padL - 8}}" y="${{getY(2) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">2.0</text>
          <text x="${{padL - 8}}" y="${{getY(4) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">4.0</text>

          <text x="${{padL}}" y="16" font-size="12" font-weight="700" fill="var(--text-primary)">
            Critical Day (2026-02-03) 전후 7일 일별 일사량 (Daily GHI, kWh/m²)
          </text>

          ${{list.map((d, i) => {{
            const bx = getBarX(i);
            const by = getY(d.ghi_kwh_m2);
            const bh = getY(0) - by;
            const fillCol = d.is_critical ? "var(--lge-active-red)" : "var(--lge-gray)";
            return `
              <rect x="${{bx}}" y="${{by}}" width="${{barW}}" height="${{bh}}" fill="${{fillCol}}" />
              <text x="${{bx + barW / 2}}" y="${{by - 4}}" font-size="10" fill="var(--text-primary)" text-anchor="middle">${{d.ghi_kwh_m2.toFixed(2)}}</text>
              <text x="${{bx + barW / 2}}" y="${{h - padB + 14}}" font-size="10" fill="${{d.is_critical ? 'var(--lge-red)' : 'var(--text-secondary)'}}" font-weight="${{d.is_critical ? '700' : '400'}}" text-anchor="middle">${{d.date.substring(5)}}</text>
            `;
          }}).join('')}}
        </svg>
      `;
      container.innerHTML = svg;
    }}

    // Section 5: Critical Day 15-min Time Series Chart
    function renderCritical15mChart() {{
      const container = document.getElementById("chartCritical15mContainer");
      const c = REPORT_DATA.critical_window_15min;
      if (!c || !c.load_kw || c.load_kw.length === 0) return;

      const w = 900;
      const h = 200;
      const padL = 50;
      const padR = 20;
      const padT = 25;
      const padB = 30;

      const n = c.load_kw.length;
      const maxKw = Math.max(8.0, ...c.load_kw, ...c.pv_kw_series);

      function getX(i) {{ return padL + (i / (n - 1)) * (w - padL - padR); }}
      function getY(val) {{ return h - padB - (val / maxKw) * (h - padT - padB); }}

      let pathLoad = `M ${{getX(0)}} ${{getY(c.load_kw[0])}}`;
      let pathPv = `M ${{getX(0)}} ${{getY(c.pv_kw_series[0])}}`;
      for (let i = 1; i < n; i++) {{
        pathLoad += ` L ${{getX(i)}} ${{getY(c.load_kw[i])}}`;
        pathPv += ` L ${{getX(i)}} ${{getY(c.pv_kw_series[i])}}`;
      }}

      let svg = `
        <svg viewBox="0 0 ${{w}} ${{h}}" style="width: 100%; height: auto; display: block;">
          <line x1="${{padL}}" y1="${{getY(0)}}" x2="${{w - padR}}" y2="${{getY(0)}}" stroke="var(--chart-axis)" stroke-width="1"/>
          <text x="${{padL - 8}}" y="${{getY(0) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">0 kW</text>
          <text x="${{padL - 8}}" y="${{getY(4) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">4 kW</text>
          <text x="${{padL - 8}}" y="${{getY(8) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">8 kW</text>

          <text x="${{padL}}" y="16" font-size="12" font-weight="700" fill="var(--text-primary)">
            15일간 15분 단위 부하 vs PV 발전량 (MONO Core 54 Zero Energy 기준: PV ${{c.pv_kw}}kW, ESS ${{c.ess_kwh}}kWh)
          </text>

          <path d="${{pathLoad}}" fill="none" stroke="var(--lge-dark)" stroke-width="1.2" />
          <path d="${{pathPv}}" fill="none" stroke="var(--lge-red)" stroke-width="1.2" />
        </svg>
      `;
      container.innerHTML = svg;
    }}

    // Section 6: Render Zero Energy Table
    function renderZeroEnergyTable() {{
      const tbody = document.getElementById("zeTableBody");
      tbody.innerHTML = "";
      REPORT_DATA.zero_energy_cases.forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${{r.house_model}}</strong></td>
          <td>${{r.heating_package}}</td>
          <td>${{r.ev_count}}대</td>
          <td style="text-align: right;">${{r.daily_pv_kw.toFixed(1)}} kW</td>
          <td style="text-align: right;">${{r.daily_pv_deg_kw.toFixed(1)}} kW</td>
          <td style="text-align: right;">${{r.daily_ess_kwh.toFixed(1)}} kWh</td>
          <td style="text-align: right;">${{formatKRW(r.daily_capex_krw)}}</td>
          <td style="text-align: right; color: var(--lge-red);"><strong>${{r.ref_pv_kw.toFixed(1)}} kW</strong></td>
          <td style="text-align: right; color: var(--lge-red);"><strong>${{r.ref_ess_kwh.toFixed(1)}} kWh</strong></td>
          <td style="text-align: right; color: var(--lge-red);"><strong>${{formatKRW(r.ref_capex_krw)}}</strong></td>
          <td style="text-align: center;">${{r.ref_pv_land_m2}} m²</td>
          <td style="text-align: center;">${{r.lol_hours.toFixed(1)}} h</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Section 7: Render Zero Bill Table
    function renderZeroBillTable() {{
      const tbody = document.getElementById("zbTableBody");
      tbody.innerHTML = "";
      REPORT_DATA.zero_bill_details.forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${{r.house_model}}</strong></td>
          <td>${{r.heating_package}}</td>
          <td>${{r.pv_kw}} kW</td>
          <td>${{r.ess_kwh}} kWh</td>
          <td style="text-align: right;">${{formatKRW(r.capex_low_krw)}}</td>
          <td style="text-align: right;"><strong>${{formatKRW(r.capex_central_krw)}}</strong></td>
          <td style="text-align: right;">${{formatKRW(r.capex_high_krw)}}</td>
          <td style="text-align: center;">${{r.payback_low}}</td>
          <td style="text-align: center;"><strong>${{r.payback_central}}</strong></td>
          <td style="text-align: center;">${{r.payback_high}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Section 8: Render Near Zero Table
    function renderNearZeroTable() {{
      const tbody = document.getElementById("nzTableBody");
      tbody.innerHTML = "";
      REPORT_DATA.near_zero_details.forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${{r.house_model}}</strong></td>
          <td>${{r.heating_package}}</td>
          <td>${{r.pv_kw}} kW</td>
          <td>${{r.ess_kwh}} kWh</td>
          <td style="text-align: right;">${{formatKRW(r.actual_capex_krw)}}</td>
          <td style="text-align: center; font-weight: 600;">${{r.payback}}</td>
          <td style="text-align: right; color: var(--lge-red);">${{formatKRW(r.target_capex_for_3y_krw)}}</td>
          <td style="text-align: right;">${{formatKRW(r.capex_reduction_needed_krw)}}</td>
          <td style="text-align: center;">-${{r.reduction_pct}}%</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Section 9: Heatmap Logic
    let currentHeatmapModel = "zero_bill";
    let isSubsidizedHeatmap = false;

    function switchHeatmapModel(tm) {{
      currentHeatmapModel = tm;
      document.getElementById("btnModelZb").classList.toggle("active", tm === "zero_bill");
      document.getElementById("btnModelNz").classList.toggle("active", tm === "near_zero_bill");
      document.getElementById("btnModelZe").classList.toggle("active", tm === "zero_energy");
      renderHeatmapTable();
    }}

    function switchHeatmapSub(withSub) {{
      isSubsidizedHeatmap = withSub;
      document.getElementById("btnSubFalse").classList.toggle("active", !withSub);
      document.getElementById("btnSubTrue").classList.toggle("active", withSub);
      renderHeatmapTable();
    }}

    function renderHeatmapTable() {{
      const tbody = document.getElementById("heatmapTableBody");
      tbody.innerHTML = "";
      const modelData = REPORT_DATA.heatmaps[currentHeatmapModel];
      const dataset = isSubsidizedHeatmap ? modelData.with_subsidy : modelData.no_subsidy;

      dataset.forEach(r => {{
        const tr = document.createElement("tr");
        let tds = `<td><strong>${{r.house_model}}</strong></td><td>${{r.heating_package}}</td>`;
        ["100", "70", "50", "30", "10", "5"].forEach(k => {{
          const valStr = r.values[k];
          const isFeasible = valStr !== ">25년";
          const bg = isFeasible ? '#FD312E15' : 'transparent';
          const txtColor = isFeasible ? 'var(--lge-red)' : 'var(--text-muted)';
          const weight = isFeasible ? '700' : '400';
          tds += `<td style="text-align: center; background: ${{bg}}; color: ${{txtColor}}; font-weight: ${{weight}};">${{valStr}}</td>`;
        }});
        tr.innerHTML = tds;
        tbody.appendChild(tr);
      }});
    }}

    // Section 10: Render Subsidy & AWHP 70% Table
    function renderSubsidyTable() {{
      const tbody = document.getElementById("subsidyTableBody");
      tbody.innerHTML = "";
      REPORT_DATA.subsidy_sensitivity.forEach(r => {{
        const tr = document.createElement("tr");
        const tmStr = r.target_model === "near_zero_bill" ? "Near Zero" : "Zero Bill";
        tr.innerHTML = `
          <td><strong>${{r.house_model}}</strong></td>
          <td>${{tmStr}}</td>
          <td style="text-align: right;">${{formatKRW(r.base_capex_krw)}}</td>
          <td style="text-align: center;">${{r.base_payback}}</td>
          <td style="text-align: right; color: var(--lge-red);"><strong>${{formatKRW(r.awhp70_capex_krw)}}</strong></td>
          <td style="text-align: center; color: var(--lge-red);"><strong>${{r.awhp70_payback}}</strong></td>
          <td style="text-align: center; font-weight: 600;">${{r.payback_reduction}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Section 11: Scenarios Table Filter
    function filterScenarios() {{
      const hm = document.getElementById("filterHouse").value;
      const hp = document.getElementById("filterHeat").value;
      const tm = document.getElementById("filterTarget").value;
      const oc = document.getElementById("filterOcc").value;

      const filtered = REPORT_DATA.all_scenarios.filter(r => {{
        if (hm && r.house_model !== hm) return false;
        if (hp && !r.heating_package.includes(hp)) return false;
        if (tm && r.target_model !== tm) return false;
        if (oc && Math.abs(r.occupancy_rate - parseFloat(oc)) > 0.001) return false;
        return true;
      }});

      document.getElementById("scenarioCountLabel").innerText = `검색 결과: ${{filtered.length}}건 / 432건`;
      const tbody = document.getElementById("allScenariosBody");
      tbody.innerHTML = "";
      filtered.slice(0, 100).forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{r.scenario_id}}</td>
          <td>${{r.house_model}}</td>
          <td>${{r.heating_package}}</td>
          <td>${{r.ev_count}}대</td>
          <td>${{Math.round(r.occupancy_rate * 100)}}%</td>
          <td>${{r.target_model}}</td>
          <td>${{r.subsidy_applied ? '적용' : '미적용'}}</td>
          <td>${{r.pv_capacity_kw}}</td>
          <td>${{r.ess_capacity_kwh}}</td>
          <td>${{r.pv_land_area_m2}}</td>
          <td style="text-align: right;">${{formatKRW(r.net_capex_krw)}}</td>
          <td style="text-align: center; font-weight: 600;">${{r.payback_str}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Section 12: Render DUO Incremental Table
    function renderDuoIncTable() {{
      const tbody = document.getElementById("duoIncBody");
      tbody.innerHTML = "";
      REPORT_DATA.duomax_incremental.slice(0, 30).forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{r.scenario_id}}</td>
          <td>${{Math.round(r.occupancy_rate * 100)}}%</td>
          <td>${{r.ev_count}}대</td>
          <td>${{r.target_model}}</td>
          <td>${{r.subsidy_applied ? '적용' : '미적용'}}</td>
          <td>${{r.total_pv_kw}} kW</td>
          <td>${{r.total_ess_kwh}} kWh</td>
          <td style="text-align: right;">${{formatKRW(r.incremental_capex_krw)}}</td>
          <td style="text-align: center; font-weight: 600;">${{r.payback_str}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Init All
    window.addEventListener("DOMContentLoaded", () => {{
      populateFindings();
      renderHeroTable();
      switchPeakTab("MONO Core 54");
      renderCriticalDailyChart();
      renderCritical15mChart();
      renderZeroEnergyTable();
      renderZeroBillTable();
      renderNearZeroTable();
      renderHeatmapTable();
      renderSubsidyTable();
      filterScenarios();
      renderDuoIncTable();
    }});
  </script>
</body>
</html>
"""

    out_html_path = report_dir / "LG_SC_Korea_ROI_Report.html"
    with open(out_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated {out_html_path}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    generate_html_report(project_root)
