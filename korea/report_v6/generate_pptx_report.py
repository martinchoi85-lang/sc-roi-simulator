"""Generates LG_SC_Korea_ROI_Report.pptx using python-pptx.

Requirements:
- 16:9 widescreen layout (13.333 x 7.5 inches)
- Korean language
- Body: 12 slides exactly
  1 결론 요약 / 2 분석 범위 / 3 모델 정의 / 4 요금과 상계 / 5 비용 근거
  6 부하 패턴 / 7 Critical day / 8 Zero energy / 9 Zero bill / 10 Near zero
  11 이용률 히트맵 / 12 보조금과 민감도
- Appendix: 대표 요약표, DUO Max incremental, 가정과 PLACEHOLDER/UNVERIFIED 목록
- 100% strict adherence to report_data.json and LGE Color Palette tokens
- Common required notices in footnotes
"""

import json
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE


# LGE Palette Colors
LGE_RED = RGBColor(165, 0, 52)        # #A50034 (Heritage Red)
LGE_ACTIVE_RED = RGBColor(253, 49, 46) # #FD312E (Active Red)
LGE_DARK = RGBColor(0, 0, 0)          # #000000 (Black)
LGE_GRAY = RGBColor(112, 112, 112)     # #707070 (Gray)
LGE_WARM_GRAY = RGBColor(240, 236, 228)# #F0ECE4 (Warm Gray)
WHITE = RGBColor(255, 255, 255)
DARK_BORDER = RGBColor(220, 218, 212)
LIGHT_ROW_BG = RGBColor(250, 249, 247)


def add_slide_header(slide, title_text, category_text="LG Electronics · Smart Cottage ROI Report"):
    """Adds a standard formal header to a 16:9 slide."""
    # Top banner bar
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    shape.fill.solid()
    shape.fill.fore_color.rgb = LGE_RED
    shape.line.fill.background()

    # Category / Breadcrumb
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.7), Inches(0.3))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = category_text.upper()
    p_c.font.size = Pt(9.5)
    p_c.font.bold = True
    p_c.font.color.rgb = LGE_GRAY

    # Main Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.52), Inches(11.7), Inches(0.55))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = LGE_RED


def add_footnote(slide, text="* 부하는 실측이 아닌 5R1C 시뮬레이션 기반이며, ESS 단가는 NREL 미국 벤치마크 범위값(환율 1,400원/$) 적용. 지상 설치비 0원."):
    """Adds standard required footnote to bottom."""
    box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.7), Inches(0.35))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(8)
    p.font.color.rgb = LGE_GRAY


