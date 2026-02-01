import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import base64
import os
from openai import OpenAI
import time


api_key = st.secrets["api_key"]

# Minimal + Modern CSS 스타일 추가
st.set_page_config(
    page_title="Naver Blog AI Scraper",
    page_icon="🎈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Modern CSS using Google Fonts and Glassmorphism
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap');

    :root {
        --primary: #4f46e5;
        --primary-hover: #4338ca;
        --bg-gradient: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        --card-bg: rgba(255, 255, 255, 0.8);
        --text-main: #1e293b;
        --text-secondary: #64748b;
        --accent: #10b981;
    }

    .main {
        background: var(--bg-gradient);
        font-family: 'Inter', sans-serif;
    }

    /* Reduce top margin */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    /* Gradient Header */
    .header-container {
        padding: 1rem 0;
        text-align: center;
    }
    
    .gradient-text {
        background: linear-gradient(90deg, #4f46e5, #0ea5e9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        color: var(--text-secondary);
        font-size: 1.1rem;
        font-weight: 500;
    }

    /* Glassmorphism Card Style */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.1);
    }

    /* Customizing Streamlit Components */
    .stSelectbox label, .stTextArea label {
        font-weight: 600 !important;
        color: var(--text-main) !important;
    }

    .stButton > button {
        background: linear-gradient(90deg, #4f46e5, #4338ca);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 0.6rem 2rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(90deg, #4338ca, #3730a3);
        transform: scale(1.02);
    }

    /* Section Headers */
    .section-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .status-badge {
        background: #ecfdf5;
        color: #059669;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
</style>

<div class="header-container">
    <h1 class="gradient-text">Naver Blog Scraper</h1>
    <p class="subtitle">AI-powered insights from Naver's most popular blogs</p>
</div>
""", unsafe_allow_html=True)


def fetch_post_list(category_no=0, item_count=24, page=1, user_id="gomting"):
    """
    네이버 모바일 블로그 API에서 포스트 목록을 가져옵니다.
    
    Args:
        category_no (int): 카테고리 번호 (기본값: 0)
        item_count (int): 한 번에 가져올 아이템 수 (기본값: 24)
        page (int): 페이지 번호 (기본값: 1)
        user_id (str): 사용자 ID (예: "gomting")
    
    Returns:
        dict or None: JSON 파싱 결과, 실패 시 None
    """
    url = "https://m.blog.naver.com/api/blogs/ranto28/post-list"
    params = {
        "categoryNo": category_no,
        "itemCount": item_count,
        "page": page,
        "userId": user_id
    }
    # 주어진 모든 헤더를 그대로 반영
    headers = {
        "Host": "m.blog.naver.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Referer": "https://m.blog.naver.com/ranto28?categoryNo=0&tab=1",
        "Sec-CH-UA": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Priority": "u=1, i"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"요청 중 오류 발생: {e}")
    except ValueError:
        print("응답을 JSON으로 파싱할 수 없습니다.")

    return None

def print_blog_summary(response):
    links = {}
    """
    네이버 블로그 JSON 응답에서 주요 항목만 간결하게 출력합니다.
    """
    # 요청 성공 여부 확인
    if not response.get('isSuccess', False):
        print("요청에 실패했습니다.")
        return

    result = response.get('result', {})
    items = result.get('items', [])

    if not items:
        print("표시할 게시글이 없습니다.")
        return

    for item in items:
        blog_id = item.get('domainIdOrBlogId')
        log_no = item.get('logNo')
        title = item.get('titleWithInspectMessage', '<제목 없음>')
        comments = item.get('commentCnt', 0)
        sympathies = item.get('sympathyCnt', 0)
        # 본문은 첫 문장만 추출해 간략하게 보여줍니다.
        brief = item.get('briefContents', '').split('。')[0]
        link = f"https://m.blog.naver.com/{blog_id}/{log_no}"

        # links.append(f"{link}")
        links[f"{title}"] = f"{link}"
        # print(f"제목       : {title}")
        # print(f"링크       : {link}")
        # print(f"댓글/공감  : {comments}개  /  {sympathies}개")
        # print(f"요약       : {brief}…")
        # print("-" * 60)
    
    return links

def convert_to_mobile_url(pc_url: str) -> str:
    """
    PC 버전 네이버 블로그 URL을 모바일 버전 URL로 변환합니다.
    예: https://blog.naver.com/아이디/포스트번호 -> https://m.blog.naver.com/아이디/포스트번호
    """
    if "blog.naver.com" not in pc_url:
        raise ValueError("유효한 네이버 블로그 URL이 아닙니다.")
    # URL이 이미 모바일 버전이면 그대로 반환
    if "m.blog.naver.com" in pc_url:
        return pc_url

    # 간단하게 'blog.naver.com'을 'm.blog.naver.com'으로 대체합니다.
    mobile_url = pc_url.replace("blog.naver.com", "m.blog.naver.com")
    return mobile_url

def scrape_naver_blog(pc_url: str) -> str:
    """
    네이버 블로그 PC 버전 URL을 받아, 모바일 페이지에서 본문 HTML을 추출합니다.
    """
    mobile_url = convert_to_mobile_url(pc_url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/98.0.4758.102 Safari/537.36"
        )
    }
    response = requests.get(mobile_url, headers=headers)
    if not response.ok:
        raise ConnectionError(f"모바일 페이지 요청 실패: {response.status_code}")

    html_text = response.text
    soup = BeautifulSoup(html_text, "html.parser")

    # 예제 1: 일반적인 본문 컨테이너 div를 활용하는 경우
    content_div = soup.find("div", {"class": "se-main-container"})
    if content_div:
        # return str(content_div)
        return content_div.get_text(separator='\n', strip=True)

    # 예제 2: JSON 데이터가 포함된 <script> 태그에서 본문 추출 (예상 변수명이 __APOLLO_STATE__ 등)
    # 아래 정규식은 예시이며, 실제 변수명과 구조는 HTML 소스 확인 후 수정 필요합니다.
    pattern = re.compile(r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});', re.DOTALL)
    match = pattern.search(html_text)
    if match:
        json_str = match.group(1).strip()
        try:
            data = json.loads(json_str)
            # 데이터 구조에 따라 수정 필요: 예시로 postContent 혹은 content를 찾음
            if "post" in data and "content" in data["post"]:
                return data["post"]["content"]
        except json.JSONDecodeError:
            pass  # JSON 파싱 실패 시 아래 방법 사용

    # 예제 3: iframe 구조인 경우, iframe의 src를 추출하여 추가 요청
    iframe = soup.find("iframe")
    if iframe and iframe.has_attr("src"):
        iframe_src = iframe["src"]
        iframe_response = requests.get(iframe_src, headers=headers)
        if iframe_response.ok:
            iframe_soup = BeautifulSoup(iframe_response.text, "html.parser")
            # iframe 내에 본문이 있는지 확인 (예: div id="postViewArea")
            iframe_content = iframe_soup.find("div", {"id": "postViewArea"})
            if iframe_content:
                return str(iframe_content)

    raise ValueError("본문 데이터를 찾지 못했습니다. HTML 구조를 재확인해 주세요.")

def insert_line_breaks(text):
    """
    주어진 텍스트에서 아래 세 경우에 줄바꿈을 삽입합니다:
    1) 문장이 마침표로 끝난 직후
    2) 일련번호(예: '1.')가 나오기 바로 앞
    3) '한줄코멘트' 또는 '한줄 코멘트'가 나오기 바로 직전
    """
    # 1) 문장이 마침표로 끝난 직후: '...' 뒤에 \n 추가
    #    (?<!\n) 으로 이미 줄바꿈이 없는 경우만 처리
    text = re.sub(r'(?<!\n)\.(?=\s|$)', r'.\n', text)

    # 2) 일련번호 앞: '숫자+.' 앞에 \n 추가
    text = re.sub(r'(?<!\n)(?=(\d+\.))', r'\n', text)

    # 3) '한줄코멘트' 또는 '한줄 코멘트' 바로 직전: 앞에 \n 추가
    text = re.sub(r'(?<!\n)(?=(한줄\s*코멘트))', r'\n', text)

    return text

def generate(api_key, content_html, is_ranto28=True):

    if is_ranto28:
        prompt_text = f"""다음 원문에서 한줄 코멘트만 정확하게 추출해서 출력해주세요.
