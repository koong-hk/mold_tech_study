import streamlit as st
import pandas as pd
import json
import os
import re
import time
from datetime import datetime
import base64

NOTES_FILE = "notes.json"

# 학습노트 로드 함수
def load_notes():
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# 학습노트 저장 함수
def save_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

# 이미지를 base64 텍스트로 인코딩하는 함수
def convert_image_to_base64(uploaded_file):
    if uploaded_file is not None:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return None

# 세션 상태 초기화 (기본 모드: exam)
if "main_mode" not in st.session_state:
    st.session_state.main_mode = "exam"  # 'exam' (기출문제) 또는 'note' (학습노트)

if "notes" not in st.session_state:
    st.session_state.notes = load_notes()


# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 CSS 적용
# -----------------------------------------------------------------------------
st.set_page_config(page_title="금형기술사 학습 시스템", layout="wide")

IMAGE_DIR = "saved_images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR, exist_ok=True)

st.markdown("""
    <style>
        /* 1. 메인 영역 상단 여백 최소화 */
        .block-container {
            padding-top: 2.0rem !important;
            padding-bottom: 1.5rem !important;
        }
        
        /* 2. 제목 글자 크기 및 여백 축소 */
        div[data-testid="stMarkdownContainer"] h1 {
            font-size: 1.4rem !important;
            margin-top: 0px !important;
            margin-bottom: 0.8rem !important;
        }

        /* 3. 좌측 사이드바 폭 및 수직 수평 간격 대폭 축소 */
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }
        
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 0.2rem !important;
            padding-top: 0.2rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stElementContainer"] {
            margin-bottom: 2px !important;
        }

        section[data-testid="stSidebar"] hr {
            margin-top: 0.4rem !important;
            margin-bottom: 0.4rem !important;
        }

        /* 4. 파일 업로더 너비 100% 확대, 높이 단축 및 여백 최소화 */
        div[data-testid="stFileUploader"] {
            width: 100% !important;
            padding: 0px !important;
            margin-bottom: 0.2rem !important;
        }

        div[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] {
            padding: 4px 8px !important;
            min-height: 48px !important;
            width: 100% !important;
        }

        div[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] > div {
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }

        /* 5. 버튼 스타일 정의 (사이드바 버튼 너비 100% 및 밀도 높이기) */
        div.stButton > button {
            display: inline-flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            margin-top: 2px !important;
            margin-bottom: 2px !important;
            padding: 4px 12px !important;
            min-height: 32px !important;
            height: 32px !important;
        }
        
        section[data-testid="stSidebar"] div.stButton > button {
            width: 100% !important;
            font-size: 0.85rem !important;
        }

        div.stButton > button p {
            margin: 0 !important;
            padding: 0 !important;
            text-align: center !important;
            font-size: 0.85rem !important;
        }

        /* 6. 사이드바 필터 라벨 및 드롭다운 밀도 조정 */
        section[data-testid="stSidebar"] label {
            text-align: left !important;
            justify-content: flex-start !important;
            margin-bottom: 0px !important;
            padding-bottom: 0px !important;
            padding-top: 0px !important;
        }
        
        section[data-testid="stSidebar"] label p {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            margin: 0 !important;
            padding: 0 !important;
            text-align: left !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSelectbox"],
        section[data-testid="stSidebar"] div[data-testid="stMultiSelect"],
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] {
            margin-bottom: 4px !important;
            margin-top: 0px !important;
            padding: 0px !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
            min-height: 32px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            padding-left: 6px !important;
            padding-right: 6px !important;
            display: flex !important;
            align-items: center !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] * {
            font-size: 0.82rem !important;
            line-height: 1.1 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCheckbox"] {
            margin-top: 2px !important;
            margin-bottom: 2px !important;
        }

        /* 7. 상세 페이지 문제 박스와 하단 탭 사이 간격 */
        div[data-testid="stTabs"] {
            margin-top: 1.0rem !important;
        }

        /* 8. 탭 상단 우측 버튼 정렬 */
        div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) div[data-testid="stButton"],
        div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] {
            display: flex !important;
            width: 100% !important;
        }
        
        div[data-testid="stTabs"] div[data-testid="stButton"] > button {
            width: 100% !important;
        }

        /* 9. 본문 마크다운 서식 조정 */
        div[data-testid="stMarkdownContainer"] p {
            line-height: 1.85 !important;
            margin-bottom: 0.9em !important;
            word-break: keep-all !important;
            font-size: 1.02rem !important;
        }

        div[data-testid="stMarkdownContainer"] ol {
            list-style-type: decimal !important;
            margin-left: 1.8em !important;
            padding-left: 0.2em !important;
            margin-bottom: 0.8em !important;
        }
        
        div[data-testid="stMarkdownContainer"] ul {
            list-style-type: disc !important;
            margin-left: 1.8em !important;
            padding-left: 0.2em !important;
            margin-bottom: 0.8em !important;
        }

        div[data-testid="stMarkdownContainer"] li {
            line-height: 1.8 !important;
            margin-bottom: 0.4em !important;
            word-break: keep-all !important;
        }
    </style>
""", unsafe_allow_html=True)

