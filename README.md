# 🎈 네이버 블로그 스크래핑 및 AI 한줄 코멘트 생성기

모던한 Streamlit 애플리케이션으로, 네이버 블로그 포스트를 스크래핑하고 OpenRouter AI를 이용하여 간결한 한줄 코멘트를 생성합니다.

[![Streamlit에서 열기](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://naver-blog-scraping.streamlit.app/)

## 📋 개요

이 애플리케이션은 다음 기능을 제공하는 미니멀하고 모던한 인터페이스를 제공합니다:
- 네이버 블로그 포스트 가져오기 및 표시
- 모바일 페이지에서 블로그 콘텐츠 스크래핑
- OpenRouter를 이용한 AI 한줄 코멘트 생성
- AI 코멘트와 원문 별도 표시
- 원문 복사 기능 제공

## 🎨 기능

### 1. **네이버 블로그 스크래핑**
- 네이버 모바일 API에서 블로그 포스트 목록 가져오기
- 개별 블로그 포스트에서 전체 콘텐츠 스크래핑
- 다양한 블로그 콘텐츠 형식 처리 (HTML, JSON, iframe)

### 2. **AI 한줄 코멘트 생성**
- OpenRouter AI API를 이용하여 간결한 한줄 코멘트 생성
- 실시간 피드백을 위한 스트리밍 응답 처리
- AI 코멘트 추출 및 별도 표시

### 3. **콘텐츠 표시 및 관리**
- 깨끗한 포맷으로 원문 블로그 콘텐츠 표시
- 불필요한 빈 줄 및 보이지 않는 문자 제거
- 쉽게 읽을 수 있는 텍스트 영역 제공
- 원문 다운로드 기능 제공

### 4. **모던 UI 디자인**
- 미니멀하고 깨끗한 인터페이스에 모던한 스타일링
- 반응형 레이아웃 및 부드러운 전환 효과
- 모든 컴포넌트에 커스텀 CSS 스타일링
- 호버 효과 및 시각적 피드백 제공

## 🚀 사용 방법

### 필수 조건
- Python 3.7+
- Streamlit
- OpenRouter API 키

### 설치
```bash
# 저장소 클론
git clone https://github.com/yourusername/naverblog.git
cd naverblog

# 의존성 설치
pip install -r requirements.txt
```

### 설정
`.streamlit/secrets.toml` 파일에 OpenRouter API 키를 추가합니다:
```toml
api_key = "your_openrouter_api_key"
```

### 애플리케이션 실행
```bash
streamlit run streamlit_app.py
```

## 📝 동작 방식

1. **블로그 목록 가져오기**: 앱이 지정된 네이버 블로그에서 포스트 목록을 가져옵니다
2. **포스트 선택**: 사용자가 드롭다운 목록에서 포스트를 선택합니다
3. **콘텐츠 스크래핑**: 앱이 선택한 블로그 포스트에서 전체 콘텐츠를 스크래핑합니다
4. **코멘트 생성**: OpenRouter AI가 간결한 한줄 코멘트를 생성합니다
5. **결과 표시**: AI 코멘트와 원문이 모두 표시됩니다
6. **콘텐츠 복사**: 사용자가 원문을 다운로드하거나 복사할 수 있습니다

## 🔧 기술적 세부사항

### 주요 함수

- `fetch_post_list()`: 네이버 API에서 블로그 포스트 목록 가져오기
- `scrape_naver_blog()`: 개별 블로그 포스트에서 콘텐츠 스크래핑
- `generate()`: OpenRouter를 이용한 AI 코멘트 생성
- `extract_comment()`: AI 응답에서 코멘트 추출
- `remove_blank_lines()`: 불필요한 빈 줄 제거로 콘텐츠 정리

### 의존성
- `streamlit`: 웹 애플리케이션 프레임워크
- `requests`: HTTP 요청
- `beautifulsoup4`: HTML 파싱
- `openai`: OpenRouter API 클라이언트
- `re`: 텍스트 처리용 정규 표현식

## 📄 라이선스

이 프로젝트는 MIT 라이선스에 따라 라이선스가 부여됩니다 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🤝 기여하기

기여를 환영합니다! 자유롭게 Pull Request를 제출해 주세요.

## 📬 연락처

질문이나 문제가 있는 경우 GitHub에 이슈를 열어 주세요.
