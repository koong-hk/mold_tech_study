import streamlit as st
import json
import os
from datetime import datetime
import base64

# ==========================================
# 1. 페이지 설정 및 Custom CSS
# ==========================================
st.set_page_config(
    page_title="금형기술사 학습 시스템",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 사이드바 스타일 및 너비 고정 */
    [data-testid="stSidebar"] {
        min-width: 290px;
        max-width: 290px;
        background-color: #f8f9fa;
        border-right: 1px solid #e9ecef;
    }
    
    /* 카드 및 컨테이너 스타일 */
    .st-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    
    /* 배지 스타일 */
    .badge-category {
        background-color: #e7f5ff;
        color: #1971c2;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-keyword {
        background-color: #f1f3f5;
        color: #495057;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        margin-right: 4px;
        display: inline-block;
    }
    .text-date {
        color: #868e96;
        font-size: 12px;
    }

    /* 가독성 향상 마크다운 스타일 */
    .readable-content p {
        line-height: 1.7;
        margin-bottom: 1rem;
    }
    
    /* 버튼 커스텀 */
    .stButton>button {
        width: 100%;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 파일 제어 및 세션 상태 초기화
# ==========================================
QUESTION_DATA_FILE = "user_study_data.json"
NOTE_DATA_FILE = "user_notes_data.json"

DEFAULT_QUESTIONS = [
    {
        "id": "1",
        "round": "128회",
        "period": "1교시",
        "category": "사출금형",
        "title": "사출성형기 변수 중 사출압력과 보압의 역할 및 차이점에 대하여 설명하시오.",
        "views": 15,
        "rating": 5
    },
    {
        "id": "2",
        "round": "128회",
        "period": "2교시",
        "category": "프레스금형",
        "title": "프로그레시브 금형에서 사이드 컷(Side Cut)의 설치 목적과 사용 시 주의사항을 설명하시오.",
        "views": 8,
        "rating": 4
    },
    {
        "id": "3",
        "round": "129회",
        "period": "1교시",
        "category": "재료/열처리",
        "title": "STAVAX(SUS420J2 계열) 몰드강의 열처리 특성 및 래핑(Lapping) 작업 시 발생할 수 있는 결함에 대해 설명하시오.",
        "views": 22,
        "rating": 5
    }
]

def load_data(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_str = base64.b64encode(bytes_data).decode()
        return f"data:{uploaded_file.type};base64,{base64_str}"
    return None

# 세션 초기화 및 ID 자동 보완 (KeyError 방지)
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "기출문제"

if "questions" not in st.session_state:
    loaded_qs = load_data(QUESTION_DATA_FILE, DEFAULT_QUESTIONS)
    # 기존 JSON 파일에 id 키가 없는 경우 대비한 자동 ID 생성
    for idx, q in enumerate(loaded_qs):
        if "id" not in q or not q["id"]:
            q["id"] = str(idx + 1)
    st.session_state["questions"] = loaded_qs

if "notes" not in st.session_state:
    st.session_state["notes"] = load_data(NOTE_DATA_FILE, [])

if "selected_q_id" not in st.session_state:
    if st.session_state["questions"]:
        st.session_state["selected_q_id"] = st.session_state["questions"][0].get("id", "1")
    else:
        st.session_state["selected_q_id"] = None

if "note_action" not in st.session_state:
    st.session_state["note_action"] = "list"
if "editing_note_id" not in st.session_state:
    st.session_state["editing_note_id"] = None

# ==========================================
# 3. 사이드바 (필터링, 검색, 모드 전환)
# ==========================================
with st.sidebar:
    st.title("📘 금형기술사 시스템")
    
    st.markdown("### 📌 메뉴 선택")
    mode_col1, mode_col2 = st.columns(2)
    with mode_col1:
        if st.button("📝 기출문제", type="primary" if st.session_state["view_mode"] == "기출문제" else "secondary"):
            st.session_state["view_mode"] = "기출문제"
            st.rerun()
    with mode_col2:
        if st.button("📓 학습노트", type="primary" if st.session_state["view_mode"] == "학습노트" else "secondary"):
            st.session_state["view_mode"] = "학습노트"
            st.rerun()
            
    st.markdown("---")

    if st.session_state["view_mode"] == "기출문제":
        st.subheader("🔍 기출문제 검색 및 필터")
        
        q_search_query = st.text_input("문제 검색", placeholder="검색어를 입력하세요...", key="q_search_input")
        
        all_rounds = sorted(list(set(q.get("round", "") for q in st.session_state["questions"] if q.get("round"))))
        all_periods = sorted(list(set(q.get("period", "") for q in st.session_state["questions"] if q.get("period"))))
        all_categories = sorted(list(set(q.get("category", "기타") for q in st.session_state["questions"])))

        selected_rounds = st.multiselect("회차 선택 (복수)", options=all_rounds, default=[])
        selected_periods = st.multiselect("교시 선택 (복수)", options=all_periods, default=[])
        selected_categories = st.multiselect("분류 선택 (복수)", options=all_categories, default=[])

        st.markdown("---")
        
        filtered_qs = st.session_state["questions"]
        if selected_rounds:
            filtered_qs = [q for q in filtered_qs if q.get("round") in selected_rounds]
        if selected_periods:
            filtered_qs = [q for q in filtered_qs if q.get("period") in selected_periods]
        if selected_categories:
            filtered_qs = [q for q in filtered_qs if q.get("category") in selected_categories]
        if q_search_query:
            query_lower = q_search_query.lower()
            filtered_qs = [
                q for q in filtered_qs 
                if query_lower in q.get("title", "").lower() or query_lower in q.get("category", "").lower()
            ]

        st.subheader(f"📋 문제 리스트 ({len(filtered_qs)}개)")
        for q in filtered_qs:
            q_id = q.get("id", str(hash(q.get("title", ""))))
            round_str = q.get("round", "")
            period_str = q.get("period", "")
            title_str = q.get("title", "제목 없음")
            btn_label = f"[{round_str} {period_str}] {title_str[:18]}..."
            
            if st.button(btn_label, key=f"q_btn_{q_id}"):
                st.session_state["selected_q_id"] = q_id
                q["views"] = q.get("views", 0) + 1
                save_data(QUESTION_DATA_FILE, st.session_state["questions"])
                st.rerun()

# ==========================================
# 4. 메인 화면: 기출문제 상세 View
# ==========================================
if st.session_state["view_mode"] == "기출문제":
    selected_q = next((q for q in st.session_state["questions"] if str(q.get("id")) == str(st.session_state["selected_q_id"])), None)
    
    if selected_q:
        st.title(f"[{selected_q.get('round', '')} {selected_q.get('period', '')}] {selected_q.get('category', '공통')}")
        st.subheader(selected_q.get('title', ''))
        
        col_m1, col_m2, col_m3 = st.columns([1, 1, 4])
        with col_m1:
            st.caption(f"👁️ 조회수: {selected_q.get('views', 0)}")
        with col_m2:
            st.caption(f"⭐ 중요도: {'★' * selected_q.get('rating', 3)}")

        st.markdown("---")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["💡 핵심 개념", "📝 모범 답안", "📌 추가 메모", "🌐 구글 검색", "🖼️ 이미지/자료"])

        with tab1:
            st.markdown("### 핵심 개념 정의 및 설명")
            concept_text = selected_q.get("concept", "등록된 핵심 개념이 없습니다.")
            st.markdown(f"<div class='readable-content'>{concept_text}</div>", unsafe_allow_html=True)
            
            with st.expander("개념 수정하기"):
                new_concept = st.text_area("개념 작성", value=concept_text, height=150)
                if st.button("개념 저장", key="save_concept"):
                    selected_q["concept"] = new_concept
                    save_data(QUESTION_DATA_FILE, st.session_state["questions"])
                    st.success("핵심 개념이 저장되었습니다.")
                    st.rerun()

        with tab2:
            st.markdown("### 표준 답안 / 서술 가이드")
            answer_text = selected_q.get("answer", "등록된 모범 답안이 없습니다.")
            st.markdown(f"<div class='readable-content'>{answer_text}</div>", unsafe_allow_html=True)
            
            with st.expander("모범 답안 수정하기"):
                new_answer = st.text_area("답안 작성", value=answer_text, height=200)
                if st.button("답안 저장", key="save_answer"):
                    selected_q["answer"] = new_answer
                    save_data(QUESTION_DATA_FILE, st.session_state["questions"])
                    st.success("모범 답안이 저장되었습니다.")
                    st.rerun()

        with tab3:
            st.markdown("### 개인 학습 메모")
            memo_text = selected_q.get("memo", "")
            new_memo = st.text_area("메모를 입력하세요", value=memo_text, height=120)
            if st.button("메모 저장", key="save_memo"):
                selected_q["memo"] = new_memo
                save_data(QUESTION_DATA_FILE, st.session_state["questions"])
                st.success("메모가 저장되었습니다.")

        with tab4:
            st.markdown("### 연관 자료 구글 검색")
            search_url = f"https://www.google.com/search?q=금형기술사+{selected_q.get('title', '')}"
            st.markdown(f"🔗 [Google에서 '{selected_q.get('title', '')}' 관련 기술 자료 검색하기]({search_url})")

        with tab5:
            st.markdown("### 참고 이미지 및 도면")
            uploaded_img = st.file_uploader("이미지 첨부", type=["png", "jpg", "jpeg"], key="q_img_up")
            if uploaded_img:
                b64_img = image_to_base64(uploaded_img)
                if "images" not in selected_q:
                    selected_q["images"] = []
                selected_q["images"].append(b64_img)
                save_data(QUESTION_DATA_FILE, st.session_state["questions"])
                st.success("이미지가 추가되었습니다.")
                st.rerun()

            if "images" in selected_q and selected_q["images"]:
                for idx, img_b64 in enumerate(selected_q["images"]):
                    st.image(img_b64, use_column_width=True)
                    if st.button(f"이미지 삭제 #{idx+1}", key=f"del_img_{idx}"):
                        selected_q["images"].pop(idx)
                        save_data(QUESTION_DATA_FILE, st.session_state["questions"])
                        st.rerun()
    else:
        st.info("좌측 리스트에서 문제를 선택해주세요.")

# ==========================================
# 5. 메인 화면: 학습노트 (Note List & 생성/수정)
# ==========================================
elif st.session_state["view_mode"] == "학습노트":
    st.title("📓 금형기술사 학습노트")
    
    if st.session_state["note_action"] in ["create", "edit"]:
        is_edit = st.session_state["note_action"] == "edit"
        target_note = {}
        if is_edit:
            target_note = next((n for n in st.session_state["notes"] if str(n.get("id")) == str(st.session_state["editing_note_id"])), {})
            
        st.subheader("✏️ " + ("학습노트 수정" if is_edit else "새 학습노트 생성"))
        
        with st.form("note_form", clear_on_submit=False):
            title = st.text_input("제목 *", value=target_note.get("title", ""))
            keywords_str = st.text_input("키워드 (쉼표로 구분)", value=", ".join(target_note.get("keywords", [])))
            link = st.text_input("웹 페이지 링크 (선택)", value=target_note.get("link", ""))
            content = st.text_area("본문 내용 *", value=target_note.get("content", ""), height=250)
            
            uploaded_imgs = st.file_uploader("이미지 첨부 (복수 가능)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
            
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                submit_btn = st.form_submit_button("💾 저장하기", type="primary")
            with col_f2:
                cancel_btn = st.form_submit_button("❌ 취소")

        if cancel_btn:
            st.session_state["note_action"] = "list"
            st.session_state["editing_note_id"] = None
            st.rerun()

        if submit_btn:
            if not title.strip() or not content.strip():
                st.error("제목과 본문 내용은 필수 항목입니다.")
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                img_b64_list = target_note.get("images", []) if is_edit else []
                if uploaded_imgs:
                    for img in uploaded_imgs:
                        img_b64_list.append(image_to_base64(img))

                keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

                if is_edit:
                    target_note["title"] = title
                    target_note["keywords"] = keywords
                    target_note["link"] = link
                    target_note["content"] = content
                    target_note["images"] = img_b64_list
                    target_note["updated_at"] = now_str
                else:
                    new_note = {
                        "id": str(datetime.now().timestamp()),
                        "title": title,
                        "keywords": keywords,
                        "link": link,
                        "content": content,
                        "images": img_b64_list,
                        "created_at": now_str,
                        "updated_at": now_str
                    }
                    st.session_state["notes"].insert(0, new_note)

                save_data(NOTE_DATA_FILE, st.session_state["notes"])
                st.success("노트가 성공적으로 저장되었습니다!")
                st.session_state["note_action"] = "list"
                st.session_state["editing_note_id"] = None
                st.rerun()

    else:
        col_t1, col_t2 = st.columns([1, 3])
        with col_t1:
            if st.button("➕ 새 노트 작성", type="primary"):
                st.session_state["note_action"] = "create"
                st.rerun()
        with col_t2:
            note_search = st.text_input("🔍 노트 검색 (제목, 키워드, 본문)", placeholder="검색어를 입력하고 엔터를 누르세요...", label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)

        filtered_notes = st.session_state["notes"]
        if note_search:
            s_query = note_search.lower()
            filtered_notes = [
                n for n in filtered_notes 
                if s_query in n.get("title", "").lower() 
                or s_query in n.get("content", "").lower() 
                or any(s_query in k.lower() for k in n.get("keywords", []))
            ]

        if not filtered_notes:
            st.info("등록된 학습노트가 없거나 검색 결과가 없습니다.")
        else:
            for note in filtered_notes:
                note_id = note.get("id", str(hash(note.get("title", ""))))
                with st.container():
                    st.markdown("<div class='st-card'>", unsafe_allow_html=True)
                    
                    c_title, c_act = st.columns([4, 1])
                    with c_title:
                        st.markdown(f"### {note.get('title', '제목 없음')}")
                        st.markdown(f"<span class='text-date'>📅 작성일: {note.get('created_at', '-')} | 🔄 수정일: {note.get('updated_at', '-')}</span>", unsafe_allow_html=True)
                    with c_act:
                        btn_e, btn_d = st.columns(2)
                        if btn_e.button("✏️", key=f"edit_n_{note_id}"):
                            st.session_state["note_action"] = "edit"
                            st.session_state["editing_note_id"] = note_id
                            st.rerun()
                        if btn_d.button("🗑️", key=f"del_n_{note_id}"):
                            st.session_state["notes"] = [n for n in st.session_state["notes"] if str(n.get("id")) != str(note_id)]
                            save_data(NOTE_DATA_FILE, st.session_state["notes"])
                            st.rerun()

                    if note.get("keywords"):
                        kw_html = "".join([f"<span class='badge-keyword'>#{k}</span>" for k in note["keywords"]])
                        st.markdown(f"<div style='margin: 8px 0;'>{kw_html}</div>", unsafe_allow_html=True)

                    if note.get("link"):
                        st.markdown(f"🔗 **관련 링크:** [{note['link']}]({note['link']})")

                    st.markdown("---")
                    st.markdown(f"<div class='readable-content'>{note.get('content', '')}</div>", unsafe_allow_html=True)

                    if note.get("images"):
                        st.markdown("<br><b>🖼️ 첨부 이미지</b>", unsafe_allow_html=True)
                        img_cols = st.columns(min(len(note["images"]), 3))
                        for idx, img_data in enumerate(note["images"]):
                            with img_cols[idx % 3]:
                                st.image(img_data, use_column_width=True)

                    st.markdown("</div>", unsafe_allow_html=True)
