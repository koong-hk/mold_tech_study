import streamlit as st
import pandas as pd
import json
import os
import re

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 CSS 적용
# -----------------------------------------------------------------------------
st.set_page_config(page_title="금형기술사 학습 시스템", layout="wide")

st.markdown("""
    <style>
        /* 1. 메인 영역 상단 여백 최소화 */
        .block-container {
            padding-top: 3.0rem !important;
            padding-bottom: 1.5rem !important;
        }
        
        /* 2. 제목 글자 크기 축소 */
        div[data-testid="stMarkdownContainer"] h1 {
            font-size: 1.5rem !important;
            margin-top: 5px !important;
            margin-bottom: 1.5rem !important;
        }

        /* 3. 좌측 파일 업로더 가로/세로 여백 조정 */
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

        section[data-testid="stSidebar"] label {
            text-align: left !important;
            justify-content: flex-start !important;
            margin-bottom: 0px !important;
            padding-bottom: 0px !important;
            padding-top: 0px !important;
        }
        section[data-testid="stSidebar"] label p {
            font-size: 0.88rem !important;
            font-weight: 600 !important;
            margin: 0 !important;
            padding: 0 !important;
            text-align: left !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSelectbox"] {
            margin-bottom: 6px !important;
            margin-top: 0px !important;
            padding: 0px !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
            min-height: 32px !important;
            height: 32px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            padding-left: 8px !important;
            padding-right: 8px !important;
            display: flex !important;
            align-items: center !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] * {
            font-size: 0.85rem !important;
            line-height: 1.1 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCheckbox"] {
            margin-top: 4px !important;
            margin-bottom: 4px !important;
        }

        /* 7. 상세 페이지 문제 박스와 하단 탭 사이 간격 */
        div[data-testid="stTabs"] {
            margin-top: 1.5rem !important;
        }

        /* 8. 탭 상단 우측 버튼 동일 사이즈 및 우측 밀착 정렬 */
        div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) div[data-testid="stButton"],
        div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] {
            display: flex !important;
            width: 100% !important;
        }
        div[data-testid="stTabs"] div[data-testid="stButton"] > button {
            width: 100% !important;
        }

        /* 9. 중요도 설정 등 일반 Selectbox 라벨 여백 축소 */
        div[data-testid="stSelectbox"] label {
            margin-bottom: 2px !important;
            padding-bottom: 0px !important;
        }
        div[data-testid="stSelectbox"] label p {
            margin-bottom: 0px !important;
        }
        
        /* 10. 마크다운 서식 적용 화면 가독성 및 계층별 들여쓰기/번호 스타일링 */
        div[data-testid="stMarkdownContainer"] p {
            line-height: 1.85 !important;
            margin-bottom: 0.9em !important;
            word-break: keep-all !important;
            font-size: 1.02rem !important;
        }

        /* 1계층 순서 있는 목록 (1. 2. 3.) */
        div[data-testid="stMarkdownContainer"] ol {
            list-style-type: decimal !important;
            margin-left: 1.8em !important;
            padding-left: 0.2em !important;
            margin-bottom: 0.8em !important;
        }
        /* 2계층 순서 있는 목록 (A. B. C.) */
        div[data-testid="stMarkdownContainer"] ol ol {
            list-style-type: upper-alpha !important;
            margin-left: 1.6em !important;
            margin-top: 0.3em !important;
            margin-bottom: 0.5em !important;
        }
        /* 3계층 순서 있는 목록 (a. b. c.) */
        div[data-testid="stMarkdownContainer"] ol ol ol {
            list-style-type: lower-alpha !important;
            margin-left: 1.6em !important;
        }

        /* 1계층 순서 없는 목록 (● 채운 원) */
        div[data-testid="stMarkdownContainer"] ul {
            list-style-type: disc !important;
            margin-left: 1.8em !important;
            padding-left: 0.2em !important;
            margin-bottom: 0.8em !important;
        }
        /* 2계층 순서 없는 목록 (○ 빈 원) */
        div[data-testid="stMarkdownContainer"] ul ul {
            list-style-type: circle !important;
            margin-left: 1.6em !important;
            margin-top: 0.3em !important;
            margin-bottom: 0.5em !important;
        }
        /* 3계층 순서 없는 목록 (■ 사각형) */
        div[data-testid="stMarkdownContainer"] ul ul ul {
            list-style-type: square !important;
            margin-left: 1.6em !important;
        }

        /* 리스트 항목 높이 및 여백 */
        div[data-testid="stMarkdownContainer"] li {
            line-height: 1.8 !important;
            margin-bottom: 0.4em !important;
            word-break: keep-all !important;
        }
        
        /* 제목 스타일링 */
        div[data-testid="stMarkdownContainer"] h2 {
            margin-top: 1.6em !important;
            margin-bottom: 0.7em !important;
            border-bottom: 1px solid #4a5568;
            padding-bottom: 0.3em;
        }
        div[data-testid="stMarkdownContainer"] h3 {
            margin-top: 1.3em !important;
            margin-bottom: 0.5em !important;
        }
        div[data-testid="stMarkdownContainer"] h4 {
            margin-top: 1.0em !important;
            margin-bottom: 0.4em !important;
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
    """
    가독성 향상을 위한 마크다운 텍스트 자동 가공 함수
    1. 마침표(.)로 끝나고 한 절/문장이 약 80% 이상(45자 이상) 채워진 경우 강제 줄바꿈(  \n) 삽입
    2. 일반 문장 단락 분할 최적화
    """
    if not text:
        return ""
    
    lines = text.splitlines()
    formatted_lines = []
    
    for line in lines:
        stripped = line.strip()
        # 제목(#), 표(|), 코드블록(```), 구분선(---) 등 특수 서식은 기존 형태 유지
        if stripped.startswith(('#', '|', '