def create_pptx_report(project_root: Path):
    korea_dir = project_root / "korea"
    report_dir = korea_dir / "report"
    data_path = report_dir / "report_data.json"

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: 결론 요약 (Executive Summary)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_slide_header(s1, "핵심 결론 요약 (Executive Summary)", "01. Executive Summary")
    add_footnote(s1)

    # 5 Findings Boxes
    findings = data["key_findings"]
    lefts = [Inches(0.8 + i * 2.38) for i in range(5)]
    for i, f in enumerate(findings):
        box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, lefts[i], Inches(1.3), Inches(2.26), Inches(4.2))
        box.fill.solid()
        box.fill.fore_color.rgb = LGE_WARM_GRAY
        box.line.color.rgb = LGE_RED if i == 0 else DARK_BORDER
        box.line.width = Pt(1.5 if i == 0 else 1)

        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.12)
        tf.margin_right = Inches(0.12)
        tf.margin_top = Inches(0.15)

        p0 = tf.paragraphs[0]
        p0.text = f"{f['id']}. {f['topic']}"
        p0.font.bold = True
        p0.font.size = Pt(12)
        p0.font.color.rgb = LGE_RED

        p1 = tf.add_paragraph()
        p1.space_before = Pt(8)
        p1.text = f["summary"]
        p1.font.size = Pt(9.5)
        p1.font.color.rgb = LGE_DARK

    # Summary callout banner at bottom
    banner = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(5.65), Inches(11.73), Inches(1.25))
    banner.fill.solid()
    banner.fill.fore_color.rgb = WHITE
    banner.line.color.rgb = LGE_RED
    banner.line.width = Pt(1.5)
    tf_b = banner.text_frame
    tf_b.word_wrap = True
    p_b0 = tf_b.paragraphs[0]
    p_b0.text = "※ 종합 시사점:"
    p_b0.font.bold = True
    p_b0.font.size = Pt(11)
    p_b0.font.color.rgb = LGE_RED
    p_b1 = tf_b.add_paragraph()
    p_b1.text = "국내 주택용 누진제 요금의 낮은 단가(1~2구간 120~215원/kWh)와 배터리 팩 단가 한계로 인해 3년 회수는 구조적으로 불가능(최단 15.3년). " \
               "Zero energy는 2026-02-03 동계 극단일 대응으로 고비용(4,922만~2.1억)이 소요되어 무수전 비상전원 용도로 포지셔닝해야 하며, " \
               "실질적 경제성 관점에서는 계통연계 Near Zero Bill 및 프로판 대체용 AWHP 전환이 가장 타당합니다."
    p_b1.font.size = Pt(9.5)
    p_b1.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 2: 분석 범위 및 프레임워크
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "분석 범위 및 시뮬레이션 프레임워크", "02. Scope & Framework")
    add_footnote(s2)

    # 4 Pillar cards
    pillars = [
        ("기상 데이터", "강원특별자치도 춘천시\n(기상청 표준 TMYx 2009-2023)\n15분 단위 35,040 타임스텝\n연간 수평면 일사량 1,299 kWh/m²"),
        ("주택 모델 (3종)", "MONO Core 54 (54m², 2인)\nMONO Core 72 (73m², 3인)\nDUO Max 45 (복층 45m², 2인)\n공식 건축 설계 도면 및 단열 반영"),
        ("설비 패키지", "PV: 0.5~150kW (단가 비례)\nESS: 9.6kWh 모듈 단위 (DoD 70%)\n난방: 가스보일러 vs AWHP\nEV 충전기: 0대 vs 1대 (7kW)"),
        ("이용률 & 시나리오", "이용률 6단계 (100%~5%)\n타겟 3단계 (Energy/Bill/Near)\n보조금 유무 (265만원 지원)\n총 432개 전수 시나리오 산출"),
    ]
    for i, (title, desc) in enumerate(pillars):
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + i * 2.98), Inches(1.3), Inches(2.83), Inches(4.0))
        card.fill.solid()
        card.fill.fore_color.rgb = LGE_WARM_GRAY
        card.line.color.rgb = DARK_BORDER
        tf = card.text_frame
        tf.word_wrap = True
        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.bold = True
        p0.font.size = Pt(13)
        p0.font.color.rgb = LGE_RED
        p1 = tf.add_paragraph()
        p1.space_before = Pt(10)
        p1.text = desc
        p1.font.size = Pt(10.5)
        p1.font.color.rgb = LGE_DARK

    # Bottom note
    b_note = s2.shapes.add_textbox(Inches(0.8), Inches(5.5), Inches(11.73), Inches(1.3))
    tf_bn = b_note.text_frame
    tf_bn.word_wrap = True
    p = tf_bn.paragraphs[0]
    p.text = "■ 시뮬레이션 체계: ISO 13790 5R1C 동적 열평형 모델 + KEPCO 주택용 누진제 + 순환 정상상태(Periodic Steady-State) 배터리 디스패치"
    p.font.bold = True
    p.font.size = Pt(10.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 3: 모델 정의 (Core 54, 72, DUO Max)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "주택 모델 사양 및 부하 산정 기준", "03. Building & Load Specifications")
    add_footnote(s3)

    # Table of models
    table_shape = s3.shapes.add_table(4, 6, Inches(0.8), Inches(1.4), Inches(11.73), Inches(3.2))
    table = table_shape.table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(1.4)
    table.columns[2].width = Inches(1.2)
    table.columns[3].width = Inches(3.4)
    table.columns[4].width = Inches(1.5)
    table.columns[5].width = Inches(2.03)

    headers = ["주택 모델", "연면적", "설계 인원", "기본 포함 가전", "상시 소비전력", "냉방 설비 사양"]
    for c_idx, h in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10)
            p.font.color.rgb = LGE_DARK

    row_data = [
        ["MONO Core 54", "54.0 m²", "2인", "냉장고(35W), 세탁기(130kWh/y), 3구 인덕션(420kWh/y)", "80.0 W", "시스템에어컨 (COP 4.40)"],
        ["MONO Core 72", "72.9 m²", "3인", "냉장고, 워시타워, 3구 인덕션, 12인용 식기세척기", "80.0 W", "시스템에어컨 (COP 4.40)"],
        ["DUO Max 45", "45.4 m²", "2인", "워시타워, 식기세척기, 인덕션, 광파오븐, 정수기, ERV", "126.7 W", "Therma V (EER 2.6, 5.5kW) / 가스시 에어컨"],
    ]
    for r_idx, r in enumerate(row_data):
        for c_idx, val in enumerate(r):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r_idx % 2 == 0 else LIGHT_ROW_BG
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                p.font.color.rgb = LGE_DARK

    # Bottom notes
    b_box = s3.shapes.add_textbox(Inches(0.8), Inches(4.8), Inches(11.73), Inches(2.0))
    tf = b_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "■ 부하 분리 산정 원칙:\n" \
             "1. 조명 부하: 바닥면적에 비례 산정 (4.345 kWh/m²·년)\n" \
             "2. 가전 부하: 실제 모델별 빌트인 탑재 목록(워시타워, 광파오븐, 정수기, ERV 등)을 개별 반영하여 모델별 전력 부하 차별화\n" \
             "3. 냉방 부하: DUO Max AWHP 적용 시 팬코일/복사냉방을 가정한 Therma V A35/W7 (EER 2.6, 정격 5.5kW) 적용. Core 모델 및 가스 케이스는 시스템에어컨(COP 4.40) 유지"
    p.font.size = Pt(9.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 4: 요금과 상계 (Tariff & Net-metering)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "전기요금 누진 구조 및 월 합산 상계 제도", "04. Tariff & Net-Metering")
    add_footnote(s4)

    # Left: Tariff Table
    t_shape = s4.shapes.add_table(4, 3, Inches(0.8), Inches(1.4), Inches(5.6), Inches(2.2))
    t = t_shape.table
    t_headers = ["누진 구간 (비하계 기준)", "기본요금 (원/호)", "전력량요금 (원/kWh)"]
    for c, h in enumerate(t_headers):
        cell = t.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)
            p.font.color.rgb = LGE_DARK
    t_rows = [
        ["1단계 (200 kWh 이하)", "910원", "120.0원"],
        ["2단계 (201 ~ 400 kWh)", "1,600원", "214.6원"],
        ["3단계 (400 kWh 초과)", "7,300원", "307.3원"],
    ]
    for r_i, r in enumerate(t_rows):
        for c_i, v in enumerate(r):
            cell = t.cell(r_i + 1, c_i)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)

    # Right: 300kWh calculation
    t_right = s4.shapes.add_table(7, 2, Inches(6.8), Inches(1.4), Inches(5.7), Inches(3.2))
    tr = t_right.table
    tr_data = [
        ["항목 (월 300 kWh 사용 기준)", "금액 (원)"],
        ["기본요금 (2단계)", "1,600원"],
        ["전력량요금 (200k×120원 + 100k×214.6원)", "45,460원"],
        ["기후환경요금 (9원/k) + 연료비조정액 (+5원/k)", "4,200원"],
        ["전기요금계 (소계)", "51,260원"],
        ["부가가치세 (10%) + 전력산업기반기금 (2.7%)", "6,500원"],
        ["최종 청구금액 (10원 미만 절사)", "57,760원"],
    ]
    for r_i, r in enumerate(tr_data):
        for c_i, v in enumerate(r):
            cell = tr.cell(r_i, c_i)
            cell.text = v
            if r_i == 0 or r_i == 6:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LGE_WARM_GRAY
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)
                if r_i == 0 or r_i == 6:
                    p.font.bold = True

    # Net-metering rule box
    rule_box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.8), Inches(11.73), Inches(2.0))
    rule_box.fill.solid()
    rule_box.fill.fore_color.rgb = WHITE
    rule_box.line.color.rgb = LGE_RED
    tf = rule_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "■ 소규모 신·재생에너지 상계 지침 (law.go.kr 지침 제18조, VERIFIED):\n" \
             "• 월 합산 상계: 수전 전력량과 잉여 발전량을 1:1로 상계한 후 순수전량에 대해서만 누진 요금 청구\n" \
             "• 무기한 누적 이월: 당월 잉여 발전량이 수전량을 초과하는 경우, 소멸되지 않고 익월로 영구 누적 이월되어 동계 난방 피크 시 상계 활용\n" \
             "• 기본요금 정책: 상계 후 순사용량이 0 kWh인 경우에도 해당 계약전력 1단계 기본요금(910원)은 청구됨"
    p.font.size = Pt(9.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 5: 비용 근거 (CAPEX Benchmarks)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_header(s5, "설비 설치비(CAPEX) 및 단가 산정 근거", "05. CAPEX & Cost Basis")
    add_footnote(s5)

    c_table_shape = s5.shapes.add_table(7, 5, Inches(0.8), Inches(1.4), Inches(11.73), Inches(3.6))
    ct = c_table_shape.table
    c_headers = ["설비 구분", "적용 단가 (Central)", "단가 범위 (Low ~ High)", "출처 및 산출 기준", "상태 뱃지"]
    for c_i, h in enumerate(c_headers):
        cell = ct.cell(0, c_i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)

    c_rows = [
        ["태양광 (PV)", "1,513,667원/kW", "110만 ~ 200만원/kW", "2026 주택지원 3kW 상한 4,541,000원 공식 공고 비례 산출", "공식 확인 (VERIFIED)"],
        ["ESS 시스템", "1,775,200원/kWh", "39.6만 ~ 187.2만원/kWh", "NREL Q1 2021 Benchmark ($1,268/kWh, 1,400원/$) 해외값", "미검증 (UNVERIFIED)"],
        ["AWHP (Therma V)", "14,000,000원", "1,400만원 고정", "HM091HF UB40 기기 1,200만원 + 전기·배관 시공 200만원", "미검증 (UNVERIFIED)"],
        ["프로판 (LPG)", "2,812.26원/kg", "-", "오피넷 일반프로판 전국 평균 (2026년 10월 4주 공식가)", "공식 확인 (VERIFIED)"],
        ["인버터 교체비", "250,000원/kW (최소 75만)", "-", "12년차 인버터 단품 교체 비용 가정치", "(가정) (PLACEHOLDER)"],
        ["지상 설치비", "0원", "-", "5kW 초과 지상 설치 추가 시공비 0원 적용 (부지비 별도)", "(가정) (PLACEHOLDER)"],
    ]
    for r_i, r in enumerate(c_rows):
        for c_i, v in enumerate(r):
            cell = ct.cell(r_i + 1, c_i)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)
                if c_i == 4:
                    if "공식 확인" in v:
                        p.font.color.rgb = LGE_RED
                        p.font.bold = True
                    elif "미검증" in v:
                        p.font.color.rgb = LGE_GRAY

    # Note
    note_box = s5.shapes.add_textbox(Inches(0.8), Inches(5.2), Inches(11.73), Inches(1.6))
    tf = note_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "■ 단가 적용 주의사항:\n" \
             "• 춘천시 지역 프로판 단가(2,780.15원) 대신 전국 평균 공식가(2,812.26원/kg)를 반영하여 국가 간 비교 기준을 일원화함\n" \
             "• 국내 가정용 ESS 실거래가 데이터 부재로 NREL 미국 조달 단가를 임시 환율(1,400원/$)로 환산하였으므로 ESS 경제성은 범위값(Low/High)으로 해석해야 함\n" \
             "• 지상형 PV 설치 시 토목 공사비와 부지 매입비는 본 분석에서 제외됨(0원 반영)"
    p.font.size = Pt(9.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 6: 부하 패턴 (Load Profiles)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "주택 모델별 연간 최대 부하일 15분 프로파일", "06. Load Profiles")
    add_footnote(s6)

    # 3 model summary cards
    for i, hm in enumerate(["MONO Core 54", "MONO Core 72", "DUO Max 45"]):
        prof = data["profiles_sample"][hm]
        card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + i * 3.98), Inches(1.4), Inches(3.78), Inches(5.2))
        card.fill.solid()
        card.fill.fore_color.rgb = LGE_WARM_GRAY
        card.line.color.rgb = DARK_BORDER
        tf = card.text_frame
        tf.word_wrap = True
        p0 = tf.paragraphs[0]
        p0.text = f"■ {hm}"
        p0.font.bold = True
        p0.font.size = Pt(13)
        p0.font.color.rgb = LGE_RED

        p1 = tf.add_paragraph()
        p1.space_before = Pt(8)
        p1.text = f"• 최대 부하 발생일: 1월 25일 (Day {prof['peak_day_index']})\n" \
                  f"• 당일 피크 부하: {prof['max_load_kw']} kW\n" \
                  f"• 당일 총 전력량: {prof['daily_total_kwh']} kWh\n" \
                  f"• 난방+가전 피크 시간: 07:00 ~ 09:00, 19:00 ~ 22:00\n" \
                  f"• 5kWp 태양광 발전량: 주간 10~15시 집중\n" \
                  f"• 배터리 역할: 주간 잉여 태양광 충전 후 야간 피크 부하 방전 대응"
        p1.font.size = Pt(10)
        p1.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 7: Critical Day (2026-02-03)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_header(s7, "Critical Day (2026-02-03) 및 무정전 사이징 검증", "07. Critical Day & Reliability")
    add_footnote(s7)

    # Comparison box: Peak day method vs Critical day method
    comp_box = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(11.73), Inches(2.6))
    comp_box.fill.solid()
    comp_box.fill.fore_color.rgb = WHITE
    comp_box.line.color.rgb = LGE_RED
    comp_box.line.width = Pt(1.5)
    tf = comp_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "■ 2026-02-03 (Day 34) 저조도 현상 원인 및 기존 방식과의 비교:"
    p.font.bold = True
    p.font.size = Pt(12)
    p.font.color.rgb = LGE_RED

    p_body = tf.add_paragraph()
    p_body.space_before = Pt(6)
    p_body.text = "• 실제 일사량: 춘천 TMYx 공식 기상 데이터 상 GHI = 0.2465 kWh/m² (DNI = 0, DHI = 0.2465)로 연중 최저 일사 강설일\n" \
                  "• 1kWp AC 발전량: 0.2137 kWh (25년 열화 적용 시 0.1895 kWh)로 일반 맑은 날(4~5 kWh)의 5% 수준에 불과\n" \
                  "• 기존 피크데이 방식 한계: 하계/동계 단일 최대 부하일 기준으로 PV/ESS를 산출하면, 이와 같은 연속 저조도 기간 동안 배터리가 고갈되어 연간 622 ~ 3,420시간의 정전(Loss of Load) 발생\n" \
                  "• 본 분석 365일 정상상태 탐색 결과: 12개 Zero Energy 케이스 전수 연간 LOL = 0.00시간(무정전) 달성"
    p_body.font.size = Pt(10)
    p_body.font.color.rgb = LGE_DARK

    # 15-day window summary table
    w_table_shape = s7.shapes.add_table(2, 8, Inches(0.8), Inches(4.3), Inches(11.73), Inches(2.0))
    wt = w_table_shape.table
    crit_w = data["critical_window_15d"][4:12] # 8 days centered on Day 34
    for c_i, d in enumerate(crit_w):
        c0 = wt.cell(0, c_i)
        c0.text = d["date"].split("-")[1] + "/" + d["date"].split("-")[2]
        c0.fill.solid()
        c0.fill.fore_color.rgb = LGE_ACTIVE_RED if d["is_critical"] else LGE_WARM_GRAY
        for p in c0.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)
            p.font.color.rgb = WHITE if d["is_critical"] else LGE_DARK

        c1 = wt.cell(1, c_i)
        c1.text = f"{d['ghi_kwh_m2']} kWh/m²\n({d['temp_mean_c']}℃)"
        c1.fill.solid()
        c1.fill.fore_color.rgb = WHITE
        for p in c1.text_frame.paragraphs:
            p.font.size = Pt(9)
            if d["is_critical"]:
                p.font.bold = True
                p.font.color.rgb = LGE_ACTIVE_RED

    # =========================================================================
    # SLIDE 8: Zero Energy
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_header(s8, "Zero Energy (오프그리드 무수전) 12개 케이스 분석", "08. Zero Energy Sizing")
    add_footnote(s8)

    # 12 rows table
    ze_table_shape = s8.shapes.add_table(7, 7, Inches(0.8), Inches(1.4), Inches(11.73), Inches(4.5))
    zet = ze_table_shape.table
    zet_headers = ["주택 모델", "난방", "EV", "최적 PV (kW)", "최적 ESS (kWh)", "필요 부지 (5m²/kW)", "최소 투자비 (Central)"]
    for c_i, h in enumerate(zet_headers):
        cell = zet.cell(0, c_i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)

    # Display 6 representative cases out of 12
    ze_rows = [r for r in data["zero_energy_reference"] if r["ev_count"] == 0]
    for r_i, r in enumerate(ze_rows):
        vals = [
            r["house_model"],
            r["heating_package"].replace("PV+ESS+", ""),
            f"{r['ev_count']}대",
            f"{r['optimal_pv_kw']} kW",
            f"{r['optimal_ess_kwh']} kWh",
            f"{r['pv_land_area_m2']} m²",
            f"{r['min_capex_central_krw']:,.0f}원",
        ]
        for c_i, v in enumerate(vals):
            cell = zet.cell(r_i + 1, c_i)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)
                if c_i >= 3:
                    p.font.bold = True

    b_text = s8.shapes.add_textbox(Inches(0.8), Inches(6.0), Inches(11.73), Inches(0.9))
    tf = b_text.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• 탐색 하한 0.5kW 확대 결과: ESS 용량을 최적화하여 Core 54 가스 케이스 기준 PV 10kW + ESS 19.2kWh(4,922만원)의 최소 비용 조합 발견\n" \
             "• 회수기간: 12개 케이스 전수 >25년(경제성 미확보). 상시 계통 연계가 어려운 오프그리드 도서산간 특수 목적용으로 적합"
    p.font.size = Pt(9.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 9: Zero Bill
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_header(s9, "Zero Bill (순전기요금 0원) ESS 단가 민감도 분석", "09. Zero Bill Economics")
    add_footnote(s9)

    zb_table_shape = s9.shapes.add_table(7, 7, Inches(0.8), Inches(1.4), Inches(11.73), Inches(4.2))
    zbt = zb_table_shape.table
    zb_headers = ["주택 모델", "난방", "PV 용량", "ESS 용량", "CAPEX (Low)", "CAPEX (Central)", "회수기간 (Low vs Central)"]
    for c_i, h in enumerate(zb_headers):
        cell = zbt.cell(0, c_i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)

    for r_i, r in enumerate(data["zero_bill_details"]):
        vals = [
            r["house_model"],
            r["heating_package"],
            f"{r['pv_kw']} kW",
            f"{r['ess_kwh']} kWh",
            f"{r['capex_low_krw']:,.0f}원",
            f"{r['capex_central_krw']:,.0f}원",
            f"{r['payback_low']} vs {r['payback_central']}",
        ]
        for c_i, v in enumerate(vals):
            cell = zbt.cell(r_i + 1, c_i)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)
                if c_i == 6:
                    p.font.bold = True
                    p.font.color.rgb = LGE_RED

    b_text = s9.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.73), Inches(1.1))
    tf = b_text.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• ESS 단가 영향: Low 시나리오($283/kWh)에서는 Core 72 AWHP 기준 투자비가 2,746만원으로 낮아져 회수기간 10년 안팎으로 단축됨\n" \
             "• Central 시나리오($1,268/kWh)에서는 회수기간이 18.6년으로 연장되어, 배터리 조달 원가가 Zero Bill 상용화의 핵심 전제조건임"
    p.font.size = Pt(9.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 10: Near Zero Bill
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_header(s10, "Near Zero Bill 최단 회수기간 및 3년 달성 요건", "10. Near Zero Bill & 3Y Feasibility")
    add_footnote(s10)

    nz_table_shape = s10.shapes.add_table(7, 7, Inches(0.8), Inches(1.4), Inches(11.73), Inches(4.2))
    nzt = nz_table_shape.table
    nz_headers = ["주택 모델", "난방", "PV 용량", "ESS 용량", "실제 CAPEX (원)", "현재 회수기간", "3년 달성 필요 CAPEX"]
    for c_i, h in enumerate(nz_headers):
        cell = nzt.cell(0, c_i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)

    for r_i, r in enumerate(data["near_zero_details"]):
        vals = [
            r["house_model"],
            r["heating_package"],
            f"{r['pv_kw']} kW",
            f"{r['ess_kwh']} kWh",
            f"{r['actual_capex_krw']:,.0f}원",
            f"{r['payback']}",
            f"{r['target_capex_for_3y_krw']:,.0f}원 (-{r['reduction_pct']}%)",
        ]
        for c_i, v in enumerate(vals):
            cell = nzt.cell(r_i + 1, c_i)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)
                if c_i == 6:
                    p.font.bold = True
                    p.font.color.rgb = LGE_RED

    b_text = s10.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.73), Inches(1.1))
    tf = b_text.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• 3년 회수 진단 결론: 3년 이내 회수를 달성하기 위해서는 설비 CAPEX가 현재 대비 80% 이상 인하되어야 함\n" \
             "• 현행 단가 및 요금제 하에서 스마트코티지 PV+ESS+AWHP 패키지는 3년 회수가 불가하며, 15~18년 장기 투자 회수 모델로 안내 필요"
    p.font.size = Pt(9.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 11: 이용률 히트맵
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_header(s11, "이용률(점유율)별 경제성(회수기간) 변화 분석", "11. Occupancy Sensitivity")
    add_footnote(s11)

    hm_table_shape = s11.shapes.add_table(7, 8, Inches(0.8), Inches(1.4), Inches(11.73), Inches(4.2))
    hmt = hm_table_shape.table
    hm_headers = ["주택 모델", "난방", "100% (상시)", "70% (주 5일)", "50% (격주)", "30% (주말)", "10% (월 3일)", "5% (연휴)"]
    for c_i, h in enumerate(hm_headers):
        cell = hmt.cell(0, c_i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)

    for r_i, r in enumerate(data["heatmap_no_sub"]):
        cell0 = hmt.cell(r_i + 1, 0)
        cell0.text = r["house_model"]
        cell1 = hmt.cell(r_i + 1, 1)
        cell1.text = r["heating_package"]
        for c_i, v in enumerate(r["values"]):
            cell = hmt.cell(r_i + 1, c_i + 2)
            cell.text = v["payback_str"]
            if v["payback_years"] < 25.0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LGE_WARM_GRAY
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                if v["payback_years"] < 25.0:
                    p.font.bold = True
                    p.font.color.rgb = LGE_RED

    b_text = s11.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.73), Inches(1.1))
    tf = b_text.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• 점유율 임계점: 주말 세컨드하우스(이용률 10~30%)의 경우 baseline 전력/난방 사용량이 극히 적어 연간 절감액이 미미함\n" \
             "• 따라서 세컨드하우스 용도로는 25년 이내 투자비 회수가 불가능하며, 최소 70% 이상 상시 거주 주택에 한해 경제적 타당성 형성"
    p.font.size = Pt(9.5)
    p.font.color.rgb = LGE_DARK

    # =========================================================================
    # SLIDE 12: 보조금과 민감도
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_slide_header(s12, "정부·지자체 보조금 및 AWHP 70% 민감도 분석", "12. Subsidy & Policy Sensitivity")
    add_footnote(s12, "* 춘천시 안내문은 2025 단가(공사비 4.93M, 공단 1.79M), 본 분석은 2026 공고(4.54M, 1.65M)+시비 1.0M 반영. AWHP 70%는 춘천 미적용 가상 시나리오.")

    sub_table_shape = s12.shapes.add_table(4, 5, Inches(0.8), Inches(1.4), Inches(11.73), Inches(2.6))
    st = sub_table_shape.table
    st_headers = ["주택 모델 (AWHP 100% 거주)", "기준 CAPEX (무보조)", "기준 회수기간", "AWHP 70% 지원 적용 CAPEX", "AWHP 70% 적용 회수기간"]
    for c_i, h in enumerate(st_headers):
        cell = st.cell(0, c_i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)

    for r_i, r in enumerate(data["subsidy_sensitivity"]):
        vals = [
            r["house_model"],
            f"{r['base_capex_krw']:,.0f}원",
            f"{r['base_payback']}",
            f"{r['awhp70_capex_krw']:,.0f}원",
            f"{r['awhp70_payback']}",
        ]
        for c_i, v in enumerate(vals):
            cell = st.cell(r_i + 1, c_i)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                if c_i == 4:
                    p.font.bold = True
                    p.font.color.rgb = LGE_RED

    policy_box = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.3), Inches(11.73), Inches(2.5))
    policy_box.fill.solid()
    policy_box.fill.fore_color.rgb = WHITE
    policy_box.line.color.rgb = LGE_RED
    tf = policy_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "■ 보조금 정책 시사점 및 제언:"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = LGE_RED

    p_body = tf.add_paragraph()
    p_body.space_before = Pt(6)
    p_body.text = "• 2026 주택지원 사업: 3kW PV 기준 국비 165만원 + 춘천시 시비 하한 100만원 = 총 265만원 지원으로 초기 투자비 절감 기여\n" \
                  "• AWHP 보조금 필요성: 현재 춘천시 등 중부 한랭지는 AWHP 전용 보조금이 전무함. 만약 온난지역·실거주 가정 기준 70%(980만원) 수준의 히트펌프 전환 보조금이 도입될 경우, 회수기간이 18년에서 10~12년대로 6~8년 대폭 단축되어 제품 경쟁력 획기적 개선 가능\n" \
                  "• 정책 건의 방향: 농어촌 소형 단독주택의 탈탄소 난방 전환을 위한 가정용 AWHP/히트펌프 전용 국고보조금 신설 요구 필요"
    p_body.font.size = Pt(9.5)
    p_body.font.color.rgb = LGE_DARK

    # =========================================================================
    # APPENDIX SLIDE 1: 대표 요약표
    # =========================================================================
    sa1 = prs.slides.add_slide(blank_layout)
    add_slide_header(sa1, "[부록] 대표 케이스 6행 요약 종합표", "Appendix 01. Summary Table")
    add_footnote(sa1)

    app1_table = sa1.shapes.add_table(7, 8, Inches(0.8), Inches(1.4), Inches(11.73), Inches(4.8))
    at = app1_table.table
    a_headers = ["주택 모델", "난방", "Zero Energy CAPEX", "ZE 회수", "Zero Bill CAPEX", "ZB 회수", "Near Zero CAPEX", "NZ 회수"]
    for c_i, h in enumerate(a_headers):
        cell = at.cell(0, c_i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = LGE_WARM_GRAY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)

    for r_i, r in enumerate(data["representative_table"]):
        vals = [
            r["house_model"],
            r["heating_package"],
            r["zero_energy"]["capex_str"],
            r["zero_energy"]["payback_str"],
            r["zero_bill"]["capex_str"],
            r["zero_bill"]["payback_str"],
            r["near_zero_bill"]["capex_str"],
            r["near_zero_bill"]["payback_str"],
        ]
        for c_i, v in enumerate(vals):
            cell = at.cell(r_i + 1, c_i)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9)
                if c_i in [3, 5, 7] and "년" in v and not ">" in v:
                    p.font.bold = True
                    p.font.color.rgb = LGE_RED

    # =========================================================================
    # APPENDIX SLIDE 2: DUO Max Incremental & Limitations
    # =========================================================================
    sa2 = prs.slides.add_slide(blank_layout)
    add_slide_header(sa2, "[부록] DUO Max 증분 분석 및 가정·한계 목록", "Appendix 02. Incremental & Placeholders")
    add_footnote(sa2)

    # Left: DUO Max incremental
    card_l = sa2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.2))
    card_l.fill.solid()
    card_l.fill.fore_color.rgb = LGE_WARM_GRAY
    card_l.line.color.rgb = DARK_BORDER
    tf_l = card_l.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "■ DUO Max 45 증분 투자(Incremental) 요약:"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = LGE_RED

    p_body = tf_l.add_paragraph()
    p_body.space_before = Pt(6)
    p_body.text = "• 기준 전제: 루프탑 기본 PV 5kW 및 AWHP 기본 탑재 모델\n" \
                  "• 분석 목적: 추가 PV/ESS 설치 비용 대비 추가 전기요금 절감액만으로 순수 증분 ROI 산출 (총 72건 시나리오)\n" \
                  "• 증분 최단 회수기간: 18.1년 (이용률 100%, EV 1대, Zero Bill 기준)\n" \
                  "• 기본 탑재 설비의 가치를 제외하더라도 배터리 증설 비용 회수에는 최소 18년 이상 소요됨"
    p_body.font.size = Pt(9.5)
    p_body.font.color.rgb = LGE_DARK

    # Right: Limitations & Placeholders
    card_r = sa2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.4), Inches(5.73), Inches(5.2))
    card_r.fill.solid()
    card_r.fill.fore_color.rgb = WHITE
    card_r.line.color.rgb = DARK_BORDER
    tf_r = card_r.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "■ 주요 PLACEHOLDER 및 UNVERIFIED 목록:"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = LGE_RED

    p_body = tf_r.add_paragraph()
    p_body.space_before = Pt(6)
    p_body.text = "1. PLACEHOLDER (11개 항목):\n" \
                  "  • 환율 (1,400원/$), 지상 설치 추가비 (0원 가정)\n" \
                  "  • 인버터 교체비(25만원/kW), 분전반 개체비(45만원)\n" \
                  "  • 가정용 ESS 보조금 (미반영, 0원)\n" \
                  "  • ERV 전열교환기 연속 가동 소비전력 (30W)\n\n" \
                  "2. UNVERIFIED (25개 항목):\n" \
                  "  • 가구원수별 전력량 3,749/4,094kWh (KESIS 자료 유사 수준, 표 미특정, 검증 통과 근거 미사용)\n" \
                  "  • Therma V HM091HF A-7℃ 미만 성능 외삽값\n" \
                  "  • NREL ESS 해외 단가 벤치마크\n\n" \
                  "※ 전체 432개 시나리오 세부 데이터 및 인터랙티브 필터는 단일 HTML 보고서(LG_SC_Korea_ROI_Report.html)를 참조하십시오."
    p_body.font.size = Pt(9)
    p_body.font.color.rgb = LGE_DARK

    out_pptx = report_dir / "LG_SC_Korea_ROI_Report.pptx"
    prs.save(out_pptx)
    print(f"Generated standalone PPTX report: {out_pptx}")
    return out_pptx


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    create_pptx_report(project_root)

