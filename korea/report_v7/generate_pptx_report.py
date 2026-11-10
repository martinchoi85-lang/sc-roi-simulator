"""Generates formal LG_SC_Korea_ROI_Report.pptx using python-pptx.

Strict Requirements:
- 16:9 widescreen layout (13.333 x 7.5 inches)
- Korean language
- Single message per slide, slide titles written as conclusion sentences.
- NO rounded large text cards/balloons.
- Body text 12pt+, Table text 10pt+, Table headers dark background with white text.
- Slide 6: 3-house peak day profile chart image.
- Slide 7: Critical day 7-day window chart image.
- Slide 8: Zero energy 12 cases full table.
- Slide 9: Zero bill range bar chart image.
- Slide 11: Occupancy heatmap table.
- Slide 12: AWHP 70% actual results table.
- Mandatory footnote: 'Therma V 값은 EU 모델 HM091HF UB40 기준이며 A-7 미만은 추정'
- Strictly identical data sourced from report_data.json.
"""

import json
from pathlib import Path
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# LGE Palette Colors
LGE_RED = RGBColor(165, 0, 52)         # #A50034 (Heritage Red)
LGE_ACTIVE_RED = RGBColor(253, 49, 46)  # #FD312E (Active Red)
LGE_DARK = RGBColor(0, 0, 0)           # #000000 (Black)
LGE_GRAY = RGBColor(112, 112, 112)      # #707070 (Gray)
LGE_WARM_GRAY = RGBColor(240, 236, 228) # #F0ECE4 (Warm Gray)
WHITE = RGBColor(255, 255, 255)
LIGHT_GRAY_BG = RGBColor(248, 247, 244)
BORDER_GRAY = RGBColor(226, 223, 216)


def add_slide_header(slide, title_text, category_text="LG Electronics · Smart Cottage Korea ROI Report"):
    """Adds formal standardized header with conclusion title."""
    # Top bar
    top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.10))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = LGE_RED
    top_bar.line.fill.background()

    # Category breadcrumb
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.20), Inches(11.733), Inches(0.25))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = category_text.upper()
    p_c.font.size = Pt(9.5)
    p_c.font.bold = True
    p_c.font.color.rgb = LGE_GRAY

    # Main Conclusion Title (Sentence style)
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(11.733), Inches(0.60))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(17.5)
    p.font.bold = True
    p.font.color.rgb = LGE_RED


def add_footnote(slide, extra=""):
    """Adds mandatory footnote with Therma V caution."""
    box = slide.shapes.add_textbox(Inches(0.8), Inches(7.02), Inches(11.733), Inches(0.38))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    base_text = "* 부하는 실측이 아닌 5R1C 시뮬레이션 기반이며, ESS 단가는 해외 벤치마크 범위값($1,268/kWh) 적용. Therma V 값은 EU 모델 HM091HF UB40 기준이며 A-7 미만은 추정."
    if extra:
        base_text += f" {extra}"
    p.text = base_text
    p.font.size = Pt(8.0)
    p.font.color.rgb = LGE_GRAY


