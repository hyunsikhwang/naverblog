import streamlit as st
import httpx
from bs4 import BeautifulSoup
import re
import time

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

GAS_URL = "https://script.google.com/macros/s/AKfycbx0PDDwIUOPlRenwl0fUKEUvkaxIi0fS91H7bTfZ9Vx_e30Sk30_EnT6yGPMHJSf-zUWg/exec"

def fetch_via_gas(target_url):
    try:
        params = {"url": target_url}
        res = httpx.get(GAS_URL, params=params, timeout=20.0)
        if res.status_code == 200:
            return res.text
    except Exception:
        return None
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

    # --- GAS 우회 요청 전용 ---
    if blog_id and log_no:
        add_log("GAS 우회 요청 가동...")
        try:
            mobile_url = (
                "https://m.blog.naver.com/PostView.naver"
                f"?blogId={blog_id}"
                f"&logNo={log_no}"
                "&redirect=Dlog"
                "&widgetTypeCall=true"
                "&noTrackingCode=true"
                "&directAccess=false"
            )
            html = fetch_via_gas(mobile_url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                div = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
                if div: return div.get_text(separator='\n', strip=True)
        except Exception: pass

    return "네이버 보안 시스템을 통과할 수 없습니다. 프록시 사용을 권장합니다."

def remove_blank_lines(text: str) -> str:
    if not text: return ""
    for ch in ('\u200B', '\uFEFF'): text = text.replace(ch, '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    cleaned = re.sub(r'(?m)^[\s\u00A0]*\n', '', text)
    return cleaned.strip()

# UI 구성
st.title("📝 네이버 블로그 본문 스크래퍼 v2.6")
st.markdown("---")

blog_url = st.text_input("스크래핑할 네이버 블로그 URL을 입력하세요", placeholder="https://blog.naver.com/...")
scrape_button = st.button("내용 추출하기")

if scrape_button:
    if not blog_url:
        st.warning("URL을 입력해주세요.")
    else:
        with st.spinner("네이버 보안 우회망을 통과 중입니다..."):
            raw_content = scrape_naver_blog_content(blog_url)
            
        if raw_content and not raw_content.startswith("네이버 보안 시스템"):
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
st.caption("© 2024 HTTP Scraper Engine v2.6 | Streamlit Cloud Optimized")
