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

def scrape_with_playwright(url):
    """Playwright 고도화 버전: Stealth 설정 및 복합 추출 로직"""
    try:
        add_log(f"Playwright 시작: {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # 수동 Stealth 설정 적용
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                locale="ko-KR",
                timezone_id="Asia/Seoul"
            )
            
            page = context.new_page()
            # 헤드리스 탐지 회피를 위한 추가 스크립트
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            add_log("페이지 접속 중...")
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # 1. Iframe(mainFrame) 탐색
            add_log("mainFrame 탐색 중...")
            content = ""
            try:
                iframe_element = page.wait_for_selector("iframe#mainFrame", timeout=10000)
                if iframe_element:
                    add_log("mainFrame 발견, 내부 진입 시도...")
                    frame = page.frame(name="mainFrame")
                    if frame:
                        # 본문 셀렉터 대기
                        try:
                            frame.wait_for_selector(".se-main-container, #postViewArea", timeout=10000)
                            add_log("본문 영역(Iframe) 발견")
                            content = frame.inner_text(".se-main-container") or frame.inner_text("#postViewArea")
                        except Exception as e:
                            add_log(f"Iframe 내부 선택자 탐색 실패: {str(e)}")
                            # Iframe 소스 직접 분석 시도
                            frame_content = frame.content()
                            soup = BeautifulSoup(frame_content, 'html.parser')
                            div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
                            if div:
                                add_log("BeautifulSoup으로 Iframe 본문 추출 성공")
                                content = div.get_text(separator='\n', strip=True)
            except Exception as e:
                add_log(f"Iframe 탐색 중 예외 발생: {str(e)}")
            
            # 2. Iframe 실패 시 전체 페이지에서 직접 탐색 (Mobile 등)
            if not content:
                add_log("페이지 직접 추출 시도...")
                try:
                    page.wait_for_selector(".se-main-container, #postViewArea", timeout=5000)
                    content = page.inner_text(".se-main-container") or page.inner_text("#postViewArea")
                except:
                    add_log("BeautifulSoup으로 전체 페이지 분석 중...")
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
                    if div: 
                        add_log("BeautifulSoup으로 본문 추출 성공")
                        content = div.get_text(separator='\n', strip=True)

            browser.close()
            if content:
                add_log("스크래핑 최종 성공")
                return content
            else:
                add_log("모든 추출 로직 실패")
                return None
                
    except Exception as e:
        add_log(f"Playwright 에러 발생: {str(e)}")
        if 'browser' in locals(): browser.close()
        return None

def scrape_naver_blog_content(blog_url):
    st.session_state.debug_logs = [] # 로그 초기화
    
    blog_id, log_no = "", ""
    # URL에서 ID와 No 추출 (Backup용)
    mid = re.search(r'blogId=([^&]+)', blog_url)
    mno = re.search(r'logNo=([^&]+)', blog_url)
    if mid and mno:
        blog_id, log_no = mid.group(1), mno.group(1)
    
    # --- Layer 1: Playwright (최고의 성공률) ---
    content = scrape_with_playwright(blog_url)
    if content: return content

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