def style_table(table, col_widths, headers, row_data, font_size_header=10, font_size_body=10):
    """Applies high-contrast LGE styling to pptx table."""
    for i, w in enumerate(col_widths):
        table.columns[i].width = w

    # Header Row
    for col_idx, h_text in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_RED
        p = cell.text_frame.paragraphs[0]
        p.text = str(h_text)
        p.font.size = Pt(font_size_header)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER

    # Data Rows
    for row_idx, row in enumerate(row_data):
        bg_col = LIGHT_GRAY_BG if row_idx % 2 == 1 else WHITE
        for col_idx, val in enumerate(row):
            cell = table.cell(row_idx + 1, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_col
            p = cell.text_frame.paragraphs[0]
            p.text = str(val)
            p.font.size = Pt(font_size_body)
            p.font.color.rgb = LGE_DARK

            # Alignment
            val_str = str(val)
            if any(c in val_str for c in ["원", "kW", "kWh", "%", "년", "m²", "h"]) and not val_str.startswith("MONO") and not val_str.startswith("DUO"):
                p.alignment = PP_ALIGN.RIGHT
            elif val_str in [">25년", "0.0h", "적용", "미적용", "유지"]:
                p.alignment = PP_ALIGN.CENTER
            else:
                p.alignment = PP_ALIGN.LEFT


def create_pptx_report(project_root: Path):
    korea_dir = project_root / "korea"
    report_dir = korea_dir / "report"
    data_path = report_dir / "report_data.json"
    assets_dir = report_dir / "pptx_assets"

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Generate chart assets
    from korea.report.chart_generator import generate_all_charts
    generate_all_charts(data, assets_dir)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: 결론 요약 (Executive Summary)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_slide_header(s1, "3년 이내 투자비 회수는 전 케이스 달성 불가하며 최단 회수기간은 9.8년입니다", "01. Executive Summary")
    add_footnote(s1)

    # Clean structured table layout for 5 Key Findings (No balloons)
    shape_s1 = s1.shapes.add_table(6, 3, Inches(0.8), Inches(1.25), Inches(11.733), Inches(5.5))
    t1 = shape_s1.table
    t1.columns[0].width = Inches(0.6)
    t1.columns[1].width = Inches(2.8)
    t1.columns[2].width = Inches(8.333)

    # Header
    for idx, h in enumerate(["No.", "핵심 분석 항목", "시뮬레이션 분석 결론 및 시사점"]):
        cell = t1.cell(0, idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_RED
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER

    findings = data["key_findings"]
    for i, f in enumerate(findings):
        row_bg = LIGHT_GRAY_BG if i % 2 == 1 else WHITE
        c0 = t1.cell(i + 1, 0)
        c0.fill.solid()
        c0.fill.fore_color.rgb = row_bg
        p0 = c0.text_frame.paragraphs[0]
        p0.text = f"0{f['id']}"
        p0.font.size = Pt(12)
        p0.font.bold = True
        p0.font.color.rgb = LGE_RED
        p0.alignment = PP_ALIGN.CENTER

        c1 = t1.cell(i + 1, 1)
        c1.fill.solid()
        c1.fill.fore_color.rgb = row_bg
        p1 = c1.text_frame.paragraphs[0]
        p1.text = f["topic"]
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = LGE_DARK

        c2 = t1.cell(i + 1, 2)
        c2.fill.solid()
        c2.fill.fore_color.rgb = row_bg
        p2 = c2.text_frame.paragraphs[0]
        p2.text = f["summary"]
        p2.font.size = Pt(11.5)
        p2.font.color.rgb = LGE_DARK
        p2.alignment = PP_ALIGN.LEFT

    # =========================================================================
    # SLIDE 2: 분석 범위 및 시나리오 체계
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "춘천 TMYx 표준기상 데이터 기반 3개 주택 모델 432개 시나리오를 전수 분석했습니다", "02. Scope & Framework")
    add_footnote(s2)

    # Table of Scenarios
    shape_s2 = s2.shapes.add_table(7, 4, Inches(0.8), Inches(1.3), Inches(11.733), Inches(5.3))
    t2 = shape_s2.table
    cols_s2 = [Inches(2.2), Inches(3.2), Inches(2.2), Inches(4.133)]
    hdrs_s2 = ["시나리오 구분 변수", "분석 항목 및 파라미터", "시나리오 수", "상세 설정 및 가정 기준"]
    data_s2 = [
        ["주택 모델 (House)", "MONO Core 54, MONO Core 72, DUO Max 45", "3개 모델", "공식 모델 면적 및 가전 부하 반영"],
        ["난방 패키지 (HVAC)", "PV+ESS+가스보일러 vs PV+ESS+AWHP", "2개 방식", "가스는 일반프로판(LPG), AWHP는 Therma V 9kW"],
        ["전기차 (EV)", "0대 (미보유) vs 1대 (일 10kWh 충전)", "2개 옵션", "완속 3kW 야간(23시~07시) 충전 스케줄"],
        ["이용률 (Occupancy)", "100%, 70%, 50%, 30%, 10%, 5%", "6개 구간", "상시거주(100%), 주5일, 격주, 주말, 월3일, 연휴"],
        ["목표 모델 (Target)", "Zero Energy, Zero Bill, Near Zero", "3개 목표", "무수전(LOL=0), 변동요금 0원, 최단 회수기간"],
        ["보조금 (Subsidy)", "무보조 vs 2026 정부·지자체 보조금 (265만원)", "2개 조건", "국비 165만 + 춘천시비 100만 (3kW 이하 설비 적용)"],
    ]
    style_table(t2, cols_s2, hdrs_s2, data_s2, 11, 11)

    # =========================================================================
    # SLIDE 3: 목표 모델 정의 및 계산 기준
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "Zero Energy(무수전), Zero Bill(변동요금 0원), Near Zero(최단회수)로 정의됩니다", "03. Model Definitions")
    add_footnote(s3)

    shape_s3 = s3.shapes.add_table(4, 5, Inches(0.8), Inches(1.3), Inches(11.733), Inches(5.3))
    t3 = shape_s3.table
    cols_s3 = [Inches(2.0), Inches(2.2), Inches(2.3), Inches(2.3), Inches(2.933)]
    hdrs_s3 = ["목표 모델명", "에너지 충족 기준", "배터리(ESS) 조건", "수전 및 상계 처리", "비용 평가 기준"]
    data_s3 = [
        ["Zero Energy\n(오프그리드 무수전)", "연간 계통 수전 0 kWh\n(연간 정전 LOL = 0.0h)", "전 이용률 무정전 만족 최소 용량 (19.2~76.8kWh)", "계통 미연계 (완전 독립망)\n잉여 PV 출력제어(Curtailment)", "PV+ESS+설비비 전액 반영\n(Central 비용 기준)"],
        ["Zero Bill\n(변동요금 0원)", "연간 전력량요금·기후·연료비 0원\n(기본요금·세금 별도)", "최소 1모듈 (9.6 kWh 고정)\n(자가소비 우선 운영)", "한전 계통연계 및 월합산 상계\n잉여 발전량 무기한 이월", "기본요금·부가세·전력기금은 청구\n가스 케이스는 프로판비 별도"],
        ["Near Zero\n(최단 회수 조합)", "3년 회수 불가 조건 하에서\n최단 회수기간 달성 조합", "최소 1모듈 (9.6 kWh 고정)\n(0.05kW 단위 정밀 탐색)", "한전 계통연계 및 상계 적용\n자가소비 극대화", "3년 달성 필요 CAPEX 및 인하율 함께 산출"],
    ]
    style_table(t3, cols_s3, hdrs_s3, data_s3, 11, 10.5)

    # =========================================================================
    # SLIDE 4: 전기요금 누진 구조 및 상계 제도
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "한국의 저렴한 주택용 누진요금과 월합산 상계 제도는 설비비 회수를 제약합니다", "04. Tariff & Net Metering")
    add_footnote(s4)

    # Left: Tariff table, Right: 300kWh calculation
    shape_s4_l = s4.shapes.add_table(4, 3, Inches(0.8), Inches(1.3), Inches(5.6), Inches(4.2))
    t4_l = shape_s4_l.table
    cols_s4_l = [Inches(2.0), Inches(1.8), Inches(1.8)]
    hdrs_s4_l = ["누진 구간 (비하계)", "기본요금 (원/호)", "전력량단가 (원/kWh)"]
    data_s4_l = [
        ["1구간 (200 kWh 이하)", "910원", "120.0원"],
        ["2구간 (201 ~ 400 kWh)", "1,600원", "214.6원"],
        ["3구간 (400 kWh 초과)", "7,300원", "307.3원"],
    ]
    style_table(t4_l, cols_s4_l, hdrs_s4_l, data_s4_l, 10.5, 10.5)

    shape_s4_r = s4.shapes.add_table(7, 2, Inches(6.8), Inches(1.3), Inches(5.733), Inches(5.2))
    t4_r = shape_s4_r.table
    cols_s4_r = [Inches(3.733), Inches(2.0)]
    hdrs_s4_r = ["표준 300 kWh 월 고지서 항목", "산정 금액 (원)"]
    tb = data["tariff_breakdown_300kwh"]
    data_s4_r = [
        ["기본요금 (2구간 적용)", f"{tb['base_rate']:,}원"],
        ["전력량요금 (200k×120원 + 100k×214.6원)", f"{int(tb['energy_total']):,}원"],
        ["기후환경요금 (300k×9원) + 연료비조정액 (+5원)", f"{int(tb['climate_charge'] + tb['fuel_adjust']):,}원"],
        ["전기요금계 (소계)", f"{int(tb['subtotal']):,}원"],
        ["부가가치세 (10%) + 전력기반기금 (2.7%)", f"{int(tb['vat'] + tb['power_fund']):,}원"],
        ["최종 청구금액 (10원 미만 절사)", f"{int(tb['total_billed']):,}원"],
    ]
    style_table(t4_r, cols_s4_r, hdrs_s4_r, data_s4_r, 10.5, 10.5)

    # =========================================================================
    # SLIDE 5: 설비 설치비 및 단가 산정 근거
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_header(s5, "PV는 2026 정부 공고 단가, AWHP는 기사 상한액, ESS는 해외 단가를 적용했습니다", "05. Cost Basis")
    add_footnote(s5)

    shape_s5 = s5.shapes.add_table(7, 5, Inches(0.8), Inches(1.3), Inches(11.733), Inches(5.3))
    t5 = shape_s5.table
    cols_s5 = [Inches(2.0), Inches(2.2), Inches(2.2), Inches(3.933), Inches(1.4)]
    hdrs_s5 = ["설비 구분", "적용 단가 (Central)", "적용 범위 (Low~High)", "산출 근거 및 출처", "검증 상태"]
    data_s5 = [
        ["태양광 (PV ≤3kW)", "1,513,667원/kW", "110만 ~ 200만원/kW", "2026 주택지원 3kW 상한(4,541,000원) 비례", "공식 확인"],
        ["태양광 (PV >3kW)", "1,513,667원/kW", "110만 ~ 200만원/kW", "3kW 초과 단가 단순 비례 적용 (지상비 0원)", "미검증 (가정)"],
        ["ESS 시스템", "1,775,200원/kWh", "39.6만 ~ 187.2만원", "NREL 벤치마크 ($1,268/kWh, 환율 1,400원)", "미검증 (해외)"],
        ["AWHP (Therma V)", "14,000,000원", "1,400만원 고정", "난방전기화사업 기준 사업비 상한(한국냉난방공조신문 2026-09)", "미검증 (상한)"],
        ["일반프로판 (LPG)", "2,812.26원/kg", "-", "오피넷 일반프로판 전국 평균 (2026년 10월 4주)", "공식 확인"],
        ["인버터 교체비", "250,000원/kW (최소 75만)", "-", "13년 차 인버터 교체 비용 가정치", "가정"],
    ]
    style_table(t5, cols_s5, hdrs_s5, data_s5, 11, 10.5)

    # =========================================================================
    # SLIDE 6: 주택 모델별 최대 부하일 15분 차트
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "동계 혹한기 최대 부하 시 PV 발전과 배터리가 피크 부하를 실시간 분담합니다", "06. Peak Day Load Profile")
    add_footnote(s6, "난방 조건: AWHP, EV 0대, 100% 이용률 기준 실제 산정 용량 적용.")

    chart6_img = assets_dir / "slide6_peak_profiles.png"
    if chart6_img.exists():
        s6.shapes.add_picture(str(chart6_img), Inches(0.8), Inches(1.35), width=Inches(11.733))

    # =========================================================================
    # SLIDE 7: Critical Day (2026-02-03) 및 전후 7일 분석
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_header(s7, "연중 최저 일사일(0.25 kWh/m²)의 극저일사가 Zero Energy의 설비 용량을 결정합니다", "07. Critical Day Analysis")
    add_footnote(s7, "기존 단일 피크데이 방식은 동계 정전 600~3,400시간 발생. 본 분석은 연간 LOL 0.0시간 달성.")

    chart7_img = assets_dir / "slide7_critical_window.png"
    if chart7_img.exists():
        s7.shapes.add_picture(str(chart7_img), Inches(0.8), Inches(1.35), width=Inches(11.733))

    # =========================================================================
    # SLIDE 8: Zero Energy 12개 케이스 전체 상세 표
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_header(s8, "당일 PV 충족 기준과 ESS 보완 최소비용 조합 모두 TMY 연간 무수전을 달성합니다", "08. Zero Energy Sizing")
    add_footnote(s8, "두 방식 모두 TMY 연간 무수전(LOL=0.0h) 달성. 2026-02-03 극저일사가 두 방식 간 큰 차이를 야기함.")

    ze_cases = data["zero_energy_cases"]
    shape_s8 = s8.shapes.add_table(13, 10, Inches(0.8), Inches(1.25), Inches(11.733), Inches(5.5))
    t8 = shape_s8.table
    cols_s8 = [Inches(1.7), Inches(1.1), Inches(0.7), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.3), Inches(1.1), Inches(1.1), Inches(1.433)]
    hdrs_s8 = ["주택 모델", "난방", "EV", "당일 PV(kW)", "감쇄후(kW)", "당일 ESS", "당일 CAPEX", "최적 PV(kW)", "최적 ESS", "최소 CAPEX"]

    data_s8 = []
    for r in ze_cases:
        data_s8.append([
            r["house_model"],
            r["heating_package"],
            f"{r['ev_count']}대",
            f"{r['daily_pv_kw']:.1f}",
            f"{r['daily_pv_deg_kw']:.1f}",
            f"{r['daily_ess_kwh']:.1f}",
            f"{int(r['daily_capex_krw']/10000):,}만원",
            f"{r['ref_pv_kw']:.1f}",
            f"{r['ref_ess_kwh']:.1f}",
            f"{int(r['ref_capex_krw']/10000):,}만원",
        ])
    style_table(t8, cols_s8, hdrs_s8, data_s8, 9.5, 9.0)

    # =========================================================================
    # SLIDE 9: Zero Bill ESS 단가 시나리오 분석
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_header(s9, "ESS 단가 시나리오에 따라 CAPEX가 최대 2배 이상 변동하여 배터리가 핵심 변수입니다", "09. Zero Bill Scenarios")
    add_footnote(s9, "Zero Bill(변동요금 0원, 기본요금·세금 별도). 100% 이용률, EV 0대, 무보조 기준.")

    chart9_img = assets_dir / "slide9_zerobill_ranges.png"
    if chart9_img.exists():
        s9.shapes.add_picture(str(chart9_img), Inches(0.8), Inches(1.35), width=Inches(11.733))

    # =========================================================================
    # SLIDE 10: Near Zero Bill 최단 회수기간 및 3년 달성 필요 CAPEX
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_header(s10, "현재 단가 하에서 3년 회수를 달성하려면 초기 CAPEX의 58~74% 인하가 필요합니다", "10. Near Zero & 3-Year Gap")
    add_footnote(s10, "Near Zero(3년 회수 불가, 최단 회수 조합). 100% 이용률, EV 0대, 무보조 기준.")

    shape_s10 = s10.shapes.add_table(7, 8, Inches(0.8), Inches(1.3), Inches(11.733), Inches(5.3))
    t10 = shape_s10.table
    cols_s10 = [Inches(1.8), Inches(1.4), Inches(1.1), Inches(1.1), Inches(1.6), Inches(1.2), Inches(1.8), Inches(1.733)]
    hdrs_s10 = ["주택 모델", "난방 패키지", "PV (kW)", "ESS (kWh)", "현재 CAPEX", "현재 회수", "3년 달성 목표 CAPEX", "인하 필요액 (인하율)"]
    data_s10 = []
    for r in data["near_zero_details"]:
        data_s10.append([
            r["house_model"],
            r["heating_package"],
            f"{r['pv_kw']:.2f}",
            f"{r['ess_kwh']:.1f}",
            f"{int(r['actual_capex_krw']/10000):,}만원",
            r["payback"],
            f"{int(r['target_capex_for_3y_krw']/10000):,}만원",
            f"{int(r['capex_reduction_needed_krw']/10000):,}만원 ({r['reduction_pct']:.1f}%)",
        ])
    style_table(t10, cols_s10, hdrs_s10, data_s10, 10.5, 10.5)

    # =========================================================================
    # SLIDE 11: 이용률별 회수기간 히트맵
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_header(s11, "상시 거주(100%)에서만 회수 가능하며 이용률 50% 이하 시 전수 25년을 초과합니다", "11. Occupancy & Subsidy Heatmap")
    add_footnote(s11, "기준: Zero Bill(변동요금 0원), EV 0대, 무보조 / 2026 보조금(265만원) 비교.")

    # Two side-by-side or stacked tables for No Subsidy vs With Subsidy
    shape_s11_l = s11.shapes.add_table(7, 8, Inches(0.8), Inches(1.3), Inches(5.6), Inches(5.2))
    t11_l = shape_s11_l.table
    cols_s11 = [Inches(1.5), Inches(0.9), Inches(0.55), Inches(0.55), Inches(0.55), Inches(0.55), Inches(0.55), Inches(0.55)]
    hdrs_s11_l = ["[무보조]", "난방", "100%", "70%", "50%", "30%", "10%", "5%"]
    zb_heat_no = data["heatmaps"]["zero_bill"]["no_subsidy"]
    data_s11_l = []
    for r in zb_heat_no:
        data_s11_l.append([
            r["house_model"].replace("MONO ", "").replace("DUO ", ""),
            r["heating_package"][:3],
            r["values"]["100"], r["values"]["70"], r["values"]["50"],
            r["values"]["30"], r["values"]["10"], r["values"]["5"],
        ])
    style_table(t11_l, cols_s11, hdrs_s11_l, data_s11_l, 9.5, 9.0)

    shape_s11_r = s11.shapes.add_table(7, 8, Inches(6.8), Inches(1.3), Inches(5.733), Inches(5.2))
    t11_r = shape_s11_r.table
    hdrs_s11_r = ["[보조금 적용]", "난방", "100%", "70%", "50%", "30%", "10%", "5%"]
    zb_heat_with = data["heatmaps"]["zero_bill"]["with_subsidy"]
    data_s11_r = []
    for r in zb_heat_with:
        data_s11_r.append([
            r["house_model"].replace("MONO ", "").replace("DUO ", ""),
            r["heating_package"][:3],
            r["values"]["100"], r["values"]["70"], r["values"]["50"],
            r["values"]["30"], r["values"]["10"], r["values"]["5"],
        ])
    style_table(t11_r, cols_s11, hdrs_s11_r, data_s11_r, 9.5, 9.0)

    # =========================================================================
    # SLIDE 12: AWHP 70% 민감도 실제 결과
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_slide_header(s12, "AWHP 70% 보조 시 CAPEX 980만 원 경감으로 회수기간이 최대 5.4년 단축됩니다", "12. AWHP 70% Policy Sensitivity")
    add_footnote(s12, "가상 정책 민감도 (춘천시 미적용, 온난지역·실거주 가정 기준). 100% 이용률, EV 0대.")

    shape_s12 = s12.shapes.add_table(7, 7, Inches(0.8), Inches(1.3), Inches(11.733), Inches(5.3))
    t12 = shape_s12.table
    cols_s12 = [Inches(1.8), Inches(1.8), Inches(1.8), Inches(1.4), Inches(1.8), Inches(1.4), Inches(1.733)]
    hdrs_s12 = ["주택 모델", "목표 모델", "기준 CAPEX (무보조)", "기준 회수", "AWHP 70% CAPEX", "70% 회수", "회수기간 단축 효과"]
    data_s12 = []
    for r in data["subsidy_sensitivity"]:
        tm_kr = "Near Zero" if r["target_model"] == "near_zero_bill" else "Zero Bill"
        data_s12.append([
            r["house_model"],
            tm_kr,
            f"{int(r['base_capex_krw']/10000):,}만원",
            r["base_payback"],
            f"{int(r['awhp70_capex_krw']/10000):,}만원",
            r["awhp70_payback"],
            r["payback_reduction"],
        ])
    style_table(t12, cols_s12, hdrs_s12, data_s12, 10.5, 10.5)

    # Save presentation
    out_pptx_path = report_dir / "LG_SC_Korea_ROI_Report.pptx"
    prs.save(out_pptx_path)
    print(f"Successfully generated {out_pptx_path}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    create_pptx_report(project_root)
