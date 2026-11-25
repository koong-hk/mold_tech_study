# Backup 261114 2210

import base64
import calendar
from datetime import date, datetime, timedelta, timezone
import json
import os
import re
import time
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import io
import uuid
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials as OAuthCredentials


# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="금형기술사 학습 시스템", layout="wide")

# -----------------------------------------------------------------------------
# 2. 파일 경로 및 절대경로 설정
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_FILE = os.path.join(BASE_DIR, "notes.json")
USER_DATA_FILE = os.path.join(BASE_DIR, "user_study_data.json")

# -----------------------------------------------------------------------------
# 헬퍼 함수: 마크다운 자동 변환 및 수식 보정
# -----------------------------------------------------------------------------
def format_to_markdown(text: str) -> str:
    """텍스트를 마크다운으로 깔끔하게 정돈하는 함수."""
    if not text:
        return ""

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'-\s+-\s+', '- ', text)
    text = re.sub(r'(?:###\s*){2,}', '### ', text)
    text = re.sub(r'(?:##\s*){2,}', '#### ', text)
    text = re.sub(r'(?:📌\s*){2,}', '📌 ', text)
    text = re.sub(r'(?:###\s*📌\s*){2,}', '### 📌 ', text)

    lines = text.split('\n')
    cleaned_lines = []
    is_after_header = False

    for line in lines:
        line_clean_gt = re.sub(r'^\s*>\s*', '', line)
        stripped = line_clean_gt.strip()
        
        if not stripped:
            cleaned_lines.append("")
            is_after_header = False
            continue

        if stripped.startswith("---") or stripped.startswith("===") or stripped.startswith("|"):
            cleaned_lines.append(stripped)
            is_after_header = False
            continue

        if re.match(r'^(#+|\*|-|\+|\d+\.)\s', stripped):
            # 기존 ##로 시작하는 줄이 있다면 ####로 변경하여 저장
            if stripped.startswith('## '):
                stripped = stripped.replace('## ', '#### ', 1)
        
            is_after_header = stripped.startswith('#')
            cleaned_lines.append(stripped)
            continue


        if re.match(r'^\d+\.\s+[^\n]+', stripped) and len(stripped) < 40:
            cleaned_lines.append(f"##### {stripped}")
            is_after_header = True
            continue

        if stripped.endswith(":") and len(stripped) < 25:
            cleaned_lines.append(f"**{stripped}**")
            is_after_header = True
            continue

        if is_after_header:
            if ":" in stripped and not stripped.startswith("-"):
                parts = stripped.split(":", 1)
                if len(parts[0].strip()) < 20:
                    cleaned_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;- **{parts[0].strip()}:** {parts[1].strip()}")
                else:
                    cleaned_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;{stripped}")
            else:
                cleaned_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;{stripped}")
            is_after_header = False
            continue

        if ":" in stripped and not stripped.startswith("http") and not stripped.startswith(("-", "*", "###", "##")):
            parts = stripped.split(":", 1)
            if len(parts[0].strip()) < 20 and not parts[0].strip().startswith("-"):
                cleaned_lines.append(f"- **{parts[0].strip()}:** {parts[1].strip()}")
                is_after_header = False
                continue

        cleaned_lines.append(stripped)
        is_after_header = False

    result = "\n".join(cleaned_lines)
    return re.sub(r'\n{3,}', '\n\n', result).strip()

def format_readable_text(text: str) -> str:
    """노트 본문의 LaTeX 수식 및 텍스트 가독성 자동 보정"""
    if not text or not str(text).strip():
        return "*작성된 내용이 없습니다.*"
    
    text_str = str(text)
    
    def replace_bracket_math(match):
        formula = match.group(1).strip()
        formula_clean = re.sub(r'_\{([a-zA-Z0-9_\-]+)\}', r'_{\\text{\1}}', formula)
        return f"\n\n$$\n{formula_clean}\n$$\n\n"

    text_str = re.sub(r'\(([^)]*?=[^)]*?\\[a-zA-Z]+[^)]*?)\)', replace_bracket_math, text_str)
    
    def clean_latex_block(match):
        formula = match.group(1)
        formula_clean = re.sub(r'_\{([a-zA-Z0-9_\-]+)\}', r'_{\\text{\1}}', formula)
        return f"\n$$\n{formula_clean}\n$$\n"

    return re.sub(r'\$\$(.*?)\$\$', clean_latex_block, text_str, flags=re.DOTALL)

