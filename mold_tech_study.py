import os
import re
import json
import urllib.parse
import pandas as pd
import streamlit as st
from PIL import Image

# ---------------------------------------------------------
# 1. 페이지 설정 및 CSS (목록 계층화, 사이드바, 들여쓰기)
# ---------------------------------------------------------
st.set_page_config(
    page_title="금형기술사 자격검정 학습 시스템",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* 사이드바 너비 조정 및 여백 축소 */
[data-testid="stSidebar"] {
    min-width: 280px;
    max-width: 280px;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

/* 1계층: 1., 2., 3. */
.stMarkdown ol {
    list-style-type: decimal;
    padding-left: 1.5rem;
}

/* 2계층: 1), 2), 3) */
.stMarkdown ol > li > ol {
    list-style-type: none;
    counter-reset: level2;
    padding-left: 1.5rem;
}
.stMarkdown ol > li > ol > li {
    counter-increment: level2;
}
.stMarkdown ol > li > ol > li::marker {
    content: counter(level2) ") ";
}

/* 3계층: ①, ②, ③ */
@counter-style circled-numbers {
    system: numeric;
    symbols: "①" "②" "③" "④" "⑤" "⑥" "⑦" "⑧" "⑨" "⑩";
    suffix: " ";
}
.stMarkdown ol > li > ol > li > ol {
    list-style-type: circled-numbers;
    padding-left: 1.5rem;
}

/* 콜론 분리 후 본문 들여쓰기 스타일 */
.indented-body {
    display: block;
    margin-left: 1.5rem;
    margin-top: 0.2rem;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 경로 및 데이터 관리 함수
# ---------------------------------------------------------
DATA_FILE = "user_study_data.json"
IMAGE_DIR = "saved_images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@st.cache_data
def load_exam_data():
    # 엑셀 파일 로드 (파일명이 다를 경우 수정 필요)
    try:
        df = pd.read_excel("mold_questions.xlsx")
    except Exception:
        # 데이터가 없을 경우를 대비한 가상 뼈대 데이터
        df = pd.DataFrame({
            "ID": [1, 2, 3],
            "회차": [120, 120, 121],
            "교시": [1, 2, 1],
            "문제번호": [1, 1, 1],
            "분류": ["사출금형", "프레스금형", "재료/열처리"],
            "문제": [
                "사출성형기 수지 용융 메커니즘을 설명하시오.",
                "프로그레시브 금형의 스트립 레이아웃 설계 시 고려사항을 서술하시오.",
                "금형용 강재 Stavax의 특성과 열처리 조건에 대해 설명하시오."
            ]
        })
    return df

def format_readable_text(text: str) -> str:
    """콜론(:) 분리 후 줄바꿈 및 들여쓰기 적용 (단, : 뒤에 * 또는 - 가 오는 경우는 제외)"""
    if not text or not isinstance(text, str):
        return ""
    
    pattern = r':\s*(?!\*|-)'
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        if ':' in line:
            subbed = re.sub(pattern, ':\n<span class="indented-body">', line)
            if '<span class="indented-body">' in subbed and not subbed.endswith('</span>'):
                subbed += '</span>'
            formatted_lines.append(subbed)
        else:
            formatted_lines.append(line)
            
    return "\n".join(formatted_lines)

# ---------------------------------------------------------
# 3. 데이터 준비 및 상태 초기화
# ---------------------------------------------------------
df_raw = load_exam_data()
user_data = load_user_data()

# 세션 상태 초기화
if "user_db" not in st.session_state:
    st.session_state.user_db = user_data

# ---------------------------------------------------------
# 4. 사이드바 검색 및 필터링
# ---------------------------------------------------------
st.sidebar.header("🔍 문제 필터링")

# 회차 선택
rounds = sorted(df_raw["회차"].unique().tolist(), reverse=True)
selected_round = st.sidebar.selectbox("회차 선택", ["전체"] + [str(r) for r in rounds])

# 교시 선택 (2~4교시 통합 옵션 추가)
period_options = ["전체", "1교시", "2교시", "3교시", "4교시", "2~4교시 통합"]
selected_period = st.sidebar.selectbox("교시 선택", period_options)

# 분류 선택
categories = sorted(df_raw["분류"].dropna().unique().tolist())
selected_cat = st.sidebar.selectbox("분류 선택", ["전체"] + categories)

# 조회수 순 정렬 옵션
sort_by_views = st.sidebar.checkbox("조회수 많은 순 정렬")

# 데이터 필터링 적용
filtered_df = df_raw.copy()

if selected_round != "전체":
    filtered_df = filtered_df[filtered_df["회차"] == int(selected_round)]

if selected_period != "전체":
    if selected_period == "2~4교시 통합":
        filtered_df = filtered_df[filtered_df["교시"].isin([2, 3, 4])]
    else:
        period_num = int(selected_period.replace("교시", ""))
        filtered_df = filtered_df[filtered_df["교시"] == period_num]

if selected_cat != "전체":
    filtered_df = filtered_df[filtered_df["분류"] == selected_cat]

# 조회수 계산 및 정렬
filtered_df["조회수"] = filtered_df["ID"].apply(
    lambda q_id: st.session_state.user_db.get(str(q_id), {}).get("views", 0)
)

if sort_by_views:
    filtered_df = filtered_df.sort_values(by="조회수", ascending=False)

# ---------------------------------------------------------
# 5. 메인 화면: 문제 목록 및 선택
# ---------------------------------------------------------
st.title("📘 금형기술사 자격검정 학습 시스템")

if filtered_df.empty:
    st.warning("선택한 조건에 해당하는 문제가 없습니다.")
    st.stop()

# 문제 선택을 위한 레이블 리스트 구성
question_options = {
    f"[{row['회차']}회 {row['교시']}교시 {row['문제번호']}번] {row['문제'][:30]}... (조회수: {row['조회수']})": row["ID"]
    for _, row in filtered_df.iterrows()
}

selected_label = st.selectbox("학습할 문제를 선택하세요:", list(question_options.keys()))
selected_id = str(question_options[selected_label])

# 현재 선택된 문제 상세 정보 추출
q_info = filtered_df[filtered_df["ID"] == int(selected_id)].iloc[0]

# 조회수 업데이트
if selected_id not in st.session_state.user_db:
    st.session_state.user_db[selected_id] = {
        "views": 0, "concept": "", "intro": "", "body": "",
        "conclusion": "", "memo": "", "images": {}
    }

st.session_state.user_db[selected_id]["views"] += 1
save_user_data(st.session_state.user_db)

# 문제 상세 헤더
st.subheader(f"제 {q_info['회차']} 회 {q_info['교시']}교시 {q_info['문제번호']}번")
st.markdown(f"**분류**: `{q_info['분류']}` | **조회수**: `{st.session_state.user_db[selected_id]['views']}`회")
st.info(f"**문제**: {q_info['문제']}")

# ---------------------------------------------------------
# 6. 5단계 상세 학습 탭
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💡 답안 개념 설명",
    "📝 실제 시험 모범 답안",
    "📌 추가 자료 및 메모",
    "🔍 구글 검색",
    "🖼️ 이미지 및 설명 자료"
])

curr_q_data = st.session_state.user_db[selected_id]

# --- TAB 1: 답안 개념 설명 ---
with tab1:
    st.markdown("### 답안 핵심 개념")
    
    # 개념 설명 출력 (수정된 계층/들여쓰기 적용)
    if curr_q_data.get("concept"):
        formatted_concept = format_readable_text(curr_q_data["concept"])
        st.markdown(formatted_concept, unsafe_allow_html=True)
    else:
        st.caption("작성된 데이터가 없습니다.")

    st.markdown("---")
    show_concept_edit = st.checkbox("개념 설명 작성/수정", key="toggle_concept")
    if show_concept_edit:
        new_concept = st.text_area("개념 내용을 입력하세요", value=curr_q_data.get("concept", ""), height=200)
        if st.button("개념 저장", key="btn_save_concept"):
            st.session_state.user_db[selected_id]["concept"] = new_concept
            save_user_data(st.session_state.user_db)
            st.success("저장되었습니다.")
            st.rerun()

# --- TAB 2: 실제 시험 모범 답안 ---
with tab2:
    st.markdown("### 답안 구성 (개요 · 본론 · 결론)")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**1. 개요**")
        st.markdown(format_readable_text(curr_q_data.get("intro", "- ")), unsafe_allow_html=True)
    with col_b:
        st.markdown("**2. 본론**")
        st.markdown(format_readable_text(curr_q_data.get("body", "- ")), unsafe_allow_html=True)
    with col_c:
        st.markdown("**3. 결론**")
        st.markdown(format_readable_text(curr_q_data.get("conclusion", "- ")), unsafe_allow_html=True)

    st.markdown("---")
    show_answer_edit = st.checkbox("모범 답안 작성/수정", key="toggle_answer")
    if show_answer_edit:
        c1, c2, c3 = st.columns(3)
        with c1:
            new_intro = st.text_area("개요 입력", value=curr_q_data.get("intro", ""), height=250)
        with c2:
            new_body = st.text_area("본론 입력", value=curr_q_data.get("body", ""), height=250)
        with c3:
            new_conclusion = st.text_area("결론 입력", value=curr_q_data.get("conclusion", ""), height=250)

        if st.button("답안 저장", key="btn_save_answer"):
            st.session_state.user_db[selected_id]["intro"] = new_intro
            st.session_state.user_db[selected_id]["body"] = new_body
            st.session_state.user_db[selected_id]["conclusion"] = new_conclusion
            save_user_data(st.session_state.user_db)
            st.success("답안이 저장되었습니다.")
            st.rerun()

# --- TAB 3: 추가 자료 및 메모 ---
with tab3:
    st.markdown("### 참고 링크 및 학습 수식/메모")
    if curr_q_data.get("memo"):
        st.markdown(format_readable_text(curr_q_data["memo"]), unsafe_allow_html=True)
    else:
        st.caption("작성된 메모가 없습니다.")

    st.markdown("---")
    show_memo_edit = st.checkbox("메모 작성/수정", key="toggle_memo")
    if show_memo_edit:
        new_memo = st.text_area("메모 및 수식 입력", value=curr_q_data.get("memo", ""), height=200)
        if st.button("메모 저장", key="btn_save_memo"):
            st.session_state.user_db[selected_id]["memo"] = new_memo
            save_user_data(st.session_state.user_db)
            st.success("메모가 저장되었습니다.")
            st.rerun()

# --- TAB 4: 구글 검색 ---
with tab4:
    st.markdown("### 🔍 관련 자료 외부 검색")
    query = f"금형기술사 {q_info['문제']}"
    encoded_query = urllib.parse.quote(query)
    google_url = f"https://www.google.com/search?q={encoded_query}"

    st.write(f"검색어: **{query}**")
    st.link_button("🌐 구글에서 검색 결과 확인하기", google_url)

# --- TAB 5: 이미지 및 설명 자료 ---
with tab5:
    st.markdown("### 이미지 참고 자료 및 도면 설명")

    # 이미지 등록 폼
    with st.expander("📷 새 이미지 및 설명 추가"):
        img_file = st.file_uploader("이미지 파일 선택", type=["png", "jpg", "jpeg", "webp"])
        img_title = st.text_input("이미지 제목/명칭")
        img_desc = st.text_area("이미지 상세 설명 (구조, 메커니즘 등)")

        if st.button("이미지 저장", key="btn_save_img"):
            if img_file and img_title:
                filename = f"{selected_id}_{int(pd.Timestamp.now().timestamp())}_{img_file.name}"
                filepath = os.path.join(IMAGE_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(img_file.getbuffer())

                if "images" not in st.session_state.user_db[selected_id]:
                    st.session_state.user_db[selected_id]["images"] = {}

                st.session_state.user_db[selected_id]["images"][filename] = {
                    "title": img_title,
                    "desc": img_desc
                }
                save_user_data(st.session_state.user_db)
                st.success("이미지가 정상 등록되었습니다.")
                st.rerun()
            else:
                st.error("이미지 파일과 제목을 모두 입력해주세요.")

    # 저장된 이미지 출력 (6:4 Split 레이아웃)
    saved_images = curr_q_data.get("images", {})
    if saved_images:
        st.markdown("---")
        img_keys = list(saved_images.keys())
        selected_img_key = st.selectbox("보려는 이미지 선택", img_keys, format_func=lambda k: saved_images[k]["title"])

        if selected_img_key:
            target_img_data = saved_images[selected_img_key]
            full_img_path = os.path.join(IMAGE_DIR, selected_img_key)

            col_left, col_right = st.columns([6, 4])

            with col_left:
                if os.path.exists(full_img_path):
                    image = Image.open(full_img_path)
                    st.image(image, caption=target_img_data["title"], use_container_width=True)
                else:
                    st.error("파일을 찾을 수 없습니다.")

            with col_right:
                st.markdown(f"#### {target_img_data['title']}")
                st.markdown(format_readable_text(target_img_data["desc"]), unsafe_allow_html=True)
                
                if st.button("❌ 선택한 이미지 삭제", key="btn_del_img"):
                    if os.path.exists(full_img_path):
                        os.remove(full_img_path)
                    del st.session_state.user_db[selected_id]["images"][selected_img_key]
                    save_user_data(st.session_state.user_db)
                    st.success("삭제되었습니다.")
                    st.rerun()
    else:
        st.caption("등록된 이미지 자료가 없습니다.")
