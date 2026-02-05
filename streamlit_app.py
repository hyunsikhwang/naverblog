import streamlit as st
import httpx
from bs4 import BeautifulSoup
import re
import time
import random
import string
import xml.etree.ElementTree as ET
import os
import subprocess

# 페이지 설정
st.set_page_config(
    page_title="네이버 블로그 스크래퍼 v2.0.0",
    page_icon="📝",
    layout="wide"
)

# Playwright 설치 확인 및 실행
def install_playwright():
    try:
        import playwright
    except ImportError:
        subprocess.run(["pip", "install", "playwright"])
    
    # 브라우저 설치 여부 확인 후 설치
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch()
    except Exception:
        with st.spinner("브라우저 엔진을 설치 중입니다 (최초 1회)..."):
            subprocess.run(["python", "-m", "playwright", "install", "chromium"])

# 앱 시작 시 설치 시도
install_playwright()

from playwright.sync_api import sync_playwright

# 커스텀 CSS (디자인 유지)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%; border-radius: 10px; height: 3em;
        background-color: #2db400; color: white; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #269600; color: white; border: none; }
    .stTextInput>div>div>input { border-radius: 10px; }
    div.stTextArea textarea { border-radius: 10px; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

def generate_random_id(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_stealth_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    ua = random.choice(user_agents)
    return {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://section.blog.naver.com/',
        'Upgrade-Insecure-Requests': '1'
    }

def scrape_with_playwright(url):
    """Playwright를 사용한 리얼 브라우저 스크래핑 (최강의 차단 우회)"""
    try:
        with sync_playwright() as p:
            # 헤드리스 브라우저 실행
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            
            # 페이지 이동
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # iframe(mainFrame) 체크
            iframe_element = page.query_selector("iframe#mainFrame")
            if iframe_element:
                # iframe 내부로 전환하여 데이터 가져오기
                frame = page.frame(name="mainFrame")
                if frame:
                    # 스마트 에디터 본문 대기
                    frame.wait_for_selector(".se-main-container, #postViewArea", timeout=10000)
                    content = frame.inner_text(".se-main-container") or frame.inner_text("#postViewArea")
                    browser.close()
                    return content
            
            # iframe이 없는 경우 직접 추출
            content = page.inner_text(".se-main-container") or page.inner_text("#postViewArea")
            browser.close()
            return content
    except Exception as e:
        if 'browser' in locals(): browser.close()
        return None

def scrape_rss_content(blog_id, log_no):
    try:
        with httpx.Client(timeout=10.0) as client:
            rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
            response = client.get(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall('.//item'):
                    if log_no in item.find('link').text:
                        soup = BeautifulSoup(item.find('description').text, 'html.parser')
                        return soup.get_text(separator='\n', strip=True)
    except Exception: pass
    return None

def scrape_naver_blog_content(blog_url):
    # URL 분석
    blog_id, log_no = "", ""
    if 'blog.naver.com' in blog_url:
        mid = re.search(r'blogId=([^&]+)', blog_url)
        mno = re.search(r'logNo=([^&]+)', blog_url)
        if mid and mno:
            blog_id, log_no = mid.group(1), mno.group(1)
        else:
            parts = blog_url.split('/')
            if len(parts) >= 5:
                blog_id, log_no = parts[3], parts[4].split('?')[0]

    # --- Layer 1: Playwright (최우선 브라우저 자동화) ---
    with st.spinner("브라우저를 구동하여 안전하게 접근 중..."):
        content = scrape_with_playwright(blog_url)
        if content: return content

    # --- Layer 2: RSS Fallback ---
    if blog_id and log_no:
        content = scrape_rss_content(blog_id, log_no)
        if content: return content

    # --- Layer 3: Stealth HTTP Fallback ---
    try:
        with httpx.Client(http2=True, timeout=15.0) as client:
            mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            res = client.get(mobile_url, headers=get_stealth_headers())
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                content_div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
                if content_div: return content_div.get_text(separator='\n', strip=True)
    except Exception: pass

    return "모든 시도가 실패했습니다. (네이버 보안 시스템 차단 가능성 높음)"

def remove_blank_lines(text: str) -> str:
    if not text: return ""
    for ch in ('\u200B', '\uFEFF'):
        text = text.replace(ch, '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    cleaned = re.sub(r'(?m)^[\s\u00A0]*\n', '', text)
    return cleaned.strip()

# UI 구성 (기존 유지)
st.title("📝 네이버 블로그 본문 스크래퍼 v2.0")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    blog_url = st.text_input("스크래핑할 네이버 블로그 URL을 입력하세요", placeholder="https://blog.naver.com/...")
    scrape_button = st.button("내용 추출하기")

with col2:
    st.info("""
    **사용 방법:**
    1. 네이버 블로그 주소를 입력합니다.
    2. '내용 추출하기' 버튼을 누릅니다.
    3. 아래 결과창에서 텍스트를 복사합니다.
    """)

if scrape_button:
    if not blog_url:
        st.warning("URL을 입력해주세요.")
    else:
        raw_content = scrape_naver_blog_content(blog_url)
        if raw_content and not raw_content.startswith("모든 시도가"):
            content = remove_blank_lines(raw_content)
            st.success("데이터 추출 성공!")
            st.subheader("추출된 본문 내용")
            st.text_area(label="결과물 (복사 가능)", value=content, height=400, help="전체 텍스트를 선택하여 복사할 수 있습니다.")
            st.download_button(
                label="텍스트 파일로 다운로드",
                data=content,
                file_name="scraped_blog.txt",
                mime="text/plain"
            )
        else:
            st.error(raw_content)

st.markdown("---")
st.caption("© 2024 Naver Blog Scraper Tools | Playwright & Cloud 최적화 v2.0")
