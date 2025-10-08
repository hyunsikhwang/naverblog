import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
from google import genai
from google.genai import types
import time

# --- 🎨 CSS 스타일 정의 ---
css = """
/* --- 전체 페이지 및 폰트 스타일 --- */
body {
    font-family: 'Pretendard', sans-serif;
}

/* --- Streamlit 기본 UI 숨기기 --- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- 메인 앱 컨테이너 스타일 --- */
.stApp {
    background-color: #1a1a1a; /* 어두운 배경색 */
    color: #fafafa; /* 밝은 텍스트 색상 */
}

/* --- 제목 스타일 --- */
h1 {
    color: #64ffda; /* 포인트 컬러 (민트) */
    text-align: center;
    font-weight: bold;
    padding-bottom: 20px;
    border-bottom: 1px solid #333;
}

/* --- 설명 텍스트 스타일 --- */
.st-emotion-cache-16idsys p {
    text-align: center;
    color: #a9a9a9;
    font-size: 1.1rem;
    padding-bottom: 20px;
}

/* --- Selectbox 스타일 --- */
div[data-baseweb="select"] > div {
    background-color: #262730;
    border: 1px solid #444;
    border-radius: 8px;
    color: #fafafa;
}
div[data-baseweb="select"] > div:hover {
    border-color: #64ffda;
}

/* --- 버튼 스타일 --- */
.stButton>button {
    width: 100%;
    border: 2px solid #64ffda;
    border-radius: 8px;
    background-color: transparent;
    color: #64ffda;
    font-weight: bold;
    padding: 10px 0;
    transition: all 0.2s ease-in-out;
}
.stButton>button:hover {
    background-color: #64ffda;
    color: #1a1a1a;
    border-color: #64ffda;
}
.stButton>button:active {
    background-color: #52cca9;
    border-color: #52cca9;
}

/* --- 결과 출력 영역 스타일 --- */
.result-container {
    background-color: #262730;
    padding: 25px;
    border-radius: 10px;
    border: 1px solid #333;
    margin-top: 20px;
    line-height: 1.8; /* 줄 간격 조절로 가독성 향상 */
}

/* 결과 컨테이너 내의 마크다운 h-tag 색상 변경 */
.result-container h2, .result-container h3, .result-container strong {
    color: #64ffda;
}

/* 결과 컨테이너 내의 구분선 스타일 */
.result-container hr {
    border-top: 1px solid #444;
}
"""

st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Streamlit secrets에서 API 키 가져오기
api_key = st.secrets["api_key"]

st.title("🎈 NAVER Blog Scraper")
st.write("네이버 블로그 포스트를 선택하면 본문을 요약 및 정리해 드립니다.")


def fetch_post_list(category_no=0, item_count=24, page=1, user_id="gomting"):
    url = f"https://m.blog.naver.com/api/blogs/{user_id}/post-list"
    params = {"categoryNo": category_no, "itemCount": item_count, "page": page}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Referer": f"https://m.blog.naver.com/{user_id}?categoryNo={category_no}",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"블로그 목록 요청 중 오류 발생: {e}")
    except ValueError:
        st.error("응답을 JSON으로 파싱할 수 없습니다.")
    return None

def get_post_links(response):
    links = {}
    if not response or not response.get('isSuccess', False):
        st.warning("블로그 포스트 목록을 가져오는데 실패했습니다.")
        return {}
    items = response.get('result', {}).get('items', [])
    if not items:
        st.info("해당 블로그에 표시할 게시글이 없습니다.")
        return {}
    for item in items:
        blog_id = item.get('domainIdOrBlogId')
        log_no = item.get('logNo')
        title = item.get('titleWithInspectMessage', '<제목 없음>')
        link = f"https://m.blog.naver.com/{blog_id}/{log_no}"
        links[title] = link
    return links

def scrape_naver_blog(pc_url: str) -> str:
    mobile_url = pc_url.replace("blog.naver.com", "m.blog.naver.com")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"}
    try:
        response = requests.get(mobile_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        content_div = soup.find("div", {"class": "se-main-container"})
        if content_div:
            return content_div.get_text(separator='\n', strip=True)
        else:
            raise ValueError("본문 컨테이너(se-main-container)를 찾지 못했습니다.")
    except requests.RequestException as e:
        raise ConnectionError(f"페이지 요청 실패: {e}")

# --- ✨ 모델 변경 및 스트리밍 로직 적용 ---
def generate(api_key, content_html):
    """ gemma-3-27b-it 모델을 사용하여 스트리밍 방식으로 텍스트를 생성합니다. """
    text = f"""다음 원문에서 '한줄 코멘트'를 추출해서 가장 먼저 보여주고, 나머지 내용은 문단에 맞춰 적절하게 줄바꿈을 삽입해줘. '한줄 코멘트'와 '본문'이라는 제목을 Markdown 형식으로 강조해줘. 원문의 내용은 절대 변경하지 마.

포맷:
**한줄 코멘트:** {{한줄 코멘트}}

---

**본문**
{{본문}}

---
원문: {content_html}
"""
    client = genai.Client(api_key=api_key)
    model = "gemma-3-27b-it"  # 사용자 요청 모델로 변경
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.text:
            yield chunk.text
        time.sleep(0.01)

# --- 메인 실행 로직 ---
if __name__ == "__main__":
    response = fetch_post_list(user_id="ranto28") # 블로그 ID
    
    if response:
        links = get_post_links(response)
        if links:
            with st.form(key='blog_form'):
                selected_title = st.selectbox("정리할 블로그 포스트를 선택하세요:", options=list(links.keys()))
                submit_button = st.form_submit_button(label="본문 정리 시작")

            if submit_button and selected_title:
                selected_url = links[selected_title]
                
                with st.spinner('블로그 본문을 가져오는 중...'):
                    try:
                        content_html = scrape_naver_blog(selected_url)
                    except Exception as e:
                        st.error(f"본문을 가져오는 중 오류가 발생했습니다: {e}")
                        content_html = None
                
                if content_html:
                    with st.spinner('AI가 본문을 정리하고 있습니다... 잠시만 기다려주세요.'):
                        try:
                            # st.empty()를 사용하여 스트리밍 결과를 담을 공간 확보
                            result_placeholder = st.empty()
                            full_response = ""
                            # 스트리밍 응답을 수동으로 반복 처리
                            for chunk in generate(api_key, content_html):
                                full_response += chunk
                                # 매번 전체 내용을 CSS 컨테이너와 함께 다시 그림
                                result_placeholder.markdown(f'<div class="result-container">{full_response}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"AI 모델 호출 중 오류가 발생했습니다: {e}")
    else:
        st.error("블로그 데이터를 가져오지 못했습니다. 블로그 ID를 확인해주세요.")