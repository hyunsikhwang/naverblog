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

def generate_naver_cookies():
    """네이버 추적 쿠키 시뮬레이션 (NNB, ASID 등)"""
    nnb = ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))
    asid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
    return [
        {'name': 'NNB', 'value': nnb, 'domain': '.naver.com', 'path': '/'},
        {'name': 'ASID', 'value': asid, 'domain': '.naver.com', 'path': '/'},
    ]

def get_stealth_headers(is_mobile=False):
    """최신 브라우저 지문(Client Hints)이 포함된 헤더 생성"""
    if is_mobile:
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        ch_ua = '"Chromium";v="121", "Not A(Brand";v="99"'
        platform = '"iOS"'
    else:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ch_ua = '"Chromium";v="121", "Google Chrome";v="121", "Not:A-Brand";v="99"'
        platform = '"Windows"'

    referers = [
        "https://search.naver.com/search.naver?query=%EB%84%A4%EC%9D%B4%EB%B2%84+%EB%B8%94%EB%A1%9C%EA%B7%B8",
        "https://section.blog.naver.com/BlogHome.naver",
        "https://m.blog.naver.com/FeedList.naver",
        "https://www.naver.com/"
    ]

    return {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': random.choice(referers),
        'sec-ch-ua': ch_ua,
        'sec-ch-ua-mobile': '?1' if is_mobile else '?0',
        'sec-ch-ua-platform': platform,
        'Upgrade-Insecure-Requests': '1',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1'
    }

def scrape_with_playwright(url, blog_id, log_no):
    """Playwright v2.3.0: Akamai 우회 및 브라우저 지문 고도화"""
    browser = None
    try:
        if blog_id and log_no:
            target_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            add_log(f"Playwright 모바일(Stealth) 시작: {target_url}")
        else:
            target_url = url
            add_log(f"Playwright PC(Stealth) 시작: {url}")

        with sync_playwright() as p:
            try:
                # 브라우저 실행 시 더 많은 인자 추가 (탐지 회피)
                browser = p.chromium.launch(headless=True, args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--no-sandbox'
                ])
            except Exception as e:
                add_log(f"브라우저 실행 실패: {str(e)[:100]}")
                return None

            headers = get_stealth_headers(is_mobile=bool(blog_id))
            context = browser.new_context(
                user_agent=headers['User-Agent'],
                viewport={'width': 390, 'height': 844} if blog_id else {'width': 1280, 'height': 800},
                extra_http_headers={k: v for k, v in headers.items() if k != 'User-Agent'},
                locale="ko-KR",
                timezone_id="Asia/Seoul"
            )
            
            # 쿠키 주입
            context.add_cookies(generate_naver_cookies())
            
            page = context.new_page()
            # 고도화된 스텔스 스크립트 (navigator 지문 수정)
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko']});
            """)
            
            # 내비게이션 전 지터링
            delay = random.uniform(1.0, 2.5)
            add_log(f"접속 전 지연 중... ({delay:.1f}s)")
            time.sleep(delay)

            add_log("페이지 접속 시도...")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            
            page_title = page.title()
            add_log(f"페이지 제목: {page_title}")

            if "Access Denied" in page_title or "Deny" in page_title:
                add_log("Akamai WAF 차단 감지됨 (403 Access Denied)")
                browser.close()
                return None # Fallback 레이어로 전환

            if "페이지를 찾을 수 없습니다" in page_title or "삭제된 게시글" in page_title:
                browser.close()
                return "존재하지 않거나 삭제된 게시글입니다."

            content = ""
            add_log("본문 데이터 추출 시도...")
            
            # 셀렉터 탐색 (우선순위: 모바일 -> 전체 -> Iframe)
            selectors = [".se-main-container", "#postViewArea", ".post_ct", "#post_1", ".article_body"]
            for selector in selectors:
                element = page.query_selector(selector)
                if element:
                    content = element.inner_text()
                    if content.strip(): 
                        add_log(f"성공: {selector}")
                        break

            # PC Iframe 백업 (모바일 모드가 아닐 때만)
            if not content and "m.blog.naver.com" not in target_url:
                iframe = page.frame(name="mainFrame")
                if iframe:
                    add_log("PC Iframe 본문 탐색 중...")
                    content = iframe.inner_text(".se-main-container") or iframe.inner_text("#postViewArea")

            browser.close()
            return content
                
    except Exception as e:
        add_log(f"Playwright 예외: {str(e)}")
        if browser: browser.close()
        return None

def scrape_naver_blog_content(blog_url):
    st.session_state.debug_logs = []
    
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

    # --- Layer 1: Playwright (v2.3.0 Stealth) ---
    content = scrape_with_playwright(blog_url, blog_id, log_no)
    if content and not content.startswith("Playwright"): return content

    # --- Layer 2: Stealth HTTP Fallback (고도화된 헤더) ---
    if blog_id and log_no:
        add_log("Stealth HTTP Fallback(v2.3.0) 가동...")
        try:
            with httpx.Client(http2=True, timeout=15.0) as client:
                mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
                headers = get_stealth_headers(is_mobile=True)
                # HTTP 레이어에도 쿠키 적용
                cookies = {c['name']: c['value'] for c in generate_naver_cookies()}
                res = client.get(mobile_url, headers=headers, cookies=cookies)
                
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
                    if div:
                        add_log("HTTP Fallback 성공!")
                        return div.get_text(separator='\n', strip=True)
                add_log(f"HTTP 가동 실패 (Status: {res.status_code})")
        except Exception as e:
            add_log(f"HTTP Fallback 예외: {str(e)}")

    return "네이버 보안 차단(Akamai WAF)을 통과하지 못했습니다. 잠시 후 다시 시도하거나, 다른 블로그 URL을 입력해 보세요."

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
