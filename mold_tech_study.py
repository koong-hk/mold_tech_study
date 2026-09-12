import streamlit as st
import pandas as pd
import json
import os
import re
import time

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 CSS 적용 (목록 계층 차등화)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="금형기술사 학습 시스템", layout="wide")

IMAGE_DIR = "saved_images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR, exist_ok=True)

st.markdown("""
    <style>
        /* 1. 메인 영역 상단 여백 최소화 */
        .block-container {
            padding-top: 2.5rem !important;
            padding-bottom: 1.5rem !important;
        }
        
        /* 2. 제목 글자 크기 축소 */
        div[data-testid="stMarkdownContainer"] h1 {
            font-size: 1.5rem !important;
            margin-top: 5px !important;
            margin-bottom: 1.2rem !important;
        }

        /* 3. 좌측 파일 업로더 여백 조정 */
        div[data-testid="stFileUploader"] {
            width: 90% !important;
            padding: 0px !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stFileUploader"] section {
            padding: 6px 8px !important;
        }

        /* 4. 좌측 사이드바 전체 폭 (280px) */
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }

        /* 5. 기본 버튼 서식 */
        div.stButton > button {
            display: inline-flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            margin-top: 5px !important;
            margin-bottom: 5px !important;
            padding: 6px 16px !important;
        }
        div.stButton > button p {
            margin: 0 !important;
            padding: 0 !important;
            text-align: center !important;
        }

        /* 6. 사이드바 필터 간격 축소 */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 0.25rem !important;
        }

        section[data-testid="stSidebar"] label p {
            font-size: 0.88rem !important;
            font-weight: 600 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
            min-height: 32px !important;
            height: 32px !important;
            padding: 0 8px !important;
        }

        /* 7. 상세 페이지 문제 박스 및 탭 간격 */
        div[data-testid="stTabs"] {
            margin-top: 1.2rem !important;
        }

        div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) div[data-testid="stButton"],
        div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] {
            display: flex !important;
            width: 100% !important;
        }
        div[data-testid="stTabs"] div[data-testid="stButton"] > button {
            width: 100% !important;
        }
        
        /* 8. 마크다운 본문 기본 서식 */
        div[data-testid="stMarkdownContainer"] p {
            line-height: 1.85 !important;
            margin-bottom: 0.6em !important;
            word-break: keep-all !important;
            font-size: 1.02rem !important;
        }

        /* --- 계층별 목록 들여쓰기 및 번호 스타일링 --- */
        
        /* [순서 있는 목록] 1계층: 1. 2. 3. */
        div[data-testid="stMarkdownContainer"] ol {
            list-style-type: decimal !important;
            margin-left: 1.6em !important;
            padding-left: 0.2em !important;
            margin-bottom: 0.8em !important;
        }
        
        /* [순서 있는 목록] 2계층: 1) 2) 3) */
        div[data-testid="stMarkdownContainer"] ol ol {
            list-style-type: none !important;
            counter-reset: sub-item;
            margin-left: 1.2em !important;
            margin-top: 0.4em !important;
            margin-bottom: 0.6em !important;
            padding-left: 0px !important;
        }
        div[data-testid="stMarkdownContainer"] ol ol > li {
            counter-increment: sub-item;
            position: relative;
        }
        div[data-testid="stMarkdownContainer"] ol ol > li::before {
            content: counter(sub-item) ") ";
            font-weight: bold;
            display: inline-block;
            width: 1.6em;
            margin-left: -1.6em;
        }

        /* [순서 있는 목록] 3계층: ① ② ③ */
        @counter-style circled-numbers {
            system: numeric;
            symbols: "①" "②" "③" "④" "⑤" "⑥" "⑦" "⑧" "⑨" "⑩";
            suffix: " ";
        }
        div[data-testid="stMarkdownContainer"] ol ol ol {
            list-style-type: circled-numbers !important;
            margin-left: 1.4em !important;
            margin-top: 0.3em !important;
            padding-left: 0.5em !important;
        }

        /* 콜론 분리 후 본문 들여쓰기 클래스 */
        .indented-body {
            display: block;
            margin-left: 1.5rem;
            margin-top: 0.2rem;
            margin-bottom: 0.5rem;
            line-height: 1.85;
            word-break: keep-all;
        }

        /* 제목 서식 */
        div[data-testid="stMarkdownContainer"] h2 {
            margin-top: 1.4em !important;
            margin-bottom: 0.6em !important;
            border-bottom: 1px solid #4a5568;
            padding-bottom: 0.3em;
            color: #e2e8f0;
        }
        div[data-testid="stMarkdownContainer"] h3 {
            margin-top: 1.2em !important;
            margin-bottom: 0.5em !important;
            color: #63b3ed;
        }
        div[data-testid="stMarkdownContainer"] h4 {
            margin-top: 0.9em !important;
            margin-bottom: 0.4em !important;
            color: #cbd5e0;
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

def format_readable_text(text: str) -> str:
    """
    콜론(:) 분리 후 줄바꿈 및 본문 블록 들여쓰기 적용
    (단, 콜론 바로 뒤에 불릿 기호 * 또는 - 가 오는 경우는 제외)
    """
    if not text or not isinstance(text, str):
        return ""

    # 붙어버린 구분선과 제목 사전 강제 분리
    text = re.sub(r'---\s*', '\n---\n', text)
    text = re.sub(r'(#+)', r'\n\1', text)

    lines = text.splitlines()
    formatted_lines = []

    # 콜론 뒤에 불릿 기호(* 또는 -)가 오지 않는 경우에만 적용하는 정규식
    pattern = r':\s*(?!\*|-)'

    for line in lines:
        if ':' in line and not any(proto in line for proto in ['http://', 'https://']):
            subbed = re.sub(pattern, ':\n<span class="indented-body">', line)
            if '<span class="indented-body">' in subbed and not subbed.endswith('</span>'):
                subbed += '</span>'
            formatted_lines.append(subbed)
        else:
            formatted_lines.append(line)

    return "\n".join(formatted_lines)

if "user_data" not in st.session_state:
    st.session_state.user_data = load_user_data()
if "show_detail" not in st.session_state:
    st.session_state.show_detail = False
if "current_q" not in st.session_state:
    st.session_state.current_q = None

# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 (사이드바 엑셀 업로더 기능 복원)
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

uploaded_file = st.sidebar.file_uploader("기출문제 엑셀 파일", type=['xlsx', 'xls'])
df = load_excel_data(uploaded_file)

# -----------------------------------------------------------------------------
# 3. 데이터 전처리 및 학습 데이터 매핑
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 4. 좌측 화면 (사이드바 필터링)
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 문제 필터링")

rounds = ["전체"] + sorted(list(df['회차'].unique()), reverse=True)
unique_periods = sorted(list(df['교시'].unique()))
periods = ["전체", "2~4교시"] + [str(p) for p in unique_periods]
categories = ["전체"] + sorted(list(df['분류'].unique()))

sel_round = st.sidebar.selectbox("회차 선택", rounds)
sel_period = st.sidebar.selectbox("교시 선택", periods)
sel_category = st.sidebar.selectbox("분류 선택", categories)
sort_by_clicks = st.sidebar.checkbox("자주 본 문제 순으로 정렬 (조회수 ⇧)")

filtered_df = df.copy()

if sel_round != "전체":
    filtered_df = filtered_df[filtered_df['회차'] == sel_round]

if sel_period == "2~4교시":
    filtered_df = filtered_df[filtered_df['교시'].astype(str).isin(["2", "3", "4"])]
elif sel_period != "전체":
    filtered_df = filtered_df[filtered_df['교시'].astype(str) == str(sel_period)]

if sel_category != "전체":
    filtered_df = filtered_df[filtered_df['분류'] == sel_category]

if sort_by_clicks:
    filtered_df = filtered_df.sort_values(by='조회수', ascending=False)

# -----------------------------------------------------------------------------
# 5. 우측 화면 (리스트 뷰 vs 상세 뷰)
# -----------------------------------------------------------------------------
if not st.session_state.show_detail:
    st.markdown("<h1>📚 금형기술사 기출문제 리스트</h1>", unsafe_allow_html=True)
    st.write("필터링된 문제 목록입니다. 목록에서 문제를 클릭하면 하단 선택 영역에 자동으로 반영됩니다.")
    
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
        selected_rows = event.selection.get("rows", [])
        if selected_rows:
            row_idx = selected_rows[0]
            if row_idx < len(filtered_df):
                st.session_state["sb_question"] = filtered_df.iloc[row_idx]['문제']

        if "sb_question" not in st.session_state or st.session_state["sb_question"] not in q_options:
            st.session_state["sb_question"] = q_options[0]

        selected_q = st.selectbox("학습할 문제 선택", options=q_options, key="sb_question")
        
        if st.button("✏️ 선택한 문제 학습하기", type="primary", use_container_width=False):
            st.session_state.user_data[selected_q]['clicks'] += 1
            save_user_data(st.session_state.user_data)
            
            st.session_state.current_q = selected_q
            st.session_state.show_detail = True
            st.rerun()
    else:
        st.warning("조건에 해당하는 문제가 없습니다.")

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
                    st.markdown(format_readable_text(q_data['concept']), unsafe_allow_html=True)
        else:
            if q_data['concept']:
                with st.container(border=True):
                    st.markdown(format_readable_text(q_data['concept']), unsafe_allow_html=True)
            else:
                st.caption("작성된 개념 설명이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")

    # -------------------------------------------------------------------------
    # TAB 2: 모범 답안
    # -------------------------------------------------------------------------
    with tab2:
        st.markdown("### 2. 실제 시험 모범 답안")
        
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
                    st.markdown(format_readable_text(q_data['answer']), unsafe_allow_html=True)
        else:
            if q_data['answer']:
                with st.container(border=True):
                    st.markdown(format_readable_text(q_data['answer']), unsafe_allow_html=True)
            else:
                st.caption("작성된 모범 답안이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")

    # -------------------------------------------------------------------------
    # TAB 3: 추가 자료 및 메모
    # -------------------------------------------------------------------------
    with tab3:
        st.markdown("### 3. 추가 자료 및 메모")
        
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
                    st.markdown(format_readable_text(q_data['extra']), unsafe_allow_html=True)
        else:
            if q_data['extra']:
                with st.container(border=True):
                    st.markdown(format_readable_text(q_data['extra']), unsafe_allow_html=True)
            else:
                st.caption("작성된 추가 자료가 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")

    # -------------------------------------------------------------------------
    # TAB 4: 구글 검색
    # -------------------------------------------------------------------------
    with tab4:
        st.markdown("### 4. 구글 검색")
        
        search_query = st.text_input("검색어 입력", value=q_text)
        
        if search_query:
            encoded_query = search_query.replace(" ", "+")
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
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
                        st.markdown(format_readable_text(note_content), unsafe_allow_html=True)
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
