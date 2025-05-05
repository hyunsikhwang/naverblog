import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import re


st.title("🎈 NAVER Blog Scraping")

st.write("네이버 블로그의 본문 내용을 스크래핑합니다.")



import requests
from bs4 import BeautifulSoup
import re
import json

def convert_to_mobile_url(pc_url: str) -> str:
    """
    PC 버전 네이버 블로그 URL을 모바일 버전 URL로 변환합니다.
    예: https://blog.naver.com/아이디/포스트번호 -> https://m.blog.naver.com/아이디/포스트번호
    """
    if "blog.naver.com" not in pc_url:
        raise ValueError("유효한 네이버 블로그 URL이 아닙니다.")
    # URL이 이미 모바일 버전이면 그대로 반환
    if "m.blog.naver.com" in pc_url:
        return pc_url

    # 간단하게 'blog.naver.com'을 'm.blog.naver.com'으로 대체합니다.
    mobile_url = pc_url.replace("blog.naver.com", "m.blog.naver.com")
    return mobile_url

def scrape_naver_blog(pc_url: str) -> str:
    """
    네이버 블로그 PC 버전 URL을 받아, 모바일 페이지에서 본문 HTML을 추출합니다.
    """
    mobile_url = convert_to_mobile_url(pc_url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/98.0.4758.102 Safari/537.36"
        )
    }
    response = requests.get(mobile_url, headers=headers)
    if not response.ok:
        raise ConnectionError(f"모바일 페이지 요청 실패: {response.status_code}")

    html_text = response.text
    soup = BeautifulSoup(html_text, "html.parser")

    # 예제 1: 일반적인 본문 컨테이너 div를 활용하는 경우
    content_div = soup.find("div", {"class": "se-main-container"})
    if content_div:
        # return str(content_div)
        return content_div.get_text(separator='\n', strip=True)

    # 예제 2: JSON 데이터가 포함된 <script> 태그에서 본문 추출 (예상 변수명이 __APOLLO_STATE__ 등)
    # 아래 정규식은 예시이며, 실제 변수명과 구조는 HTML 소스 확인 후 수정 필요합니다.
    pattern = re.compile(r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});', re.DOTALL)
    match = pattern.search(html_text)
    if match:
        json_str = match.group(1).strip()
        try:
            data = json.loads(json_str)
            # 데이터 구조에 따라 수정 필요: 예시로 postContent 혹은 content를 찾음
            if "post" in data and "content" in data["post"]:
                return data["post"]["content"]
        except json.JSONDecodeError:
            pass  # JSON 파싱 실패 시 아래 방법 사용

    # 예제 3: iframe 구조인 경우, iframe의 src를 추출하여 추가 요청
    iframe = soup.find("iframe")
    if iframe and iframe.has_attr("src"):
        iframe_src = iframe["src"]
        iframe_response = requests.get(iframe_src, headers=headers)
        if iframe_response.ok:
            iframe_soup = BeautifulSoup(iframe_response.text, "html.parser")
            # iframe 내에 본문이 있는지 확인 (예: div id="postViewArea")
            iframe_content = iframe_soup.find("div", {"id": "postViewArea"})
            if iframe_content:
                return str(iframe_content)

    raise ValueError("본문 데이터를 찾지 못했습니다. HTML 구조를 재확인해 주세요.")

if __name__ == "__main__":
    url = st.text_input("네이버 블로그 URL을 입력하세요:", "https://blog.naver.com/ranto28/223839799372")

    try:
        content_html = scrape_naver_blog(url)
        st.write("=== 본문 HTML ===")
        st.write(content_html)
    except Exception as e:
        st.write(f"오류 발생: {e}")
