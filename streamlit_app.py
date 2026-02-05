import streamlit as st
import httpx
from bs4 import BeautifulSoup
import re
import time
import random
import string
import os
import subprocess

# 페이지 설정
st.set_page_config(
    page_title="네이버 블로그 스크래퍼 v2.1.0",
    page_icon="📝",
    layout="wide"
)

# 디버깅 로그를 위한 세션 상태 초기화
if 'debug_logs' not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

# Playwright 설치 확인 및 실행
def install_playwright():
    try:
        import playwright
    except ImportError:
        add_log("Playwright 패키지 설치 시도 중...")
        subprocess.run(["pip", "install", "playwright"])
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch()
    except Exception as e:
        add_log(f"브라우저 엔진 미설치 확인: {str(e)}")
        with st.spinner("브라우저 엔진을 설치 중입니다 (최초 1회)..."):
            subprocess.run(["python", "-m", "playwright", "install", "chromium"])
            add_log("브라우저 엔진 설치 완료")

# 앱 시작 시 설치 시도
install_playwright()

from playwright.sync_api import sync_playwright

# 커스텀 CSS
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
    .stExpander { border-radius: 10px; border: 1px solid #ddd; }
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

def scrape_with_playwright(url, blog_id, log_no):
    """Playwright 고도화 버전: 모바일 우선 접근 및 복합 추출 로직"""
    browser = None
    try:
        # 모바일 URL을 기본 타겟으로 설정 (Iframe이 없어 성공률이 훨씬 높음)
        if blog_id and log_no:
            target_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            add_log(f"Playwright 모바일 모드로 시작: {target_url}")
        else:
            target_url = url
            add_log(f"Playwright PC 모드로 시작: {url}")

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                err_msg = str(e)
                add_log(f"브라우저 실행 실패: {err_msg[:100]}...")
                return None

            # 모바일 환경 시뮬레이션
            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1" if blog_id else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 390, 'height': 844} if blog_id else {'width': 1280, 'height': 800},
                locale="ko-KR",
                timezone_id="Asia/Seoul"
            )
            
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            add_log("페이지 접속 중...")
            page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            
            # 페이지 상태 확인
            page_title = page.title()
            add_log(f"페이지 제목 확인: {page_title}")

            if "페이지를 찾을 수 없습니다" in page_title or "삭제된 게시글" in page_title:
                add_log("존재하지 않거나 삭제된 게시글입니다.")
                browser.close()
                return "존재하지 않거나 삭제된 게시글입니다."

            content = ""
            
            # 1. 모바일/직접 추출 시도 (Iframe 없음)
            add_log("본문 영역 탐색 중...")
            try:
                # 다양한 본문 셀렉터 시도 (모바일/PC 공용)
                selectors = [".se-main-container", "#postViewArea", ".post_ct", "#post_1", ".article_body"]
                for selector in selectors:
                    element = page.query_selector(selector)
                    if element:
                        add_log(f"본문 영역 발견 ({selector})")
                        content = element.inner_text()
                        if content.strip(): break
            except Exception as e:
                add_log(f"직접 추출 중 예외: {str(e)}")

            # 2. 실패 시 PC Iframe 버전으로 재시도 (PC URL인 경우만)
            if not content and "m.blog.naver.com" not in target_url:
                add_log("PC Iframe 탐색 시도...")
                try:
                    iframe_element = page.query_selector("iframe#mainFrame")
                    if iframe_element:
                        add_log("mainFrame 발견, 내부 진입...")
                        frame = page.frame(name="mainFrame")
                        if frame:
                            frame.wait_for_selector(".se-main-container, #postViewArea", timeout=10000)
                            content = frame.inner_text(".se-main-container") or frame.inner_text("#postViewArea")
                except Exception as e:
                    add_log(f"Iframe 탐색 실패: {str(e)}")

            # 3. BeautifulSoup 최종 백업 (현재 렌더링된 소스 기반)
            if not content:
                add_log("최종 BeautifulSoup 분석 중...")
                html_source = page.content()
                soup = BeautifulSoup(html_source, 'html.parser')
                div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea') or soup.find('div', class_='post_ct')
                if div:
                    content = div.get_text(separator='\n', strip=True)
                    add_log("BeautifulSoup 추출 성공")
                else:
                    snippet = html_source[:300].replace('\n', ' ')
                    add_log(f"추출 실패. 페이지 스니펫: {snippet}")

            browser.close()
            return content
                
    except Exception as e:
        add_log(f"Playwright 에러 발생: {str(e)}")
        if browser: browser.close()
        return None

