import streamlit as st
import httpx
from bs4 import BeautifulSoup
import re
import time
import random
import string

# 페이지 설정
st.set_page_config(
    page_title="네이버 블로그 스크래퍼 v1.5.0",
    page_icon="📝",
    layout="wide"
)

# 커스텀 CSS (Premium Design)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #2db400;
        color: white;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #269600;
        border: none;
        color: white;
    }
    .stTextInput>div>div>input {
        border-radius: 10px;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    .css-10trblm {
        color: #2db400;
    }
    div.stTextArea textarea {
        border-radius: 10px;
        background-color: white;
    }
    </style>
    """, unsafe_allow_html=True)

def generate_random_id(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_stealth_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Edge/121.0.0.0'
    ]
    
    ua = random.choice(user_agents)
    is_chrome = 'Chrome' in ua
    
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Referer': 'https://section.blog.naver.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }
    
    if is_chrome:
        headers.update({
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        })
        
    return headers

def scrape_naver_blog_content(blog_url):
    try:
        # URL에서 blogId와 logNo 추출
        blog_id = ""
        log_no = ""
        
        if 'blog.naver.com' in blog_url:
            if 'PostView.naver' in blog_url or 'PostView.nhn' in blog_url:
                blog_id_match = re.search(r'blogId=([^&]+)', blog_url)
                log_no_match = re.search(r'logNo=([^&]+)', blog_url)
                if blog_id_match: blog_id = blog_id_match.group(1)
                if log_no_match: log_no = log_no_match.group(1)
            else:
                parts = blog_url.split('/')
                if len(parts) >= 5:
                    blog_id = parts[3]
                    log_no = parts[4]
        
        if not blog_id or not log_no:
            if 'blog.naver.com' not in blog_url:
                return "유효한 네이버 블로그 URL이 아닙니다."

        # Stealth Session with httpx (Best for bypassing Cloud IP blocks)
        with httpx.Client(http2=True, follow_redirects=True, timeout=15.0) as client:
            headers = get_stealth_headers()
            
            # 더미 쿠키 시뮬레이션 (NNB 등)
            dummy_cookies = {
                'NNB': generate_random_id(13).upper(),
                'ASID': generate_random_id(32),
                'B_W_S': '0'
            }
            
            # --- Layer 1: Mobile Web App (가장 높은 성공률) ---
            mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            
            # 무작위 지터 추가
            time.sleep(random.uniform(0.3, 0.8))
            
            response = client.get(mobile_url, headers=headers, cookies=dummy_cookies)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                content_div = soup.find('div', class_='se-main-container')
                if not content_div:
                    content_div = soup.find('div', id='postViewArea')
                if content_div:
                    return content_div.get_text(separator='\n', strip=True)

            # --- Layer 2: PC Version (Iframe) ---
            # 지터 후 재시도
            time.sleep(random.uniform(0.5, 1.2))
            headers = get_stealth_headers() # 유저 에이전트 교체
            response = client.get(blog_url, headers=headers, cookies=dummy_cookies)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                main_frame = soup.find('iframe', id='mainFrame')
                if main_frame:
                    iframe_url = main_frame['src']
                    if not iframe_url.startswith('http'):
                        base_url = blog_url.split('/')[0] + '//' + blog_url.split('/')[2]
                        iframe_url = base_url + iframe_url
                    
                    iframe_response = client.get(iframe_url, headers=headers, cookies=dummy_cookies)
                    if iframe_response.status_code == 200:
                        iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                        content_div = iframe_soup.find('div', class_='se-main-container')
                        if not content_div:
                            content_div = iframe_soup.find('div', id='postViewArea')
                        if content_div:
                            return content_div.get_text(separator='\n', strip=True)

        # 모든 레이어 실패 시
        status_code = response.status_code if 'response' in locals() else "N/A"
        if status_code == 403:
            return f"403 Forbidden: 클라우드 IP가 차단되었습니다. (Status: {status_code})"
        return f"본문 내용을 찾을 수 없습니다. (응답 코드: {status_code})"

    except Exception as e:
        return f"스크래핑 오류 발생: {str(e)}"

def remove_blank_lines(text: str) -> str:
    if not text: return ""
    for ch in ('\u200B', '\uFEFF'):
        text = text.replace(ch, '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    cleaned = re.sub(r'(?m)^[\s\u00A0]*\n', '', text)
    return cleaned.strip()

# UI 레이아웃
st.title("📝 네이버 블로그 본문 스크래퍼")
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
        with st.spinner('블로그 본문을 분석 중입니다...'):
            raw_content = scrape_naver_blog_content(blog_url)
            
            if raw_content and not raw_content.startswith(("요청 오류", "스크래핑 오류", "본문 내용을 찾을 수", "유효한 네이버")):
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
                st.error(raw_content if raw_content else "알 수 없는 오류가 발생했습니다.")

st.markdown("---")
st.caption("© 2024 Naver Blog Scraper Tools | Streamlit Cloud 최적화 버전")
