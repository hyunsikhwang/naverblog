import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import base64
import os
import time

# Google GenAI 관련 임포트는 제거되었습니다.

api_key = st.secrets["api_key"]

st.title("🎈 NAVER Blog Scraping")

st.write("네이버 블로그의 본문 내용을 스크래핑합니다.")

def fetch_post_list(category_no=0, item_count=24, page=1, user_id="gomting"):
    """
    네이버 모바일 블로그 API에서 포스트 목록을 가져옵니다.
    """
    url = "https://m.blog.naver.com/api/blogs/ranto28/post-list"
    params = {
        "categoryNo": category_no,
        "itemCount": item_count,
        "page": page,
        "userId": user_id
    }
    headers = {
        "Host": "m.blog.naver.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Referer": "https://m.blog.naver.com/ranto28?categoryNo=0&tab=1",
        "Sec-CH-UA": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Priority": "u=1, i"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"요청 중 오류 발생: {e}")
    except ValueError:
        st.error("응답을 JSON으로 파싱할 수 없습니다.")

    return None

def print_blog_summary(response):
    links = {}
    if not response.get('isSuccess', False):
        return links

    result = response.get('result', {})
    items = result.get('items', [])

    if not items:
        return links

    for item in items:
        blog_id = item.get('domainIdOrBlogId')
        log_no = item.get('logNo')
        title = item.get('titleWithInspectMessage', '<제목 없음>')
        link = f"https://m.blog.naver.com/{blog_id}/{log_no}"
        links[f"{title}"] = f"{link}"
    
    return links

def convert_to_mobile_url(pc_url: str) -> str:
    if "blog.naver.com" not in pc_url:
        raise ValueError("유효한 네이버 블로그 URL이 아닙니다.")
    if "m.blog.naver.com" in pc_url:
        return pc_url
    return pc_url.replace("blog.naver.com", "m.blog.naver.com")

def scrape_naver_blog(pc_url: str) -> str:
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

    content_div = soup.find("div", {"class": "se-main-container"})
    if content_div:
        return content_div.get_text(separator='\n', strip=True)

    raise ValueError("본문 데이터를 찾지 못했습니다. HTML 구조를 재확인해 주세요.")

# OpenRouter 모델을 사용하도록 업데이트된 generate 함수
def generate(api_key, content_html):
    prompt_text = """다음 원문에서 한줄 코멘트를 추출해서 맨 처음으로 보여주고, 나머지 내용들은 내용과 문단에 맞춰서 적절하게 빈줄을 삽입해서 다음과 같은 포맷으로 정리해주세요. 한줄 코멘트와 본문 내용은 원래의 내용에서 절대 변경하지 마세요.
한줄 코멘트: {한줄 코멘트}

본문
{본문}

원문: """ + content_html

    # OpenRouter API 엔드포인트 및 헤더 설정
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.io", # 선택 사항
        "X-Title": "Naver Blog Scraper"         # 선택 사항
    }
    
    # 요청 페이로드
    payload = {
        "model": "nex-agi/deepseek-v3.1-nex-n1:free",
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
        "stream": True
    }

    try:
        # 스트리밍 요청 실행
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    content = decoded_line[6:] # 'data: ' 접두사 제거
                    if content.strip() == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(content)
                        # OpenRouter(OpenAI 호환) 응답 구조에서 텍스트 추출
                        delta = chunk_json['choices'][0].get('delta', {})
                        if 'content' in delta:
                            yield delta['content']
                    except json.JSONDecodeError:
                        continue
            time.sleep(0.01)
    except Exception as e:
        yield f"API 요청 중 오류 발생: {e}"

if __name__ == "__main__":
    response = fetch_post_list()
    if response:
        links = print_blog_summary(response)
        titles = list(links.keys())
        
        if titles:
            url_title = st.selectbox("네이버 블로그 포스트를 선택하세요:", titles)
            st.write(f"선택한 URL: {links[url_title]}")

            try:
                content_html = scrape_naver_blog(links[url_title])
                # OpenRouter 기반 스트리밍 출력
                st.write_stream(generate(api_key, content_html))
            except Exception as e:
                st.error(f"오류 발생: {e}")
        else:
            st.write("표시할 게시글이 없습니다.")
    else:
        st.write("데이터를 가져오지 못했습니다.")