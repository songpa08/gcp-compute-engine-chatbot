# Google Gemini 웹 챗봇 (로컬 & GCP Compute Engine)

Google Gemini 공식 웹 UI(`https://gemini.google.com/app?hl=ko`) 디자인을 기반으로 제작된 모던 웹 챗봇 애플리케이션입니다.

## ✨ 주요 기능
- **차세대 AI 모델 탑재**:
  - **Gemini 3.8 Flash** (`gemini-3.8-flash`) - 기본값
  - **Gemini 3.7 Flash** (`gemini-3.7-flash`) - 드롭다운 메뉴로 전환 지원
- **실시간 스트리밍 대화**: Server-Sent Events (SSE) 기반의 유려한 타자 타이핑 효과
- **Gemini 스타일 UI/UX**:
  - 파스텔톤 그라데이션 및 캡슐형 인풋 필드
  - 실시간 마크다운 렌더링, 수식 및 코드 블록 하이라이팅, 원클릭 코드 복사 기능
  - 마이크 음성 입력 지원 (Web Speech API)
  - 새 대화 시작 및 추천 퀵 프롬프트 칩
- **안전한 API 키 관리**: 시스템 환경변수(`GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`) 및 `.env` 파일 자동 로드

---

## 🚀 빠른 시작 방법 (로컬 PC)

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. API 키 설정 (선택 사항)
이미 시스템 환경변수에 `GEMINI_API_KEY`가 등록되어 있다면 별도 설정 없이 바로 실행 가능합니다.  
필요한 경우 프로젝트 루트에 `.env` 파일을 생성하여 등록할 수 있습니다:
```env
GEMINI_API_KEY="your-gemini-api-key"
```

### 3. 서버 실행
아래 두 가지 방법 중 하나로 실행하면 기본 웹 브라우저에서 `http://127.0.0.1:8000`이 자동으로 열립니다.

- **방법 1 (파이썬 실행)**:
  ```bash
  python run.py
  ```
- **방법 2 (윈도우 탐색기)**:
  - `start.bat` 파일을 더블클릭

---

## 📁 프로젝트 구조
```text
gcp-compute-engine-chatbot/
├── app.py                 # FastAPI 백엔드 (SSE 스트리밍, 모델 라우팅)
├── run.py                 # 서버 실행 및 브라우저 자동 오픈 스크립트
├── start.bat              # 윈도우 원클릭 실행 배치 파일
├── requirements.txt       # Python 의존성 패키지 목록
├── README.md              # 프로젝트 안내 문서
└── static/
    ├── index.html         # Gemini 웹 UI 구조
    ├── style.css          # Gemini 감성의 커스텀 CSS
    └── app.js             # 스트리밍 및 모델 전환 자바스크립트 로직
```