한줄 코멘트: {{한줄 코멘트}}
원문: {content_html}"""
    else:
        # For other blogs, provide Implications and 5-10 bullet points
        prompt_text = f"""다음 원문 내용을 분석하여 '시사점'과 함께 5개에서 10개 사이의 핵심 내용을 불렛 포인트(bullet points)로 요약해 주세요.
텍스트의 분량에 따라 불렛 포인트 개수를 5개에서 10개 사이로 적절히 조절해 주세요.

형식:
[시사점]
(여기에 시사점 내용 작성)

[핵심 요약]
- (핵심 내용 1)
- (핵심 내용 2)
...

원문: {content_html}"""

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    model = "openai/gpt-oss-120b:free"

    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt_text},
        ],
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content
        time.sleep(0.01)

def get_full_response(api_key, content_html, is_ranto28=True):
    """스트리밍 응답을 완전한 텍스트로 수집합니다."""
    full_response = ""
    for chunk in generate(api_key, content_html, is_ranto28):
        full_response += chunk
    return full_response

def extract_comment(full_response):
    """응답에서 한줄 코멘트만 추출합니다."""
    comment_match = re.search(r'한줄 코멘트:\s*(.*?)(?=\n원문:|$)', full_response, re.DOTALL)
    comment = comment_match.group(1).strip() if comment_match else "한줄 코멘트를 찾을 수 없습니다."
    return comment

def remove_blank_lines(text: str) -> str:
    # 1) Zero‑width space, BOM 같은 보이지 않는 문자 제거
    for ch in ('\u200B', '\uFEFF'):
        text = text.replace(ch, '')

    # 2) 줄 구분을 모두 '\n' 으로 통일
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 3) 완전히 공백만 있는 줄(탭, 스페이스, NBSP 등 포함) 제거
    #    (?m) 멀티라인 모드, ^…$ 에 \s 를 써서 유니코드 공백 전부 매칭
    cleaned = re.sub(r'(?m)^[\s\u00A0]*\n', '', text)

    # 4) 앞뒤에 남은 빈 줄/공백 잘라내기
    return cleaned.strip()

if __name__ == "__main__":
    # Settings in Sidebar
    with st.sidebar:
        st.markdown('<div class="section-header">⚙️ Settings</div>', unsafe_allow_html=True)
        
        custom_url = st.text_input("Custom Naver Blog URL (Optional):", placeholder="https://blog.naver.com/...")
        
        response = fetch_post_list()
        if response:
            links = print_blog_summary(response)
            if links:
                titles = list(links.keys())
                selected_title = st.selectbox("Or Select from Recent Posts:", titles)
                
                if not custom_url:
                    st.info(f"🔗 [Open Original Post]({links[selected_title]})")
                else:
                    st.info(f"🔗 [Open Custom Post]({custom_url})")
            else:
                st.error("Could not fetch post list.")
                st.stop()
        else:
            st.error("Failed to connect to Naver API.")
            st.stop()

    # Main Content Area
    col1, col2 = st.columns([1, 1], gap="large")

    try:
        with st.spinner("✨ AI is analyzing the post..."):
            if custom_url:
                post_url = custom_url
                display_title = "Custom URL Post"
            else:
                post_url = links[selected_title]
                display_title = selected_title
                
            is_ranto28 = "ranto28" in post_url
            
            content_text = scrape_naver_blog(post_url)
            content_text = remove_blank_lines(content_text)
            
            # AI Inference
            full_response = get_full_response(api_key, content_text, is_ranto28=is_ranto28)
            
            if is_ranto28:
                summary_content = extract_comment(full_response)
            else:
                summary_content = full_response

        with col1:
            st.markdown('<div class="section-header">📝 AI Summary <span class="status-badge">Powered by GPT-4</span></div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="glass-card">
                <div style="font-size: 1.1rem; line-height: 1.6; color: #1e293b; font-weight: 500; white-space: pre-wrap;">
                    {summary_content}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="section-header">📥 Export</div>', unsafe_allow_html=True)
            st.download_button(
                label="Download Original Content (.txt)",
                data=content_text,
                file_name=f"{display_title}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with col2:
            st.markdown('<div class="section-header">📄 Original Content</div>', unsafe_allow_html=True)
            
            # Clipboard Copy Button implementation
            import json
            
            # Use columns for labels and copy button
            c1, c2 = st.columns([3, 1])
            with c2:
                # Custom JS for clipboard copy
                safe_text = json.dumps(content_text)
                copy_button_html = f"""
                <button onclick='navigator.clipboard.writeText({safe_text})' style="
                    background-color: #4f46e5;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-family: 'Inter', sans-serif;
                    font-size: 0.8rem;
                    float: right;
                ">📋 Copy Content</button>
                """
                st.components.v1.html(f"""
                <style>
                    button:hover {{
                        background-color: #4338ca !important;
                    }}
                </style>
                {copy_button_html}
                """, height=50)

            st.markdown(f"""
            <div class="glass-card" style="height: 500px; overflow-y: auto;">
                <pre style="white-space: pre-wrap; font-family: 'Inter', sans-serif; font-size: 0.9rem; color: #475569;">
{content_text}
                </pre>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.exception(e)