def scrape_naver_blog_content(blog_url):
    st.session_state.debug_logs = [] # 로그 초기화
    
    # URL에서 ID와 No 추출
    blog_id, log_no = "", ""
    if 'blog.naver.com' in blog_url:
        mid = re.search(r'blogId=([^&]+)', blog_url)
        mno = re.search(r'logNo=([^&]+)', blog_url)
        if mid and mno:
            blog_id, log_no = mid.group(1), mno.group(1)
        else:
            parts = blog_url.split('/')
            if len(parts) >= 5:
                # blog.naver.com/id/logno 형식 처리
                blog_id, log_no = parts[3], parts[4].split('?')[0]

    # --- Layer 1: Playwright (모바일 우선 접근) ---
    content = scrape_with_playwright(blog_url, blog_id, log_no)
    if content and not content.startswith("Playwright"): return content

    # --- Layer 2: Stealth HTTP Fallback (최후의 수단) ---
    if blog_id and log_no:
        add_log("Stealth HTTP Fallback 시도 중...")
        try:
            with httpx.Client(http2=True, timeout=15.0) as client:
                mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
                res = client.get(mobile_url, headers=get_stealth_headers())
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
                    if div:
                        add_log("HTTP Fallback 성공")
                        return div.get_text(separator='\n', strip=True)
                add_log(f"HTTP Fallback 실패 (상태 코드: {res.status_code})")
        except Exception as e:
            add_log(f"HTTP Fallback 에러: {str(e)}")

    return "모든 시도가 실패했습니다. 아래 [기술 디버그 정보]를 확인하여 에러 원인을 파악해 주세요."

def remove_blank_lines(text: str) -> str:
    if not text: return ""
    for ch in ('\u200B', '\uFEFF'): text = text.replace(ch, '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    cleaned = re.sub(r'(?m)^[\s\u00A0]*\n', '', text)
    return cleaned.strip()

# UI 구성
st.title("📝 네이버 블로그 본문 스크래퍼 v2.1")
st.markdown("---")

blog_url = st.text_input("스크래핑할 네이버 블로그 URL을 입력하세요", placeholder="https://blog.naver.com/...")
scrape_button = st.button("내용 추출하기")

if scrape_button:
    if not blog_url:
        st.warning("URL을 입력해주세요.")
    else:
        with st.spinner("네이버 보안 우회망을 통과 중입니다..."):
            raw_content = scrape_naver_blog_content(blog_url)
            
        if raw_content and not raw_content.startswith("모든 시도가"):
            content = remove_blank_lines(raw_content)
            st.success("데이터 추출 성공!")
            st.text_area("추출 결과", value=content, height=450)
            st.download_button("텍스트 파일 다운로드", data=content, file_name="naver_blog_scraped.txt")
        else:
            st.error(raw_content)
            
        # 디버그 정보 출력
        with st.expander("🛠️ 기술 디버그 정보 (실패 원인 분석)"):
            if st.session_state.debug_logs:
                for log in st.session_state.debug_logs:
                    st.code(log)
            else:
                st.write("로그 정보가 없습니다.")

st.markdown("---")
st.caption("© 2024 Playwright Scraper Engine v2.1 | Streamlit Cloud Optimized")