USER_DATA_FILE = "user_study_data.json"

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def format_readable_text(text):
    """가독성 향상을 위한 마크다운 텍스트 자동 가공 함수"""
    if not text:
        return ""
    
    lines = text.splitlines()
    formatted_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('#', '|', '```', '---')) or not stripped:
            formatted_lines.append(line)
            continue
        
        sentences = re.split(r'(?<=\.)\s+', line)
        if len(sentences) > 1:
            processed_line = ""
            curr_len = 0
            for idx, s in enumerate(sentences):
                curr_len += len(s)
                if curr_len >= 45 and s.endswith('.'):
                    processed_line += s + "  \n"
                    curr_len = 0
                else:
                    processed_line += s + (" " if idx < len(sentences) - 1 else "")
            formatted_lines.append(processed_line)
        else:
            formatted_lines.append(line)
            
    return "\n".join(formatted_lines)

if "user_data" not in st.session_state or not isinstance(st.session_state.user_data, dict):
    st.session_state.user_data = load_user_data()
if "show_detail" not in st.session_state:
    st.session_state.show_detail = False
if "current_q" not in st.session_state:
    st.session_state.current_q = None

# -----------------------------------------------------------------------------
# 2. 데이터 불러오기
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
# 3. 사이드바 레이아웃 (파일 업로드 -> 메인 모드 버튼 -> 검색 및 필터)
# -----------------------------------------------------------------------------
with st.sidebar:
    # 1. 상단 100% 폭 파일 업로더
    uploaded_file = st.file_uploader("📂 엑셀 파일 업로드", type=['xlsx', 'xls'])
    
    # 2. 모드 전환 버튼 (기출문제 / 학습노트)
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

    # 3. 키워드 검색 및 필터 컨트롤 (간격 최소화)
    search_keyword = st.text_input("문제 키워드 검색", placeholder="검색어 입력...", label_visibility="collapsed")

    df = load_excel_data(uploaded_file)

    # 데이터 전처리
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

# -----------------------------------------------------------------------------
# 4. 필터링 조건 적용
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
# 5. 우측 화면 (리스트 뷰 vs 상세 뷰 vs 학습노트)
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
            
