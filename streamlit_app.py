import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time

# 페이지 설정
st.set_page_config(
    page_title="네이버 블로그 스크래퍼",
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

def scrape_naver_blog_content(blog_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # URL 형식 체크 (blog.naver.com 포함 여부)
        if 'blog.naver.com' not in blog_url:
            return "유효한 네이버 블로그 URL이 아닙니다."

        response = requests.get(blog_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. iframe 내부의 본문 (최근 방식)
        main_frame = soup.find('iframe', id='mainFrame')
        if main_frame:
            iframe_url = main_frame['src']
            if not iframe_url.startswith('http'):
                base_url = blog_url.split('/')[0] + '//' + blog_url.split('/')[2]
                iframe_url = base_url + iframe_url
            
            iframe_response = requests.get(iframe_url, headers=headers)
            iframe_response.raise_for_status()
            iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
            
            content_div = iframe_soup.find('div', class_='se-main-container') # 스마트 에디터
            if not content_div:
                content_div = iframe_soup.find('div', id='postViewArea') # 구버전 에디터
            
            if content_div:
                return content_div.get_text(separator='\n', strip=True)

        # 2. iframe 없이 직접 본문
        else:
            content_div = soup.find('div', class_='se-main-container')
            if not content_div:
                content_div = soup.find('div', id='postViewArea')
            
            if content_div:
                return content_div.get_text(separator='\n', strip=True)

        return "본문 내용을 찾을 수 없습니다."

    except requests.exceptions.RequestException as e:
        return f"요청 오류: {e}"
    except Exception as e:
        return f"스크래핑 오류: {e}"

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
