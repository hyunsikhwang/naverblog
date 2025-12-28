import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time

# ✅ 중요: google.genai 관련 임포트를 제거했습니다.
api_key = st.secrets["api_key"]

st.title("🎈 NAVER Blog Scraping (DeepSeek v3.1)")

st.write("네이버 블로그의 본문 내용을 스크래핑하여 OpenRouter 모델로 정리합니다.")

# ... (fetch_post_list, print_blog_summary, scrape_naver_blog 함수는 기존과 동일) ...

def generate(api_key, content_html):
    prompt_text = f"""다음 원문에서 한줄 코멘트를 추출해서 맨 처음으로 보여주고, 나머지 내용들은 내용과 문단에 맞춰서 적절하게 빈줄을 삽입해서 다음과 같은 포맷으로 정리해주세요. 한줄 코멘트와 본문 내용은 원래의 내용에서 절대 변경하지 마세요.
한줄 코멘트: {{한줄 코멘트}}

본문
{{본문}}

원문: {content_html}"""

    # ✅ OpenRouter API 엔드포인트 사용
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "nex-agi/deepseek-v3.1-nex-n1:free",
        "messages": [{"role": "user", "content": prompt_text}],
        "stream": True
    }

    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    content = decoded_line[6:]
                    if content.strip() == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(content)
                        delta = chunk_json['choices'][0].get('delta', {})
                        if 'content' in delta:
                            yield delta['content']
                    except json.JSONDecodeError:
                        continue
            time.sleep(0.01)
    except Exception as e:
        yield f"API 요청 중 오류 발생: {e}. API 키가 OpenRouter용인지 확인해 주세요."

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