# 수정코드_260918
# mold_tech_study_app.py

import base64
import calendar
from datetime import date, datetime, timedelta, timezone
import json
import os
import re
import time
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 설정 (반드시 모든 Streamlit 명령어 중 최상단에 위치해야 함)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="금형기술사 학습 시스템", layout="wide")

# -----------------------------------------------------------------------------
# 2. 파일 경로 및 절대경로 설정
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_FILE = os.path.join(BASE_DIR, "notes.json")
USER_DATA_FILE = os.path.join(BASE_DIR, "user_study_data.json")
IMAGE_DIR = os.path.join(BASE_DIR, "saved_images")

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 3. 데이터 입출력 함수
# -----------------------------------------------------------------------------
def get_kst_today():
    """한국 표준시(KST: UTC+9) 기준 오늘 날짜 구하기"""
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).date()

def load_notes():
    """학습노트 데이터 안전 로드"""
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            st.error(f"노트 파일 로드 오류: {e}")
            return []
    return []

def save_notes(notes):
    """학습노트 데이터 안전 저장"""
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"노트 저장 오류: {e}")

def load_user_data():
    """기출문제 학습 데이터 및 D-Day 안전 로드"""
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            st.error(f"사용자 데이터 로드 오류: {e}")
            return {}
    return {}

def save_user_data(data):
    """기출문제 학습 데이터 및 D-Day 안전 저장"""
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"사용자 데이터 저장 오류: {e}")

def convert_image_to_base64(uploaded_file):
    """이미지를 base64 텍스트로 인코딩"""
    if uploaded_file is not None:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return None

# -----------------------------------------------------------------------------
# 4. UI 및 텍스트/수식 포맷팅 헬퍼 함수
# -----------------------------------------------------------------------------
def render_mini_calendar():
    """커스텀 미니 달력 HTML 생성 함수"""
    today = get_kst_today()
    year, month, today_day = today.year, today.month, today.day
    cal = calendar.monthcalendar(year, month)
    
    html = f"""
    <div style="background-color: #121212; border-radius: 8px; padding: 10px 4px; width: 100%; box-sizing: border-box; margin-bottom: 8px; overflow: hidden;">
        <div style="text-align: center; font-weight: bold; font-size: 0.88rem; margin-bottom: 8px; color: #ffffff;">
            📅 {year}년 {month}월
        </div>
        <table style="width: 100%; table-layout: fixed; border-collapse: collapse; text-align: center; font-size: 0.75rem; margin: 0; padding: 0;">
            <thead>
                <tr style="font-weight: 600; border-bottom: 1px solid #333333;">
                    <th style="width: 14.285%; color: #ff7979; padding: 4px 0;">일</th>
                    <th style="width: 14.285%; color: #ffffff; padding: 4px 0;">월</th>
                    <th style="width: 14.285%; color: #ffffff; padding: 4px 0;">화</th>
                    <th style="width: 14.285%; color: #ffffff; padding: 4px 0;">수</th>
                    <th style="width: 14.285%; color: #ffffff; padding: 4px 0;">목</th>
                    <th style="width: 14.285%; color: #ffffff; padding: 4px 0;">금</th>
                    <th style="width: 14.285%; color: #64b5f6; padding: 4px 0;">토</th>
                </tr>
            </thead>
            <tbody>
    """
    for week in cal:
        html += "<tr style='height: 26px;'>"
        for idx, day in enumerate(week):
            if day == 0:
                html += "<td style='width: 14.285%; padding: 2px 0;'></td>"
            elif day == today_day:
                html += f"""<td style='width: 14.285%; padding: 2px 0; text-align: center;'>
                    <span style='background-color: #ff4b4b; color: #ffffff; border-radius: 50%; width: 20px; height: 20px; line-height: 20px; display: inline-block; font-weight: bold; font-size: 0.72rem; margin: 0 auto;'>{day}</span>
                </td>"""
            else:
                color_style = "color: #ff7979;" if idx == 0 else ("color: #64b5f6;" if idx == 6 else "color: #ffffff;")
                html += f"<td style='width: 14.285%; padding: 2px 0; {color_style}'>{day}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

def format_readable_text(text: str) -> str:
    """노트 본문의 LaTeX 수식 및 텍스트 가독성 자동 보정"""
    if not text or not str(text).strip():
        return "*작성된 내용이 없습니다.*"
    
    text_str = str(text)
    
    # 1. 괄호 수식 구문 (예: (F_{clamp} = P_{cavity} \times A_{projected})) 자동 변환
    def replace_bracket_math(match):
        formula = match.group(1).strip()
        formula_clean = re.sub(r'_\{([a-zA-Z0-9_\-]+)\}', r'_{\\text{\1}}', formula)
        return f"\n\n$$\n{formula_clean}\n$$\n\n"

    text_str = re.sub(r'\(([^)]*?=[^)]*?\\[a-zA-Z]+[^)]*?)\)', replace_bracket_math, text_str)
    
    # 2. 명시적 블록 수식 $$ ... $$ 내 단어 첨자 보정
    def clean_latex_block(match):
        formula = match.group(1)
        formula_clean = re.sub(r'_\{([a-zA-Z0-9_\-]+)\}', r'_{\\text{\1}}', formula)
        return f"\n$$\n{formula_clean}\n$$\n"

    text_str = re.sub(r'\$\$(.*?)\$\$', clean_latex_block, text_str, flags=re.DOTALL)

    return text_str


# -----------------------------------------------------------------------------
# 5. 세션 상태 초기화
# -----------------------------------------------------------------------------
if "user_data" not in st.session_state or not isinstance(st.session_state.user_data, dict):
    loaded_data = load_user_data()
    st.session_state["user_data"] = loaded_data if isinstance(loaded_data, dict) else {}

if not isinstance(st.session_state.get("user_data"), dict):
    st.session_state["user_data"] = {}

if "main_mode" not in st.session_state:
    st.session_state.main_mode = "exam"

if "notes" not in st.session_state:
    st.session_state.notes = load_notes()

