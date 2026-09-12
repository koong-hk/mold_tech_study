import streamlit as st
import pandas as pd
import json
import os

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 CSS 적용
# -----------------------------------------------------------------------------
st.set_page_config(page_title="금형기술사 학습 시스템", layout="wide")

st.markdown("""
    <style>
        /* 1. 메인 영역 상단 여백 최소화 (상단으로 이동) */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
        }
        
        /* 2. 제목 글자 크기 축소 (기본 H1 크기의 70% 수준) */
        div[data-testid="stMarkdownContainer"] h1 {
            font-size: 1.5rem !important;
            margin-top: 0px !important;
            margin-bottom: 0.5rem !important;
        }

        /* 3. 좌측 파일 업로더 가로/세로 여백 조정 */
        div[data-testid="stFileUploader"] {
            width: 100% !important;
            padding: 0px !important;
        }
        div[data-testid="stFileUploader"] section {
            padding: 6px 12px !important; /* 높이는 줄이고 좌우 여백은 동일하게 */
        }

        /* 4. 모든 버튼 안쪽 글자 가운데 정렬 & 8. 가로 사이즈 글자수에 맞춤 */
        div.stButton > button {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            margin-top: 0px !important;
            margin-bottom: 0px !important;
            width: auto !important; /* 글자 수에 맞추어 자동 조절 */
            padding: 4px 12px !important;
        }

        /* 5. 좌측 사이드바 필터 라벨 좌측 정렬 및 간격 축소 */
        div[data-testid="stSidebar"] label {
            text-align: left !important;
            justify-content: flex-start !important;
            margin-bottom: 2px !important;
            padding-bottom: 0px !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stSelectbox"] {
            margin-bottom: 6px !important;
        }
        
        /* 요소 간 기본 세로 간격(gap) 축소 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.3rem !important;
        }
        
        /* --------------------------------------------------------------------- */
        /* 서식 적용 화면의 계층별 들여쓰기 및 제목 간격 스타일 지정 */
        /* --------------------------------------------------------------------- */
        div[data-testid="stMarkdownContainer"] h2 {
            margin-top: 1.8em !important;
            margin-bottom: 0.8em !important;
            margin-left: 0px !important;
            text-indent: 0px !important;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.3em;
        }
        
        div[data-testid="stMarkdownContainer"] h3,
        div[data-testid="stMarkdownContainer"] h4,
        div[data-testid="stMarkdownContainer"] h5 {
            margin-left: 1.5em !important;     /* 1탭 들여쓰기 */
            margin-top: 1.2em !important;
            margin-bottom: 0.5em !important;
            text-indent: 0px !important;
        }
        
        div[data-testid="stMarkdownContainer"] p {
            margin-left: 3.0em !important;     /* 2탭 들여쓰기 */
            text-indent: 0px !important;
            line-height: 1.75 !important;
            margin-bottom: 0.8em !important;
            word-break: keep-all !important;
            font-size: 1.05rem !important;
        }
        
        div[data-testid="stMarkdownContainer"] ul,
        div[data-testid="stMarkdownContainer"] ol {
            margin-left: 3.0em !important;     /* 2탭 들여쓰기 */
            line-height: 1.75 !important;
            margin-bottom: 0.8em !important;
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

if "user_data" not in st.session_state:
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

uploaded_file = st.sidebar.file_uploader("기출문제 엑셀 파일 업로드", type=['xlsx', 'xls'])
df = load_excel_data(uploaded_file)

# -----------------------------------------------------------------------------
# 3. 데이터 전처리 및 학습 데이터 매핑
# -----------------------------------------------------------------------------
for q in df['문제']:
    if q not in st.session_state.user_data:
        st.session_state.user_data[q] = {
            'clicks': 0, 'importance': 3, 
            'concept': '', 'answer': '', 'extra': ''
        }

df['조회수'] = df['문제'].apply(lambda x: st.session_state.user_data[x]['clicks'])
df['중요도(별)'] = df['문제'].apply(lambda x: "⭐" * st.session_state.user_data[x]['importance'])

# -----------------------------------------------------------------------------
# 4. 좌측 화면 (사이드바 필터링)
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 문제 필터링")

rounds = ["전체"] + sorted(list(df['회차'].unique()), reverse=True)
periods = ["전체"] + sorted(list(df['교시'].unique()))
categories = ["전체"] + sorted(list(df['분류'].unique()))

sel_round = st.sidebar.selectbox("회차 선택", rounds)
sel_period = st.sidebar.selectbox("교시 선택", periods)
sel_category = st.sidebar.selectbox("분류 선택", categories)

sort_by_clicks = st.sidebar.checkbox("자주 본 문제 순으로 정렬 (조회수 ⇧)")

filtered_df = df.copy()
if sel_round != "전체": filtered_df = filtered_df[filtered_df['회차'] == sel_round]
if sel_period != "전체": filtered_df = filtered_df[filtered_df['교시'] == sel_period]
if sel_category != "전체": filtered_df = filtered_df[filtered_df['분류'] == sel_category]

if sort_by_clicks:
    filtered_df = filtered_df.sort_values(by='조회수', ascending=False)

# -----------------------------------------------------------------------------
# 5. 우측 화면 (리스트 뷰 vs 상세 뷰)
# -----------------------------------------------------------------------------
if not st.session_state.show_detail:
    # 2. 제목 글자 크기를 줄인 상단 제목
    st.markdown("<h1>📚 금형기술사 기출문제 리스트</h1>", unsafe_allow_html=True)
    st.write("필터링된 문제 목록입니다. 목록에서 문제를 클릭하면 하단 선택 영역에 자동으로 반영됩니다.")
    
    # 문제 리스트 출력
    event = st.dataframe(
        filtered_df[['회차', '교시', '분류', '문제', '조회수', '중요도(별)']], 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
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
        
        # 8. 버튼 가로 크기 자동 맞춤 (use_container_width=False 적용)
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
    
    # 1. 돌아가기 버튼
    if st.button("⬅️ 리스트로 돌아가기", use_container_width=False):
        st.session_state.show_detail = False
        st.session_state.current_q = None
        st.rerun()

    # 2. 문제 상자 및 중요도 영역 (80% : 20%)
    col_prob, col_star = st.columns([80, 20])

    with col_prob:
        # 6. 문제 배경 색상을 보다 어둡게 변경 (#2d3748 slate 색상 적용)
        st.markdown(f"""
            <div style="background-color:#2d3748; padding: 10px 15px; border-radius: 8px; margin-top: 4px;">
                <h3 style="color:#63b3ed; margin: 0px 0px 4px 0px; font-size: 90%; font-weight: bold; line-height: 1.3;">📝 {q_text}</h3>
                <span style="color:#e2e8f0; font-size: 85%;">현재 조회수: {q_data['clicks']}회</span>
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

    # 3. 하단 답안 영역 (4개 탭)
    tab1, tab2, tab3, tab4 = st.tabs(["📖 답안 개념 설명", "✅ 모범 답안", "📎 추가 자료 및 메모", "🔍 구글 검색"])

    # -------------------------------------------------------------------------
    # TAB 1: 개념 설명
    # -------------------------------------------------------------------------
    with tab1:
        key_hide_concept = f"hide_concept_{q_text}"
        # 7. 입력 창 숨김 상태를 디폴트(True)로 변경
        if key_hide_concept not in st.session_state:
            st.session_state[key_hide_concept] = True
        is_concept_hidden = st.session_state[key_hide_concept]

        col_t1, col_h1, col_b1 = st.columns([50, 25, 25], vertical_alignment="center")
        with col_t1:
            st.markdown("### 1. 답안 개념 설명")
        with col_h1:
            # 7. 입력창 보이기 버튼 명칭 적용
            toggle_label = "👁️ 입력창 보이기" if is_concept_hidden else "🙈 입력창 숨기기"
            if st.button(toggle_label, key=f"btn_toggle_concept_{q_text}", use_container_width=False):
                if f"concept_area_{q_text}" in st.session_state:
                    st.session_state.user_data[q_text]['concept'] = st.session_state[f"concept_area_{q_text}"]
                    save_user_data(st.session_state.user_data)
                st.session_state[key_hide_concept] = not is_concept_hidden
                st.rerun()
        with col_b1:
            # 8. 저장 버튼 자동 크기 맞춤
            if st.button("💾 저장하기", key=f"save_concept_{q_text}", type="primary", use_container_width=False):
                if f"concept_area_{q_text}" in st.session_state:
                    st.session_state.user_data[q_text]['concept'] = st.session_state[f"concept_area_{q_text}"]
                save_user_data(st.session_state.user_data)
                st.toast("개념 설명이 저장되었습니다!")

        if not is_concept_hidden:
            concept_text = st.text_area(
                "개념을 정리하세요. (제미나이 답변 복사-붙여넣기 및 마크다운 지원)", 
                value=q_data['concept'], 
                height=180, 
                key=f"concept_area_{q_text}",
                label_visibility="collapsed"
            )
            if q_data['concept']:
                st.write("---")
                st.markdown("#### 📖 개념 설명 (서식 적용 화면)")
                st.markdown(q_data['concept'])
        else:
            if q_data['concept']:
                st.markdown(q_data['concept'])
            else:
                st.info("작성된 개념 설명이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")

    # -------------------------------------------------------------------------
    # TAB 2: 모범 답안
    # -------------------------------------------------------------------------
    with tab2:
        key_hide_answer = f"hide_answer_{q_text}"
        # 7. 입력 창 숨김 상태를 디폴트(True)로 변경
        if key_hide_answer not in st.session_state:
            st.session_state[key_hide_answer] = True
        is_answer_hidden = st.session_state[key_hide_answer]

        col_t2, col_h2, col_b2 = st.columns([50, 25, 25], vertical_alignment="center")
        with col_t2:
            st.markdown("### 2. 실제 시험 모범 답안")
        with col_h2:
            toggle_label = "👁️ 입력창 보이기" if is_answer_hidden else "🙈 입력창 숨기기"
            if st.button(toggle_label, key=f"btn_toggle_answer_{q_text}", use_container_width=False):
                if f"answer_area_{q_text}" in st.session_state:
                    st.session_state.user_data[q_text]['answer'] = st.session_state[f"answer_area_{q_text}"]
                    save_user_data(st.session_state.user_data)
                st.session_state[key_hide_answer] = not is_answer_hidden
                st.rerun()
        with col_b2:
            if st.button("💾 저장하기", key=f"save_answer_{q_text}", type="primary", use_container_width=False):
                if f"answer_area_{q_text}" in st.session_state:
                    st.session_state.user_data[q_text]['answer'] = st.session_state[f"answer_area_{q_text}"]
                save_user_data(st.session_state.user_data)
                st.toast("모범 답안이 저장되었습니다!")

        if not is_answer_hidden:
            answer_text = st.text_area(
                "시험 양식에 맞춘 모범 답안을 작성하세요. (제미나이 답변 복사-붙여넣기 및 마크다운 지원)", 
                value=q_data['answer'], 
                height=180, 
                key=f"answer_area_{q_text}",
                label_visibility="collapsed"
            )
            if q_data['answer']:
                st.write("---")
                st.markdown("#### 📄 모범 답안 (서식 적용 화면)")
                st.markdown(q_data['answer'])
        else:
            if q_data['answer']:
                st.markdown(q_data['answer'])
            else:
                st.info("작성된 모범 답안이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")

    # -------------------------------------------------------------------------
    # TAB 3: 추가 자료
    # -------------------------------------------------------------------------
    with tab3:
        key_hide_extra = f"hide_extra_{q_text}"
        # 7. 입력 창 숨김 상태를 디폴트(True)로 변경
        if key_hide_extra not in st.session_state:
            st.session_state[key_hide_extra] = True
        is_extra_hidden = st.session_state[key_hide_extra]

        col_t3, col_h3, col_b3 = st.columns([50, 25, 25], vertical_alignment="center")
        with col_t3:
            st.markdown("### 3. 추가 자료 (메모, 링크, 참고사항)")
        with col_h3:
            toggle_label = "👁️ 입력창 보이기" if is_extra_hidden else "🙈 입력창 숨기기"
            if st.button(toggle_label, key=f"btn_toggle_extra_{q_text}", use_container_width=False):
                if f"extra_area_{q_text}" in st.session_state:
                    st.session_state.user_data[q_text]['extra'] = st.session_state[f"extra_area_{q_text}"]
                    save_user_data(st.session_state.user_data)
                st.session_state[key_hide_extra] = not is_extra_hidden
                st.rerun()
        with col_b3:
            if st.button("💾 저장하기", key=f"save_extra_{q_text}", type="primary", use_container_width=False):
                if f"extra_area_{q_text}" in st.session_state:
                    st.session_state.user_data[q_text]['extra'] = st.session_state[f"extra_area_{q_text}"]
                save_user_data(st.session_state.user_data)
                st.toast("추가 자료가 저장되었습니다!")

        if not is_extra_hidden:
            extra_text = st.text_area(
                "참고할 추가 메모나 링크를 입력하세요. (제미나이 답변 복사-붙여넣기 및 마크다운 지원)", 
                value=q_data['extra'], 
                height=180, 
                key=f"extra_area_{q_text}",
                label_visibility="collapsed"
            )
            if q_data['extra']:
                st.write("---")
                st.markdown("#### 📎 추가 자료 및 메모 (서식 적용 화면)")
                st.markdown(q_data['extra'])
        else:
            if q_data['extra']:
                st.markdown(q_data['extra'])
            else:
                st.info("작성된 추가 자료가 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")

    # -------------------------------------------------------------------------
    # TAB 4: 구글 검색
    # -------------------------------------------------------------------------
    with tab4:
        st.markdown("### 4. 구글 검색")
        st.info("문제를 해결하기 위해 관련된 정보를 구글에서 검색해 보세요.")
        search_query = st.text_input("검색어", value=q_text)
        
        if search_query:
            encoded_query = search_query.replace(" ", "+")
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            st.markdown(
                f"""
                <a href="{search_url}" target="_blank">
                    <button style="background-color:#4285F4; color:white; border:none; padding:8px 16px; border-radius:5px; cursor:pointer; font-size:15px;">
                        🌐 구글에서 검색 결과 보기 (새 창)
                    </button>
                </a>
                """, 
                unsafe_allow_html=True
            )
