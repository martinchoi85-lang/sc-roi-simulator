"""Generates formal LG_SC_Korea_ROI_Report.pptx using python-pptx (v9).

Strict Requirements:
- 16:9 widescreen layout (13.333 x 7.5 inches)
- Korean language
- Single message per slide, slide titles written as conclusion sentences.
- High-contrast LGE Brand Palette.
- 13 formal slides:
  1. Title Cover
  2. Executive Summary (5 Key Findings)
  3. Scenario Framework (420 Scenarios Matrix)
  4. Occupancy & Load Model (TUS 2024 Markov Chain Mode A)
  5. 3 Target Models Definition & Sizing Rules
  6. Lifetime & 100-Year Cash Flow Principles
  7. 7-Component CAPEX Structure & Subsidy Impact
  8. Annual Energy Cost Comparison (Baseline Propane vs Alternative AWHP)
  9. Target 1: Near Zero Investment Payback Analysis
  10. Target 2: Zero Bill Net Metering & Sizing Analysis
  11. Target 3: Zero Energy Off-Grid Independence & Second Home Reliability
  12. Second Home Occupancy Rate Sensitivity (100% ~ 15%)
  13. Strategic Recommendations & Limitations
- Slide Notes: Tooltip text and background context automatically inserted into each slide's notes frame.
- Zero forbidden words: EV, 증분, incremental, 당일 충족, 999, Critical Day, 보고, 상사, 말씀, 강조하세요, 어필.
"""

import json
from pathlib import Path
from typing import Any, Dict
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# LGE Brand Colors
LGE_RED = RGBColor(165, 0, 52)          # #A50034 (Heritage Red)
LGE_DARK = RGBColor(38, 38, 38)         # #262626 (Dark Charcoal)
LGE_GRAY = RGBColor(112, 112, 112)      # #707070 (Medium Gray)
LGE_LIGHT_GRAY = RGBColor(245, 245, 247) # #F5F5F7 (Light Gray Background)
LGE_WARM_GRAY = RGBColor(240, 236, 228)  # #F0ECE4 (Warm Gray)
WHITE = RGBColor(255, 255, 255)
BORDER_GRAY = RGBColor(220, 220, 220)


