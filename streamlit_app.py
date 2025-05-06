import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json


st.title("🎈 NAVER Blog Scraping")

st.write("네이버 블로그의 본문 내용을 스크래핑합니다.")


import requests

def fetch_post_list(category_no=0, item_count=24, page=1, user_id="gomting"):
    """
    네이버 모바일 블로그 API에서 포스트 목록을 가져옵니다.
    
    Args:
        category_no (int): 카테고리 번호 (기본값: 0)
        item_count (int): 한 번에 가져올 아이템 수 (기본값: 24)
        page (int): 페이지 번호 (기본값: 1)
        user_id (str): 사용자 ID (예: "gomting")
    
    Returns:
        dict or None: JSON 파싱 결과, 실패 시 None
    """
    url = "https://m.blog.naver.com/api/blogs/ranto28/post-list"
    params = {
        "categoryNo": category_no,
        "itemCount": item_count,
        "page": page,
        "userId": user_id
    }
    # 주어진 모든 헤더를 그대로 반영
    headers = {
        "Host": "m.blog.naver.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        # "Cookie": (
        #     "NNB=7M2TKPQSXKWGC; stat_yn=1; BMR=s=1678195925790&r=https%3A%2F%2Fm.post.naver.com%2Fviewer%2FpostView.naver%3FmemberNo%3D37966086%26volumeNo%3D35583566"
        #     "&r2=https%3A%2F%2Fwww.naver.com%2Fmy.html; ba.uuid=0; m_loc=11130e4b1b9a413a653df5ca74a909e251462cda8340fec489dba5f19fc140ca;"
        #     'NV_WETR_LOCATION_RGN_M="MDIzNjAyNTY="; tooltipDisplayed=true; NFS=2; BA_DEVICE=61a4ec76-de32-4960-a16d-c11fc9aaef73;'
        #     'NV_WETR_LAST_ACCESS_RGN_M="MDIzNjAyNTY="; nstore_session=pvYgGdc32RjrCi05sB8wWxA1; NID_AUT=bns3r5WpId46252AZmVwF64qnag9m4gF0QT9UQSdLmAAeZop4s0iV31BzJ6lB86D;'
        #     "NID_JKL=h9Qg0W2Qc8jPtOMZvp/zrCMkSOzmP0SYyC/yZ+D3Q74=; ASID=738c015f000001947848ed1000000055; BNB_FINANCE_HOME_TOOLTIP_STOCK=true;"
        #     "BNB_FINANCE_HOME_TOOLTIP_ESTATE=true; _ga=GA1.1.1795909208.1738987026; naverfinancial_CID=b3315d5dea424c45e3b8fb63a8f0f03a; _gcl_au=1.1.742333026.1738987026;"
        #     "_tt_enable_cookie=1; _ttp=zLLgXYt97Q_3LsR_-nOWlsvuJZw.tt.1; _ga_Q7G1QTKPGB=GS1.1.1738987025.1.1.1738987043.0.0.0; NAC=r4UQBkQAcMI9;"
        #     "_ga_K2ECMCJBFQ=GS1.1.1745140624.1.0.1745140629.0.0.0; _ga_SQ24F7Q7YW=GS1.1.1745140624.1.0.1745140629.0.0.0; JSESSIONID=E299B5F7A1237F4BBB6BBA65B118899D.jvm1;"
        #     "SRT30=1746515923; page_uid=jtEI+wqo1fsssS855/wssssssAh-373171; NID_SES=AAABw+OSE8kAfR+cfS6+AGOLvkusjXoMrXSguKUGlZuS4wqvCr71CksIxzQ1Ec6aHeeyi3MwCCnq98jHXuAhug8HYzfsnWljppjjR1wnxfjuqCaigbwJOGTq8/Q05fR89QlGovxXVx1Ye/XUqy5lDtyIdRYsxfIeWBZjzGAc/xllozHTXA7flWSQ10ca0+C3oVEpaFPVWXLvDQlkHjzDGFpJBoJMbxml8/Aqgncw7OjyuJViF51a/D+ih28z6JUJkBARcxarnNURq1v4UD7LWW+jFtIamMIVbiFO3HsU64BvZyp/sNnt/8s017umcADw1fv5g25bWiHGnSrsbZsRdNNeaHUcIymCIbDCnfO+eBmUsR7NlvJKKJFK6a6XsN/5KKkNegQbQoy3GMaY2AIibDCCSquwmBnzSam5jE50p28EGDMoHNWZLxvoeEUQe1/E1fgksQZhNI99FYoa5f+gQjAYCOsB/ZOXo+tFxp1pJYzKv/aDDNBaBg6WSukzdzDxljE2tRZK2BfsWhbUpTbxr+aclIKSNt+M8XFcQvxYF51fvfzg4xlhFdpuZLNp3klyOVnTRTKTuIjzIAw94tZbl+CRzalDDtIBSJZIzWHm6DL/4EOe; nstore_pagesession=jtE/3sqrZpJVcwsMDZd-358989; SRT5=1746519782; BUC=E_CivUq4tO2ACvTvfwivm5O-ay0RIneThGnZi6r8Uwo="
        # ),
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
        print(f"요청 중 오류 발생: {e}")
    except ValueError:
        print("응답을 JSON으로 파싱할 수 없습니다.")

    return None

def print_blog_summary(response):
    links = {}
    """
    네이버 블로그 JSON 응답에서 주요 항목만 간결하게 출력합니다.
    """
    # 요청 성공 여부 확인
    if not response.get('isSuccess', False):
        print("요청에 실패했습니다.")
        return

    result = response.get('result', {})
    items = result.get('items', [])

    if not items:
        print("표시할 게시글이 없습니다.")
        return

    for item in items:
        blog_id = item.get('domainIdOrBlogId')
        log_no = item.get('logNo')
        title = item.get('titleWithInspectMessage', '<제목 없음>')
        comments = item.get('commentCnt', 0)
        sympathies = item.get('sympathyCnt', 0)
        # 본문은 첫 문장만 추출해 간략하게 보여줍니다.
        brief = item.get('briefContents', '').split('。')[0]
        link = f"https://m.blog.naver.com/{blog_id}/{log_no}"

        # links.append(f"{link}")
        links[f"{title}"] = f"{link}"
        # print(f"제목       : {title}")
        # print(f"링크       : {link}")
        # print(f"댓글/공감  : {comments}개  /  {sympathies}개")
        # print(f"요약       : {brief}…")
        # print("-" * 60)
    
    return links

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

    response = fetch_post_list()
    if response:
        links = print_blog_summary(response)
        titles = list(links.keys())
    else:
        st.write("데이터를 가져오지 못했습니다.")

    url = st.selectbox("네이버 블로그 포스트를 선택하세요:", titles)
    st.write(f"선택한 URL: {links[url]}")

    try:
        content_html = scrape_naver_blog(url)
        st.subheader("=== 본문 HTML ===")
        st.markdown(content_html)
    except Exception as e:
        st.write(f"오류 발생: {e}")
