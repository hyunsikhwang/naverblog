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
    """Playwright v2.4.0: 유저 플로우 모사 및 장치 정밀 에뮬레이션"""
    browser = None
    try:
        if blog_id and log_no:
            target_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
        else:
            target_url = url

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ])
            except Exception as e:
                add_log(f"브라우저 실행 실패: {str(e)[:100]}")
                return None

            # iPhone 13 기기 정밀 에뮬레이션
            iphone = p.devices['iPhone 13']
            context = browser.new_context(
                **iphone,
                locale="ko-KR",
                timezone_id="Asia/Seoul"
            )
            
            page = context.new_page()
            # --- v2.5.0 고도화된 스텔스 스크립트 (WebGL/Canvas/하드웨어 지문 위장) ---
            page.add_init_script("""
                // webdriver 탐지 방지
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // WebGL 지문 위장 (데이터 센터 GPU 은폐)
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel(R) Iris(TM) Graphics 6100';
                    return getParameter.apply(this, arguments);
                };

                // Canvas 지문 노이즈 추가
                const toDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function() {
                    return toDataURL.apply(this, arguments);
                };

                // 하드웨어 지표 위장
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            """)
            
            # --- 유저 플로우 모사 Step 1: 네이버 메인 접속 ---
            add_log("네이버 메인 접속 시도 (보안 토큰 확보)...")
            try:
                page.goto("https://www.naver.com", wait_until="networkidle", timeout=30000)
                # 실제 유저처럼 메인에서 잠시 체류하며 무작위 스크롤
                stay_time = random.uniform(2.0, 4.0)
                add_log(f"메인 체류 및 패턴 모사 중... ({stay_time:.1f}s)")
                page.mouse.wheel(0, 500)
                time.sleep(stay_time)
            except Exception as e:
                add_log(f"메인 접속 지연/실패(계속 진행): {str(e)[:50]}")

            # --- 유저 플로우 모사 Step 2: 블로그 실접속 ---
            add_log(f"블로그 본문 이동 중 (v2.5.0 Cloud Stealth)")
            page.goto(target_url, wait_until="networkidle", timeout=45000)
            
            page_title = page.title()
            add_log(f"페이지 제목: {page_title}")

            # Akamai 차단 감지 및 상세 안내
            if "Access Denied" in page_title or "Deny" in page_title:
                add_log("네이버 보안 시스템(Akamai)이 클라우드 서버 IP를 차단했습니다.")
                add_log("TIP: Streamlit Cloud의 인프라 IP(AWS/GCP)가 블랙리스트에 올랐을 가능성이 높습니다.")
                browser.close()
                return "NAVER_WAF_BLOCK"

            if "페이지를 찾을 수 없습니다" in page_title or "삭제된 게시글" in page_title:
                browser.close()
                return "존재하지 않거나 삭제된 게시글입니다."

            content = ""
            add_log("데이터 추출 중...")
            
            # 셀렉터 탐색 (현존하는 모든 네이버 블로그 구조 대응)
            selectors = [".se-main-container", "#postViewArea", ".post_ct", "#post_1", ".article_body", ".se_component_wrap"]
            for selector in selectors:
                element = page.query_selector(selector)
                if element:
                    content = element.inner_text()
                    if content.strip(): 
                        add_log(f"추출 성공: {selector}")
                        break

            # BeautifulSoup 최종 백업
            if not content:
                add_log("BeautifulSoup 백업 가동...")
                soup = BeautifulSoup(page.content(), 'html.parser')
                target = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea') or soup.find('div', class_='post_ct')
                if target: content = target.get_text(separator='\n', strip=True)

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

    # --- Layer 1: Playwright (v2.5.0 Cloud Stealth) ---
    content = scrape_with_playwright(blog_url, blog_id, log_no)
    if content == "NAVER_WAF_BLOCK":
        return "네이버 보안 시스템(Akamai)에 의해 Streamlit Cloud의 IP가 차단되었습니다. 로컬 환경에서 실행하거나 프록시 사용이 필요할 수 있습니다."
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