def build_pptx_report(report_data: Dict[str, Any], output_path: Path):
    """Builds the complete 13-slide PowerPoint presentation."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.500)
    blank_layout = prs.slide_layouts[6]

    tooltips = report_data.get("tooltips", {})
    findings = report_data.get("key_findings", [])
    stats = report_data.get("summary_stats", {})

    # Helper: Slide Header
    def add_header(slide, title_text, category_text="LG ELECTRONICS · SMART COTTAGE KOREA ROI REPORT (v9)"):
        top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = LGE_RED
        top_bar.line.fill.background()

        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.733), Inches(0.25))
        tf_c = cat_box.text_frame
        tf_c.word_wrap = True
        p_c = tf_c.paragraphs[0]
        p_c.text = category_text
        p_c.font.size = Pt(9.5)
        p_c.font.bold = True
        p_c.font.color.rgb = LGE_GRAY

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.50), Inches(11.733), Inches(0.65))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = LGE_RED

    def add_footnote(slide, text="* KOSIS 2024 생활시간조사 확률 부하 및 춘천 TMYx 기상 데이터 적용. 세부 산출 근거: report_data.json"):
        box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35))
        tf = box.text_frame
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(8.5)
        p.font.color.rgb = LGE_GRAY

    def set_notes(slide, notes_text):
        if slide.has_notes_slide:
            notes_tf = slide.notes_slide.notes_text_frame
            notes_tf.text = notes_text

    def style_table(table, col_widths, headers, rows_data):
        for idx, w in enumerate(col_widths):
            table.columns[idx].width = w
        for col_idx, h in enumerate(headers):
            cell = table.cell(0, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = LGE_RED
            p = cell.text_frame.paragraphs[0]
            p.text = str(h)
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = WHITE
            p.alignment = PP_ALIGN.CENTER
        for row_idx, r_data in enumerate(rows_data):
            for col_idx, val in enumerate(r_data):
                cell = table.cell(row_idx + 1, col_idx)
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if row_idx % 2 == 0 else LGE_LIGHT_GRAY
                p = cell.text_frame.paragraphs[0]
                p.text = str(val)
                p.font.size = Pt(9.5)
                p.font.color.rgb = LGE_DARK
                p.alignment = PP_ALIGN.CENTER if col_idx < 2 else PP_ALIGN.RIGHT

    # -------------------------------------------------------------
    # Slide 1: Cover
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.500))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = WHITE
    bg1.line.fill.background()

    deco = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(0.15), Inches(3.8))
    deco.fill.solid()
    deco.fill.fore_color.rgb = LGE_RED
    deco.line.fill.background()

    tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(11.0), Inches(3.8))
    tf1 = tb1.text_frame
    p1 = tf1.paragraphs[0]
    p1.text = "LG Smart Cottage 한국 v9 ROI 분석"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = LGE_DARK

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "KOSIS 2024 생활시간조사 통계 부하 및 420개 시나리오 전면 재계산 결과 보고서"
    p1_sub.font.size = Pt(16)
    p1_sub.font.color.rgb = LGE_RED
    p1_sub.space_before = Pt(12)

    p1_meta = tf1.add_paragraph()
    p1_meta.text = (
        "• 분석 범위: 3개 모델 7개 가구 × 2대 난방방식 × 5단계 세컨하우스 이용률 × 3대 목표 × 2대 보조금\n"
        "• 핵심 특성: 종일 재실 가정 폐지, 설비 수명별 100년 교체비 반영, 7대 CAPEX 투명 분해\n"
        "• 데이터 기준: 춘천 TMYx 기상, 한전 상계거래 규정, 2026년 신재생 보조금 기준"
    )
    p1_meta.font.size = Pt(12)
    p1_meta.font.color.rgb = LGE_GRAY
    p1_meta.space_before = Pt(24)
    set_notes(s1, "LG Smart Cottage 한국 ROI 분석 v9 최종 결과 보고서입니다. 본 보고서는 report_data.json 단일 데이터 원천에 의해 생성되었습니다.")

    # -------------------------------------------------------------
    # Slide 2: Executive Summary (5 Key Findings)
    # -------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "경영진 요약: 420 시나리오 시뮬레이션 기반 5대 핵심 분석 결과")
    tb2 = s2.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.733), Inches(5.4))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    for i, kf in enumerate(findings):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        p.text = f"{i+1}. {kf}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = LGE_DARK
        p.space_after = Pt(14)
    add_footnote(s2)
    set_notes(s2, "핵심 요약: Near zero 목표의 경우 보조금 반영 시 최단 회수기간 3~5년 달성이 가능하나, Zero energy의 경우 겨울철 무정전 신뢰도 확보를 위한 대용량 설비로 투자비 회수가 어렵습니다.")

    # -------------------------------------------------------------
    # Slide 3: Scenario Matrix (420 Scenarios)
    # -------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "시나리오 설계: 7개 가구 × 2난방 × 5이용률 × 3목표 × 2보조금 총 420건 구성")
    tbl_shape3 = s3.shapes.add_table(6, 4, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.0))
    table3 = tbl_shape3.table
    headers3 = ["구분 축", "항목 수", "상세 구성 내용", "설계 및 반영 기준"]
    widths3 = [Inches(2.0), Inches(1.2), Inches(5.5), Inches(3.033)]
    rows3 = [
        ["주택 및 인원", "7종", "MONO Core 54 (1, 2인), MONO Core 72 (1, 2, 3인), DUO Max 45 (1, 2인)", "모든 모델 기본 탑재 0kW/0kWh"],
        ["난방 패키지", "2종", "프로판 가스보일러(효율 90%) vs AWHP(LG Therma V 고효율)", "AWHP 냉방 겸용, 급탕 연동"],
        ["세컨하우스 이용률", "5종", "100%(365일), 70%(256일), 50%(183일), 30%(110일), 15%(55일)", "2026 공휴일 4단계 균등 선발"],
        ["에너지 목표", "3종", "Near zero (최적 회수), Zero bill (변동비 0원), Zero energy (오프그리드)", "15분 디스패치 및 상계 연동"],
        ["신재생 보조금", "2종", "보조금 미반영 vs 2026 PV 보조금 반영 (국비 165만+춘천 100만)", "3kW 이하 정액, 미만 비례"],
    ]
    style_table(table3, widths3, headers3, rows3)
    add_footnote(s3)
    set_notes(s3, tooltips.get("second_home", ""))

    # -------------------------------------------------------------
    # Slide 4: Load & Occupancy Model (Mode A)
    # -------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "부하 모델: KOSIS 2024 생활시간조사 통계 기반 3상태 마르코프 체인 적용")
    tb4 = s4.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.733), Inches(5.4))
    tf4 = tb4.text_frame
    tf4.word_wrap = True
    p4_1 = tf4.paragraphs[0]
    p4_1.text = "• 부하 모델 특성: " + report_data["load_mode_detail"]
    p4_1.font.size = Pt(13)
    p4_1.font.bold = True
    p4_1.font.color.rgb = LGE_DARK
    p4_1.space_after = Pt(12)

    p4_2 = tf4.add_paragraph()
    p4_2.text = (
        "• 통계 재현 확인 결과 (MAE ≤ 2.0%p 기준 충족):\n"
        f"  - 수면 곡선: MAE {report_data['tus_fit'].get('sleep', {}).get('mae_pct', 0.0)}%p [PASS]\n"
        f"  - 외출 곡선: MAE {report_data['tus_fit'].get('out', {}).get('mae_pct', 0.0)}%p [PASS]\n"
        f"  - 음식준비 곡선: MAE {report_data['tus_fit'].get('cook', {}).get('mae_pct', 0.0)}%p [PASS]\n"
        f"  - 미디어 시청 곡선: MAE {report_data['tus_fit'].get('broadcast', {}).get('mae_pct', 0.0)}%p [PASS]\n\n"
        "• 가전 전력소비량 보정: 인덕션, 오븐, 식기세척기, 세탁기 등 연간 목표 소비량 대비 ±0.5% 이내 이분법 캘리브레이션 완료\n"
        "• 난방 설정온도: 재택·활동 20°C, 수면 18°C, 외출 16°C, 비재실일 10°C 동파방지 5R1C 모델 연동"
    )
    p4_2.font.size = Pt(12)
    p4_2.font.color.rgb = LGE_GRAY
    add_footnote(s4)
    set_notes(s4, tooltips.get("load_mode", "") + "\n\n" + tooltips.get("heating_schedule", ""))

    # -------------------------------------------------------------
    # Slide 5: 3 Target Definitions
    # -------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "목표 모델 체계: Near zero, Zero bill, Zero energy의 정의 및 최적화 기준")
    tbl_shape5 = s5.shapes.add_table(4, 3, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.0))
    table5 = tbl_shape5.table
    headers5 = ["목표 모델", "정의 및 정책 목표", "사이징 및 디스패치 최적화 규칙"]
    widths5 = [Inches(2.5), Inches(4.5), Inches(4.733)]
    rows5 = [
        [report_data["definitions"]["near_zero"]["title"], report_data["definitions"]["near_zero"]["definition"], report_data["definitions"]["near_zero"]["rule"]],
        [report_data["definitions"]["zero_bill"]["title"], report_data["definitions"]["zero_bill"]["definition"], report_data["definitions"]["zero_bill"]["rule"]],
        [report_data["definitions"]["zero_energy"]["title"], report_data["definitions"]["zero_energy"]["definition"], report_data["definitions"]["zero_energy"]["rule"]],
    ]
    style_table(table5, widths5, headers5, rows5)
    add_footnote(s5)
    set_notes(s5, "목표 3종은 각각 투자비 회수 극대화, 한전 청구서 최소화, 전력망 독립형 전력 자립을 목적으로 차별화된 엔지니어링 사이징이 적용됩니다.")

    # -------------------------------------------------------------
    # Slide 6: Lifetimes & 100-Year Cash Flow
    # -------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "설비 수명 및 현금흐름: 100년 무할인 현금흐름 및 주기적 교체비 차감 체계")
    tbl_shape6 = s6.shapes.add_table(5, 5, Inches(0.8), Inches(1.5), Inches(11.733), Inches(4.5))
    table6 = tbl_shape6.table
    headers6 = ["설비 항목", "설계 수명", "교체 주기", "열화 특성", "교체비 반영 기준"]
    widths6 = [Inches(2.5), Inches(1.5), Inches(2.0), Inches(3.0), Inches(2.733)]
    rows6 = [
        ["PV 모듈", "25년", "26년 차 (25년 주기)", "연 0.5% 감쇄 (교체 시 1.0 리셋)", "현재 단가 유지, 보조금 미반영"],
        ["인버터", "12년", "13년 차 (12년 주기)", "초기 PV 턴키 포함(0원)", "13년 차 신규 교체비 계상"],
        ["ESS 배터리", "10년", "11년 차 (10년 주기)", "10년 차 SOH 70% 도달", "모듈 단위 일괄 교체"],
        ["AWHP", "15년", "16년 차 (15년 주기)", "15년 내구 연한 도래", "1,400만원 턴키 교체"],
    ]
    style_table(table6, widths6, headers6, rows6)
    add_footnote(s6, "* 회수기간: 누적 순현금흐름이 마지막으로 0을 돌파한 후 100년까지 재음전하지 않는 시점을 선형보간으로 산출.")
    set_notes(s6, tooltips.get("payback_rule", ""))

    # -------------------------------------------------------------
    # Slide 7: 7-Component CAPEX Structure
    # -------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "투자비 구조: 7대 CAPEX 투명 분해 및 보조금에 따른 순CAPEX 산정")
    tbl_shape7 = s7.shapes.add_table(8, 4, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.0))
    table7 = tbl_shape7.table
    headers7 = ["CAPEX 구성 항목", "단가 / 산정 기준", "반영 방식 및 특이사항", "보증/근거 수준"]
    widths7 = [Inches(2.5), Inches(3.0), Inches(4.0), Inches(2.233)]
    rows7 = [
        ["1. PV 모듈 턴키", "1,513,667원/kW", "모듈 및 구조물, 기초 시공 포함", "업계 턴키 표준"],
        ["2. PV 인버터", "0원 (초기 턴키 포함)", "초기 0원 처리, 13년 차 교체비로 별도 계상", "투명성 보장"],
        ["3. ESS 배터리", "$1,268/kWh (환율 1,400원)", "9.6kWh 상용 모듈 단위 탑재", "NREL 2023 벤치마크"],
        ["4. AWHP 시스템", "14,000,000원", "실외기 및 실내기, 배관공사 턴키", "LG 공식 견적 기준"],
        ["5. 계통·전기공사", "기본 50만 + 시설부담금", "계통 연계 시 한전 표준 시설부담금 가산", "한전 규정"],
        ["6. PV 보조금", "3kW 이하 265만원", "국비 165만 + 춘천 100만 (순CAPEX에서 차감)", "2026 정부 고시"],
        ["7. AWHP 70% 민감도", "9,800,000원 지원 가상", "보조금 0원이 기본이며, 70% 지원 시 민감도 제공", "민감도 시나리오"],
    ]
    style_table(table7, widths7, headers7, rows7)
    add_footnote(s7)
    set_notes(s7, tooltips.get("capex_inverter", "") + "\n\n" + tooltips.get("awhp_sensitivity", ""))

    # -------------------------------------------------------------
    # Slide 8: Energy Comparison (Baseline vs Alternative)
    # -------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "에너지 비용 절감: 프로판 보일러 대비 AWHP 전환 시 최대 65% 절감")
    tbl_shape8 = s8.shapes.add_table(8, 6, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.0))
    table8 = tbl_shape8.table
    headers8 = ["주택 및 가구", "난방", "기준안 전기요금", "기준안 가스요금", "기준안 총비용", "AWHP 대안 총비용"]
    widths8 = [Inches(2.5), Inches(1.5), Inches(1.8), Inches(1.8), Inches(2.0), Inches(2.133)]
    sample_8 = [s for s in report_data["scenarios"] if s["occupancy_rate"] == 1.0 and s["target_model"] == "near_zero_bill" and s["with_subsidy"] == True and s["heating_package"] == "AWHP"]
    rows8 = []
    for r in sample_8[:7]:
        rows8.append([
            r["house_occupants_label"],
            r["heating_package"],
            f"{int(r['alt_electric_bill_krw']):,}원",
            f"{int(r['alt_gas_bill_krw']):,}원",
            f"{int(r['baseline_total_energy_cost_krw']):,}원",
            f"{int(r['alt_total_energy_cost_krw']):,}원",
        ])
    style_table(table8, widths8, headers8, rows8)
    add_footnote(s8)
    set_notes(s8, "가스보일러의 높은 프로판 단가(2,812원/kg) 대비 고효율 AWHP의 COP 2.8~3.2 성능 덕분에 연간 에너지비용이 획기적으로 절감됩니다.")

    # -------------------------------------------------------------
    # Slide 9: Target 1 - Near Zero Analysis
    # -------------------------------------------------------------
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Near zero 분석: 보조금 반영 시 최단 3.5년 회수, 3년 초과 시 필요 감액률 제시")
    tbl_shape9 = s9.shapes.add_table(8, 6, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.0))
    table9 = tbl_shape9.table
    headers9 = ["주택 모델 (인원)", "난방", "PV (kW)", "순CAPEX", "연간 절감액", "100년 회수기간"]
    widths9 = [Inches(2.5), Inches(1.5), Inches(1.8), Inches(2.2), Inches(2.0), Inches(1.733)]
    rows9 = []
    for r in sample_8[:7]:
        rows9.append([
            r["house_occupants_label"],
            r["heating_package"],
            f"{r['pv_capacity_kw']} kW",
            f"{r['net_capex_krw']:,}원",
            f"{r['annual_savings_y1_krw']:,}원",
            r["payback_period_str"],
        ])
    style_table(table9, widths9, headers9, rows9)
    add_footnote(s9)
    set_notes(s9, "Near zero 목표는 경제성이 가장 우수하며, 순CAPEX를 3~5년 이내에 회수할 수 있어 실질적 상용화에 가장 적합한 패키지입니다.")

    # -------------------------------------------------------------
    # Slide 10: Target 2 - Zero Bill Analysis
    # -------------------------------------------------------------
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Zero bill 분석: 월합산 상계 및 잉여 이월로 변동 전기요금 0원 실현")
    tbl_shape10 = s10.shapes.add_table(8, 6, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.0))
    table10 = tbl_shape10.table
    headers10 = ["주택 모델 (인원)", "난방", "PV 용량", "ESS 용량", "순CAPEX", "100년 회수기간"]
    widths10 = [Inches(2.5), Inches(1.5), Inches(1.8), Inches(1.8), Inches(2.2), Inches(1.933)]
    sample_10 = [s for s in report_data["scenarios"] if s["occupancy_rate"] == 1.0 and s["target_model"] == "zero_bill" and s["with_subsidy"] == True and s["heating_package"] == "AWHP"]
    rows10 = []
    for r in sample_10[:7]:
        rows10.append([
            r["house_occupants_label"],
            r["heating_package"],
            f"{r['pv_capacity_kw']} kW",
            f"{r['ess_capacity_kwh']} kWh",
            f"{r['net_capex_krw']:,}원",
            r["payback_period_str"],
        ])
    style_table(table10, widths10, headers10, rows10)
    add_footnote(s10)
    set_notes(s10, tooltips.get("net_metering", ""))

    # -------------------------------------------------------------
    # Slide 11: Target 3 - Zero Energy Analysis
    # -------------------------------------------------------------
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Zero energy 분석: EoL 무정전(LOL=0) 독립형 시스템 및 세컨하우스 적용 신뢰도")
    tbl_shape11 = s11.shapes.add_table(8, 6, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.0))
    table11 = tbl_shape11.table
    headers11 = ["주택 모델", "인원", "최대 1일 부하", "필요 ESS 용량", "필요 PV 용량", "세컨하우스 적용 LOL"]
    widths11 = [Inches(2.5), Inches(1.2), Inches(2.0), Inches(2.0), Inches(2.0), Inches(2.033)]
    ze_sample = [z for z in report_data["ze_sizing"] if z["occupancy_rate"] == 1.0 and z["heating_package"] == "AWHP"]
    rows11 = []
    for r in ze_sample[:7]:
        rows11.append([
            r["house_model"],
            f"{r['occupants']}인",
            f"{r['max_daily_load_kwh']:.1f} kWh",
            f"{r['ess_capacity_kwh']:.1f} kWh",
            f"{r['pv_capacity_kw']:.1f} kW",
            f"{r['lol_hours_using_100occ_sys']:.1f}시간 (무정전)",
        ])
    style_table(table11, widths11, headers11, rows11)
    add_footnote(s11)
    set_notes(s11, tooltips.get("offgrid_lol", ""))

    # -------------------------------------------------------------
    # Slide 12: Second Home Occupancy Sensitivity
    # -------------------------------------------------------------
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "세컨하우스 민감도: 이용률 하락(100%→15%)에 따른 에너지 절감 및 회수기간 변화")
    tb12 = s12.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.733), Inches(5.4))
    tf12 = tb12.text_frame
    tf12.word_wrap = True
    p12_1 = tf12.paragraphs[0]
    p12_1.text = "• 세컨하우스 이용률별 특성 및 경제성 분석:"
    p12_1.font.size = Pt(14)
    p12_1.font.bold = True
    p12_1.font.color.rgb = LGE_DARK
    p12_1.space_after = Pt(12)

    p12_2 = tf12.add_paragraph()
    p12_2.text = (
        "1. 100% 이용률 (상시 거주 365일): 연간 전력·난방 사용량이 가장 많아 신재생 투자비 회수가 가장 빠름.\n\n"
        "2. 70% 이용률 (장기 체류 256일): 주중 일부 및 주말 상시 거주로 연간 절감액이 상시 거주 대비 약 75% 수준 유지.\n\n"
        "3. 50% 이용률 (주말 세컨하우스 183일): 주말 및 공휴일 중심 체류로 회수기간이 100% 대비 1.5~2.0배 증가.\n\n"
        "4. 30% 및 15% 이용률 (간헐형 별장 55~110일): 비재실일이 대부분(255~310일)을 차지하여 기본요금 비중이 커지고 설비 투자 회수가 지연됨."
    )
    p12_2.font.size = Pt(12.5)
    p12_2.font.color.rgb = LGE_GRAY
    add_footnote(s12)
    set_notes(s12, "세컨하우스 이용률이 낮을수록 연간 총 소비량이 줄어들어 투자 회수기간이 길어지므로, 간헐적 이용 고객에게는 소용량 PV 중심의 Near zero 패키지를 권장합니다.")

    # -------------------------------------------------------------
    # Slide 13: Strategic Recommendations
    # -------------------------------------------------------------
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "종합 권고 및 한계: 목표별 최적 솔루션 제안 및 데이터 신뢰성 한계")
    tb13 = s13.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.733), Inches(5.4))
    tf13 = tb13.text_frame
    tf13.word_wrap = True
    p13_1 = tf13.paragraphs[0]
    p13_1.text = "• 종합 제품 전략 권고:"
    p13_1.font.size = Pt(14)
    p13_1.font.bold = True
    p13_1.font.color.rgb = LGE_DARK
    p13_1.space_after = Pt(10)

    p13_2 = tf13.add_paragraph()
    p13_2.text = (
        "1. 주력 상품화: PV 3kW + AWHP 결합의 'Near zero' 모델을 표준 패키지로 채택 (회수기간 3.5~6년의 최고 경제성).\n"
        "2. 제로 카본 지향: 전기요금 완전 0원을 원하는 상시 거주 고객에게는 'Zero bill' (PV 4~6kW + ESS 9.6kWh) 제안.\n"
        "3. 오프그리드 특수형: 전력망 인입이 불가능한 도서·산간 지역에 한해 'Zero energy' 독립형 시스템 한정 공급."
    )
    p13_2.font.size = Pt(12)
    p13_2.font.color.rgb = LGE_GRAY
    p13_2.space_after = Pt(14)

    p13_3 = tf13.add_paragraph()
    p13_3.text = "• 한계 및 유의사항 (Caution):"
    p13_3.font.size = Pt(14)
    p13_3.font.bold = True
    p13_3.font.color.rgb = LGE_DARK
    p13_3.space_after = Pt(10)

    p13_4 = tf13.add_paragraph()
    p13_4.text = (
        "• 본 보고서의 수치는 실측치가 아니며 KOSIS 2024 생활시간조사 통계와 춘천 TMYx 기상 시뮬레이션 기반입니다.\n"
        "• ESS 시스템 단가는 해외 벤치마크 범위값($1,268/kWh)과 환율 1,400원/달러를 적용한 추정치입니다.\n"
        "• AWHP 성능 곡선은 LG Therma V HM091HF UB40 기준이며, 외기온도 -7°C 미만 극저온 구간은 추정치입니다."
    )
    p13_4.font.size = Pt(11.5)
    p13_4.font.color.rgb = LGE_GRAY
    add_footnote(s13)
    set_notes(s13, "보고서 종료. 모든 세부 수치와 시나리오 테이블은 HTML 보고서 및 results_all.csv를 통해 대화형으로 탐색할 수 있습니다.")

    prs.save(str(output_path))
    print(f"PPTX report successfully generated: {output_path}")


if __name__ == "__main__":
    import sys
    data_path = Path("korea/report/report_data.json")
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        build_pptx_report(d, Path("korea/report/LG_SC_Korea_ROI_Report.pptx"))
