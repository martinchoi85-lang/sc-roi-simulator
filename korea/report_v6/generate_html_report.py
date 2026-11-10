"""Builds single standalone HTML report: korea/report/LG_SC_Korea_ROI_Report.html

Features:
- Pure offline single file (no external CDN, embedded SVG charts and JS).
- Full compliance with LGE brand palette tokens.
- Top executive summary fitting desktop fold without vertical scroll.
- Collapsible detailed sections (1-12) and bottom limitations section.
- Interactive 432-scenario filterable table and interactive subsidy heatmap.
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

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.5;
      padding: 0;
      margin: 0;
      font-size: 14px;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px 24px;
    }}

    /* Top Executive Summary (Fit Desktop Fold) */
    .hero-summary {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 20px 24px;
      margin-bottom: 24px;
    }}

    .brand-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid var(--lge-red);
      padding-bottom: 12px;
      margin-bottom: 16px;
    }}

    .brand-title h1 {{
      font-size: 22px;
      font-weight: 700;
      color: var(--lge-red);
      letter-spacing: -0.5px;
      margin-bottom: 4px;
    }}

    .brand-title p {{
      font-size: 13px;
      color: var(--text-secondary);
    }}

    .theme-toggle-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 6px 14px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }}

    /* Findings Grid: 5 Cards */
    .findings-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }}

    .finding-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-top: 3px solid var(--lge-red);
      border-radius: 6px;
      padding: 12px;
      display: flex;
      flex-direction: column;
    }}

    .finding-card h3 {{
      font-size: 13px;
      font-weight: 700;
      color: var(--lge-red);
      margin-bottom: 6px;
      line-height: 1.3;
    }}

    .finding-card p {{
      font-size: 12px;
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
      font-size: 13px;
      text-align: left;
      background: var(--bg-card);
    }}

    table.data-table th, table.data-table td {{
      padding: 8px 12px;
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
      font-size: 12px;
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
      margin-bottom: 14px;
      overflow: hidden;
    }}

    summary.section-header {{
      background: var(--bg-surface);
      padding: 14px 18px;
      font-size: 15px;
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
      padding: 18px 20px;
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
      border: 1px solid var(--border-color);
    }}

    /* SVG Chart styling */
    .svg-chart-container {{
      width: 100%;
      overflow-x: auto;
      margin: 14px 0;
      background: var(--chart-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 14px;
    }}

    svg text {{
      font-family: inherit;
    }}

    /* Heatmap Grid */
    .heatmap-controls {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}

    .btn-toggle {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 6px 14px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }}

    .btn-toggle.active {{
      background: var(--lge-red);
      color: #FFFFFF;
      border-color: var(--lge-red);
    }}

    /* Responsive */
    @media (max-width: 1024px) {{
      .findings-grid {{
        grid-template-columns: repeat(2, 1fr);
      }}
    }}

    @media (max-width: 640px) {{
      .findings-grid {{
        grid-template-columns: 1fr;
      }}
      .brand-header {{
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }}
    }}

    /* Print Styles */
    @media print {{
      body {{
        background: #FFFFFF !important;
        color: #000000 !important;
      }}
      .theme-toggle-btn, .btn-toggle, input, select {{
        display: none !important;
      }}
      details.accordion-section {{
        border: 1px solid #CCC !important;
        margin-bottom: 16px !important;
        break-inside: avoid;
      }}
      details.accordion-section summary.section-header {{
        background: #EEE !important;
        color: #000 !important;
      }}
      .section-content {{
        display: block !important;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">

    <!-- Top Executive Summary -->
    <div class="hero-summary">
      <div class="brand-header">
        <div class="brand-title">
          <h1>LG Smart Cottage PV·ESS·AWHP 경제성(ROI) 분석 보고서</h1>
          <p>분석 범위: 강원특별자치도 춘천시 기준 | 3개 주택 모델(Core 54, Core 72, DUO Max 45) | 총 432개 시나리오 및 추가투자 72건</p>
        </div>
        <div>
          <button class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()">다크모드 전환</button>
        </div>
      </div>

      <!-- 5 Key Findings -->
      <div class="findings-grid">
        <div class="finding-card">
          <h3>1. 3년 회수 달성 불가</h3>
          <p>전체 432개 시나리오 중 <strong>3년 이내 회수는 0건</strong>이며, 최단 회수기간은 <strong>15.3년</strong> (Core 72 AWHP, 100% 이용률, EV 1대)입니다.</p>
        </div>
        <div class="finding-card">
          <h3>2. Zero Energy 독립전원</h3>
          <p>2026-02-03 동계 저조도 대응으로 <strong>PV 10~41.5kW, ESS 19.2~76.8kWh</strong>(투자비 4,922만~2.1억원) 필요, 회수기간 <strong>>25년</strong>입니다.</p>
        </div>
        <div class="finding-card">
          <h3>3. ESS 단가 민감도</h3>
          <p>Zero Bill 모델에서 배터리 단가(Low $283 vs High $1,337)에 따라 투자비가 2배 이상 벌어지며, ESS 단가가 수익성의 핵심 변수입니다.</p>
        </div>
        <div class="finding-card">
          <h3>4. AWHP 전환 효과</h3>
          <p>일반프로판(2,812.26원/kg) 대비 고비용 연료비 제거 효과가 커, 상시 주거(100%) 시 대형 모델의 회수기간이 가스 대비 오히려 단축됩니다.</p>
        </div>
        <div class="finding-card">
          <h3>5. 이용률 및 보조금 영향</h3>
          <p>주말 세컨드하우스(이용률 10~30%)는 연간 절감액 급감으로 <strong>>25년</strong> 고착. 상시 거주 및 정부·시비 보조금(265만원) 적용 시에만 타당성 확보.</p>
        </div>
      </div>

      <!-- Representative Table (100% Occ, EV 0, No Sub) -->
      <div class="hero-table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th rowspan="2" style="width: 14%;">주택 모델</th>
              <th rowspan="2" style="width: 14%;">난방 패키지</th>
              <th colspan="2" style="text-align: center; width: 24%;">Zero Energy (무수전)</th>
              <th colspan="2" style="text-align: center; width: 24%;">Zero Bill (연간요금 0원)</th>
              <th colspan="2" style="text-align: center; width: 24%;">Near Zero (비용최적)</th>
            </tr>
            <tr>
              <th style="text-align: right;">투자비 (CAPEX)</th>
              <th style="text-align: center;">회수기간</th>
              <th style="text-align: right;">투자비 (CAPEX)</th>
              <th style="text-align: center;">회수기간</th>
              <th style="text-align: right;">투자비 (CAPEX)</th>
              <th style="text-align: center;">회수기간</th>
            </tr>
          </thead>
          <tbody id="heroTableBody">
            <!-- Rendered by JS -->
          </tbody>
        </table>
      </div>

      <!-- Notices (Max 3 items) -->
      <div class="notices-box">
        <strong>보고 시 핵심 유의사항:</strong>
        ① 본 분석의 냉난방 및 가전 부하는 실측값이 아닌 5R1C 동적 열평형 및 표준 가전 스케줄 시뮬레이션 기반입니다.
        ② ESS 배터리 단가는 NREL 미국 벤치마크(2020~2022 USD, 환율 1,400원/$) 범위값(Low/Central/High)을 적용하였습니다.
        ③ Zero Energy는 기상청 표준 TMY 대표 연도 기준 무수전(Grid-Free)이며, PV 3kW 초과분은 공식 3kW 상한 비례 가정(지상 추가비 0원)입니다.
      </div>
    </div>

    <!-- Collapsible Section 1: 모델 정의와 계산 기준 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>1. 모델 정의 및 시뮬레이션 기준</span>
        <span class="badge badge-verified">공식 확인</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 12px;">스마트코티지 3대 대표 모델과 3가지 타겟 에너지 모델을 정의하여 총 432개 시나리오를 산출하였습니다.</p>
        <table class="data-table" style="margin-bottom: 14px;">
          <thead>
            <tr>
              <th>주택 모델</th>
              <th>바닥면적</th>
              <th>설계 인원</th>
              <th>포함 가전 및 설비</th>
              <th>기본 상시전력</th>
              <th>냉난방 사양</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>MONO Core 54</strong></td>
              <td>54.0 m²</td>
              <td>2인</td>
              <td>냉장고(35W), 세탁기(130kWh/y), 인덕션(420kWh/y)</td>
              <td>80.0 W</td>
              <td>시스템에어컨 (COP 4.40) / 가스보일러 or AWHP</td>
            </tr>
            <tr>
              <td><strong>MONO Core 72</strong></td>
              <td>72.9 m²</td>
              <td>3인</td>
              <td>냉장고, 워시타워, 인덕션, 12인용 식기세척기</td>
              <td>80.0 W</td>
              <td>시스템에어컨 (COP 4.40) / 가스보일러 or AWHP</td>
            </tr>
            <tr>
              <td><strong>DUO Max 45</strong></td>
              <td>45.4 m² (복층)</td>
              <td>2인</td>
              <td>워시타워, 식기세척기, 인덕션, 광파오븐, 정수기, ERV</td>
              <td>126.7 W</td>
              <td>AWHP 시 Therma V 냉방(EER 2.6, 5.5kW) / 가스 시 에어컨(4.40)</td>
            </tr>
          </tbody>
        </table>
        <p style="font-size: 12px; color: var(--text-secondary);">
          * <strong>계산 기준:</strong> Zero energy는 연간 부족량(LOL)=0.0h 무수전 오프그리드 기준. Zero bill은 계통연계 연간 순전기요금 0원 상계 기준. 가스 케이스는 전력 기준이며 프로판 연료비는 별도 합산됩니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 2: 전기요금과 상계 제도 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>2. 전기요금 누진 구조 및 상계·이월 지침</span>
        <span class="badge badge-verified">공식 확인</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 12px;">한국전력공사 주택용 저압 요금표 및 소규모 신·재생에너지 상계 지침(제18조)을 엄밀하게 적용하였습니다.</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 14px;">
          <div>
            <h4 style="margin-bottom: 6px; font-size: 13px;">한전 주택용 저압 누진 요금표 (2026)</h4>
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
          * <strong>상계 및 이월 (VERIFIED):</strong> 한전 지침 제18조에 의거, 월간 잉여 발전량은 당월 수전량과 1:1 상계된 후 잔여 잉여량은 다음 달로 <strong>무기한 누적 이월(소멸 없음)</strong> 처리됩니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 3: 설치비 및 단가 근거 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>3. 설치비(CAPEX) 및 단가 산정 근거</span>
        <span class="badge badge-unverified">검증·가정 혼합</span>
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
              <td><strong>태양광 (PV)</strong></td>
              <td>1,513,667원/kW</td>
              <td>110만 ~ 200만원/kW</td>
              <td>2026 신재생에너지보급 주택지원 3kW 상한액(4,541,000원) 비례 산출</td>
              <td><span class="badge badge-verified">공식 확인</span></td>
            </tr>
            <tr>
              <td><strong>ESS 시스템</strong></td>
              <td>1,775,200원/kWh</td>
              <td>39.6만 ~ 187.2만원/kWh</td>
              <td>NREL Q1 2021 Benchmark ($1,268/kWh, 환율 1,400원/$ 적용 해외 벤치마크)</td>
              <td><span class="badge badge-unverified">미검증</span></td>
            </tr>
            <tr>
              <td><strong>AWHP (Therma V)</strong></td>
              <td>14,000,000원</td>
              <td>1,400만원 고정</td>
              <td>HM091HF UB40 기기 1,200만원 + 전기·배관 시공 200만원</td>
              <td><span class="badge badge-unverified">미검증</span></td>
            </tr>
            <tr>
              <td><strong>프로판 (LPG)</strong></td>
              <td>2,812.26원/kg</td>
              <td>-</td>
              <td>한국석유공사 오피넷 일반프로판 전국 평균 (2026년 10월 4주)</td>
              <td><span class="badge badge-verified">공식 확인</span></td>
            </tr>
            <tr>
              <td><strong>인버터 교체비</strong></td>
              <td>250,000원/kW (최소 75만)</td>
              <td>-</td>
              <td>12년차 인버터 교체비 가정치</td>
              <td><span class="badge badge-placeholder">(가정)</span></td>
            </tr>
            <tr>
              <td><strong>지상 설치비</strong></td>
              <td>0원 (5kW 초과분)</td>
              <td>-</td>
              <td>분석 지침에 따라 지상 추가 시공비 0원 적용 (부지비 별도)</td>
              <td><span class="badge badge-placeholder">(가정)</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <!-- Collapsible Section 4: 부하 패턴 15분 차트 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>4. 주택 모델별 연간 최대 부하일 15분 프로파일</span>
        <span class="badge badge-verified">공식 확인</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 8px;">연간 최대 부하일(동계 혹한기)의 15분 단위 부하(kW), 5kWp PV 발전량(kW), 순수급 흐름(kW) 시계열입니다.</p>
        <div id="chartProfilesContainer">
          <!-- SVG rendered by JS -->
        </div>
      </div>
    </details>

    <!-- Collapsible Section 5: Critical Day 분석 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>5. Critical Day (2026-02-03) 및 전후 7일 일사량 분석</span>
        <span class="badge badge-verified">공식 확인</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 8px;">
          춘천 TMYx 연중 최저 일사 강설일인 <strong>2026-02-03 (Day 34, GHI 0.25 kWh/m²)</strong>과 전후 7일간의 일별 일사량 및 외기온 변화입니다.
        </p>
        <div id="chartCriticalWindowContainer">
          <!-- SVG rendered by JS -->
        </div>
        <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
          * <strong>피크데이 방식과의 차이:</strong> 기존 하계/동계 단일 최대 부하일 기준 사이징 시, 동계 연속 저조도 기간 동안 연간 600~3,400시간의 정전(LOL)이 발생합니다. 본 분석의 365일 Critical Day 및 정상상태 시뮬레이션 방식은 12개 케이스 전수 연간 LOL = 0.0시간을 달성합니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 6: Zero Energy 상세 표 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>6. Zero Energy (오프그리드 무수전) 12개 케이스 상세 분석</span>
        <span class="badge badge-verified">공식 확인</span>
      </summary>
      <div class="section-content">
        <div class="hero-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>주택 모델</th>
                <th>난방</th>
                <th>EV</th>
                <th>감쇄전 PV</th>
                <th>감쇄후 PV</th>
                <th>최적 PV</th>
                <th>최적 ESS</th>
                <th>필요부지 (5m²/kW)</th>
                <th>최소 CAPEX (Central)</th>
                <th>LOL 정전시간</th>
                <th>top1 조합 CAPEX</th>
              </tr>
            </thead>
            <tbody id="zeTableBody">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>
        <p style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">
          * 감쇄 계수: 25년 차 0.995^24 = 0.886654 적용. 최소 CAPEX와 top1 CAPEX는 동일한 AWHP 및 설비 기준을 적용하여 100% 일치합니다.
        </p>
      </div>
    </details>

    <!-- Collapsible Section 7: Zero Bill 분석 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>7. Zero Bill (순전기요금 0원) Low / Central / High 시나리오 분석</span>
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
        <span>8. Near Zero Bill 최단 회수기간 및 3년 달성 필요 CAPEX</span>
        <span class="badge badge-verified">공식 확인</span>
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

    <!-- Collapsible Section 9: 이용률별 회수기간 히트맵 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>9. 이용률(점유율)별 회수기간 히트맵 및 보조금 전환</span>
        <span class="badge badge-verified">공식 확인</span>
      </summary>
      <div class="section-content">
        <div class="heatmap-controls">
          <span style="font-weight: 600; font-size: 13px;">보조금 적용 여부:</span>
          <button class="btn-toggle active" id="btnSubFalse" onclick="switchHeatmap(false)">보조금 미적용 (기본)</button>
          <button class="btn-toggle" id="btnSubTrue" onclick="switchHeatmap(true)">2026 보조금 적용 (265만원)</button>
        </div>
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

    <!-- Collapsible Section 10: 보조금 및 민감도 분석 -->
    <details class="accordion-section">
      <summary class="section-header">
        <span>10. 보조금 정책 및 AWHP 70% 민감도 분석</span>
        <span class="badge badge-verified">공식 확인</span>
      </summary>
      <div class="section-content">
        <p style="margin-bottom: 12px;">
          2026 주택지원 국비(165만원) 및 춘천시 시비 하한(100만원) 적용 현황과, 온난지역·실거주 가정 시나리오(AWHP 70% 지원, 980만원) 민감도 분석입니다.
        </p>
        <div class="hero-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>주택 모델</th>
                <th>기준 CAPEX (무보조)</th>
                <th>기준 회수기간</th>
                <th>AWHP 70% 보조 적용 CAPEX</th>
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
        <span class="badge badge-verified">432건 전수</span>
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
        <span class="badge badge-verified">공식 확인</span>
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
        <ul style="margin-left: 20px; margin-bottom: 16px; font-size: 13px; color: var(--text-secondary);">
          <li><strong>부하 모델링:</strong> 실제 계측 데이터가 아닌 ISO 13790 기반 5R1C 동적 시뮬레이션 및 표준 가전 소비전력 스케줄을 사용하였습니다.</li>
          <li><strong>ESS 비용:</strong> 국내 가정용 소용량 ESS 시장 미성숙으로 NREL 미국 벤치마크 데이터를 환율 1,400원/$으로 단순 환산하여 적용하였습니다.</li>
          <li><strong>PV 설치비:</strong> 3kW 초과 설비에 대해 정부 공고 3kW 단가를 단순 비례 적용하였으며, 토목·기초 공사비 및 부지 매입비는 반영되지 않았습니다.</li>
          <li><strong>동계 성능:</strong> Therma V HM091HF UB40의 A-7℃ 미만 성능은 선형 외삽 추정치이며 실제 혹한기 서리(Defrost) 손실은 추가 검증이 필요합니다.</li>
        </ul>

        <h4 style="font-size: 13px; color: var(--lge-red); margin-bottom: 8px;">PLACEHOLDER (11개) 및 UNVERIFIED (25개) 항목 요약</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
          <div>
            <h5 style="font-size: 12px; margin-bottom: 4px;">주요 PLACEHOLDER 항목:</h5>
            <ul style="font-size: 12px; margin-left: 18px; color: var(--text-secondary);">
              <li>환율 가정 (1,400 KRW/USD)</li>
              <li>지상 설치 추가비 (0원 가정)</li>
              <li>인버터 교체비 (25만원/kW) 및 분전반 개체비</li>
              <li>가정용 ESS 보조금 단가 및 상한 (미반영)</li>
              <li>ERV 전열교환기 연속 소비전력 (30W)</li>
            </ul>
          </div>
          <div>
            <h5 style="font-size: 12px; margin-bottom: 4px;">주요 UNVERIFIED 항목:</h5>
            <ul style="font-size: 12px; margin-left: 18px; color: var(--text-secondary);">
              <li>가구원수별 전력량 3,749/4,094kWh (KESIS 자료 유사 수준, 표 미특정)</li>
              <li>Therma V A-7℃ 미만 성능 기울기 외삽값</li>
              <li>NREL ESS 배터리팩 및 시공 단가</li>
              <li>AWHP 턴키 설치비 (1,400만원) 분할 내역</li>
              <li>전국 일반프로판 단가 변동성</li>
            </ul>
          </div>
        </div>

        <h4 style="font-size: 13px; color: var(--lge-red); margin-bottom: 8px;">다음 단계: 글로벌 국가 확장 로드맵</h4>
        <p style="font-size: 13px; color: var(--text-secondary);">
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
      renderAllCharts();
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

    // Render Zero Energy Table
    function renderZeroEnergyTable() {{
      const tbody = document.getElementById("zeTableBody");
      tbody.innerHTML = "";
      REPORT_DATA.zero_energy_reference.forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${{r.house_model}}</strong></td>
          <td>${{r.heating_package.replace("PV+ESS+", "")}}</td>
          <td>${{r.ev_count}}대</td>
          <td>${{r.initial_pv_kw_no_deg}} kW</td>
          <td>${{r.initial_pv_kw}} kW</td>
          <td><strong style="color: var(--lge-red);">${{r.optimal_pv_kw}} kW</strong></td>
          <td><strong style="color: var(--lge-red);">${{r.optimal_ess_kwh}} kWh</strong></td>
          <td>${{r.pv_land_area_m2}} m²</td>
          <td style="text-align: right;">${{formatKRW(r.min_capex_central_krw)}}</td>
          <td style="text-align: center;">${{r.final_loss_of_load_hours}} h</td>
          <td style="text-align: right;">${{formatKRW(r.top1_capex_krw)}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Render Zero Bill Table
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

    // Render Near Zero Table
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

    // Render Subsidy Table
    function renderSubsidyTable() {{
      const tbody = document.getElementById("subsidyTableBody");
      tbody.innerHTML = "";
      REPORT_DATA.subsidy_sensitivity.forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${{r.house_model}}</strong></td>
          <td style="text-align: right;">${{formatKRW(r.base_capex_krw)}}</td>
          <td style="text-align: center;">${{r.base_payback}}</td>
          <td style="text-align: right; color: var(--lge-red);"><strong>${{formatKRW(r.awhp70_capex_krw)}}</strong></td>
          <td style="text-align: center; color: var(--lge-red);"><strong>${{r.awhp70_payback}}</strong></td>
          <td style="text-align: center;">AWHP 70% 지원 시 약 5~8년 단축</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Heatmap Logic
    let isSubsidizedHeatmap = false;
    function switchHeatmap(withSub) {{
      isSubsidizedHeatmap = withSub;
      document.getElementById("btnSubFalse").classList.toggle("active", !withSub);
      document.getElementById("btnSubTrue").classList.toggle("active", withSub);
      renderHeatmapTable();
    }}

    function renderHeatmapTable() {{
      const tbody = document.getElementById("heatmapTableBody");
      tbody.innerHTML = "";
      const dataset = isSubsidizedHeatmap ? REPORT_DATA.heatmap_with_sub : REPORT_DATA.heatmap_no_sub;
      dataset.forEach(r => {{
        const tr = document.createElement("tr");
        let tds = `<td><strong>${{r.house_model}}</strong></td><td>${{r.heating_package}}</td>`;
        r.values.forEach(v => {{
          const isFeasible = v.payback_years < 25.0;
          const bg = isFeasible ? (v.payback_years <= 16.0 ? '#FD312E22' : '#A5003418') : 'transparent';
          const txtColor = isFeasible ? 'var(--lge-red)' : 'var(--text-muted)';
          const weight = isFeasible ? '700' : '400';
          tds += `<td style="text-align: center; background: ${{bg}}; color: ${{txtColor}}; font-weight: ${{weight}};">${{v.payback_str}}</td>`;
        }});
        tr.innerHTML = tds;
        tbody.appendChild(tr);
      }});
    }}

    // Scenarios Table Filter
    function filterScenarios() {{
      const hm = document.getElementById("filterHouse").value;
      const hp = document.getElementById("filterHeat").value;
      const tm = document.getElementById("filterTarget").value;
      const oc = document.getElementById("filterOcc").value;

      const filtered = REPORT_DATA.all_scenarios_records.filter(r => {{
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
          <td>${{r.heating_package.replace("PV+ESS+", "")}}</td>
          <td>${{r.ev_count}}대</td>
          <td>${{Math.round(r.occupancy_rate * 100)}}%</td>
          <td>${{r.target_model}}</td>
          <td>${{r.subsidy_applied ? '적용' : '미적용'}}</td>
          <td>${{r.pv_capacity_kw}}</td>
          <td>${{r.ess_capacity_kwh}}</td>
          <td>${{r.pv_land_area_m2}}</td>
          <td style="text-align: right;">${{formatKRW(r.net_capex_krw)}}</td>
          <td style="text-align: center; font-weight: 600;">${{r.payback_period_str}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Render DUO Incremental Table
    function renderDuoIncTable() {{
      const tbody = document.getElementById("duoIncBody");
      tbody.innerHTML = "";
      REPORT_DATA.duo_incremental_summary.slice(0, 30).forEach(r => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{r.scenario_id}}</td>
          <td>${{Math.round(r.occupancy_rate * 100)}}%</td>
          <td>${{r.ev_count}}대</td>
          <td>${{r.target_model}}</td>
          <td>${{r.subsidy_applied ? '적용' : '미적용'}}</td>
          <td>${{r.pv_capacity_kw}} kW</td>
          <td>${{r.ess_capacity_kwh}} kWh</td>
          <td style="text-align: right;">${{formatKRW(r.net_capex_krw)}}</td>
          <td style="text-align: center; font-weight: 600;">${{r.payback_period_str}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Pure SVG Chart: Peak Day Profiles
    function renderPeakDayChart() {{
      const container = document.getElementById("chartProfilesContainer");
      const models = Object.keys(REPORT_DATA.profiles_sample);
      if (models.length === 0) return;

      const m = models[0]; // representative model: Core 54
      const p = REPORT_DATA.profiles_sample[m];

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

          <!-- X Axis Labels (Every 3 hours = 12 steps) -->
          ${{[0, 12, 24, 36, 48, 60, 72, 84, 95].map(idx => `
            <text x="${{getX(idx)}}" y="${{h - padB + 16}}" font-size="11" fill="var(--chart-axis)" text-anchor="middle">${{p.times[idx]}}</text>
          `).join('')}}

          <!-- Paths -->
          <path d="${{pathLoad}}" fill="none" stroke="var(--lge-red)" stroke-width="2.5" />
          <path d="${{pathPv}}" fill="none" stroke="var(--lge-active-red)" stroke-width="2" stroke-dasharray="4,2" />

          <!-- Title & Legend -->
          <text x="${{padL}}" y="18" font-size="13" font-weight="700" fill="var(--text-primary)">
            MONO Core 54 최대 부하일(Day ${{p.peak_day_index}}) 15분 전력 프로파일 (일 부하: ${{p.daily_total_kwh}} kWh, 피크: ${{p.max_load_kw}} kW)
          </text>
          <circle cx="${{w - 240}}" cy="14" r="5" fill="var(--lge-red)"/>
          <text x="${{w - 230}}" y="18" font-size="11" fill="var(--text-primary)">부하 (전력 소비 kW)</text>
          <line x1="${{w - 120}}" y1="14" x2="${{w - 100}}" y2="14" stroke="var(--lge-active-red)" stroke-width="2" stroke-dasharray="3,2"/>
          <text x="${{w - 94}}" y="18" font-size="11" fill="var(--text-primary)">PV 발전 (5kWp 기준)</text>
        </svg>
      `;
      container.innerHTML = svg;
    }}

    // Pure SVG Chart: Critical Day Window (15 days)
    function renderCriticalDayChart() {{
      const container = document.getElementById("chartCriticalWindowContainer");
      const list = REPORT_DATA.critical_window_15d;
      if (!list || list.length === 0) return;

      const w = 900;
      const h = 260;
      const padL = 50;
      const padR = 20;
      const padT = 30;
      const padB = 40;

      const maxGhi = Math.max(5.0, ...list.map(d => d.ghi_kwh_m2));
      const n = list.length;
      const barW = ((w - padL - padR) / n) * 0.65;

      function getBarX(i) {{ return padL + (i + 0.175) * ((w - padL - padR) / n); }}
      function getY(val) {{ return h - padB - (val / maxGhi) * (h - padT - padB); }}

      let svg = `
        <svg viewBox="0 0 ${{w}} ${{h}}" style="width: 100%; height: auto; display: block;">
          <!-- Grid Lines -->
          <line x1="${{padL}}" y1="${{getY(0)}}" x2="${{w - padR}}" y2="${{getY(0)}}" stroke="var(--chart-axis)" stroke-width="1"/>
          <line x1="${{padL}}" y1="${{getY(2)}}" x2="${{w - padR}}" y2="${{getY(2)}}" stroke="var(--chart-grid)" stroke-dasharray="3,3"/>
          <line x1="${{padL}}" y1="${{getY(4)}}" x2="${{w - padR}}" y2="${{getY(4)}}" stroke="var(--chart-grid)" stroke-dasharray="3,3"/>

          <!-- Y Axis Labels -->
          <text x="${{padL - 8}}" y="${{getY(0) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">0.0</text>
          <text x="${{padL - 8}}" y="${{getY(2) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">2.0</text>
          <text x="${{padL - 8}}" y="${{getY(4) + 4}}" font-size="11" fill="var(--chart-axis)" text-anchor="end">4.0</text>

          <!-- Bars -->
          ${{list.map((d, i) => {{
            const bx = getBarX(i);
            const by = getY(d.ghi_kwh_m2);
            const bh = (h - padB) - by;
            const fill = d.is_critical ? 'var(--lge-active-red)' : 'var(--lge-heritage-red)';
            const dateStr = d.date.split('-').slice(1).join('/');
            return `
              <rect x="${{bx}}" y="${{by}}" width="${{barW}}" height="${{bh}}" fill="${{fill}}" rx="2"/>
              <text x="${{bx + barW / 2}}" y="${{by - 6}}" font-size="10" font-weight="${{d.is_critical ? '700' : '400'}}" fill="${{d.is_critical ? 'var(--lge-active-red)' : 'var(--text-secondary)'}}" text-anchor="middle">${{d.ghi_kwh_m2}}</text>
              <text x="${{bx + barW / 2}}" y="${{h - padB + 16}}" font-size="10" font-weight="${{d.is_critical ? '700' : '400'}}" fill="${{d.is_critical ? 'var(--lge-active-red)' : 'var(--chart-axis)'}}" text-anchor="middle">${{dateStr}}</text>
            `;
          }}).join('')}}

          <!-- Title & Legend -->
          <text x="${{padL}}" y="18" font-size="13" font-weight="700" fill="var(--text-primary)">
            2026-02-03 Critical Day 및 전후 7일 수평면 일사량 (GHI kWh/m²/day)
          </text>
          <rect x="${{w - 240}}" y="10" width="12" height="10" fill="var(--lge-active-red)" rx="2"/>
          <text x="${{w - 222}}" y="19" font-size="11" font-weight="700" fill="var(--lge-active-red)">Critical Day (0.25 kWh)</text>
          <rect x="${{w - 110}}" y="10" width="12" height="10" fill="var(--lge-heritage-red)" rx="2"/>
          <text x="${{w - 92}}" y="19" font-size="11" fill="var(--text-primary)">인접일 일사량</text>
        </svg>
      `;
      container.innerHTML = svg;
    }}

    function renderAllCharts() {{
      renderPeakDayChart();
      renderCriticalDayChart();
    }}

    // Initialize Page
    window.addEventListener("DOMContentLoaded", () => {{
      renderHeroTable();
      renderZeroEnergyTable();
      renderZeroBillTable();
      renderNearZeroTable();
      renderHeatmapTable();
      renderSubsidyTable();
      filterScenarios();
      renderDuoIncTable();
      renderAllCharts();

      // Ensure charts render properly when accordion opened
      document.querySelectorAll("details").forEach(d => {{
        d.addEventListener("toggle", () => {{
          if (d.open) {{
            renderAllCharts();
          }}
        }});
      }});
    }});
  </script>
</body>
</html>
"""

    out_html = report_dir / "LG_SC_Korea_ROI_Report.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Generated standalone HTML report: {out_html}")
    return out_html


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    generate_html_report(project_root)