if "d_day_target" not in st.session_state:
    user_data_dict = st.session_state.get("user_data", {})
    st.session_state.d_day_target = user_data_dict.get("_d_day_target", None)

if "show_d_day_picker" not in st.session_state:
    st.session_state.show_d_day_picker = False

if "show_detail" not in st.session_state:
    st.session_state.show_detail = False

if "current_q" not in st.session_state:
    st.session_state.current_q = None

# -----------------------------------------------------------------------------
# 6. 정제된 CSS 스타일 적용 (우측 탭 영역 들여쓰기 및 줄바꿈 라인 정렬 추가)
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
        /* 1. 메인 영역 패딩 최소화 */
        .block-container {
            padding-top: 2.0rem !important;
            padding-bottom: 1.5rem !important;
        }
        
        div[data-testid="stMarkdownContainer"] h1 {
            font-size: 1.4rem !important;
            margin-top: 0px !important;
            margin-bottom: 0.8rem !important;
        }

        /* 2. 사이드바 너비 지정 */
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }

        /* 3. 사이드바 기본 버튼 스타일 (블랙 테마) */
        section[data-testid="stSidebar"] div.stButton > button {
            width: 100% !important;
            height: 34px !important;
            min-height: 34px !important;
            font-size: 0.82rem !important;
            background-color: #000000 !important;
            color: #ffffff !important;
            border: 1px solid #444444 !important;
            border-radius: 8px !important;
            box-sizing: border-box !important;
            padding: 0 4px !important;
            letter-spacing: -0.3px !important;
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #222222 !important;
            border-color: #666666 !important;
        }

        /* 4. 필터링 영역 항목 간 여백 지정 */
        section[data-testid="stSidebar"] div[data-testid="stTextInput"],
        section[data-testid="stSidebar"] div[data-testid="stSelectbox"],
        section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] {
            margin-bottom: 12px !important;
            margin-top: 2px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCheckbox"] {
            margin-top: 8px !important;
            margin-bottom: 12px !important;
        }

        section[data-testid="stSidebar"] label {
            margin-bottom: 3px !important;
            padding: 0 !important;
        }

        section[data-testid="stSidebar"] label p {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            letter-spacing: -0.3px !important;
            margin: 0 !important;
        }

        /* 5. 선택박스 내부 글자 줄간격(line-height) 및 패딩 최소화 */
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] div[data-baseweb="select"] *,
        div[data-baseweb="popover"] * {
            font-size: 0.8rem !important;
            letter-spacing: -0.4px !important;
            line-height: 1.0 !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
            min-height: 30px !important;
            padding: 1px 4px !important;
            line-height: 1.0 !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="tag"] {
            margin: 1px 2px !important;
            padding: 0px 4px !important;
            height: 20px !important;
            line-height: 1.0 !important;
            border-radius: 4px !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="tag"] span {
            font-size: 0.75rem !important;
            letter-spacing: -0.4px !important;
            line-height: 1.0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCheckbox"] span {
            font-size: 0.8rem !important;
            letter-spacing: -0.3px !important;
            line-height: 1.1 !important;
        }

        /* =================================================================== */
        /* 6. [수정] 우측 탭 영역 순서 목록(1. 2. 3.) 내어쓰기 및 단락 라인 정렬 */
        /* =================================================================== */
        /* 1) 제목/헤더(h1~h6) 기준선 고정 */
        div[data-testid="stTabPanel"] h1,
        div[data-testid="stTabPanel"] h2,
        div[data-testid="stTabPanel"] h3,
        div[data-testid="stTabPanel"] h4,
        div[data-testid="stTabPanel"] h5,
        div[data-testid="stTabPanel"] h6 {
            margin-left: 0px !important;
            margin-bottom: 0.5rem !important;
        }

        /* 2) 일반 본문 단락(<p>) 기본 들여쓰기 */
        div[data-testid="stTabPanel"] div[data-testid="stMarkdownContainer"] > p {
            margin-left: 1.2rem !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
            line-height: 1.65 !important;
        }

        /* 3) 순서 있는 목록(<ol>, <li>) 내어쓰기(Hanging Indent) 및 수직 라인 맞춤 */
        div[data-testid="stTabPanel"] ol,
        div[data-testid="stTabPanel"] ul {
            margin-left: 1.2rem !important;      /* 전체 목록 들여쓰기 */
            padding-left: 1.2rem !important;     /* 번호(1. 2.)와 본문 사이 적정 간격 */
            margin-bottom: 0.8rem !important;
        }

        div[data-testid="stTabPanel"] li {
            margin-bottom: 0.4rem !important;
            line-height: 1.65 !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
        }

        /* li 항목 내 p 태그 중복 들여쓰기 방지 (수직 라인 이탈 차단) */
        div[data-testid="stTabPanel"] li > p {
            margin-left: 0px !important;
            display: inline !important;
        }

        /* 4) 입력창(st.text_area) 내부 줄바꿈 라인 유지 */
        div[data-testid="stTabPanel"] textarea {
            padding-left: 1.2rem !important;
            line-height: 1.65 !important;
            word-break: keep-all !important;
        }

        /* 7. D-Day 레이아웃 및 우측 박스 가로 100% 보정 */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
            gap: 6px !important;
            align-items: center !important;
            width: 100% !important;
            margin-top: 6px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
        section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] > p {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .dday-box {
            background-color: #000000;
            color: #ffffff;
            font-weight: bold;
            font-size: 0.85rem;
            letter-spacing: -0.2px;
            height: 34px !important;
            line-height: 32px !important;
            text-align: center;
            border-radius: 8px;
            border: 1px solid #444444;
            width: 100% !important;
            display: block !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. 데이터 로드 헬퍼
# -----------------------------------------------------------------------------
@st.cache_data
def load_excel_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    else:
        default_file = "금형기술사_기출문제 통합.xlsx"
        if os.path.exists(default_file):
            df = pd.read_excel(default_file)
        else:
            df = pd.DataFrame({
                '회차': [139, 139, 138, 138, 137],
                '교시': [1, 2, 1, 3, 4],
                '분류': ['프레스금형', '사출금형', '공통', '프레스금형', '사출금형'],
                '문제': [
                    '프로그레시브 금형에서 파일럿 핀의 역할과 종류를 설명하시오.',
                    '사출금형에서 2단 밀판(Ejector Plate) 구조와 작동 원리를 설명하시오.',
                    '금형 재료로 사용되는 고속도공구강(M42)의 특성을 설명하시오.',
                    '드로잉 가공 시 발생하는 결함의 종류와 대책을 설명하시오.',
                    '플라스틱 수지(PC, PA)의 유동 특성과 금형 설계 시 주의사항을 설명하시오.'
                ]
            })
    return df

# -----------------------------------------------------------------------------
# 8. 사이드바 구성
# -----------------------------------------------------------------------------
with st.sidebar:
    uploaded_file = st.file_uploader("📂 엑셀 파일 업로드", type=['xlsx', 'xls'])
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        btn_exam_type = "primary" if st.session_state.main_mode == "exam" else "secondary"
        if st.button("📝 기출문제", use_container_width=True, type=btn_exam_type, key="btn_nav_exam"):
            st.session_state.main_mode = "exam"
            st.session_state.show_detail = False
            st.rerun()

    with col_nav2:
        btn_note_type = "primary" if st.session_state.main_mode == "note" else "secondary"
        if st.button("📖 학습노트", use_container_width=True, type=btn_note_type, key="btn_nav_note"):
            st.session_state.main_mode = "note"
            st.rerun()

    st.markdown("---")
    st.markdown("**🔍 문제 필터링**")

    search_keyword = st.text_input("문제 키워드 검색", placeholder="검색어 입력...", label_visibility="collapsed")

    df = load_excel_data(uploaded_file)

    for q in df['문제']:
        if q not in st.session_state.user_data:
            st.session_state.user_data[q] = {
                'clicks': 0, 'importance': 3, 
                'concept': '', 'answer': '', 'extra': '',
                'image_notes': []
            }
        elif 'image_notes' not in st.session_state.user_data[q]:
            st.session_state.user_data[q]['image_notes'] = []

    df['조회수'] = df['문제'].apply(lambda x: st.session_state.user_data[x]['clicks'])
    df['중요도(별)'] = df['문제'].apply(lambda x: "⭐" * st.session_state.user_data[x]['importance'])

    rounds = sorted(list(df['회차'].unique()), reverse=True)
    unique_periods = sorted(list(df['교시'].unique()))
    periods = [str(p) for p in unique_periods]
    categories = sorted(list(df['분류'].unique()))

    sel_rounds = st.multiselect("회차 선택 (복수)", options=rounds, default=[])
    sel_periods = st.multiselect("교시 선택 (복수)", options=periods, default=[])
    sel_categories = st.multiselect("분류 선택 (복수)", options=categories, default=[])

    sort_by_clicks = st.checkbox("자주 본 문제 순 정렬 (조회수 ⇧)")

    # -------------------------------------------------------------------------
    # 사이드바 하단: 미니 달력 & D-Day 영역 (5:5 정렬 및 간격 정돈)
    # -------------------------------------------------------------------------
    st.markdown("<div style='margin-top: 15px; border-top: 1px solid #333333; padding-top: 10px;'></div>", unsafe_allow_html=True)

    # 블랙 배경 미니 달력 출력
    st.markdown(render_mini_calendar(), unsafe_allow_html=True)

    # D-Day 수치 계산
    today_date = get_kst_today()
    if st.session_state.d_day_target:
        target_dt = datetime.strptime(st.session_state.d_day_target, "%Y-%m-%d").date()
        diff_days = (target_dt - today_date).days
        if diff_days > 0:
            d_day_str = f"D-{diff_days}"
        elif diff_days == 0:
            d_day_str = "D-Day"
        else:
            d_day_str = f"D+{abs(diff_days)}"
    else:
        d_day_str = "D-XX"

    # 좌/우 5:5 비율 컬럼 분할
    col_d_btn, col_d_disp = st.columns([50, 50], gap="small", vertical_alignment="center")

    with col_d_btn:
        if st.button("D-Day 설정", use_container_width=True, key="btn_set_dday"):
            st.session_state.show_d_day_picker = not st.session_state.show_d_day_picker

    with col_d_disp:
        st.markdown(f"<div class='dday-box'>{d_day_str}</div>", unsafe_allow_html=True)

    # 날짜 피커
    if st.session_state.show_d_day_picker:
        default_val = datetime.strptime(st.session_state.d_day_target, "%Y-%m-%d").date() if st.session_state.d_day_target else get_kst_today()
        selected_date = st.date_input("목표 시험일 선택", value=default_val, key="d_day_picker_input")
        if st.button("확인 및 저장", use_container_width=True, key="btn_save_dday"):
            saved_date_str = selected_date.strftime("%Y-%m-%d")
            st.session_state.d_day_target = saved_date_str
            st.session_state.user_data["_d_day_target"] = saved_date_str
            save_user_data(st.session_state.user_data)
            st.session_state.show_d_day_picker = False
            st.rerun()
# -----------------------------------------------------------------------------
# 5. 필터링 조건 적용
# -----------------------------------------------------------------------------
filtered_df = df.copy()

if search_keyword.strip():
    filtered_df = filtered_df[
        filtered_df['문제'].astype(str).str.contains(search_keyword.strip(), case=False, na=False)
    ]

if sel_rounds:
    filtered_df = filtered_df[filtered_df['회차'].isin(sel_rounds)]

if sel_periods:
    filtered_df = filtered_df[filtered_df['교시'].astype(str).isin(sel_periods)]

if sel_categories:
    filtered_df = filtered_df[filtered_df['분류'].isin(sel_categories)]

if sort_by_clicks:
    filtered_df = filtered_df.sort_values(by='조회수', ascending=False)

# -----------------------------------------------------------------------------
# 6. 우측 화면 (리스트 뷰 vs 상세 뷰 vs 학습노트)
# -----------------------------------------------------------------------------
# =============================================================================
# [수정] main_mode 값에 따라 화면 분기 처리
# =============================================================================
if st.session_state.main_mode == "exam":
    # -------------------------------------------------------------------------
    # 기존 기출문제 화면 (리스트 뷰 vs 상세 뷰 Tab1~5) 전체 들여쓰기 처리
    # -------------------------------------------------------------------------
    if not st.session_state.show_detail:
        st.markdown("<h1>📚 금형기술사 기출문제 리스트</h1>", unsafe_allow_html=True)
        st.write("필터링된 문제 목록입니다. 목록에서 문제를 선택한 후 하단 버튼을 클릭하면 상세 학습 화면으로 이동합니다.")
        
        # 문제 목록 데이터프레임 출력
        event = st.dataframe(
            filtered_df[['회차', '교시', '분류', '문제', '조회수', '중요도(별)']], 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "회차": st.column_config.Column("회차", width=60),
                "교시": st.column_config.Column("교시", width=60),
                "분류": st.column_config.Column("분류", width=110),
                "문제": st.column_config.Column("문제", width=680),
                "조회수": st.column_config.Column("조회수", width=70),
                "중요도(별)": st.column_config.Column("중요도(별)", width=100)
            }
        )
        
        q_options = list(filtered_df['문제'])
        if q_options:
            # 표에서 클릭한 행을 아래 셀렉트박스 선택값과 연동
            selected_rows = event.selection.get("rows", [])
            if selected_rows:
                row_idx = selected_rows[0]
                if row_idx < len(filtered_df):
                    st.session_state["sb_question"] = filtered_df.iloc[row_idx]['문제']
    
            if "sb_question" not in st.session_state or st.session_state["sb_question"] not in q_options:
                st.session_state["sb_question"] = q_options[0]
    
            selected_q = st.selectbox("학습할 문제 선택", options=q_options, key="sb_question")
            
            # [핵심] 버튼 클릭 시 조회수 1 증가 + 저장 + 상세 페이지(Tab 1~5)로 이동
            if st.button("✏️ 선택한 문제 학습하기", type="primary", use_container_width=False):
                st.session_state.user_data[selected_q]['clicks'] += 1
                save_user_data(st.session_state.user_data)
                
                st.session_state.current_q = selected_q
                st.session_state.show_detail = True
                st.rerun()
        else:
            st.warning("조건에 해당하는 문제가 없습니다. 좌측 사이드바 필터를 변경해 보세요.")
    
    else:
        # --- 상세 학습 뷰 ---
        q_text = st.session_state.current_q
        q_data = st.session_state.user_data[q_text]
        
        if st.button("⬅️ 리스트로 돌아가기", use_container_width=False):
            st.session_state.show_detail = False
            st.session_state.current_q = None
            st.rerun()
    
        col_prob, col_star = st.columns([82, 18], vertical_alignment="center")
    
        with col_prob:
            st.markdown(f"""
                <div style="background-color:#2d3748; padding: 8px 12px; border-radius: 8px; margin: 0px;">
                    <div style="color:#63b3ed; font-size: 1.05rem; font-weight: bold; line-height: 1.35; margin-bottom: 4px;">📝 {q_text}</div>
                    <span style="color:#e2e8f0; font-size: 0.85rem;">현재 조회수: {q_data['clicks']}회</span>
                </div>
            """, unsafe_allow_html=True)
    
        with col_star:
            new_importance = st.selectbox(
                "중요도 설정", 
                options=[1, 2, 3, 4, 5], 
                index=q_data['importance'] - 1,
                format_func=lambda x: "⭐" * x
            )
            if new_importance != q_data['importance']:
                st.session_state.user_data[q_text]['importance'] = new_importance
                save_user_data(st.session_state.user_data)
                st.rerun()
    
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📖 답안 개념 설명", 
            "✅ 모범 답안", 
            "📎 추가 자료 및 메모", 
            "🔍 구글 검색", 
            "🖼️ 이미지 및 설명 자료"
        ])
    
        # -------------------------------------------------------------------------
        # TAB 1: 개념 설명
        # -------------------------------------------------------------------------
        with tab1:
            st.markdown("### 1. 답안 개념 설명")
            st.info("해당 문제에 필요한 이론적 배경, 핵심 메커니즘 및 요약 개념을 정리합니다.")
            
            key_hide_concept = f"hide_concept_{q_text}"
            if key_hide_concept not in st.session_state:
                st.session_state[key_hide_concept] = True
            is_concept_hidden = st.session_state[key_hide_concept]
    
            col_t1, col_h1, col_b1 = st.columns([68, 16, 16], vertical_alignment="center")
            with col_t1:
                st.write("")
            with col_h1:
                toggle_label = "👁️ 입력창 보이기" if is_concept_hidden else "🙈 입력창 숨기기"
                if st.button(toggle_label, key=f"btn_toggle_concept_{q_text}", use_container_width=True):
                    if f"concept_area_{q_text}" in st.session_state:
                        st.session_state.user_data[q_text]['concept'] = st.session_state[f"concept_area_{q_text}"]
                        save_user_data(st.session_state.user_data)
                    st.session_state[key_hide_concept] = not is_concept_hidden
                    st.rerun()
            with col_b1:
                if st.button("💾 저장하기", key=f"save_concept_{q_text}", type="primary", use_container_width=True):
                    if f"concept_area_{q_text}" in st.session_state:
                        st.session_state.user_data[q_text]['concept'] = st.session_state[f"concept_area_{q_text}"]
                    save_user_data(st.session_state.user_data)
                    st.toast("개념 설명이 저장되었습니다!")
    
            if not is_concept_hidden:
                concept_text = st.text_area(
                    "개념을 정리하세요. (마크다운 지원)", 
                    value=q_data['concept'], 
                    height=180, 
                    key=f"concept_area_{q_text}",
                    label_visibility="collapsed"
                )
                if q_data['concept']:
                    st.write("---")
                    st.markdown("#### 📖 개념 설명 (서식 적용 화면)")
                    with st.container(border=True):
                        st.markdown(format_readable_text(q_data['concept']))
            else:
                if q_data['concept']:
                    with st.container(border=True):
                        st.markdown(format_readable_text(q_data['concept']))
                else:
                    st.caption("작성된 개념 설명이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")
    
        # -------------------------------------------------------------------------
        # TAB 2: 모범 답안
        # -------------------------------------------------------------------------
        with tab2:
            st.markdown("### 2. 실제 시험 모범 답안")
            st.info("실제 시험 채점 기준에 맞춰 개요, 본론, 결론 형식으로 서술형 답안을 작성합니다.")
            
            key_hide_answer = f"hide_answer_{q_text}"
            if key_hide_answer not in st.session_state:
                st.session_state[key_hide_answer] = True
            is_answer_hidden = st.session_state[key_hide_answer]
    
            col_t2, col_h2, col_b2 = st.columns([68, 16, 16], vertical_alignment="center")
            with col_t2:
                st.write("")
            with col_h2:
                toggle_label = "👁️ 입력창 보이기" if is_answer_hidden else "🙈 입력창 숨기기"
                if st.button(toggle_label, key=f"btn_toggle_answer_{q_text}", use_container_width=True):
                    if f"answer_area_{q_text}" in st.session_state:
                        st.session_state.user_data[q_text]['answer'] = st.session_state[f"answer_area_{q_text}"]
                        save_user_data(st.session_state.user_data)
                    st.session_state[key_hide_answer] = not is_answer_hidden
                    st.rerun()
            with col_b2:
                if st.button("💾 저장하기", key=f"save_answer_{q_text}", type="primary", use_container_width=True):
                    if f"answer_area_{q_text}" in st.session_state:
                        st.session_state.user_data[q_text]['answer'] = st.session_state[f"answer_area_{q_text}"]
                    save_user_data(st.session_state.user_data)
                    st.toast("모범 답안이 저장되었습니다!")
    
            if not is_answer_hidden:
                answer_text = st.text_area(
                    "시험 양식에 맞춘 모범 답안을 작성하세요. (마크다운 지원)", 
                    value=q_data['answer'], 
                    height=180, 
                    key=f"answer_area_{q_text}",
                    label_visibility="collapsed"
                )
                if q_data['answer']:
                    st.write("---")
                    st.markdown("#### 📄 모범 답안 (서식 적용 화면)")
                    with st.container(border=True):
                        st.markdown(format_readable_text(q_data['answer']))
            else:
                if q_data['answer']:
                    with st.container(border=True):
                        st.markdown(format_readable_text(q_data['answer']))
                else:
                    st.caption("작성된 모범 답안이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")
    
        # -------------------------------------------------------------------------
        # TAB 3: 추가 자료
        # -------------------------------------------------------------------------
        with tab3:
            st.markdown("### 3. 추가 자료 및 메모")
            st.info("관련 수식, 외부 논문 출처, 참고 웹페이지 링크 및 개인적인 학습 메모를 작성합니다.")
            
            key_hide_extra = f"hide_extra_{q_text}"
            if key_hide_extra not in st.session_state:
                st.session_state[key_hide_extra] = True
            is_extra_hidden = st.session_state[key_hide_extra]
    
            col_t3, col_h3, col_b3 = st.columns([68, 16, 16], vertical_alignment="center")
            with col_t3:
                st.write("")
            with col_h3:
                toggle_label = "👁️ 입력창 보이기" if is_extra_hidden else "🙈 입력창 숨기기"
                if st.button(toggle_label, key=f"btn_toggle_extra_{q_text}", use_container_width=True):
                    if f"extra_area_{q_text}" in st.session_state:
                        st.session_state.user_data[q_text]['extra'] = st.session_state[f"extra_area_{q_text}"]
                        save_user_data(st.session_state.user_data)
                    st.session_state[key_hide_extra] = not is_extra_hidden
                    st.rerun()
            with col_b3:
                if st.button("💾 저장하기", key=f"save_extra_{q_text}", type="primary", use_container_width=True):
                    if f"extra_area_{q_text}" in st.session_state:
                        st.session_state.user_data[q_text]['extra'] = st.session_state[f"extra_area_{q_text}"]
                    save_user_data(st.session_state.user_data)
                    st.toast("추가 자료가 저장되었습니다!")
    
            if not is_extra_hidden:
                extra_text = st.text_area(
                    "참고할 추가 메모나 링크를 입력하세요. (마크다운 지원)", 
                    value=q_data['extra'], 
                    height=180, 
                    key=f"extra_area_{q_text}",
                    label_visibility="collapsed"
                )
                if q_data['extra']:
                    st.write("---")
                    st.markdown("#### 📎 추가 자료 및 메모 (서식 적용 화면)")
                    with st.container(border=True):
                        st.markdown(format_readable_text(q_data['extra']))
            else:
                if q_data['extra']:
                    with st.container(border=True):
                        st.markdown(format_readable_text(q_data['extra']))
                else:
                    st.caption("작성된 추가 자료가 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")
    
        # -------------------------------------------------------------------------
        # TAB 4: 구글 검색
        # -------------------------------------------------------------------------
        with tab4:
            st.markdown("### 4. 구글 검색")
            st.info("문제를 해결하기 위해 관련된 최신 technical자료 및 도면 정보를 구글에서 바로 검색합니다.")
            
            search_query = st.text_input("검색어 입력", value=q_text)
            
            if search_query:
                encoded_query = search_query.replace(" ", "+")
                search_url = f"[https://www.google.com/search?q=](https://www.google.com/search?q=){encoded_query}"
                
                st.markdown(
                    f"""
                    <a href="{search_url}" target="_blank">
                        <button style="background-color:#4285F4; color:white; border:none; padding:8px 16px; border-radius:5px; cursor:pointer; font-size:15px; font-weight:bold;">
                            🌐 구글에서 검색 결과 보기 (새 창)
                        </button>
                    </a>
                    """, 
                    unsafe_allow_html=True
                )
    
        # -------------------------------------------------------------------------
        # TAB 5: 이미지 및 설명 자료
        # -------------------------------------------------------------------------
        with tab5:
            st.markdown("### 5. 이미지 및 설명 자료")
            st.info("금형 구조 도면, 3D CAD 캡처, 시뮬레이션 결과 이미지와 관련 설명을 함께 등록 및 확인할 수 있습니다.")
            
            # 1. 신규 이미지 업로드 및 설명 저장 영역
            with st.expander("➕ 새 이미지 및 설명 추가하기", expanded=False):
                uploaded_img = st.file_uploader(
                    "이미지 파일 업로드", 
                    type=["png", "jpg", "jpeg", "webp", "gif"], 
                    key=f"uploader_{q_text}"
                )
                img_caption = st.text_input("이미지 제목/캡션 (선택)", key=f"img_cap_{q_text}")
                img_note = st.text_area(
                    "이미지 설명 내용 입력 (마크다운 서식 지원)", 
                    height=150, 
                    key=f"img_note_{q_text}"
                )
                
                if st.button("💾 이미지 및 설명 저장", key=f"btn_save_img_{q_text}", type="primary"):
                    if uploaded_img is not None:
                        saved_filename = f"{int(time.time())}_{uploaded_img.name}"
                        file_path = os.path.join(IMAGE_DIR, saved_filename)
                        
                        with open(file_path, "wb") as f:
                            f.write(uploaded_img.getbuffer())
                        
                        new_image_item = {
                            "file_path": file_path,
                            "caption": img_caption if img_caption else uploaded_img.name,
                            "note": img_note
                        }
                        
                        st.session_state.user_data[q_text]['image_notes'].append(new_image_item)
                        save_user_data(st.session_state.user_data)
                        st.toast("이미지와 설명이 성공적으로 저장되었습니다!")
                        st.rerun()
                    else:
                        st.warning("업로드할 이미지 파일을 선택해 주세요.")
    
            st.write("---")
    
            # 2. 저장된 이미지 목록 및 6:4 상세 보기 영역
            image_notes_list = q_data.get('image_notes', [])
    
            if not image_notes_list:
                st.caption("저장된 이미지 자료가 없습니다. 상단의 '➕ 새 이미지 및 설명 추가하기'를 눌러 자료를 등록해 보세요.")
            else:
                st.markdown("#### 🖼️ 저장된 이미지 목록")
                
                options_label = [f"[{i+1}] {item.get('caption', '제목 없음')}" for i, item in enumerate(image_notes_list)]
                
                selected_img_idx = st.selectbox(
                    "저장된 이미지를 선택하세요",
                    options=range(len(image_notes_list)),
                    format_func=lambda i: options_label[i],
                    key=f"select_img_item_{q_text}"
                )
                
                selected_item = image_notes_list[selected_img_idx]
                
                st.write("")
                col_img, col_text = st.columns([6, 4], gap="medium")
    
                with col_img:
                    st.markdown(f"##### 📷 {selected_item.get('caption', '이미지')}")
                    if os.path.exists(selected_item['file_path']):
                        st.image(selected_item['file_path'], use_container_width=True)
                    else:
                        st.error("저장된 이미지 파일을 찾을 수 없습니다.")
    
                with col_text:
                    st.markdown("##### 📝 이미지 설명 내용")
                    note_content = selected_item.get('note', '')
                    if note_content:
                        with st.container(border=True):
                            st.markdown(format_readable_text(note_content))
                    else:
                        st.caption("작성된 설명 내용이 없습니다.")
                    
                    st.write("---")
                    if st.button("🗑️ 선택된 이미지 삭제", key=f"del_img_{selected_img_idx}_{q_text}"):
                        if os.path.exists(selected_item['file_path']):
                            try:
                                os.remove(selected_item['file_path'])
                            except Exception:
                                pass
                        st.session_state.user_data[q_text]['image_notes'].pop(selected_img_idx)
                        save_user_data(st.session_state.user_data)
                        st.toast("이미지 자료가 삭제되었습니다.")
                        st.rerun()
            pass


    # st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            
