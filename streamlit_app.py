import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import re


st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)



def scrape_naver_blog_content(blog_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(blog_url, headers=headers)
        response.raise_for_status()  # 응답 상태 코드가 200 OK가 아니면 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')

        # 네이버 블로그의 본문 내용은 다양한 태그와 클래스에 담길 수 있습니다.
        # 아래는 몇 가지 흔한 경우를 가정한 선택자이며, 실제 블로그 구조에 따라 수정해야 할 수 있습니다.

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

        # 2. iframe 없이 직접 본문 (과거 방식 또는 특정 설정)
        else:
            content_div = soup.find('div', class_='se-main-container') # 스마트 에디터
            if not content_div:
                content_div = soup.find('div', id='postViewArea') # 구버전 에디터
            if content_div:
                return content_div.get_text(separator='\n', strip=True)

        return "본문 내용을 찾을 수 없습니다."

    except requests.exceptions.RequestException as e:
        print(f"요청 오류: {e}")
        return None
    except Exception as e:
        print(f"스크래핑 오류: {e}")
        return None

def remove_blank_lines(text: str) -> str:
    # 1) Zero‑width space, BOM 같은 보이지 않는 문자 제거
    for ch in ('\u200B', '\uFEFF'):
        text = text.replace(ch, '')

    # 2) 줄 구분을 모두 '\n' 으로 통일
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 3) 완전히 공백만 있는 줄(탭, 스페이스, NBSP 등 포함) 제거
    #    (?m) 멀티라인 모드, ^…$ 에 \s 를 써서 유니코드 공백 전부 매칭
    cleaned = re.sub(r'(?m)^[\s\u00A0]*\n', '', text)

    # 4) 앞뒤에 남은 빈 줄/공백 잘라내기
    return cleaned.strip()


if __name__ == "__main__":
    blog_url_to_scrape = "https://m.blog.naver.com/hkn238/223839853717" # 여기에 스크래핑하려는 네이버 블로그 URL을 넣어주세요.
    content_1 = scrape_naver_blog_content(blog_url_to_scrape)
    content = remove_blank_lines(content_1)

    if content:
        st.write("스크래핑된 본문 내용:\n")
        st.write(content)
    else:
        st.write("본문 스크래핑에 실패했습니다.")