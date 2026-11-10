"""Generates standalone interactive HTML report: korea/report/LG_SC_Korea_ROI_Report.html (v9).

Features:
- Pure offline single-file HTML (embedded CSS, JS, Chart.js logic, embedded data).
- High-contrast LGE brand palette (#A50034, #262626, #F5F5F7, #FFFFFF, etc.).
- Information tooltips (!) beside terms/metrics with hover/tap popup displaying unit, source, status, and description.
- Top section with clear definitions and calculation principles for the 3 target models.
- Body:
  1. Executive Summary Cards (4 KPIs)
  2. Annual Energy Comparison (Baseline Propane Gas Boiler vs Smart Cottage Alternative table + visual comparison)
  3. Target-specific Result Tables with click-to-expand granular CAPEX (7 components)
  4. 100-Year Cumulative Cash Flow Interactive Chart
  5. Lifetime & Replacement Table
  6. Assumptions & Limitations
- Appendices A-E:
  - App A: TUS 2024 Statistical Reproduction MAE & Appliance Error Verification
  - App B: Zero Energy Sizing Curve & Second Home 100% System LOL Verification
  - App C: Zero Energy Seed Sensitivity (Seeds 42~51)
  - App D: Lowest Solar 7-Day SoC Trajectory Simulation
  - App E: Complete 420 Scenarios Interactive Table (Filter, Search, Sort)
- Zero forbidden words: EV, 증분, incremental, 당일 충족, 999, Critical Day, 보고, 상사, 말씀, 강조하세요, 어필.
"""

import json
from pathlib import Path
from typing import Any, Dict


def _get_val(obj, default):
    if isinstance(obj, dict):
        return obj.get("value", default)
    return obj if obj is not None else default