elif st.session_state.main_mode == "note":

    st.markdown("### 📖 서술형 학습노트 관리")
    
    # 백업 및 데이터 관리 (Expander)
    with st.expander("💾 노트 데이터 백업 / 복원 (JSON 파일)"):
        col_export, col_import = st.columns(2)
        
        # 1) 내 컴퓨터로 백업 다운로드
        with col_export:
            notes_json_str = json.dumps(st.session_state.notes, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 노트 데이터 백업 다운로드",
                data=notes_json_str,
                file_name="notes_backup.json",
                mime="application/json",
                use_container_width=True
            )
        
        # 2) 파일 올려서 복원하기
        with col_import:
            uploaded_backup = st.file_uploader("📤 백업 JSON 파일 불러오기", type=["json"], key="restore_notes_uploader")
            if uploaded_backup is not None:
                if st.button("🔄 데이터 복원 적용", type="primary", use_container_width=True):
                    try:
                        loaded_backup_notes = json.load(uploaded_backup)
                        if isinstance(loaded_backup_notes, list):
                            st.session_state.notes = loaded_backup_notes
                            save_notes(st.session_state.notes)
                            st.success("성공적으로 노트를 복원했습니다!")
                            st.rerun()
                        else:
                            st.error("올바른 노트 백업 파일 형식이 아닙니다.")
                    except Exception as e:
                        st.error(f"복원 실패: {e}")
    # -------------------------------------------------------------
    # 1) 노트목록 및 편집 버튼 영역 (상단 여백을 주어 잘림 방지)
    # -------------------------------------------------------------
    st.markdown("""
        <style>
        /* 노트 목록 / 편집 버튼 컨테이너 상단 여백 추가 */
        .note-header-container {
            margin-top: 15px;      /* 상단 여백을 두어 잘림 방지 */
            margin-bottom: 3px;
        }
        
        /* 아래 제목의 상하 여백 줄이기 */
        .custom-title {
            margin-top: 3px !important;    /* 위 여백 축소 */
            margin-bottom: 3px !important; /* 아래 여백 축소 */
            font-size: 1.4rem;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
 
    # -------------------------------------------------------------
    # 3) 상하 여백을 줄인 제목 배치
    # -------------------------------------------------------------
    # st.subheader 대신 커스텀 클래스가 적용된 HTML 제목 사용
    st.markdown('<div class="custom-title">📌 노트 </div>', unsafe_allow_html=True)
   
    # 이어서 기존 노트 본문 및 수정 폼 코드 작성...
    # -------------------------------------------------------------------------
    # 학습노트 내 세부 상태 초기화 (list: 목록, detail: 상세보기, edit: 편집)
    # -------------------------------------------------------------------------
    if "selected_note_id" not in st.session_state:
        st.session_state.selected_note_id = None
    if "note_sub_mode" not in st.session_state:
        st.session_state.note_sub_mode = "list"

    # =========================================================================
    # [화면 1] 노트 상세 보기 화면 (전체 화면 전환)
    # =========================================================================
    if st.session_state.note_sub_mode == "detail" and st.session_state.selected_note_id:
        note = next((n for n in st.session_state.notes if n["id"] == st.session_state.selected_note_id), None)
        
        if note:
            # 1. 상단 컨트롤 바: [노트목록], [편집] 버튼 나란히 배치
            col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 7])
            with col_btn1:
                if st.button("📋 노트목록", use_container_width=True):
                    st.session_state.note_sub_mode = "list"
                    st.session_state.selected_note_id = None
                    st.rerun()
            with col_btn2:
                if st.button("✏️ 편집", type="primary", use_container_width=True):
                    st.session_state.note_sub_mode = "edit"
                    st.rerun()

            st.markdown("---")

            # 2. 본문 영역: 수식 자동 보정 포맷 적용
            if note.get("content"):
                st.markdown(format_readable_text(note["content"]))
            else:
                st.info("작성된 노트 내용이 없습니다.")

            # 3. 첨부 이미지 다중 표시
            imgs = note.get("images", [])
            if not imgs and note.get("image_base64"):
                imgs = [note["image_base64"]]

            if imgs:
                st.markdown("---")
                st.markdown("**🖼️ 첨부 이미지**")
                img_cols = st.columns(min(len(imgs), 3))
                for idx, b64_img in enumerate(imgs):
                    try:
                        img_bytes = base64.b64decode(b64_img)
                        with img_cols[idx % 3]:
                            st.image(img_bytes, use_container_width=True)
                    except Exception:
                        pass

            # 4. 웹 링크 다중 표시
            links = note.get("links", [])
            if not links and note.get("link"):
                links = [note["link"]]

            if links:
                st.markdown("---")
                st.markdown("**🔗 관련 링크**")
                for link in links:
                    st.markdown(f"- [{link}]({link})")

        else:
            st.error("해당 노트를 찾을 수 없습니다.")
            if st.button("📋 노트목록으로 돌아가기"):
                st.session_state.note_sub_mode = "list"
                st.session_state.selected_note_id = None
                st.rerun()

    # =========================================================================
    # [화면 2] 노트 편집 화면 (제목, 분류, 내용, 이미지, 링크 수정)
    # =========================================================================
    elif st.session_state.note_sub_mode == "edit" and st.session_state.selected_note_id:
        note = next((n for n in st.session_state.notes if n["id"] == st.session_state.selected_note_id), None)
        
        if note:
            col_b1, _ = st.columns([1.5, 8.5])
            with col_b1:
                if st.button("⬅️ 취소", use_container_width=True):
                    st.session_state.note_sub_mode = "detail"
                    st.rerun()

            st.subheader("✏️ 노트 편집")
            
            existing_links = note.get("links", [])
            if not existing_links and note.get("link"):
                existing_links = [note["link"]]
            existing_links_str = "\n".join(existing_links)

            existing_imgs = note.get("images", [])
            if not existing_imgs and note.get("image_base64"):
                existing_imgs = [note["image_base64"]]

            with st.form(key=f"edit_form_{note['id']}"):
                cat_list = ["사출금형", "프레스금형", "재료/열처리", "가공/정밀측정", "기타기술"]
                cat_idx = cat_list.index(note["category"]) if note.get("category") in cat_list else 0
                edit_cat = st.selectbox("분류 (키워드)", cat_list, index=cat_idx)
                edit_title = st.text_input("노트 제목", value=note.get("title", ""))
                
                # 수식 입력 안내가 포함된 본문 영역
                edit_content = st.text_area(
                    "노트 내용 (마크다운 및 수식 지원)", 
                    value=note.get("content", ""), 
                    height=240,
                    help="수식은 $$ F_{clamp} = P_{cavity} \\times A_{projected} $$ 형식으로 작성하면 더욱 깔끔하게 렌더링됩니다."
                )
                
                edit_links_raw = st.text_area(
                    "웹 링크 (URL - 줄바꿈으로 여러 개 입력)", 
                    value=existing_links_str, 
                    height=90, 
                    placeholder="https://example.com/1\nhttps://example.com/2"
                )
                
                uploaded_imgs = st.file_uploader("이미지 추가 첨부 (복수 선택 가능)", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)
                
                keep_imgs = []
                if existing_imgs:
                    st.caption("기존 첨부 이미지 (삭제하려는 항목에 체크하세요):")
                    img_cols = st.columns(3)
                    for img_idx, b64_img in enumerate(existing_imgs):
                        with img_cols[img_idx % 3]:
                            try:
                                img_bytes = base64.b64decode(b64_img)
                                st.image(img_bytes, use_container_width=True)
                            except Exception:
                                pass
                            is_delete = st.checkbox("삭제", key=f"chk_del_edit_{note['id']}_{img_idx}")
                            if not is_delete:
                                keep_imgs.append(b64_img)

                col_save, col_del = st.columns([1, 1])
                with col_save:
                    submit_edit = st.form_submit_button("💾 수정 저장", type="primary", use_container_width=True)
                with col_del:
                    delete_note = st.form_submit_button("🗑️ 노트 삭제", use_container_width=True)

                if submit_edit:
                    if uploaded_imgs:
                        for img_f in uploaded_imgs:
                            b64_str = convert_image_to_base64(img_f)
                            if b64_str:
                                keep_imgs.append(b64_str)

                    note["category"] = edit_cat
                    note["title"] = edit_title
                    note["content"] = edit_content
                    note["links"] = [line.strip() for line in edit_links_raw.split('\n') if line.strip()]
                    note["images"] = keep_imgs
                    note["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    save_notes(st.session_state.notes)
                    st.toast("노트가 성공적으로 수정되었습니다!")
                    st.session_state.note_sub_mode = "detail"
                    st.rerun()

                if delete_note:
                    st.session_state.notes = [n for n in st.session_state.notes if n["id"] != note["id"]]
                    save_notes(st.session_state.notes)
                    st.toast("노트가 삭제되었습니다.")
                    st.session_state.note_sub_mode = "list"
                    st.session_state.selected_note_id = None
                    st.rerun()

    # =========================================================================
    # [화면 3] 노트 목록 화면 (List View)
    # =========================================================================
    else:
        st.markdown("""
            <style>
            div[data-testid="stColumn"] button {
                text-align: left !important;
                justify-content: flex-start !important;
                padding-top: 2px !important;
                padding-bottom: 2px !important;
                min-height: 32px !important;
                height: 32px !important;
                font-size: 0.88rem !important;
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.4rem !important;
                align-items: center !important;
            }
            div[data-testid="stElementContainer"] {
                margin-bottom: 0px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("<h1 style='margin-bottom: 0.5rem;'>📖 학습노트 관리</h1>", unsafe_allow_html=True)
        st.write("나만의 금형기술사 서브노트 및 개념 정리 노트 목록입니다.")

        col_search, col_btn1, col_btn2 = st.columns([3, 1.2, 1.2])
        with col_search:
            note_search_kw = st.text_input("🔍 노트 검색", placeholder="제목, 분류, 내용 키워드 입력", label_visibility="collapsed")
        with col_btn1:
            show_create_form = st.checkbox("➕ 새 노트 작성", value=False)
        with col_btn2:
            if st.button("💾 전체 저장", type="primary", use_container_width=True):
                save_notes(st.session_state.notes)
                st.toast("학습노트가 성공적으로 저장되었습니다!", icon="✅")

        if show_create_form:
            with st.expander("📝 새 학습노트 등록", expanded=True):
                with st.form(key="new_note_form", clear_on_submit=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        new_cat = st.selectbox("분류", ["사출금형", "프레스금형", "재료/열처리", "가공/정밀측정", "기타기술"])
                    with c2:
                        new_title = st.text_input("노트 제목", placeholder="예: 2단 방출 시스템의 구조 및 특성")
                    
                    new_content = st.text_area(
                        "노트 내용 (마크다운 및 수식 지원)", 
                        height=180, 
                        placeholder="예시 수식 작성법:\n$$ F_{clamp} = P_{cavity} \\times A_{projected} $$"
                    )
                    
                    new_links_raw = st.text_area("웹 링크 (URL - 줄바꿈으로 여러 개 입력)", height=80, placeholder="https://example.com/1\nhttps://example.com/2")
                    uploaded_imgs = st.file_uploader("이미지 첨부 (복수 선택 가능)", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)
                    
                    submit_note = st.form_submit_button("💾 노트 등록", type="primary")
                    
                    if submit_note:
                        if not new_title.strip():
                            st.error("노트 제목을 입력해주세요.")
                        else:
                            links_list = [line.strip() for line in new_links_raw.split('\n') if line.strip()]
                            imgs_list = []
                            if uploaded_imgs:
                                for img_f in uploaded_imgs:
                                    b64_str = convert_image_to_base64(img_f)
                                    if b64_str:
                                        imgs_list.append(b64_str)

                            new_entry = {
                                "id": int(time.time()),
                                "category": new_cat,
                                "title": new_title.strip(),
                                "content": new_content,
                                "links": links_list,
                                "images": imgs_list,
                                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            st.session_state.notes.insert(0, new_entry)
                            save_notes(st.session_state.notes)
                            st.success("새 학습노트가 추가되었습니다!")
                            st.rerun()

        # 검색 필터
        filtered_notes = st.session_state.notes
        if note_search_kw.strip():
            kw = note_search_kw.strip().lower()
            filtered_notes = [
                n for n in filtered_notes
                if kw in n.get("title", "").lower() or kw in n.get("content", "").lower() or kw in n.get("category", "").lower()
            ]

        # 고정 상단 헤더 줄
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        h_col1, h_col2, h_col3 = st.columns([3, 7, 2.5])
        with h_col1:
            st.markdown("<div style='font-weight: bold; color: #444; font-size: 0.85rem; padding-left: 4px;'>📂 분류</div>", unsafe_allow_html=True)
        with h_col2:
            st.markdown("<div style='font-weight: bold; color: #444; font-size: 0.85rem; padding-left: 4px;'>📌 노트 제목</div>", unsafe_allow_html=True)
        with h_col3:
            st.markdown("<div style='font-weight: bold; color: #444; font-size: 0.85rem; text-align: right; padding-right: 4px;'>🕒 수정일</div>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 4px 0 6px 0; border: none; border-top: 2px solid #333;'/>", unsafe_allow_html=True)

        # 컴팩트 노트 목록
        if not filtered_notes:
            st.info("등록된 학습노트가 없거나 검색 결과가 없습니다.")
        else:
            for note in filtered_notes:
                has_img = "🖼️ " if (note.get("images") or note.get("image_base64")) else ""
                has_link = "🔗 " if (note.get("links") or note.get("link")) else ""
                
                col_cat, col_title, col_date = st.columns([3, 7, 2.5])
                
                with col_cat:
                    if st.button(f"{note['category']}", key=f"note_cat_{note['id']}", use_container_width=True):
                        st.session_state.selected_note_id = note["id"]
                        st.session_state.note_sub_mode = "detail"
                        st.rerun()
                
                with col_title:
                    if st.button(f"{note['title']} {has_img}{has_link}", key=f"note_title_{note['id']}", use_container_width=True):
                        st.session_state.selected_note_id = note["id"]
                        st.session_state.note_sub_mode = "detail"
                        st.rerun()
                
                with col_date:
                    st.markdown(
                        f"<div style='text-align: right; line-height: 32px; color: #666; font-size: 0.82rem;'>"
                        f"{note.get('updated_at', '')}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
