import streamlit as st
import httpx
from bs4 import BeautifulSoup
import re
import time
import json

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
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "arcee-ai/trinity-large-preview:free"

def fetch_via_gas(target_url):
    try:
        params = {"url": target_url}
        res = httpx.get(GAS_URL, params=params, timeout=20.0)
        if res.status_code == 200:
            return res.text
        add_log(f"GAS 응답 코드: {res.status_code}")
    except Exception:
        return None
    return None

def extract_one_line_comment_via_openrouter(content):
    try:
        api_key = st.secrets.get("api_key")
        if not api_key:
            add_log("OpenRouter API 키가 설정되지 않았습니다.")
            return None
        snippet = content
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract an existing one-line comment from Korean text. "
                        "Return the exact line as-is without rewriting. "
                        "If not found, return exactly: NOT_FOUND"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "다음 본문에서 '한줄 코멘트/한줄평/한줄요약' 등 한줄 코멘트에 해당하는 "
                        "내용을 그대로 추출해줘. 변형 금지. 없으면 NOT_FOUND만 출력.\n\n"
                        f"{snippet}"
                    )
                }
            ],
            "temperature": 0.0,
            "max_tokens": 80
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://streamlit.app/",
            "X-Title": "Naver Blog Scraper"
        }
        res = httpx.post(OPENROUTER_URL, json=payload, headers=headers, timeout=40.0)
        if res.status_code == 200:
            data = res.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text == "NOT_FOUND":
                return None
            return text
        add_log(f"OpenRouter 응답 코드: {res.status_code}")
    except Exception:
        return None
    return None

def fetch_direct(target_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = httpx.get(target_url, headers=headers, timeout=15.0, follow_redirects=True)
        if res.status_code == 200:
            return res.text
        add_log(f"직접 요청 응답 코드: {res.status_code}")
    except Exception:
        return None
    return None

@st.cache_data(ttl=300)
def fetch_blog_posts(blog_id, category_no=0, item_count=24, page=1):
    posts = []
    api_url = f"https://m.blog.naver.com/api/blogs/{blog_id}/post-list"
    params = {
        "categoryNo": category_no,
        "itemCount": item_count,
        "page": page,
        "userId": blog_id
    }
    full_url = str(httpx.URL(api_url).copy_add_params(params))

    data = None
    try:
        raw = fetch_via_gas(full_url)
        if raw:
            data = json.loads(raw)
    except Exception:
        data = None

    if data is None:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
            "Referer": f"https://m.blog.naver.com/{blog_id}?categoryNo=0&tab=1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
        try:
            res = httpx.get(api_url, params=params, headers=headers, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
            else:
                add_log(f"포스트 목록 응답 코드: {res.status_code}")
        except Exception:
            data = None

    if data and data.get("isSuccess"):
        items = data.get("result", {}).get("items", [])
        for item in items:
            bid = item.get("domainIdOrBlogId") or blog_id
            log_no = item.get("logNo")
            title = item.get("titleWithInspectMessage", "").strip()
            if log_no and title:
                link = f"https://blog.naver.com/{bid}/{log_no}"
                posts.append({"title": title, "link": link})

    return posts

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

    # --- 1차: 직접 요청 (IP 미차단 환경) ---
    if blog_id and log_no:
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
            add_log("직접 요청 가동...")
            html = fetch_direct(mobile_url)
            if not html:
                add_log("직접 요청 실패, GAS 우회 시도...")
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

default_blog_id = "ranto28"
blog_id_input = st.text_input("블로그 ID", value=default_blog_id, help="예: ranto28")

with st.spinner("블로그 포스트 목록을 불러오는 중..."):
    post_list = fetch_blog_posts(blog_id_input)

if post_list:
    options = [(p["title"], p["link"]) for p in post_list]
    selected_title = st.selectbox(
        "최근 포스트에서 선택",
        options=[o[0] for o in options],
        index=0
    )
    selected_url = dict(options).get(selected_title)
else:
    selected_url = None
    st.info("포스트 목록을 불러오지 못했습니다. URL을 직접 입력해 주세요.")

blog_url = st.text_input(
    "스크래핑할 네이버 블로그 URL을 입력하세요",
    placeholder="https://blog.naver.com/...",
    key="blog_url_input"
)
if selected_url and st.session_state.get("blog_url_input") != selected_url:
    st.session_state["blog_url_input"] = selected_url
scrape_button = st.button("내용 추출하기")

if scrape_button:
    if not blog_url:
        st.warning("URL을 입력해주세요.")
    else:
        with st.spinner("네이버 보안 우회망을 통과 중입니다..."):
            raw_content = scrape_naver_blog_content(blog_url)
            
        if raw_content and not raw_content.startswith("네이버 보안 시스템"):
            content = remove_blank_lines(raw_content)
            with st.spinner("한줄 코멘트 추출 중..."):
                one_line = extract_one_line_comment_via_openrouter(content)
            if one_line:
                st.markdown(f"**{one_line}**")
            else:
                st.info("한줄 코멘트를 본문에서 찾지 못했습니다.")
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
