import re
import streamlit as st

# 1. 목록 계층화 및 들여쓰기 CSS 설정
st.markdown("""
<style>
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

# 2. 콜론(:) 조건부 줄바꿈 및 들여쓰기 처리 함수
def format_readable_text(text: str) -> str:
    if not text:
        return ""
    
    # 콜론(:) 뒤에 불릿 기호(* 또는 -)가 오지 않는 경우에만 줄바꿈 + 들여쓰기 적용
    # 예시: "개요: 본문 내용" -> "개요:\n  본문 내용"
    # 제외: "개요: * 본문 내용" -> "개요: * 본문 내용"
    pattern = r':\s*(?!\*|-)'
    processed_text = re.sub(pattern, ':\n<span class="indented-body">', text)
    
    # 태그 닫기 처리 (줄바꿈 발생 시 개별 블록 닫기)
    lines = processed_text.split('\n')
    formatted_lines = []
    for line in lines:
        if '<span class="indented-body">' in line and not line.endswith('</span>'):
            line += '</span>'
        formatted_lines.append(line)
        
    return "\n".join(formatted_lines)
