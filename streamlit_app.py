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
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"

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
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that extracts a one-line comment and summarizes the blog post. "
                        "You must respond ONLY with a JSON object containing the following keys:\n"
                        "{\n"
                        "  \"one_line_comment\": \"Extract the exact existing one-line comment (or summary/opinion phrase) usually found at the end of the text. Do not modify the text. Clean any leading/trailing asterisks. If not found, set this to null.\",\n"
                        "  \"summary\": \"Summarize the rest of the text excluding the one-line comment. Identify 3 to 6 major keywords in the summary and wrap them in **double asterisks** to emphasize them. Example: '**keyword**'.\"\n"
                        "}"
                    )
                },
                {
                    "role": "user",
                    "content": f"다음 본문에서 한줄 코멘트 추출 및 요약을 수행하여 JSON 객체로 반환해주세요:\n\n{snippet}"
                }
            ],
            "temperature": 0.0,
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
            try:
                result_json = json.loads(text)
                return result_json
            except json.JSONDecodeError:
                add_log("JSON 파싱 실패. 원본 텍스트: " + text)
                return {"one_line_comment": None, "summary": text}
        add_log(f"OpenRouter 응답 코드: {res.status_code}")
    except Exception as e:
        add_log(f"OpenRouter 호출 에러: {str(e)}")
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
    full_url = f"{api_url}?{httpx.QueryParams(params)}"

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
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        background-color: #f8fafc;
    }
    /* Streamlit 기본 헤더 숨김 및 여백 제거 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    [data-testid="stAppViewBlockContainer"], .block-container {
        max-width: 1200px !important;
        padding-top: 0px !important;
        padding-bottom: 2rem !important;
    }
    .main-title-container {
        text-align: center;
        margin-top: -1.5rem !important;
        margin-bottom: 0.5rem !important;
        padding: 0px 0 0.5rem 0 !important;
    }
    .gradient-title {
        background: linear-gradient(135deg, #03c75a 0%, #10b981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.4rem;
        letter-spacing: -1px;
        margin: 0;
    }
    .subtitle {
        color: #64748b;
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    
    /* Streamlit 내장 border 컨테이너 스타일 오버라이딩 */
    div[data-testid="stVerticalBlockBorderedTest"] {
        background: white !important;
        padding: 24px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04) !important;
        border: 1px solid #f1f5f9 !important;
        margin-bottom: 24px !important;
    }
    
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #03c75a 0%, #10b981 100%);
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.05rem;
        box-shadow: 0 4px 12px rgba(3, 199, 90, 0.15);
        transition: all 0.2s ease-in-out;
        width: 100%;
        height: 48px;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(3, 199, 90, 0.25);
        background: linear-gradient(135deg, #02b350 0%, #059669 100%);
        color: white !important;
    }
    div.stButton > button:active {
        transform: translateY(1px);
    }
    .comment-box {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        border-left: 5px solid #03c75a;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(3, 199, 90, 0.02);
    }
    .summary-box {
        background: white;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.01);
        margin-bottom: 20px;
    }
    .keyword-badge {
        background-color: #e0f2fe;
        color: #0369a1;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 8px;
        border: 1px solid #bae6fd;
        margin: 0 2px 4px 2px;
        display: inline-block;
        font-size: 0.9em;
    }
    
    /* 모바일 반응형 대응 (화면 너비 768px 이하) */
    @media (max-width: 768px) {
        [data-testid="stAppViewBlockContainer"] {
            padding: 8px !important;
            padding-top: 0px !important;
        }
        .gradient-title {
            font-size: 1.8rem !important;
        }
        div[data-testid="stVerticalBlockBorderedTest"] {
            padding: 16px !important;
            margin-bottom: 16px !important;
            border-radius: 12px !important;
        }
        .comment-box {
            padding: 14px !important;
            border-radius: 10px !important;
        }
        .summary-box {
            padding: 14px !important;
            border-radius: 10px !important;
        }
        .card-title {
            font-size: 1rem !important;
            margin-bottom: 12px !important;
        }
        div.stButton > button {
            height: 44px !important;
            font-size: 0.95rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# 헤더
st.markdown("""
    <div class="main-title-container">
        <h1 class="gradient-title">📝 네이버 블로그 스크래퍼 v3.0</h1>
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    with st.container(border=True):
        st.markdown('<div class="card-title">🔗 블로그 연동 설정</div>', unsafe_allow_html=True)
        
        default_blog_id = "ranto28"
        blog_id_input = st.text_input("블로그 ID 입력", value=default_blog_id, help="포스트 목록을 불러올 네이버 블로그 ID를 입력하세요.")
        
        with st.spinner("최근 포스트 목록 갱신 중..."):
            post_list = fetch_blog_posts(blog_id_input)
        
        if post_list:
            options = [(p["title"], p["link"]) for p in post_list]
            url_map = {title: link for title, link in options}
            st.session_state["post_url_map"] = url_map

            def _apply_selected_post():
                title = st.session_state.get("post_select")
                if title:
                    st.session_state["blog_url_input"] = st.session_state["post_url_map"].get(title, "")

            st.selectbox(
                "최근 작성 포스트 선택",
                options=[o[0] for o in options],
                index=0,
                key="post_select",
                on_change=_apply_selected_post
            )
            selected_url = url_map.get(options[0][0]) if options else None
        else:
            selected_url = None
            st.info("포스트 목록을 가져오지 못했습니다. 아래에 URL을 직접 입력해 주세요.")
            
        if "blog_url_input" not in st.session_state and selected_url:
            st.session_state["blog_url_input"] = selected_url
            
    with st.container(border=True):
        st.markdown('<div class="card-title">📝 분석 실행</div>', unsafe_allow_html=True)
        
        blog_url = st.text_input(
            "대상 포스트 URL 주소",
            placeholder="https://blog.naver.com/...",
            key="blog_url_input"
        )
        scrape_button = st.button("실시간 스크래핑 및 요약")

with col2:
    with st.container(border=True):
        st.markdown('<div class="card-title">📊 AI 요약 분석 리포트</div>', unsafe_allow_html=True)
        
        if scrape_button:
            if not blog_url:
                st.warning("URL 주소를 입력해주세요.")
            else:
                with st.spinner("네이버 보안 우회망 접속 및 본문 추출 중..."):
                    raw_content = scrape_naver_blog_content(blog_url)
                    
                if raw_content and not raw_content.startswith("네이버 보안 시스템"):
                    content = remove_blank_lines(raw_content)
                    
                    with st.spinner("DeepSeek AI가 본문을 분석하고 요약하는 중..."):
                        analysis_result = extract_one_line_comment_via_openrouter(content)
                    
                    if analysis_result:
                        one_line = analysis_result.get("one_line_comment")
                        summary = analysis_result.get("summary")
                        
                        if one_line:
                            clean_one_line = one_line.strip("* ")
                            st.markdown(
                                f"""
                                <div class="comment-box">
                                    <span style="color: #03c75a; font-weight: bold; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">💡 한줄 코멘트</span>
                                    <p style="margin: 0; font-size: 1.1rem; font-weight: bold; color: #0f172a; line-height: 1.5;">{clean_one_line}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            st.info("한줄 코멘트를 본문에서 찾지 못했습니다.")
                        
                        if summary:
                            annotated_summary = re.sub(
                                r'\*\*(.*?)\*\*', 
                                r'<span class="keyword-badge">\1</span>', 
                                summary
                            )
                            st.markdown(
                                f"""
                                <div class="summary-box">
                                    <span style="color: #475569; font-weight: bold; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 12px;">📋 본문 요약</span>
                                    <p style="line-height: 1.7; color: #334155; font-size: 1rem; margin: 0;">{annotated_summary}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        st.success("요약 분석 완료!")
                        
                        # 스크래핑 결과 전문 (Collapsed)
                        st.markdown("---")
                        with st.expander("📝 스크래핑된 원문 텍스트 보기", expanded=False):
                            st.text_area("추출 결과", value=content, height=350, label_visibility="collapsed")
                            st.download_button("텍스트 파일 다운로드", data=content, file_name="naver_blog_scraped.txt")
                            
                    else:
                        st.error("AI 요약 요청 중 오류가 발생했습니다.")
                else:
                    st.error(raw_content)
                    
                # 디버그 로그
                if st.session_state.debug_logs:
                    with st.expander("🛠️ 시스템 상세 디버그 정보", expanded=False):
                        for log in st.session_state.debug_logs:
                            st.code(log)
        else:
            st.info("좌측 입력창에서 블로그 URL을 입력 또는 선택한 뒤 [실시간 스크래핑 및 요약] 버튼을 클릭해 주세요.")

st.markdown("""
    <div style="text-align: center; margin-top: 3rem; color: #94a3b8; font-size: 0.85rem; padding-bottom: 2rem;">
        © 2026 Naver Blog Scraper Engine v3.0 | Streamlit Cloud Optimized
    </div>
    """, unsafe_allow_html=True)
