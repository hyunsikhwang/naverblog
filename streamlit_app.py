import streamlit as st
import httpx
from bs4 import BeautifulSoup
import re
import time
import random
import string
import xml.etree.ElementTree as ET

# 페이지 설정
st.set_page_config(
    page_title="네이버 블로그 스크래퍼 v1.6.0",
    page_icon="📝",
    layout="wide"
)

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
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

def generate_random_id(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_stealth_headers(mode='modern'):
    if mode == 'simple':
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/121.0.0.0'
    ]
    ua = random.choice(user_agents)
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://section.blog.naver.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Upgrade-Insecure-Requests': '1'
    }
    if 'Chrome' in ua:
        headers.update({
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        })
    return headers

def scrape_rss_content(blog_id, log_no, client):
    """RSS 피드를 통한 본문 추출 (보안 검문이 가장 낮음)"""
    try:
        rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
        response = client.get(rss_url, headers=get_stealth_headers('simple'), timeout=10.0)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall('.//item'):
                link = item.find('link').text
                if log_no in link:
                    description = item.find('description').text
                    if description:
                        # RSS는 HTML 태그가 포함될 수 있으므로 정리
                        soup = BeautifulSoup(description, 'html.parser')
                        return soup.get_text(separator='\n', strip=True)
    except Exception:
        pass
    return None

def scrape_naver_blog_content(blog_url):
    try:
        blog_id, log_no = "", ""
        if 'blog.naver.com' in blog_url:
            if 'PostView' in blog_url:
                mid = re.search(r'blogId=([^&]+)', blog_url)
                mno = re.search(r'logNo=([^&]+)', blog_url)
                if mid: blog_id = mid.group(1)
                if mno: log_no = mno.group(1)
            else:
                parts = blog_url.split('/')
                if len(parts) >= 5:
                    blog_id, log_no = parts[3], parts[4].split('?')[0] # 쿼리 스트링 제거
        
        if not blog_id or not log_no:
            return "유효한 네이버 블로그 URL 형식이 아닙니다."

        with httpx.Client(http2=True, follow_redirects=True, timeout=15.0) as client:
            # --- Layer 0: RSS (최신 글인 경우 가장 확실한 우회책) ---
            content = scrape_rss_content(blog_id, log_no, client)
            if content: return content

            # --- Layer 1: Mobile Web App ---
            time.sleep(random.uniform(0.5, 1.0))
            mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            response = client.get(mobile_url, headers=get_stealth_headers(), cookies={'NNB': generate_random_id(13).upper()})
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                content_div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
                if content_div: return content_div.get_text(separator='\n', strip=True)

            # --- Layer 2: PC Iframe ---
            if 'response' in locals() and response.status_code == 403:
                # 403 발생 시 헤더를 아주 단순하게 바꿔서 한번 더 시도 (PC)
                time.sleep(random.uniform(1.0, 2.0))
                response = client.get(blog_url, headers=get_stealth_headers('simple'))
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    iframe = soup.find('iframe', id='mainFrame')
                    if iframe:
                        iframe_url = iframe['src']
                        if not iframe_url.startswith('http'):
                            iframe_url = f"https://blog.naver.com{iframe_url}"
                        res_iframe = client.get(iframe_url, headers=get_stealth_headers('simple'))
                        if res_iframe.status_code == 200:
                            isoup = BeautifulSoup(res_iframe.text, 'html.parser')
                            content_div = isoup.find('div', class_='se-main-container') or isoup.find('div', id='postViewArea')
                            if content_div: return content_div.get_text(separator='\n', strip=True)

        status = response.status_code if 'response' in locals() else "Unknown"
        if status == 403:
            return f"403 Forbidden: 클라우드 IP 차단됨. (상태 코드: {status})\n\n팁: 이 글이 최신 글이 아니면 RSS로 추출이 불가능할 수 있습니다. 로컬 환경에서 실행하는 것을 권장합니다."
        return f"본문을 찾을 수 없습니다. (상태 코드: {status})"

    except Exception as e:
        return f"스크래핑 중 오류 발생: {str(e)}"

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