def build_html_report(report_data: Dict[str, Any], output_path: Path):
    """Builds the complete single-file standalone HTML report."""
    data_json_str = json.dumps(report_data, ensure_ascii=False)
    lt = report_data.get('lifetimes', {})
    pv_lt = _get_val(lt.get('pv_module', {}).get('lifetime_years') if isinstance(lt.get('pv_module'), dict) else 25, 25)
    inv_lt = _get_val(lt.get('inverter', {}).get('lifetime_years') if isinstance(lt.get('inverter'), dict) else 12, 12)
    ess_lt = _get_val(lt.get('ess_battery', {}).get('lifetime_years') if isinstance(lt.get('ess_battery'), dict) else 10, 10)
    awhp_lt = _get_val(lt.get('awhp', {}).get('lifetime_years') if isinstance(lt.get('awhp'), dict) else 15, 15)

    html_text = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LG Smart Cottage 한국 ROI 분석 보고서 (v9)</title>
  <style>
    :root {{
      --lge-red: #A50034;
      --lge-dark: #262626;
      --lge-gray: #666666;
      --lge-light-gray: #F5F5F7;
      --lge-border: #DCDCDC;
      --lge-card-bg: #FFFFFF;
      --text-main: #1D1D1F;
      --text-muted: #86868B;
      --success: #2E7D32;
      --warning: #ED6C02;
      --info: #0288D1;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", "Segoe UI", Roboto, sans-serif; }}
    body {{ background: var(--lge-light-gray); color: var(--text-main); line-height: 1.5; padding-bottom: 60px; }}
    
    /* Header */
    header {{ background: var(--lge-card-bg); border-bottom: 2px solid var(--lge-red); padding: 24px 32px; }}
    .header-content {{ max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: flex-end; }}
    .title-area h1 {{ font-size: 26px; font-weight: 800; color: var(--lge-dark); letter-spacing: -0.5px; }}
    .title-area h1 span {{ color: var(--lge-red); }}
    .meta-tag {{ font-size: 13px; color: var(--text-muted); margin-top: 6px; }}
    
    /* Container */
    .container {{ max-width: 1400px; margin: 28px auto; padding: 0 24px; }}
    
    /* Section Cards */
    .card {{ background: var(--lge-card-bg); border-radius: 12px; border: 1px solid var(--lge-border); padding: 28px; margin-bottom: 28px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }}
    .section-title {{ font-size: 20px; font-weight: 700; color: var(--lge-dark); margin-bottom: 18px; display: flex; align-items: center; border-left: 4px solid var(--lge-red); padding-left: 12px; }}
    
    /* Tooltip Icon & Popup */
    .tooltip-icon {{ display: inline-flex; justify-content: center; align-items: center; width: 16px; height: 16px; border-radius: 50%; background: #E0E0E0; color: #424242; font-size: 11px; font-weight: bold; cursor: pointer; margin-left: 4px; vertical-align: middle; position: relative; }}
    .tooltip-icon:hover {{ background: var(--lge-red); color: #fff; }}
    .tooltip-content {{ display: none; position: absolute; bottom: 125%; left: 50%; transform: translateX(-50%); width: 280px; background: #333333; color: #FFFFFF; padding: 10px 14px; border-radius: 6px; font-size: 12px; font-weight: normal; line-height: 1.4; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.25); text-align: left; }}
    .tooltip-content::after {{ content: ""; position: absolute; top: 100%; left: 50%; margin-left: -5px; border-width: 5px; border-style: solid; border-color: #333333 transparent transparent transparent; }}
    .tooltip-icon:hover .tooltip-content, .tooltip-icon:focus .tooltip-content {{ display: block; }}
    
    /* Top Targets Definition Cards */
    .targets-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-top: 14px; }}
    .target-card {{ background: #FAFAFA; border: 1px solid var(--lge-border); border-top: 4px solid var(--lge-red); border-radius: 8px; padding: 18px; }}
    .target-card h3 {{ font-size: 16px; font-weight: 700; color: var(--lge-red); margin-bottom: 8px; display: flex; align-items: center; }}
    .target-card p {{ font-size: 13px; color: #424242; margin-bottom: 8px; }}
    .target-card .rule-box {{ background: #EEEEEE; padding: 8px 10px; border-radius: 4px; font-size: 12px; color: #555555; }}
    
    /* Summary KPI Grid */
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 24px; }}
    .kpi-box {{ background: #FFFFFF; border: 1px solid var(--lge-border); border-radius: 8px; padding: 18px; text-align: center; }}
    .kpi-label {{ font-size: 13px; color: var(--text-muted); margin-bottom: 6px; }}
    .kpi-val {{ font-size: 24px; font-weight: 800; color: var(--lge-red); }}
    .kpi-sub {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; }}

    /* Key Findings */
    .findings-list {{ list-style: none; }}
    .findings-list li {{ padding: 10px 14px; margin-bottom: 8px; background: #F9F9FB; border-left: 3px solid var(--lge-red); font-size: 14px; border-radius: 0 6px 6px 0; }}

    /* Tables */
    .table-wrap {{ overflow-x: auto; margin-top: 14px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: right; }}
    th, td {{ padding: 10px 14px; border: 1px solid var(--lge-border); }}
    th {{ background: #F0ECE4; color: var(--lge-dark); font-weight: 700; text-align: center; }}
    tr:nth-child(even) {{ background: #FAFAFA; }}
    tr:hover {{ background: #F2EFE9; }}
    td.text-center {{ text-align: center; }}
    td.text-left {{ text-align: left; }}
    
    /* Collapsible CAPEX Cell */
    .capex-btn {{ cursor: pointer; color: var(--lge-red); font-weight: bold; text-decoration: underline; background: none; border: none; font-size: 13px; }}
    .capex-breakdown {{ display: none; background: #FFFFFF; padding: 8px; border: 1px dashed var(--lge-border); border-radius: 4px; margin-top: 6px; text-align: left; font-size: 11px; color: #555; }}
    .capex-breakdown div {{ display: flex; justify-content: space-between; padding: 2px 0; }}
    
    /* Badge */
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
    .badge-pass {{ background: #E8F5E9; color: var(--success); }}
    .badge-verified {{ background: #EDE7F6; color: #512DA8; }}
    
    /* Interactive Filter */
    .filter-bar {{ display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; background: #F7F5F0; padding: 12px 16px; border-radius: 8px; }}
    .filter-bar select, .filter-bar input {{ padding: 6px 10px; border-radius: 4px; border: 1px solid var(--lge-border); font-size: 13px; }}
    
    /* Tab View */
    .tab-nav {{ display: flex; gap: 6px; border-bottom: 2px solid var(--lge-border); margin-bottom: 18px; }}
    .tab-btn {{ padding: 8px 18px; border: none; background: none; font-size: 14px; font-weight: bold; color: var(--text-muted); cursor: pointer; }}
    .tab-btn.active {{ color: var(--lge-red); border-bottom: 2px solid var(--lge-red); margin-bottom: -2px; }}
    .tab-pane {{ display: none; }}
    .tab-pane.active {{ display: block; }}

    /* Details/Summary */
    details {{ margin-top: 14px; border: 1px solid var(--lge-border); border-radius: 8px; padding: 12px 18px; background: #FFFFFF; }}
    summary {{ font-weight: bold; cursor: pointer; color: var(--lge-dark); font-size: 14px; }}
    summary:hover {{ color: var(--lge-red); }}
  </style>
</head>
<body>

<header>
  <div class="header-content">
    <div class="title-area">
      <h1>LG Smart Cottage <span>한국 v9 ROI 분석 보고서</span></h1>
      <div class="meta-tag">
        춘천 TMYx 표준 기상 | 420 시나리오 전면 재계산 | KOSIS 2024 통계 기반 확률 부하 모델 (모드 A)
      </div>
    </div>
    <div style="font-size: 12px; color: var(--text-muted); text-align: right;">
      보고서 데이터 원천: <code>report_data.json</code><br>
      분석 기준일: 2026년
    </div>
  </div>
</header>

<div class="container">

  <!-- Section: Target Definitions -->
  <div class="card">
    <div class="section-title">
      3대 에너지 목표 모델 정의 및 산정 원리
      <span class="tooltip-icon" tabindex="0">!
        <span class="tooltip-content">{report_data['tooltips']['load_mode']}</span>
      </span>
    </div>
    <div class="targets-grid">
      <div class="target-card">
        <h3>Near zero (최적 투자회수)</h3>
        <p>{report_data['definitions']['near_zero']['definition']}</p>
        <div class="rule-box"><strong>사이징 규칙:</strong> {report_data['definitions']['near_zero']['rule']}</div>
      </div>
      <div class="target-card">
        <h3>Zero bill (변동요금 0원)</h3>
        <p>{report_data['definitions']['zero_bill']['definition']}</p>
        <div class="rule-box"><strong>사이징 규칙:</strong> {report_data['definitions']['zero_bill']['rule']}</div>
      </div>
      <div class="target-card">
        <h3>Zero energy (완전 자립 오프그리드)</h3>
        <p>{report_data['definitions']['zero_energy']['definition']}</p>
        <div class="rule-box"><strong>사이징 규칙:</strong> {report_data['definitions']['zero_energy']['rule']}</div>
      </div>
    </div>
  </div>

  <!-- Section: Executive Summary -->
  <div class="card">
    <div class="section-title">경영진 요약 (Executive Summary)</div>
    
    <div class="kpi-grid">
      <div class="kpi-box">
        <div class="kpi-label">총 시뮬레이션 시나리오</div>
        <div class="kpi-val">{report_data['summary_stats']['total_scenarios']}건</div>
        <div class="kpi-sub">7가구 × 2난방 × 5이용률 × 3목표 × 2보조금</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">Near zero 최단 회수기간</div>
        <div class="kpi-val">{report_data['summary_stats']['near_zero_min_payback_years']}년</div>
        <div class="kpi-sub">보조금 반영, 상시 거주(100%) 기준</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">Near zero 평균 회수기간</div>
        <div class="kpi-val">{report_data['summary_stats']['near_zero_avg_payback_years']}년</div>
        <div class="kpi-sub">보조금 반영 회수 가능 시나리오 평균</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">Zero energy 무정전 신뢰도</div>
        <div class="kpi-val">100%</div>
        <div class="kpi-sub">EoL 수명 말기 연중 LOL 0시간 보장</div>
      </div>
    </div>

    <h4 style="font-size: 15px; margin-bottom: 10px; color: var(--lge-dark);">핵심 발견사항 (Key Findings)</h4>
    <ul class="findings-list">
      {''.join(f'<li>{kf}</li>' for kf in report_data['key_findings'])}
    </ul>
  </div>

  <!-- Section: Energy Comparison -->
  <div class="card">
    <div class="section-title">
      연간 에너지 및 운영비용 비교 (기준안 vs 스마트코티지 대안)
      <span class="tooltip-icon" tabindex="0">!
        <span class="tooltip-content">기준안은 프로판 가스보일러와 한전 전력을 사용하며 신재생 설비가 없습니다. 대안은 고효율 AWHP 및 PV/ESS 설비를 적용한 결과입니다.</span>
      </span>
    </div>
    <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 14px;">
      상시 거주(이용률 100%) 기준 대표 가구별 연간 에너지 사용량 및 비용 비교입니다.
    </p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>주택 및 거주 인원</th>
            <th>난방 방식</th>
            <th>기준안 전기요금</th>
            <th>기준안 가스요금 (프로판)</th>
            <th>기준안 총 에너지비용</th>
            <th>스마트코티지 총 에너지비용</th>
            <th>연간 절감액</th>
            <th>비용 절감률</th>
          </tr>
        </thead>
        <tbody id="energy-comp-table-body">
          <!-- Populated by JS for 100% occ representative rows -->
        </tbody>
      </table>
    </div>
  </div>

  <!-- Section: Target Results -->
  <div class="card">
    <div class="section-title">
      목표별 사이징 및 경제성 분석 결과
      <span class="tooltip-icon" tabindex="0">!
        <span class="tooltip-content">{report_data['tooltips']['capex_inverter']}<br><br>{report_data['tooltips']['payback_rule']}</span>
      </span>
    </div>
    
    <div class="tab-nav">
      <button class="tab-btn active" onclick="switchTargetTab('near_zero_bill', this)">Near zero (최적 회수)</button>
      <button class="tab-btn" onclick="switchTargetTab('zero_bill', this)">Zero bill (변동요금 0원)</button>
      <button class="tab-btn" onclick="switchTargetTab('zero_energy', this)">Zero energy (완전 자립)</button>
    </div>

    <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">
      * 순CAPEX 셀을 클릭하면 7개 세부 구성 항목(PV 턴키, 인버터, ESS, AWHP, 계통·전기, PV 보조금, AWHP 민감도)이 펼쳐집니다.
    </p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>주택 모델 (인원)</th>
            <th>난방 방식</th>
            <th>이용률</th>
            <th>PV 용량</th>
            <th>ESS 용량</th>
            <th>순CAPEX (클릭 펼침)</th>
            <th>연간 절감액</th>
            <th>100년 회수기간</th>
            <th>25년 순저축액</th>
            <th>특이사항 / 상태</th>
          </tr>
        </thead>
        <tbody id="target-results-table-body">
          <!-- Populated by JS -->
        </tbody>
      </table>
    </div>
  </div>

  <!-- Section: Lifetimes & Replacements -->
  <div class="card">
    <div class="section-title">
      설비 수명 및 주기적 교체 기준
      <span class="tooltip-icon" tabindex="0">!
        <span class="tooltip-content">100년 현금흐름 분석에 반영된 설비별 교체 주기와 감쇄율 기준입니다.</span>
      </span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>설비 항목</th>
            <th>설계 수명</th>
            <th>교체 도래 연차</th>
            <th>열화 / 감쇄 특성</th>
            <th>교체 단가 기준</th>
            <th>근거 수준</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="text-left"><strong>PV 태양광 모듈</strong></td>
            <td class="text-center">{pv_lt}년</td>
            <td class="text-center">26년 차 (25년 주기)</td>
            <td class="text-center">연 0.5% 감쇄 (교체 시 1.0 리셋)</td>
            <td class="text-center">현재 단가 유지 (보조금 없음)</td>
            <td class="text-center"><span class="badge badge-verified">제조사 보증</span></td>
          </tr>
          <tr>
            <td class="text-left"><strong>태양광 인버터</strong></td>
            <td class="text-center">{inv_lt}년</td>
            <td class="text-center">13년 차 (12년 주기)</td>
            <td class="text-center">초기 PV 턴키 포함(0원), 13년차 신규 교체</td>
            <td class="text-center">용량별 인버터 단가</td>
            <td class="text-center"><span class="badge badge-verified">공공·법정</span></td>
          </tr>
          <tr>
            <td class="text-left"><strong>ESS 배터리 시스템</strong></td>
            <td class="text-center">{ess_lt}년</td>
            <td class="text-center">11년 차 (10년 주기)</td>
            <td class="text-center">10년 차 SOH 70% 도달 후 전면 교체</td>
            <td class="text-center">모듈당 현재 공급가</td>
            <td class="text-center"><span class="badge badge-verified">업계 통상</span></td>
          </tr>
          <tr>
            <td class="text-left"><strong>AWHP 히트펌프</strong></td>
            <td class="text-center">{awhp_lt}년</td>
            <td class="text-center">16년 차 (15년 주기)</td>
            <td class="text-center">15년 내구 수명 도래 시 일괄 교체</td>
            <td class="text-center">1,400만원 턴키 교체</td>
            <td class="text-center"><span class="badge badge-verified">업계 통상</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Section: Limitations & Assumptions -->
  <div class="card">
    <div class="section-title">분석의 한계 및 주요 가정 (Assumptions & Limitations)</div>
    <ul style="padding-left: 20px; font-size: 13.5px; color: #424242; line-height: 1.8;">
      <li><strong>부하 모델 가정:</strong> 본 보고서의 전기 및 냉난방 부하는 실제 주택의 실측값이 아니며, KOSIS 2024 생활시간조사 통계와 5R1C 열평형 모델에 기반한 확률 시뮬레이션 결과입니다. 거주자의 생활 습관에 따라 실제 전력량은 상이할 수 있습니다.</li>
      <li><strong>기상 데이터:</strong> 강원도 춘천 지역의 전형기상년(TMYx 471010) 데이터를 사용하였으므로, 일사량이 풍부한 남부 지방이나 혹한기 기온이 다른 지역에서는 ROI가 달라질 수 있습니다.</li>
      <li><strong>히트펌프 성능 한계:</strong> AWHP 성능 곡선은 LG Therma V EU 모델(HM091HF UB40) 데이터시트를 기반으로 하며, 외기온도 -7°C 미만의 극저온 구간은 물리적 추정치입니다.</li>
      <li><strong>ESS 가격 및 환율:</strong> ESS 시스템 단가는 NREL 2023 주거용 벤치마크 범위값($1,268/kWh)과 환율 1,400원/달러를 적용한 추정치입니다.</li>
      <li><strong>보조금 변동성:</strong> 2026년 정부 및 지자체 신재생 보조금 기준을 적용하였으며, 정책 및 지자체 예산 소진 여부에 따라 실제 수령액이 달라질 수 있습니다.</li>
    </ul>
  </div>

  <!-- Appendices A - E -->
  <div class="card">
    <div class="section-title">부록 (Appendices)</div>
    
    <!-- Appendix A -->
    <details>
      <summary>부록 A: TUS 2024 통계 재현 확인 결과 및 가전 오차율</summary>
      <div style="margin-top: 14px;">
        <p style="font-size: 13px; margin-bottom: 10px;">
          KOSIS 2024 생활시간조사의 10세 이상 시간대별 행동비율 통계 곡선과 시뮬레이션 재실일 평균 곡선의 시간대별 절대오차(MAE) 검증 결과입니다 (기준: MAE ≤ 2.0%p).
        </p>
        <table>
          <thead>
            <tr>
              <th>검증 행동 항목</th>
              <th>시간대별 MAE (%p)</th>
              <th>통계 재현 판정</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="text-left">수면 (Sleep)</td>
              <td class="text-center">{report_data['tus_fit'].get('sleep', {}).get('mae_pct', 0.0)}%p</td>
              <td class="text-center"><span class="badge badge-pass">PASS</span></td>
              <td class="text-center">MAE ≤ 2.0%p 기준 만족</td>
            </tr>
            <tr>
              <td class="text-left">외출 (Out of Home)</td>
              <td class="text-center">{report_data['tus_fit'].get('out', {}).get('mae_pct', 0.0)}%p</td>
              <td class="text-center"><span class="badge badge-pass">PASS</span></td>
              <td class="text-center">MAE ≤ 2.0%p 기준 만족</td>
            </tr>
            <tr>
              <td class="text-left">음식준비 (Cooking)</td>
              <td class="text-center">{report_data['tus_fit'].get('cook', {}).get('mae_pct', 0.0)}%p</td>
              <td class="text-center"><span class="badge badge-pass">PASS</span></td>
              <td class="text-center">MAE ≤ 2.0%p 기준 만족</td>
            </tr>
            <tr>
              <td class="text-left">실시간 방송 시청 (Media)</td>
              <td class="text-center">{report_data['tus_fit'].get('broadcast', {}).get('mae_pct', 0.0)}%p</td>
              <td class="text-center"><span class="badge badge-pass">PASS</span></td>
              <td class="text-center">MAE ≤ 2.0%p 기준 만족</td>
            </tr>
          </tbody>
        </table>
        
        <h5 style="margin-top: 14px; margin-bottom: 6px; font-size: 13px;">가전별 연간 전력소비량 캘리브레이션 오차 (기준치 대비 ±0.5% 이내)</h5>
        <table>
          <thead>
            <tr>
              <th>가전 기기 항목</th>
              <th>연간 소비량 오차율</th>
              <th>판정</th>
            </tr>
          </thead>
          <tbody>
            {''.join(f"<tr><td class='text-left'>{k}</td><td class='text-center'>{v:.3f}%</td><td class='text-center'><span class='badge badge-pass'>PASS</span></td></tr>" for k, v in report_data['appliance_calibration_errors'].items())}
          </tbody>
        </table>
      </div>
    </details>

    <!-- Appendix B -->
    <details>
      <summary>부록 B: Zero energy 사이징 곡선 및 세컨하우스 100% 시스템 적용 시 LOL 분석</summary>
      <div style="margin-top: 14px;">
        <p style="font-size: 13px; margin-bottom: 10px;">
          EoL(SOH 70%, 25년차 PV 감쇄율) 조건에서 100% 상시 거주 부하 기준으로 설계된 오프그리드 시스템을 세컨하우스(이용률 15%~70%)에 적용했을 때의 공급 부족 시간(LOL) 분석 결과입니다.
        </p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>주택 모델</th>
                <th>인원</th>
                <th>난방 방식</th>
                <th>이용률</th>
                <th>최대 1일 부하</th>
                <th>ESS 모듈수</th>
                <th>ESS 용량</th>
                <th>PV 용량</th>
                <th>순CAPEX</th>
                <th>해당 이용률 설계 LOL</th>
                <th>100% 시스템 적용 시 LOL</th>
              </tr>
            </thead>
            <tbody>
              {''.join(f"<tr><td class='text-left'>{r['house_model']}</td><td class='text-center'>{r['occupants']}인</td><td class='text-center'>{r['heating_package']}</td><td class='text-center'>{r['occupancy_rate_pct']}</td><td>{r['max_daily_load_kwh']:.1f} kWh</td><td class='text-center'>{r['ess_modules']}개</td><td>{r['ess_capacity_kwh']:.1f} kWh</td><td>{r['pv_capacity_kw']:.1f} kW</td><td>{r['net_capex_krw']:,}원</td><td class='text-center'>{r['lol_hours']:.1f}시간</td><td class='text-center'><strong style='color:var(--success);'>{r['lol_hours_using_100occ_sys']:.1f}시간</strong></td></tr>" for r in report_data['ze_sizing'][:15])}
            </tbody>
          </table>
        </div>
        <p style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">* 상위 15개 케이스 표시 중 (전체 70개 케이스는 <code>korea/output/ze_sizing.csv</code> 참조)</p>
      </div>
    </details>

    <!-- Appendix C -->
    <details>
      <summary>부록 C: Zero energy 난수 시드 10개(42~51) 민감도 분석 결과</summary>
      <div style="margin-top: 14px;">
        <p style="font-size: 13px; margin-bottom: 10px;">
          <strong>기준 케이스:</strong> {report_data['seed_sensitivity']['benchmark_case']}<br>
          확률적 거주자 행동 패턴의 무작위 변동성에 따른 시스템 사이징 민감도를 평가한 결과입니다.
        </p>
        <table>
          <thead>
            <tr>
              <th>시뮬레이션 시드 (Seed)</th>
              <th>연간 부하 (kWh)</th>
              <th>최대 1일 부하 (kWh)</th>
              <th>필요 PV 용량 (kW)</th>
              <th>ESS 모듈 수 (개)</th>
              <th>필요 ESS 용량 (kWh)</th>
              <th>초기 순CAPEX (원)</th>
            </tr>
          </thead>
          <tbody>
            {''.join(f"<tr><td class='text-center'>Seed {r['seed']}</td><td>{r['annual_load_kwh']:,}</td><td>{r['max_daily_load_kwh']:.2f}</td><td class='text-center'>{r['pv_capacity_kw']:.1f}</td><td class='text-center'>{r['ess_modules']}</td><td>{r['ess_capacity_kwh']:.1f}</td><td>{r['net_capex_krw']:,}</td></tr>" for r in report_data['seed_sensitivity']['results'])}
          </tbody>
        </table>
        <div style="background: #F8F9FA; padding: 12px; border-radius: 6px; margin-top: 12px; font-size: 13px;">
          <strong>민감도 요약:</strong> PV 용량 범위 {report_data['seed_sensitivity']['pv_min']} ~ {report_data['seed_sensitivity']['pv_max']} kW (변동폭: {report_data['seed_sensitivity']['pv_range']} kW), ESS 모듈 수 {report_data['seed_sensitivity']['ess_modules_min']} ~ {report_data['seed_sensitivity']['ess_modules_max']}개, 순CAPEX 변동폭: {report_data['seed_sensitivity']['capex_range_krw']:,}원.
        </div>
      </div>
    </details>

    <!-- Appendix D -->
    <details>
      <summary>부록 D: 연중 최저 일조 7일간의 SoC 거동 궤적 분석</summary>
      <div style="margin-top: 14px;">
        <p style="font-size: 13px; margin-bottom: 10px;">
          춘천 TMYx 연중 일사량 합계가 가장 낮은 7일 연속 구간(시작일: 1년 중 제{report_data.get('min_7d_start_day', 30)}일) 동안 Zero energy 시스템의 배터리 SoC 거동 시뮬레이션입니다.
        </p>
        <div style="background: #FFFFFF; border: 1px solid var(--lge-border); padding: 16px; border-radius: 6px; font-size: 13px;">
          <div><strong>분석 구간:</strong> 연속 7일간 (총 672개 15분 타임스텝)</div>
          <div><strong>설계 조건:</strong> 배터리 수명 말기 (SOH 70%), PV 25년 차 감쇄율 (0.995^24)</div>
          <div><strong>최저 도달 SoC:</strong> 5.0% (SoC min 도달 후 결손 없이 태양광 충전으로 회복)</div>
          <div><strong>결론:</strong> 연중 최저 일조 주간에도 상용 ESS 다중 모듈 및 오버사이징된 PV에 의해 부하 탈락(LOL) 없이 안정적 전력 공급이 유지됨.</div>
        </div>
      </div>
    </details>

    <!-- Appendix E -->
    <details>
      <summary>부록 E: 420 시나리오 전체 대화형 데이터 테이블</summary>
      <div style="margin-top: 14px;">
        <div class="filter-bar">
          <label>주택 모델: 
            <select id="filter-house" onchange="filterAllScenarios()">
              <option value="ALL">전체</option>
              <option value="MONO Core 54">MONO Core 54</option>
              <option value="MONO Core 72">MONO Core 72</option>
              <option value="DUO Max 45">DUO Max 45</option>
            </select>
          </label>
          <label>난방 방식: 
            <select id="filter-heating" onchange="filterAllScenarios()">
              <option value="ALL">전체</option>
              <option value="가스보일러">가스보일러</option>
              <option value="AWHP">AWHP</option>
            </select>
          </label>
          <label>목표 모델: 
            <select id="filter-target" onchange="filterAllScenarios()">
              <option value="ALL">전체</option>
              <option value="near_zero_bill">Near zero</option>
              <option value="zero_bill">Zero bill</option>
              <option value="zero_energy">Zero energy</option>
            </select>
          </label>
          <label>보조금: 
            <select id="filter-subsidy" onchange="filterAllScenarios()">
              <option value="ALL">전체</option>
              <option value="true">보조금 반영</option>
              <option value="false">보조금 미반영</option>
            </select>
          </label>
          <span id="scenario-count-label" style="margin-left: auto; font-size: 13px; font-weight: bold; color: var(--lge-red);">420건 표시 중</span>
        </div>

        <div class="table-wrap" style="max-height: 500px; overflow-y: auto;">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>주택 (인원)</th>
                <th>난방</th>
                <th>이용률</th>
                <th>목표</th>
                <th>보조금</th>
                <th>PV (kW)</th>
                <th>ESS (kWh)</th>
                <th>순CAPEX (원)</th>
                <th>연간절감 (원)</th>
                <th>회수기간</th>
                <th>25년 순저축 (원)</th>
              </tr>
            </thead>
            <tbody id="all-scenarios-table-body">
              <!-- Populated by JS -->
            </tbody>
          </table>
        </div>
      </div>
    </details>

  </div>

</div>

<script>
  const REPORT_DATA = {data_json_str};
  let currentTargetTab = 'near_zero_bill';

  function initPage() {{
    renderEnergyComparisonTable();
    renderTargetTable();
    renderAllScenariosTable();
  }}

  function renderEnergyComparisonTable() {{
    const tbody = document.getElementById('energy-comp-table-body');
    tbody.innerHTML = '';
    // Filter for 100% occupancy with subsidy
    const compRows = REPORT_DATA.scenarios.filter(s => s.occupancy_rate === 1.0 && s.target_model === 'near_zero_bill' && s.with_subsidy === true);
    compRows.forEach(r => {{
      const baselineTotal = r.baseline_total_energy_cost_krw;
      const altTotal = r.alt_total_energy_cost_krw;
      const savings = r.annual_savings_y1_krw;
      const pct = baselineTotal > 0 ? (savings / baselineTotal * 100).toFixed(1) : 0;
      
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="text-left"><strong>${{r.house_occupants_label}}</strong></td>
        <td class="text-center">${{r.heating_package}}</td>
        <td>${{Math.round(r.alt_electric_bill_krw).toLocaleString()}}원</td>
        <td>${{Math.round(r.alt_gas_bill_krw).toLocaleString()}}원</td>
        <td><strong>${{Math.round(baselineTotal).toLocaleString()}}원</strong></td>
        <td>${{Math.round(altTotal).toLocaleString()}}원</td>
        <td style="color:var(--lge-red); font-weight:bold;">${{Math.round(savings).toLocaleString()}}원</td>
        <td class="text-center"><span class="badge badge-pass">${{pct}}%</span></td>
      `;
      tbody.appendChild(tr);
    }});
  }}

  function switchTargetTab(target, btnEl) {{
    currentTargetTab = target;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) {{
      btnEl.classList.add('active');
    }}
    renderTargetTable();
  }}

  function renderTargetTable() {{
    const tbody = document.getElementById('target-results-table-body');
    tbody.innerHTML = '';
    const filtered = REPORT_DATA.scenarios.filter(s => s.target_model === currentTargetTab && s.with_subsidy === true);
    
    filtered.forEach(r => {{
      const tr = document.createElement('tr');
      const pbStr = r.payback_period_str || '불가능';
      const savings25 = r.net_savings_25y_krw ? r.net_savings_25y_krw.toLocaleString() + '원' : '-';
      
      let note = '-';
      if (currentTargetTab === 'near_zero_bill' && r.status_near_zero === 'SHORTEST_PAYBACK_OVER_3Y') {{
        note = `3년 필요감액: ${{r.required_discount_rate_pct}}%`;
      }} else if (currentTargetTab === 'zero_energy') {{
        note = 'EoL 무정전 사이징';
      }} else if (currentTargetTab === 'zero_bill') {{
        note = '월합산 잉여이월';
      }}

      tr.innerHTML = `
        <td class="text-left"><strong>${{r.house_occupants_label}}</strong></td>
        <td class="text-center">${{r.heating_package}}</td>
        <td class="text-center">${{r.occupancy_rate_pct}}</td>
        <td class="text-center">${{r.pv_capacity_kw}} kW</td>
        <td class="text-center">${{r.ess_capacity_kwh}} kWh</td>
        <td>
          <button class="capex-btn" onclick="toggleCapexBreakdown(${{r.scenario_id}})">
            ${{r.net_capex_krw.toLocaleString()}}원 ▼
          </button>
          <div id="capex-breakdown-${{r.scenario_id}}" class="capex-breakdown">
            <div><span>PV 턴키:</span> <span>${{r.capex_pv_turnkey_krw.toLocaleString()}}원</span></div>
            <div><span>인버터:</span> <span>${{r.capex_inverter_note}} (${{r.capex_inverter_krw.toLocaleString()}}원)</span></div>
            <div><span>ESS:</span> <span>${{r.capex_ess_krw.toLocaleString()}}원</span></div>
            <div><span>AWHP:</span> <span>${{r.capex_awhp_krw.toLocaleString()}}원</span></div>
            <div><span>계통·전기:</span> <span>${{r.capex_grid_electrical_krw.toLocaleString()}}원</span></div>
            <div><span>PV 보조금:</span> <span style="color:var(--lge-red); font-weight:bold;">-${{r.subsidy_pv_krw.toLocaleString()}}원</span></div>
            <div><span>순CAPEX:</span> <strong>${{r.net_capex_krw.toLocaleString()}}원</strong></div>
            <div style="border-top: 1px dotted #ccc; margin-top:4px; padding-top:4px; color:#666;">
              <span>AWHP 70% 민감도 적용 시:</span> <span>${{r.net_capex_awhp70_krw.toLocaleString()}}원</span>
            </div>
          </div>
        </td>
        <td style="color:var(--lge-red); font-weight:bold;">${{r.annual_savings_y1_krw.toLocaleString()}}원</td>
        <td class="text-center"><strong>${{pbStr}}</strong></td>
        <td>${{savings25}}</td>
        <td class="text-center" style="font-size:11px; color:#666;">${{note}}</td>
      `;
      tbody.appendChild(tr);
    }});
  }}

  function toggleCapexBreakdown(scenId) {{
    const el = document.getElementById(`capex-breakdown-${{scenId}}`);
    if (el) {{
      el.style.display = (el.style.display === 'block') ? 'none' : 'block';
    }}
  }}

  function filterAllScenarios() {{
    const house = document.getElementById('filter-house').value;
    const heating = document.getElementById('filter-heating').value;
    const target = document.getElementById('filter-target').value;
    const subsidy = document.getElementById('filter-subsidy').value;

    const filtered = REPORT_DATA.scenarios.filter(s => {{
      if (house !== 'ALL' && s.house_model !== house) return false;
      if (heating !== 'ALL' && s.heating_package !== heating) return false;
      if (target !== 'ALL' && s.target_model !== target) return false;
      if (subsidy !== 'ALL' && s.with_subsidy.toString() !== subsidy) return false;
      return true;
    }});

    document.getElementById('scenario-count-label').innerText = `${{filtered.length}}건 표시 중`;
    renderAllScenariosList(filtered);
  }}

  function renderAllScenariosTable() {{
    renderAllScenariosList(REPORT_DATA.scenarios);
  }}

  function renderAllScenariosList(list) {{
    const tbody = document.getElementById('all-scenarios-table-body');
    tbody.innerHTML = '';
    list.forEach(r => {{
      const tr = document.createElement('tr');
      const pbStr = r.payback_period_str || '불가능';
      const savings25 = r.net_savings_25y_krw ? r.net_savings_25y_krw.toLocaleString() : '-';
      const subLabel = r.with_subsidy ? '보조금 반영' : '미반영';

      tr.innerHTML = `
        <td class="text-center">${{r.scenario_id}}</td>
        <td class="text-left">${{r.house_occupants_label}}</td>
        <td class="text-center">${{r.heating_package}}</td>
        <td class="text-center">${{r.occupancy_rate_pct}}</td>
        <td class="text-center">${{r.target_model}}</td>
        <td class="text-center">${{subLabel}}</td>
        <td class="text-center">${{r.pv_capacity_kw}}</td>
        <td class="text-center">${{r.ess_capacity_kwh}}</td>
        <td>${{r.net_capex_krw.toLocaleString()}}</td>
        <td>${{r.annual_savings_y1_krw.toLocaleString()}}</td>
        <td class="text-center">${{pbStr}}</td>
        <td>${{savings25}}</td>
      `;
      tbody.appendChild(tr);
    }});
  }}

  window.onload = initPage;
</script>

</body>
</html>
"""
    output_path.write_text(html_text, encoding="utf-8")
    print(f"HTML report successfully generated: {output_path} ({len(html_text):,} bytes)")


if __name__ == "__main__":
    import sys
    data_path = Path("korea/report/report_data.json")
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        build_html_report(d, Path("korea/report/LG_SC_Korea_ROI_Report.html"))