elif st.session_state.main_mode == "note":
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

            # 2. 본문 영역: 노트 내용만 표시
            if note.get("content"):
                st.markdown(note["content"])
            else:
                st.info("작성된 노트 내용이 없습니다.")

            # 3. 첨부 이미지 표시 (💡 원본 크기로 표시되도록 옵션 수정)
            if note.get("image_base64"):
                st.markdown("---")
                st.markdown("**🖼️ 첨부 이미지**")
                img_bytes = base64.b64decode(note["image_base64"])
                st.image(img_bytes)  # use_container_width=True 옵션을 제거하여 원본 사이즈 유지

            # 4. 웹 링크 표시
            if note.get("link"):
                st.markdown("---")
                st.markdown("**🔗 관련 링크**")
                st.markdown(f"[{note['link']}]({note['link']})")

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
            
            with st.form(key=f"edit_form_{note['id']}"):
                cat_list = ["사출금형", "프레스금형", "재료/열처리", "가공/정밀측정", "기타기술"]
                cat_idx = cat_list.index(note["category"]) if note.get("category") in cat_list else 0
                edit_cat = st.selectbox("분류 (키워드)", cat_list, index=cat_idx)
                edit_title = st.text_input("노트 제목", value=note.get("title", ""))
                edit_content = st.text_area("노트 내용 (마크다운 지원)", value=note.get("content", ""), height=220)
                edit_link = st.text_input("웹 링크 (URL)", value=note.get("link", ""), placeholder="https://...")
                
                uploaded_img = st.file_uploader("이미지 첨부/교체", type=['png', 'jpg', 'jpeg', 'webp'])
                if note.get("image_base64") and not uploaded_img:
                    st.caption("※ 기존 첨부 이미지가 존재합니다. 새 파일을 올리면 기존 이미지가 대체됩니다.")

                col_save, col_del = st.columns([1, 1])
                with col_save:
                    submit_edit = st.form_submit_button("💾 수정 저장", type="primary", use_container_width=True)
                with col_del:
                    delete_note = st.form_submit_button("🗑️ 노트 삭제", use_container_width=True)

                if submit_edit:
                    note["category"] = edit_cat
                    note["title"] = edit_title
                    note["content"] = edit_content
                    note["link"] = edit_link
                    if uploaded_img is not None:
                        note["image_base64"] = convert_image_to_base64(uploaded_img)
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
        # 💡 [CSS] 상단 헤더 고정 느낌 부여 및 목록 줄 간격/높이 대폭 축소
        st.markdown("""
            <style>
            /* 버튼 좌측 정렬 및 여백/높이 밀도 높이기 */
            div[data-testid="stColumn"] button {
                text-align: left !important;
                justify-content: flex-start !important;
                padding-top: 2px !important;
                padding-bottom: 2px !important;
                min-height: 32px !important;
                height: 32px !important;
                font-size: 0.88rem !important;
            }
            
            /* 수평 블록(노트 줄) 간격 축소 */
            div[data-testid="stHorizontalBlock"] {
                gap: 0.4rem !important;
                align-items: center !important;
            }

            /* Streamlit 요소 하단 여백 제거하여 줄 간격 좁히기 */
            div[data-testid="stElementContainer"] {
                margin-bottom: 0px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("<h1 style='margin-bottom: 0.5rem;'>📖 학습노트 관리</h1>", unsafe_allow_html=True)
        st.write("나만의 금형기술사 서브노트 및 개념 정리 노트 목록입니다.")

        # 1. 컨트롤 바 (검색 / 새 노트 작성 / 전체 저장)
        col_search, col_btn1, col_btn2 = st.columns([3, 1.2, 1.2])
        with col_search:
            note_search_kw = st.text_input("🔍 노트 검색", placeholder="제목, 분류, 내용 키워드 입력", label_visibility="collapsed")
        with col_btn1:
            show_create_form = st.checkbox("➕ 새 노트 작성", value=False)
        with col_btn2:
            if st.button("💾 전체 저장", type="primary", use_container_width=True):
                save_notes(st.session_state.notes)
                st.toast("학습노트가 성공적으로 저장되었습니다!", icon="✅")

        # 새 노트 작성 양식 (체크 시에만 확장)
        if show_create_form:
            with st.expander("📝 새 학습노트 등록", expanded=True):
                with st.form(key="new_note_form", clear_on_submit=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        new_cat = st.selectbox("분류", ["사출금형", "프레스금형", "재료/열처리", "가공/정밀측정", "기타기술"])
                    with c2:
                        new_title = st.text_input("노트 제목", placeholder="예: 2단 방출 시스템의 구조 및 특성")
                    
                    new_content = st.text_area("노트 내용 (마크다운 지원)", height=160, placeholder="핵심 개념 및 답안 요약을 작성하세요.")
                    new_link = st.text_input("웹 링크 (URL)", placeholder="https://example.com")
                    uploaded_img = st.file_uploader("이미지 첨부", type=['png', 'jpg', 'jpeg', 'webp'])
                    
                    submit_note = st.form_submit_button("💾 노트 등록", type="primary")
                    
                    if submit_note:
                        if not new_title.strip():
                            st.error("노트 제목을 입력해주세요.")
                        else:
                            img_b64 = convert_image_to_base64(uploaded_img) if uploaded_img else None
                            new_entry = {
                                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                                "category": new_cat,
                                "title": new_title,
                                "content": new_content,
                                "link": new_link,
                                "image_base64": img_b64,
                                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            st.session_state.notes.insert(0, new_entry)
                            save_notes(st.session_state.notes)
                            st.success("새 학습노트가 추가되었습니다!")
                            st.rerun()

        # 검색 필터 적용
        filtered_notes = st.session_state.notes
        if note_search_kw.strip():
            kw = note_search_kw.strip().lower()
            filtered_notes = [
                n for n in filtered_notes
                if kw in n.get("title", "").lower() or kw in n.get("content", "").lower() or kw in n.get("category", "").lower()
            ]

        # 💡 [고정 상단 헤더 줄] 목록 맨 위에 컬럼 제목을 명확히 표시
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        h_col1, h_col2, h_col3 = st.columns([3, 7, 2.5])
        with h_col1:
            st.markdown("<div style='font-weight: bold; color: #444; font-size: 0.85rem; padding-left: 4px;'>📂 분류 (3)</div>", unsafe_allow_html=True)
        with h_col2:
            st.markdown("<div style='font-weight: bold; color: #444; font-size: 0.85rem; padding-left: 4px;'>📌 노트 제목 (7)</div>", unsafe_allow_html=True)
        with h_col3:
            st.markdown("<div style='font-weight: bold; color: #444; font-size: 0.85rem; text-align: right; padding-right: 4px;'>🕒 수정일</div>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 4px 0 6px 0; border: none; border-top: 2px solid #333;'/>", unsafe_allow_html=True)

        # 💡 [컴팩트 노트 목록]
        if not filtered_notes:
            st.info("등록된 학습노트가 없거나 검색 결과가 없습니다.")
        else:
            for note in filtered_notes:
                has_img = "🖼️ " if note.get("image_base64") else ""
                has_link = "🔗 " if note.get("link") else ""
                
                col_cat, col_title, col_date = st.columns([3, 7, 2.5])
                
                # 1. 분류 영역
                with col_cat:
                    if st.button(f"{note['category']}", key=f"note_cat_{note['id']}", use_container_width=True):
                        st.session_state.selected_note_id = note["id"]
                        st.session_state.note_sub_mode = "detail"
                        st.rerun()
                
                # 2. 제목 영역
                with col_title:
                    if st.button(f"{note['title']} {has_img}{has_link}", key=f"note_title_{note['id']}", use_container_width=True):
                        st.session_state.selected_note_id = note["id"]
                        st.session_state.note_sub_mode = "detail"
                        st.rerun()
                
                # 3. 수정일 영역 (32px 높이에 맞춰 세로 중앙 정렬)
                with col_date:
                    st.markdown(
                        f"<div style='text-align: right; line-height: 32px; color: #666; font-size: 0.82rem;'>"
                        f"{note['updated_at']}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