def render_formatted_content(text: str):
    """서식 적용 공통 렌더링"""
    st.markdown(
        f"""
        <div class="custom-markdown-box">
            {format_readable_text(text)}
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 3. Google Sheets 연동 및 데이터 입출력 함수 (안전성 보장)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    """gspread 클라이언트 인증"""
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scope
        )
        return gspread.authorize(credentials)
    except Exception as e:
        return None

def render_card_audio(title, narration):
    import streamlit.components.v1 as components

    payload = json.dumps(f"{title}. {narration}").replace("<", "\\u003c")
    components.html("""
        <button id="play" type="button">▶ 한국어로 듣기</button>
        <button id="stop" type="button">■ 정지</button>
        <span id="status" role="status"></span>
        <script>
          const speech = window.speechSynthesis;
          const status = document.getElementById("status");
          document.getElementById("play").onclick = () => {
            if (!speech || !window.SpeechSynthesisUtterance) {
              status.textContent = "이 브라우저에서 음성 재생을 지원하지 않습니다.";
              return;
            }
            speech.cancel();
            const utterance = new SpeechSynthesisUtterance(PAYLOAD);
            utterance.lang = "ko-KR";
            const voice = speech.getVoices().find(v => /^ko\\b/i.test(v.lang));
            if (voice) utterance.voice = voice;
            utterance.rate = 0.92;
            utterance.onstart = () => { status.textContent = "재생 중"; };
            utterance.onend = () => { status.textContent = ""; };
            utterance.onerror = event => {
              if (!["canceled", "interrupted"].includes(event.error)) {
                status.textContent = "재생할 수 없습니다. 기기의 한국어 음성 설정을 확인하세요.";
              }
            };
            speech.speak(utterance);
          };
          document.getElementById("stop").onclick = () => {
            if (speech) speech.cancel();
            status.textContent = "";
          };
          window.addEventListener("pagehide", () => { if (speech) speech.cancel(); });
        </script>
    """.replace("PAYLOAD", payload), height=62)


def render_daily_cards():
    import hmac

    st.title("데일리 암기카드")
    try:
        client = get_gspread_client()
        if client is None:
            raise RuntimeError()
        sheet = client.open(st.secrets["sheets"]["notes_sheet"]).worksheet("데일리암기카드")
        rows = sheet.get_all_values()[1:]
    except Exception:
        st.error("암기카드 Google Sheets에 연결할 수 없습니다.")
        return

    cards = {}
    for row_number, row in enumerate(rows, start=2):
        if len(row) >= 7 and row[0]:
            cards.setdefault(row[0], (row_number, row[:7]))
    if not cards:
        st.info("저장된 암기카드가 없습니다.")
        return

    query = st.text_input("암기카드 검색", placeholder="제목, 키워드, 날짜").strip().casefold().split()
    categories = sorted({row[3] for _, row in cards.values()})
    category = st.selectbox("분야", ["전체", *categories])
    matches = [
        card_id for card_id, (_, row) in cards.items()
        if (category == "전체" or row[3] == category)
        and all(term in " ".join(row[1:]).casefold() for term in query)
    ]
    if not matches:
        st.info("검색 조건에 맞는 카드가 없습니다.")
        return

    def card_label(card_id):
        _, date, time, category, title, _, _ = cards[card_id][1]
        return f"{date} {time} · {category} · {title}"

    matches.sort(key=lambda card_id: tuple(cards[card_id][1][1:3]), reverse=True)
    card_id = st.selectbox("암기카드 목록", matches, format_func=card_label)
    row_number, original = cards[card_id]
    _, _, _, category, title, summary, narration = original
    st.subheader(title)
    st.markdown(summary)
    render_card_audio(title, narration)

    with st.expander("암기카드 편집"):
        password = str(st.secrets.get("chat_study_password", ""))
        if not password:
            st.info("편집을 사용하려면 Streamlit Secrets에 chat_study_password를 설정하세요.")
            return
        with st.form(f"daily_card_edit_{card_id}"):
            new_category = st.text_input("분야", category, max_chars=100)
            new_title = st.text_input("제목", title, max_chars=200)
            new_summary = st.text_area("요약 (마크다운)", summary, max_chars=12000, height=250)
            new_narration = st.text_area("읽어줄 내용", narration, max_chars=3000)
            entered = st.text_input("편집 비밀번호", type="password")
            submitted = st.form_submit_button("변경 저장")
        if not submitted:
            return
        if not hmac.compare_digest(entered.encode("utf-8"), password.encode("utf-8")):
            st.error("비밀번호가 맞지 않습니다.")
            return
        values = [value.strip() for value in (new_category, new_title, new_summary, new_narration)]
        if not all(values):
            st.error("분야, 제목, 요약, 읽어줄 내용을 모두 입력하세요.")
            return
        try:
            if sheet.row_values(row_number)[:7] != original:
                st.warning("카드가 변경되었습니다. 새로고침 후 다시 편집하세요.")
                return
            sheet.update(range_name=f"D{row_number}:G{row_number}", values=[values], raw=True)
        except Exception:
            st.error("카드 변경을 저장할 수 없습니다.")
            return
        st.rerun()


FLASHCARD_HEADING = re.compile(r"(?:(?:데일리|일일|오늘의?)\s*)?암기\s*카드(?:\s|[:：(\-–—]|$)")
PROBLEM_HEADING = re.compile(
    r"^(?:예상\s*)?(?:문제\s*\d+|제\s*\d+\s*(?:번|문제)|"
    r"\d+\s*(?:번\s*(?:문제)?|[.)：:\-–—]\s*(?:예상\s*문제|사출|프레스|다이\s*캐스팅))|"
    r"(?:사출(?:성형|금형)?|프레스(?:금형)?|다이\s*캐스팅)\s*(?:문제|[:：\-–—]|$))",
    re.IGNORECASE,
)


ANSWER_HEADING = re.compile(
    r"^(?:\d+[.)]\s*)?(?:(?:15\s*줄|압축형|예시|기술사|문제별)\s*)*"
    r"(?:모범\s*답안|해설|정답|답안)(?=\W|\d|$)"
)
PROBLEM_NUMBER = re.compile(
    r"^(?:(?:예상\s*)?문제\s*(\d+)|제\s*(\d+)\s*(?:번|문제)|"
    r"(\d+)\s*(?:번|[.)：:\-–—]))"
)
SUBJECT = re.compile(r"사출|프레스|다이\s*캐스팅")


def split_daily_problems(text):
    """저장된 마크다운에서 문제와 모범답안을 짝짓고 암기카드를 제외한다."""
    sections = []
    lines = []
    card_level = None
    fence = None

    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker or fence:
            if marker:
                token, suffix = marker.groups()
                if fence is None:
                    fence = token
                elif token.startswith(fence) and not suffix.strip():
                    fence = None
            if card_level is None:
                lines.append((line, "", 0, False))
            continue

        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        level = len(heading[1]) if heading else 0
        title = (heading[2] if heading else stripped).strip("*_ #")
        title = re.sub(r"^[^\w가-힣]+\s*", "", title)
        title = re.sub(r"^\d+[.)]\s*(?=(?:데일리|일일|암기))", "", title)
        if FLASHCARD_HEADING.match(title) and (
            heading or stripped.startswith(("**", "__")) or len(title) <= 45
        ):
            if card_level is None:
                card_level = level
            continue

        is_problem = bool(PROBLEM_HEADING.match(title))
        if card_level is not None:
            if is_problem and (not card_level or 0 < level <= card_level):
                card_level = None
            else:
                continue
        lines.append((line, title, level, is_problem))

    def collect(entries):
        return "\n".join(line for line, _, _, _ in entries).strip()

    # 문제 목록 뒤에 붙는 공동 답안 섹션과 문제별 인라인 답안을 모두 처리한다.
    current = []
    problem_level = None
    for index, entry in enumerate(lines):
        _, title, level, is_problem = entry
        is_answer = bool(ANSWER_HEADING.match(title))
        if is_answer and not numbered_answer_heading(title, level) and sections and any(
            (candidate_is_problem or numbered_answer_heading(candidate_title, candidate_level))
            and (not level or not candidate_level or candidate_level >= level)
            for _, candidate_title, candidate_level, candidate_is_problem in lines[index + 1:]
        ):
            sections.append(current)
            return pair_daily_answers(sections, lines[index + 1:], collect)
        if is_answer and numbered_answer_heading(title, level) and sections:
            number, _ = daily_problem_identity(title)
            first_title = next((part[1] for part in sections[0] if part[3]), "")
            first_number, _ = daily_problem_identity(first_title)
            if number == (first_number or 1):
                sections.append(current)
                return pair_daily_answers(sections, lines[index:], collect)
        if is_problem and (problem_level is None or level == problem_level):
            if problem_level is not None:
                sections.append(current)
                current = []
            problem_level = level
        current.append(entry)

    if collect(current):
        sections.append(current)
    return pair_daily_answers(sections, [], collect)


def pair_daily_answers(sections, answer_lines, collect):
    problems = []
    identities = []
    for section in sections:
        title = next((title for _, title, _, is_problem in section if is_problem), "")
        identities.append(daily_problem_identity(title))
        answer_start = next(
            (index for index, (_, title, _, _) in enumerate(section) if ANSWER_HEADING.match(title)),
            len(section),
        )
        question = collect(section[:answer_start])
        answer = collect(section[answer_start:])
        problems.append((question, answer))

    if not answer_lines:
        return problems

    candidates = [
        (index, level, daily_problem_identity(title))
        for index, (_, title, level, is_problem) in enumerate(answer_lines)
        if is_problem or numbered_answer_heading(title, level)
    ]
    if not candidates:
        return problems
    heading_level = min(level for _, level, _ in candidates)
    markers = [(index, identity) for index, level, identity in candidates if level == heading_level]
    for position, (start, (number, subject)) in enumerate(markers):
        end = markers[position + 1][0] if position + 1 < len(markers) else len(answer_lines)
        matches = [
            index for index, (question_number, question_subject) in enumerate(identities)
            if (number is not None and question_number == number)
            or (subject and question_subject == subject and (number is None or question_number is None))
        ]
        if not matches and number is not None and 1 <= number <= len(problems):
            matches = [number - 1] if identities[number - 1][0] is None else []
        if len(matches) == 1:
            index = matches[0]
            question, answer = problems[index]
            problems[index] = (question, "\n\n".join(filter(None, (answer, collect(answer_lines[start:end])))))
    return problems


def numbered_answer_heading(title, level):
    return bool(
        re.match(r"^(?:모범\s*답안|해설|답안)\s*[:：]?\s*(?:문제\s*)?\d+", title)
        or (level and re.match(r"^\d+\s*번", title))
    )


def daily_problem_identity(title):
    title = re.sub(r"^(?:모범\s*답안|해설|답안)\s*[:：\-–—]?\s*(?=\d)", "문제 ", title)
    title = re.sub(r"^(?:모범\s*답안|해설|답안)\s*[:：\-–—]?\s*", "", title)
    number = PROBLEM_NUMBER.match(title)
    subject = SUBJECT.search(title)
    return (
        int(next(value for value in number.groups() if value is not None)) if number else None,
        re.sub(r"\s+", "", subject[0]) if subject else None,
    )


def render_daily_problem(day, index, question, answer):
    key = f"{day}_{index}"
    draft_key = f"daily_draft_{key}"
    input_key = f"daily_input_{key}"

    def keep_draft():
        st.session_state[draft_key] = st.session_state[input_key]

    st.markdown(question)
    if input_key not in st.session_state:
        st.session_state[input_key] = st.session_state.get(draft_key, "")
    st.text_area(
        "풀이 노트",
        key=input_key,
        height=200,
        placeholder="모범답안을 열기 전에 직접 풀어보세요.",
        on_change=keep_draft,
    )
    if not answer:
        st.caption("이 문제에 연결된 모범답안이 없습니다.")
        return
    answer_key = f"daily_answer_visible_{key}"
    visible = st.session_state.get(answer_key, False)

    def toggle_answer():
        st.session_state[answer_key] = not st.session_state.get(answer_key, False)

    st.button(
        "모범답안 숨기기" if visible else "모범답안 보기",
        key=f"daily_answer_button_{key}",
        on_click=toggle_answer,
    )
    if visible:
        st.markdown(answer)


def render_chat_study():
    st.title("금형기술사 예상문제")
    daily_tab, records_tab = st.tabs(["일일 예상문제", "채팅 학습 기록"])
    try:
        client = get_gspread_client()
        if client is None:
            raise RuntimeError()
        workbook = client.open(st.secrets["sheets"]["notes_sheet"])
    except Exception:
        st.error("학습노트 Google Sheets에 연결할 수 없습니다.")
        return

    with daily_tab:
        try:
            rows = workbook.worksheet("일일예상문제").get_all_values()[1:]
        except Exception:
            st.error("일일 예상문제를 불러올 수 없습니다.")
        else:
            issues = {}
            for row in rows:
                if len(row) >= 2 and row[0] and row[1]:
                    problems = issues.setdefault(row[0], [])
                    for problem in split_daily_problems(row[1]):
                        if problem not in problems:
                            problems.append(problem)
            issues = {day: problems for day, problems in issues.items() if problems}
            if issues:
                date = st.selectbox("알림 날짜 (한국시간)", sorted(issues, reverse=True))
                problems = issues[date]
                tabs = st.tabs([f"문제 {index}" for index in range(1, len(problems) + 1)])
                for index, (tab, (question, answer)) in enumerate(zip(tabs, problems), start=1):
                    with tab:
                        render_daily_problem(date, index, question, answer)
            else:
                st.info("저장된 예상문제가 없습니다.")

    with records_tab:
        import hmac

        password = str(st.secrets.get("chat_study_password", ""))
        if not password:
            st.info("채팅 학습 기록을 열려면 Streamlit Secrets에 chat_study_password를 설정하세요.")
            return
        if not st.session_state.get("chat_study_unlocked"):
            with st.form("chat_study_unlock"):
                entered = st.text_input("학습 기록 비밀번호", type="password")
                submitted = st.form_submit_button("열기")
            if submitted:
                if hmac.compare_digest(entered.encode("utf-8"), password.encode("utf-8")):
                    st.session_state.chat_study_unlocked = True
                    st.rerun()
                st.error("비밀번호가 맞지 않습니다.")
            return
        if st.button("학습 기록 잠그기"):
            st.session_state.pop("chat_study_unlocked", None)
            st.rerun()
        try:
            rows = workbook.worksheet("채팅학습기록").get_all_values()[1:]
        except Exception:
            st.error("채팅 학습 기록을 불러올 수 없습니다.")
            return
        records = {row[0]: row[1:5] for row in rows if len(row) >= 5 and row[0]}
        if not records:
            st.info("저장된 채팅 학습 기록이 없습니다.")
            return
        by_date = {}
        for date, question, answer, feedback in reversed(list(records.values())):
            by_date.setdefault(date, []).append((question, answer, feedback))
        selected_date = st.selectbox("학습 날짜", sorted(by_date, reverse=True))
        problems = by_date[selected_date]
        tabs = st.tabs([f"문제 {index}" for index in range(1, len(problems) + 1)])
        for tab, (question, answer, feedback) in zip(tabs, problems):
            with tab:
                st.markdown("**문제**")
                st.markdown(question)
                st.markdown("**내 답안**")
                st.markdown(answer)
                st.markdown("**피드백**")
                st.markdown(feedback)


def get_kst_today():
    """KST 기준 오늘 날짜"""
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).date()

def load_notes():
    """학습노트 데이터 로드"""
    try:
        gc = get_gspread_client()
        if gc and "sheets" in st.secrets:
            sheet_name = st.secrets["sheets"]["notes_sheet"]
            sh = gc.open(sheet_name).sheet1
            rows = sh.get_all_values()
            
            notes = []
            for row in rows:
                if len(row) >= 2 and row[1]:
                    try:
                        note_item = json.loads(row[1])
                        if isinstance(note_item, dict):
                            notes.append(note_item)
                    except Exception:
                        pass
            if notes or rows == []:
                return notes
    except Exception as e:
        st.warning(f"구글 시트 노트 로드 실패 (로컬 데이터로 대체합니다): {e}")

    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_notes(notes):
    """원격 저장 성공 시에만 완료. 기존 시트를 먼저 지우지 않는다."""
    try:
        gc = get_gspread_client()
        if not gc or "sheets" not in st.secrets:
            raise RuntimeError("Google Sheets 인증/설정이 없습니다.")
        sh = gc.open(st.secrets["sheets"]["notes_sheet"]).sheet1
        rows = []
        for note in notes:
            payload = json.dumps(note, ensure_ascii=False)
            if len(payload) > 45000:
                raise ValueError(f"노트 '{note.get('title', '')}' 용량 초과: 기존 이미지를 먼저 Drive로 이전하세요.")
            rows.append([str(note.get("id", "")), payload])
        # 쓰기 성공 전에 기존 데이터 삭제 금지. 행별 갱신 후 남은 행만 정리.
        if rows:
            sh.update(range_name=f"A1:B{len(rows)}", values=rows)
        existing = len(sh.col_values(1))
        if existing > len(rows):
            sh.batch_clear([f"A{len(rows)+1}:B{existing}"])
        _atomic_local_json(NOTES_FILE, notes)
        return True
    except Exception as e:
        st.error(f"학습노트 저장 실패: {e}")
        return False


def _atomic_local_json(path, value):
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    os.replace(temp, path)


def load_user_data():
    """기출문제 학습 데이터 로드"""
    try:
        gc = get_gspread_client()
        if gc and "sheets" in st.secrets:
            sheet_name = st.secrets["sheets"]["study_data_sheet"]
            sh = gc.open(sheet_name).sheet1
            rows = sh.get_all_values()
            data = {}
            for row in rows:
                if len(row) >= 2 and row[0] and row[1]:
                    try:
                        if row[0] == "_d_day_target":
                            data["_d_day_target"] = row[1]
                        else:
                            data[row[0]] = json.loads(row[1])
                    except Exception:
                        pass
            if data:
                return data
    except Exception as e:
        st.warning(f"구글 시트 기출 데이터 로드 실패: {e}")

    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def save_user_data(data):
    """이미지 데이터가 잘리는 저장을 거부한다."""
    try:
        gc = get_gspread_client()
        if not gc or "sheets" not in st.secrets:
            raise RuntimeError("Google Sheets 인증/설정이 없습니다.")
        sh = gc.open(st.secrets["sheets"]["study_data_sheet"]).sheet1
        rows = []
        for key, value in data.items():
            payload = str(value) if key == "_d_day_target" else json.dumps(value, ensure_ascii=False)
            if len(payload) > 45000:
                raise ValueError(f"문제 '{str(key)[:40]}' 저장 용량 초과. 기존 이미지를 Drive로 이전하세요.")
            rows.append([str(key), payload])
        if rows:
            sh.update(range_name=f"A1:B{len(rows)}", values=rows)
        existing = len(sh.col_values(1))
        if existing > len(rows):
            sh.batch_clear([f"A{len(rows)+1}:B{existing}"])
        _atomic_local_json(USER_DATA_FILE, data)
        return True
    except Exception as e:
        st.error(f"기출문제 데이터 저장 실패: {e}")
        return False


def get_drive_session():
    """Google Sheets와 분리된 사용자 OAuth 인증으로 Drive 접근.

    Streamlit Secrets의 refresh_token으로 액세스 토큰을 갱신한다.
    서비스 계정 인증은 Google Sheets에서만 사용한다.
    """
    try:
        cfg = st.secrets["drive_oauth"]
        client_id = str(cfg["client_id"]).strip()
        client_secret = str(cfg["client_secret"]).strip()
        refresh_token = str(cfg["refresh_token"]).strip()
    except (KeyError, FileNotFoundError) as exc:
        raise RuntimeError(
            "Streamlit Secrets에 [drive_oauth] client_id, client_secret, "
            "refresh_token을 모두 등록해야 합니다."
        ) from exc

    creds = OAuthCredentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    try:
        creds.refresh(Request())
    except RefreshError as exc:
        response = exc.args[1] if len(exc.args) > 1 else None
        if isinstance(response, dict) and response.get("error") == "invalid_grant":
            raise RuntimeError(
                "Google Drive 갱신 토큰이 만료되었거나 취소되었습니다. "
                "관리자가 기존 OAuth 클라이언트로 Drive 사용 계정을 다시 승인하고 "
                "Streamlit Secrets의 [drive_oauth] refresh_token을 교체해야 합니다."
            ) from exc
        raise RuntimeError(
            "Google Drive 인증을 갱신하지 못했습니다. "
            "Streamlit Secrets의 [drive_oauth] 설정을 확인하세요."
        ) from exc
    return AuthorizedSession(creds)


def get_drive_folder_id():
    try:
        return str(st.secrets["drive"]["folder_id"]).strip()
    except Exception:
        raise RuntimeError('Streamlit Secrets에 [drive] folder_id 설정이 필요합니다.')


def upload_image_to_drive(uploaded_file):
    """이미지 업로드 후 실제 다운로드까지 검증. 실패하면 예외 발생."""
    img = Image.open(uploaded_file)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if img.mode == "L":
        img = img.convert("RGB")
    img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=83, optimize=True)
    payload = buf.getvalue()
    folder = get_drive_folder_id()
    meta = {"name": f"mold_{uuid.uuid4().hex}.jpg", "parents": [folder], "mimeType": "image/jpeg"}
    with get_drive_session() as session:
        resp = session.post("https://www.googleapis.com/upload/drive/v3/files", params={"uploadType":"multipart", "fields":"id,name,size", "supportsAllDrives":"true"},
            files={"metadata": (None, json.dumps(meta), "application/json"), "file": ("image.jpg", payload, "image/jpeg")}, timeout=90)
        if not resp.ok:
            try:
                detail = resp.json().get("error", {})
                message = detail.get("message", resp.text[:500])
                reasons = [e.get("reason", "") for e in detail.get("errors", [])]
                raise RuntimeError(f"Drive 업로드 HTTP {resp.status_code}: {message} ({', '.join(reasons)})")
            except ValueError:
                raise RuntimeError(f"Drive 업로드 HTTP {resp.status_code}: {resp.text[:500]}")
        file_id = resp.json()["id"]
        try:
            restored = _fetch_drive_image(session, file_id)
            if not restored:
                raise RuntimeError("업로드 검증 중 이미지가 비어 있습니다.")
        except Exception:
            try:
                session.delete(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}",
                    params={"supportsAllDrives": "true"},
                    timeout=20,
                )
            except Exception:
                pass
            raise
    return {"drive_file_id": file_id}


@st.cache_data(ttl=1800, show_spinner=False)
def download_drive_image(file_id):
    with get_drive_session() as session:
        return _fetch_drive_image(session, file_id)


def _fetch_drive_image(session, file_id):
    resp = session.get(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        params={"alt": "media", "supportsAllDrives": "true"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def image_bytes_from_item(item):
    if isinstance(item, dict) and item.get("drive_file_id"):
        return download_drive_image(item["drive_file_id"])
    b64 = item.get("image_base64", "") if isinstance(item, dict) else item
    if not b64 or "생략됨" in b64:
        raise ValueError("기존 저장 데이터에 이미지 원본이 없습니다.")
    return base64.b64decode(b64)


def migrate_image_item(item):
    """기존 base64를 Drive로 이전하며 원본은 저장 완료 전까지 유지."""
    if isinstance(item, dict) and item.get("drive_file_id"):
        return item, False
    raw = image_bytes_from_item(item)
    fileobj = io.BytesIO(raw)
    migrated = upload_image_to_drive(fileobj)
    if isinstance(item, dict):
        new_item = {k:v for k,v in item.items() if k != "image_base64"}
        new_item.update(migrated)
    else:
        new_item = migrated
    return new_item, True


def show_stored_image(item):
    try:
        st.image(image_bytes_from_item(item), use_container_width=True)
    except Exception as e:
        st.warning(f"이미지를 불러올 수 없습니다: {e}")


def convert_image_to_base64(uploaded_file, max_size=(800, 800), quality=75):
    """
    업로드된 이미지를 800px 이하로 축소 및 JPEG 압축하여 
    Base64 문자열 용량을 구글 시트 셀 한도(50,000자) 이내로 줄이는 함수
    """
    if uploaded_file is None:
        return None
    try:
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        return None


def render_mini_calendar():
    """커스텀 미니 달력 HTML"""
    today = get_kst_today()
    year, month, today_day = today.year, today.month, today.day
    
    cal_obj = calendar.Calendar(firstweekday=calendar.SUNDAY)
    cal = cal_obj.monthdayscalendar(year, month)
    
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

# -----------------------------------------------------------------------------
# 4. 세션 상태 초기화
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
# 5. 정제된 CSS 스타일 적용
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
        .block-container {
            padding-top: 2.0rem !important;
            padding-bottom: 1.5rem !important;
        }
        div[data-testid="stMarkdownContainer"] h1 {
            font-size: 1.4rem !important;
            margin-top: 0px !important;
            margin-bottom: 0.8rem !important;
        }
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }
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
        .custom-markdown-box {
            width: 100% !important;
        }
        .custom-markdown-box h1, .custom-markdown-box h2,
        .custom-markdown-box h3, .custom-markdown-box h4,
        .custom-markdown-box h5, .custom-markdown-box h6 {
            margin-left: 0px !important;
            margin-bottom: 0.5rem !important;
        }
        .custom-markdown-box p {
            margin-left: 1.2rem !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
            line-height: 1.65 !important;
        }
        .custom-markdown-box ol, .custom-markdown-box ul {
            margin-left: 1.2rem !important;
            padding-left: 1.2rem !important;
            margin-bottom: 0.8rem !important;
        }
        .custom-markdown-box li {
            margin-bottom: 0.4rem !important;
            line-height: 1.65 !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
        }
        .custom-markdown-box li > p {
            margin-left: 0px !important;
            display: inline !important;
        }
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
        .header-aligned-buttons {
            margin-top: 0px !important;
            margin-bottom: 0.6rem !important;
            padding-top: 0px !important;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. 데이터 로드 헬퍼
# -----------------------------------------------------------------------------
@st.cache_data
def load_excel_data(uploaded_file):
    if uploaded_file is not None:
        excel_file = pd.read_excel(uploaded_file, sheet_name=None)
        df = pd.concat(excel_file.values(), ignore_index=True)
    else:
        default_file = "금형기술사_기출문제 통합.xlsx"
        if os.path.exists(default_file):
            excel_file = pd.read_excel(default_file, sheet_name=None)
            df = pd.concat(excel_file.values(), ignore_index=True)
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
# 7. 사이드바 구성
# -----------------------------------------------------------------------------
with st.sidebar:
    uploaded_file = st.file_uploader("📂 엑셀 파일 업로드", type=['xlsx', 'xls'])
    
    if st.button("예상문제 · 채팅 기록", use_container_width=True,
                 type="primary" if st.session_state.main_mode == "chat_study" else "secondary"):
        st.session_state.main_mode = "chat_study"
        st.rerun()
    if st.button("데일리 암기카드", use_container_width=True,
                 type="primary" if st.session_state.main_mode == "daily_cards" else "secondary"):
        st.session_state.main_mode = "daily_cards"
        st.rerun()

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
                'concept': '', 'answer': '', 'memo': '',
                'image_notes': []
            }
        else:
            st.session_state.user_data[q].setdefault('clicks', 0)
            st.session_state.user_data[q].setdefault('importance', 3)
            st.session_state.user_data[q].setdefault('concept', '')
            st.session_state.user_data[q].setdefault('answer', '')
            st.session_state.user_data[q].setdefault('memo', '')
            st.session_state.user_data[q].setdefault('image_notes', [])

    df['조회수'] = df['문제'].apply(lambda x: st.session_state.user_data[x]['clicks'])
    df['중요도(별)'] = df['문제'].apply(lambda x: "⭐" * st.session_state.user_data[x]['importance'])

    def extract_number_key(x):
        digits = re.sub(r'[^0-9]', '', str(x))
        if digits:
            return (0, int(digits))
        return (1, str(x))

    rounds = sorted(list(df['회차'].unique()), key=extract_number_key, reverse=True)
    unique_periods = sorted(list(df['교시'].unique()))
    periods = [str(p) for p in unique_periods]
    categories = sorted(list(df['분류'].unique()))

    sel_rounds = st.multiselect("회차 선택 (복수)", options=rounds, default=[])
    sel_periods = st.multiselect("교시 선택 (복수)", options=periods, default=[])
    sel_categories = st.multiselect("분류 선택 (복수)", options=categories, default=[])

    sort_by_clicks = st.checkbox("자주 본 문제 순 정렬 (조회수 ⇧)")

    st.markdown("<div style='margin-top: 15px; border-top: 1px solid #333333; padding-top: 10px;'></div>", unsafe_allow_html=True)
    st.markdown(render_mini_calendar(), unsafe_allow_html=True)

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

    col_d_btn, col_d_disp = st.columns([50, 50], gap="small", vertical_alignment="center")

    with col_d_btn:
        if st.button("D-Day 설정", use_container_width=True, key="btn_set_dday"):
            st.session_state.show_d_day_picker = not st.session_state.show_d_day_picker

    with col_d_disp:
        st.markdown(f"<div class='dday-box'>{d_day_str}</div>", unsafe_allow_html=True)

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
# 8. 필터링 조건 적용
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
# 9. 우측 화면 (기출문제 리스트 / 상세 / 학습노트 관리)
# -----------------------------------------------------------------------------
if st.session_state.main_mode == "daily_cards":
    render_daily_cards()
elif st.session_state.main_mode == "chat_study":
    render_chat_study()
elif st.session_state.main_mode == "exam":
    if not st.session_state.show_detail:
        st.markdown("<h1>📚 금형기술사 기출문제 리스트</h1>", unsafe_allow_html=True)
        st.write("필터링된 문제 목록입니다. 목록에서 문제를 선택한 후 하단 버튼을 클릭하면 상세 학습 화면으로 이동합니다.")
        
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
            st.warning("조건에 해당하는 문제가 없습니다. 좌측 사이드바 필터를 변경해 보세요.")
    
    else:
        q_text = st.session_state.current_q
        q_data = st.session_state.user_data[q_text]
        
        st.markdown("<div class='header-aligned-buttons'></div>", unsafe_allow_html=True)
        
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
    
        # TAB 1: 답안 개념 설명
        with tab1:
            key_hide_concept = f"hide_concept_{q_text}"
            if key_hide_concept not in st.session_state:
                st.session_state[key_hide_concept] = True
            is_concept_hidden = st.session_state[key_hide_concept]
    
            col_t1, col_h1, col_b1 = st.columns([68, 16, 16], vertical_alignment="center")
            
            with col_t1:
                st.markdown("### 1. 답안 개념 설명")
                
            with col_h1:
                toggle_label = "👁️ 입력창 보이기" if is_concept_hidden else "🙈 입력창 숨기기"
                if st.button(toggle_label, key=f"btn_toggle_concept_{q_text}", use_container_width=True):
                    if f"concept_area_{q_text}" in st.session_state:
                        c_text = st.session_state[f"concept_area_{q_text}"]
                        st.session_state.user_data[q_text]['concept'] = c_text
                        save_user_data(st.session_state.user_data)
                    st.session_state[key_hide_concept] = not is_concept_hidden
                    st.rerun()
                    
            with col_b1:
                if st.button("💾 저장하기", key=f"save_concept_{q_text}", type="primary", use_container_width=True):
                    if f"concept_area_{q_text}" in st.session_state:
                        c_text = st.session_state[f"concept_area_{q_text}"]
                        st.session_state.user_data[q_text]['concept'] = c_text
                    save_user_data(st.session_state.user_data)
                    st.toast("개념 설명이 성공적으로 저장되었습니다!")
    
            if not is_concept_hidden:
                concept_text = st.text_area(
                    "개념을 정리하세요. (마크다운 지원)", 
                    value=q_data.get('concept', ''), 
                    height=180, 
                    key=f"concept_area_{q_text}",
                    label_visibility="collapsed"
                )
                if q_data.get('concept'):
                    st.write("---")
                    st.markdown("#### 📖 개념 설명 (서식 적용 화면)")
                    with st.container(border=True):
                        render_formatted_content(q_data['concept'])
            else:
                if q_data.get('concept'):
                    with st.container(border=True):
                        render_formatted_content(q_data['concept'])
                else:
                    st.caption("작성된 개념 설명이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")
    
        # TAB 2: 모범 답안
        with tab2:
            key_hide_answer = f"hide_answer_{q_text}"
            if key_hide_answer not in st.session_state:
                st.session_state[key_hide_answer] = True
            is_answer_hidden = st.session_state[key_hide_answer]
            
            col_t2, col_h2, col_b2 = st.columns([68, 16, 16], vertical_alignment="center")
            
            with col_t2:
                st.markdown("### 2. 실제 시험 모범 답안")
                
            with col_h2:
                toggle_label = "👁️ 입력창 보이기" if is_answer_hidden else "🙈 입력창 숨기기"
                if st.button(toggle_label, key=f"btn_toggle_answer_{q_text}", use_container_width=True):
                    if f"answer_area_{q_text}" in st.session_state:
                        answer_content = st.session_state[f"answer_area_{q_text}"]
                        st.session_state.user_data[q_text]['answer'] = answer_content
                        save_user_data(st.session_state.user_data)
                    st.session_state[key_hide_answer] = not is_answer_hidden
                    st.rerun()
                    
            with col_b2:
                if st.button("💾 저장하기", key=f"save_answer_{q_text}", type="primary", use_container_width=True):
                    if f"answer_area_{q_text}" in st.session_state:
                        answer_content = st.session_state[f"answer_area_{q_text}"]
                        st.session_state.user_data[q_text]['answer'] = answer_content
                    save_user_data(st.session_state.user_data)
                    st.toast("모범 답안이 성공적으로 저장되었습니다!")
    
            if not is_answer_hidden:
                answer_text = st.text_area(
                    "시험 양식에 맞춘 모범 답안을 작성하세요. (마크다운 지원)", 
                    value=q_data.get('answer', ''), 
                    height=180, 
                    key=f"answer_area_{q_text}",
                    label_visibility="collapsed"
                )
                if q_data.get('answer'):
                    st.write("---")
                    st.markdown("#### 📄 모범 답안 (서식 적용 화면)")
                    with st.container(border=True):
                        render_formatted_content(q_data['answer'])
            else:
                if q_data.get('answer'):
                    with st.container(border=True):
                        render_formatted_content(q_data['answer'])
                else:
                    st.caption("작성된 모범 답안이 없습니다. '입력창 보이기'를 눌러 내용을 입력해 보세요.")
    
        # TAB 3: 추가자료 및 메모
        with tab3:
            key_edit_memo = f"edit_memo_{q_text}"
            key_memo_area = f"memo_area_{q_text}"
            
            if key_edit_memo not in st.session_state:
                st.session_state[key_edit_memo] = False

            col_t3, col_b3 = st.columns([70, 30], vertical_alignment="center")
            
            with col_t3:
                st.markdown("### 3. 추가자료 및 메모")

            with col_b3:
                if st.session_state[key_edit_memo]:
                    if st.button("💾 저장하기", key=f"save_memo_{q_text}", type="primary", use_container_width=True):
                        if key_memo_area in st.session_state:
                            memo_content = st.session_state[key_memo_area]
                            st.session_state.user_data[q_text]['memo'] = memo_content
                            save_user_data(st.session_state.user_data)
                            st.toast("메모가 저장되었습니다!")
                        st.session_state[key_edit_memo] = False
                        st.rerun()
                else:
                    if st.button("✏️ 수정하기", key=f"btn_edit_memo_{q_text}", use_container_width=True):
                        st.session_state[key_edit_memo] = True
                        st.rerun()

            current_memo = st.session_state.user_data[q_text].get('memo', '')

            if st.session_state[key_edit_memo]:
                st.text_area(
                    "메모 내용 편집",
                    value=current_memo,
                    key=key_memo_area,
                    height=300,
                    label_visibility="collapsed"
                )
            else:
                if current_memo.strip():
                    with st.container(border=True):
                        render_formatted_content(current_memo)
                else:
                    st.info("등록된 추가자료나 메모가 없습니다. 우측 상단의 '✏️ 수정하기' 버튼을 눌러 작성해 보세요.")
    
        # TAB 4: 구글 검색
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
    
        # TAB 5: 이미지 및 설명 자료
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
                        try:
                            new_image_item = upload_image_to_drive(uploaded_img)
                            new_image_item.update({"caption": img_caption or uploaded_img.name, "note": img_note})
                            st.session_state.user_data[q_text]['image_notes'].append(new_image_item)
                            if save_user_data(st.session_state.user_data):
                                st.toast("이미지와 설명이 성공적으로 저장되었습니다!")
                                st.rerun()
                            else:
                                st.session_state.user_data[q_text]['image_notes'].pop()
                        except Exception as e:
                            st.error(f"이미지 저장 실패: {e}")
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
                    show_stored_image(selected_item)

                with col_text:
                    key_edit_item = f"edit_item_{selected_img_idx}_{q_text}"
                    if key_edit_item not in st.session_state:
                        st.session_state[key_edit_item] = False

                    col_n_title, col_n_btn = st.columns([60, 40], vertical_alignment="center")
                    with col_n_title:
                        st.markdown("##### 📝 이미지 설명")
                    with col_n_btn:
                        if st.session_state[key_edit_item]:
                            if st.button("💾 수정 저장", key=f"btn_save_item_{selected_img_idx}_{q_text}", type="primary", use_container_width=True):
                                new_cap = st.session_state.get(f"edit_cap_{selected_img_idx}_{q_text}", selected_item.get('caption', ''))
                                new_note = st.session_state.get(f"edit_note_{selected_img_idx}_{q_text}", selected_item.get('note', ''))
                                
                                st.session_state.user_data[q_text]['image_notes'][selected_img_idx]['caption'] = new_cap
                                st.session_state.user_data[q_text]['image_notes'][selected_img_idx]['note'] = new_note
                                
                                save_user_data(st.session_state.user_data)
                                st.toast("이미지 설명이 수정되었습니다!")
                                st.session_state[key_edit_item] = False
                                st.rerun()
                        else:
                            if st.button("✏️ 설명 수정", key=f"btn_edit_item_{selected_img_idx}_{q_text}", use_container_width=True):
                                st.session_state[key_edit_item] = True
                                st.rerun()

                    if st.session_state[key_edit_item]:
                        st.text_input("제목/캡션 수정", value=selected_item.get('caption', ''), key=f"edit_cap_{selected_img_idx}_{q_text}")
                        st.text_area("설명 내용 수정", value=selected_item.get('note', ''), height=200, key=f"edit_note_{selected_img_idx}_{q_text}")
                    else:
                        note_content = selected_item.get('note', '')
                        if note_content:
                            with st.container(border=True):
                                render_formatted_content(note_content)
                        else:
                            st.caption("작성된 설명 내용이 없습니다.")
                    
                    st.write("---")
                    if st.button("🗑️ 선택된 이미지 삭제", key=f"del_img_{selected_img_idx}_{q_text}"):
                        st.session_state.user_data[q_text]['image_notes'].pop(selected_img_idx)
                        save_user_data(st.session_state.user_data)
                        st.toast("이미지 자료가 삭제되었습니다.")
                        st.rerun()

elif st.session_state.main_mode == "note":

    if "selected_note_id" not in st.session_state:
        st.session_state.selected_note_id = None
    if "note_sub_mode" not in st.session_state:
        st.session_state.note_sub_mode = "list"

    # [1] 학습노트 상세 보기
    if st.session_state.note_sub_mode == "detail" and st.session_state.selected_note_id:
        note = next((n for n in st.session_state.notes if n["id"] == st.session_state.selected_note_id), None)
        
        if note:
            st.markdown("<div class='header-aligned-buttons'></div>", unsafe_allow_html=True)
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

            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

            with st.container(border=True):
                if note.get("content"):
                    render_formatted_content(note["content"])
                else:
                    st.info("작성된 노트 내용이 없습니다.")

            imgs = note.get("images", [])
            if not imgs and note.get("image_base64"):
                imgs = [note["image_base64"]]

            if imgs:
                st.markdown("<div style='margin-top: 15px; border-top: 1px solid #333; padding-top: 10px;'></div>", unsafe_allow_html=True)
                st.markdown("**🖼️ 첨부 이미지**")
                img_cols = st.columns(min(len(imgs), 3))
                for idx, b64_img in enumerate(imgs):
                    with img_cols[idx % 3]:
                        show_stored_image(b64_img)

            links = note.get("links", [])
            if not links and note.get("link"):
                links = [note["link"]]

            if links:
                st.markdown("<div style='margin-top: 15px; border-top: 1px solid #333; padding-top: 10px;'></div>", unsafe_allow_html=True)
                st.markdown("**🔗 관련 링크**")
                for link in links:
                    st.markdown(f"- [{link}]({link})")

        else:
            st.error("해당 노트를 찾을 수 없습니다.")
            if st.button("📋 노트목록으로 돌아가기"):
                st.session_state.note_sub_mode = "list"
                st.session_state.selected_note_id = None
                st.rerun()

    # [2] 학습노트 편집
    elif st.session_state.note_sub_mode == "edit" and st.session_state.selected_note_id:
        note = next((n for n in st.session_state.notes if n["id"] == st.session_state.selected_note_id), None)
        
        if note:
            st.markdown("<div class='header-aligned-buttons'></div>", unsafe_allow_html=True)
            col_b1, _ = st.columns([1.5, 8.5])
            with col_b1:
                if st.button("⬅️ 취소", use_container_width=True):
                    st.session_state.note_sub_mode = "detail"
                    st.rerun()

            st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
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
                            show_stored_image(b64_img)
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
                            try:
                                keep_imgs.append(upload_image_to_drive(img_f))
                            except Exception as e:
                                st.error(f"이미지 업로드 실패: {e}")
                                st.stop()

                    note["category"] = edit_cat
                    note["title"] = edit_title
                    note["content"] = format_to_markdown(edit_content)
                    note["links"] = [line.strip() for line in edit_links_raw.split('\n') if line.strip()]
                    note["images"] = keep_imgs
                    note["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    if not save_notes(st.session_state.notes):
                        st.stop()
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

    # [3] 학습노트 메인 리스트
    else:
        st.markdown("<h1>📖 학습노트 관리</h1>", unsafe_allow_html=True)
        st.write("나만의 금형기술사 서브노트 및 개념 정리 노트 목록입니다. 목록에서 노트를 선택하여 상세 내용을 확인하세요.")

        c_search, c_new, c_backup, c_save = st.columns([2.8, 1.2, 1.4, 1.1])
        with c_search:
            note_search_kw = st.text_input("🔍 노트 검색", placeholder="검색어 입력...", label_visibility="collapsed")
        with c_new:
            show_create_form = st.checkbox("➕ 새 노트 작성", value=False)
        with c_backup:
            show_backup_menu = st.checkbox("💾 데이터 백업/복원", value=False)
        with c_save:
            if st.button("💾 저장", type="primary", use_container_width=True):
                save_notes(st.session_state.notes)
                st.toast("학습노트가 저장되었습니다!", icon="✅")

        with st.expander("🛠️ 기존 Base64 이미지 Google Drive로 이전"):
            st.caption("먼저 JSON 백업을 다운로드하세요. 기존 이미지가 생략된 경우 원본 백업이 필요합니다.")
            if st.button("기존 이미지 Drive로 이전 시작", key="migrate_all_images"):
                import copy
                notes_copy = copy.deepcopy(st.session_state.notes)
                data_copy = copy.deepcopy(st.session_state.user_data)
                migrated_count = 0
                errors = []
                for note in notes_copy:
                    originals = note.get("images", []) or ([note["image_base64"]] if note.get("image_base64") else [])
                    result = []
                    for item in originals:
                        try:
                            new_item, changed = migrate_image_item(item)
                            result.append(new_item)
                            migrated_count += int(changed)
                        except Exception as e:
                            result.append(item)
                            errors.append(f"노트 {note.get('title')}: {e}")
                    if originals:
                        note["images"] = result
                        note.pop("image_base64", None)
                for question, entry in data_copy.items():
                    if not isinstance(entry, dict):
                        continue
                    for i, item in enumerate(entry.get("image_notes", [])):
                        try:
                            new_item, changed = migrate_image_item(item)
                            entry["image_notes"][i] = new_item
                            migrated_count += int(changed)
                        except Exception as e:
                            errors.append(f"문제 {str(question)[:30]} 이미지 {i+1}: {e}")
                ok_notes = save_notes(notes_copy)
                ok_data = save_user_data(data_copy)
                if ok_notes:
                    st.session_state.notes = notes_copy
                if ok_data:
                    st.session_state.user_data = data_copy
                st.info(f"Drive 이전 {migrated_count}건 시도 / 학습노트 저장: {ok_notes} / 기출문제 저장: {ok_data}")
                for err in errors[:15]:
                    st.warning(err)

        if show_backup_menu:
            with st.expander("💾 노트 데이터 백업 / 복원 (JSON 파일)", expanded=True):
                col_export, col_import = st.columns(2)
                with col_export:
                    notes_json_str = json.dumps(st.session_state.notes, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📥 노트 백업 다운로드",
                        data=notes_json_str,
                        file_name="notes_backup.json",
                        mime="application/json",
                        use_container_width=True
                    )
                with col_import:
                    uploaded_backup = st.file_uploader("📤 백업 파일 불러오기", type=["json"], key="restore_notes_uploader")
                    if uploaded_backup is not None:
                        if st.button("🔄 데이터 복원 적용", type="primary", use_container_width=True):
                            try:
                                loaded_backup_notes = json.load(uploaded_backup)
                                if isinstance(loaded_backup_notes, list):
                                    st.session_state.notes = loaded_backup_notes
                                    save_notes(st.session_state.notes)
                                    st.success("노트를 성공적으로 복원했습니다!")
                                    st.rerun()
                                else:
                                    st.error("올바른 백업 파일 형식이 아닙니다.")
                            except Exception as e:
                                st.error(f"복원 실패: {e}")

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
                            formatted_content = new_content.strip()
                            links_list = [line.strip() for line in new_links_raw.split('\n') if line.strip()]
                            imgs_list = []
                            if uploaded_imgs:
                                for img_f in uploaded_imgs:
                                    try:
                                        imgs_list.append(upload_image_to_drive(img_f))
                                    except Exception as e:
                                        st.error(f"이미지 업로드 실패: {e}")
                                        st.stop()
                    
                            new_id = int(time.time())
                            new_entry = {
                                "id": new_id,
                                "category": new_cat,
                                "title": new_title.strip(),
                                "content": formatted_content,
                                "links": links_list,
                                "images": imgs_list,
                                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            st.session_state.notes.insert(0, new_entry)
                            if not save_notes(st.session_state.notes):
                                st.stop()
                            st.toast("새 학습노트가 추가되었습니다!", icon="✅")
                    
                            st.session_state.selected_note_id = new_id
                            st.session_state.note_sub_mode = "detail"
                            st.rerun()

        filtered_notes = st.session_state.notes
        if note_search_kw.strip():
            kw = note_search_kw.strip().lower()
            filtered_notes = [
                n for n in filtered_notes
                if kw in n.get("title", "").lower() or kw in n.get("content", "").lower() or kw in n.get("category", "").lower()
            ]

        if not filtered_notes:
            st.info("등록된 학습노트가 없거나 검색 결과가 없습니다.")
        else:
            table_data = []
            for n in filtered_notes:
                has_img = "🖼️" if (n.get("images") or n.get("image_base64")) else ""
                has_link = "🔗" if (n.get("links") or n.get("link")) else ""
                attach_str = f"{has_img} {has_link}".strip()
                
                table_data.append({
                    "id": n["id"],
                    "분류": n.get("category", "기타기술"),
                    "노트 제목": n.get("title", "제목 없음"),
                    "첨부": attach_str if attach_str else "-",
                    "수정일": n.get("updated_at", "-")
                })
            
            notes_df = pd.DataFrame(table_data)

            event_note = st.dataframe(
                notes_df[['분류', '노트 제목', '첨부', '수정일']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "분류": st.column_config.Column("분류", width=120),
                    "노트 제목": st.column_config.Column("노트 제목", width=620),
                    "첨부": st.column_config.Column("첨부", width=80),
                    "수정일": st.column_config.Column("수정일", width=120)
                }
            )

            title_options = list(notes_df['노트 제목'])
            selected_rows = event_note.selection.get("rows", [])
            
            if selected_rows:
                row_idx = selected_rows[0]
                if row_idx < len(notes_df):
                    st.session_state["sb_note_title"] = notes_df.iloc[row_idx]['노트 제목']

            if "sb_note_title" not in st.session_state or st.session_state["sb_note_title"] not in title_options:
                st.session_state["sb_note_title"] = title_options[0]

            selected_note_title = st.selectbox("상세 보기할 노트 선택", options=title_options, key="sb_note_title")

            if st.button("📖 선택한 노트 보기", type="primary", use_container_width=False):
                matched_note = next((n for n in filtered_notes if n.get("title") == selected_note_title), None)
                if matched_note:
                    st.session_state.selected_note_id = matched_note["id"]
                    st.session_state.note_sub_mode = "detail"
                    st.rerun()
