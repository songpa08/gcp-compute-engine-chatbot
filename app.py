import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from google import genai
from google.cloud import secretmanager

# .env 환경변수 로드 (로컬 테스트용)
load_dotenv()

app = FastAPI(title="Google Gemini Cloud Run Web Chatbot")

# 브라우저 정적 자원 최신 유지 미들웨어 (강력 캐시 방지)
class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/") or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheStaticMiddleware)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# 지원 모델 정의
SUPPORTED_MODELS = [
    {
        "id": "models/gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "badge": "Flash 3.8",
        "description": "최신 모델 (Interactions API + Google Search + Thinking)",
        "is_default": True,
    },
    {
        "id": "models/gemini-3.7-flash",
        "name": "Gemini 3.7 Flash",
        "badge": "Flash 3.7",
        "description": "고성능 하이브리드 추론 플래시 모델",
        "is_default": False,
    },
]

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "models/gemini-3.8-flash"

# Secret Manager 캐시
CACHED_API_KEY = None

def get_gemini_api_key() -> str:
    """
    1. 환경변수 확인 (Cloud Run Secret 매핑 또는 .env)
    2. GCP Secret Manager SDK (projects/298843281819/secrets/GEMINI_API_KEY) 확인
    """
    global CACHED_API_KEY
    if CACHED_API_KEY:
        return CACHED_API_KEY

    # 1. 환경변수 확인
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key:
        CACHED_API_KEY = env_key.strip()
        return CACHED_API_KEY

    # 2. GCP Secret Manager SDK 확인 (Cloud Run 서비스 계정 권한 이용)
    secret_name = "projects/298843281819/secrets/GEMINI_API_KEY/versions/latest"
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": secret_name})
        payload_key = response.payload.data.decode("utf-8").strip()
        if payload_key:
            print(f"[Secret Manager] Successfully loaded API key from {secret_name}")
            CACHED_API_KEY = payload_key
            os.environ["GEMINI_API_KEY"] = payload_key
            return CACHED_API_KEY
    except Exception as e:
        print(f"[Secret Manager SDK] 로드 시도 실패: {e}")

    return ""

def run_gemini_interaction(user_input: str, model_id: str = "models/gemini-3.8-flash"):
    """
    Interactions API 기반 Gemini 실행 (Google Search Grounding 탑재)
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY를 찾을 수 없습니다. Secret Manager 권한 또는 환경변수를 확인해주세요.")

    client = genai.Client(api_key=api_key)

    tools = [
        {
            'type': 'google_search',
        },
    ]

    generation_config = {
        'max_output_tokens': 65536,
        'thinking_level': 'medium',
    }

    interaction = client.interactions.create(
        model=model_id,
        input=user_input,
        tools=tools,
        generation_config=generation_config,
    )

    final_step = interaction.steps[-1] if interaction.steps else None

    # 응답 텍스트 및 사고과정 추출
    text_content = ""
    thoughts = []
    sources = []

    if final_step:
        # 모델 본문 텍스트 및 annotations 추출
        content_val = getattr(final_step, 'content', None)
        if isinstance(content_val, list):
            parts_text = []
            for item in content_val:
                # 1. 텍스트 추출 (TextContent.text)
                if hasattr(item, 'text') and item.text:
                    parts_text.append(str(item.text))
                elif isinstance(item, str):
                    parts_text.append(item)
                
                # 2. 검색 출처 추출 (TextContent.annotations -> URLCitation)
                ann_list = getattr(item, 'annotations', None) or []
                for ann in ann_list:
                    title = getattr(ann, 'title', None) or '웹 검색 출처'
                    url = getattr(ann, 'url', None) or getattr(ann, 'uri', None)
                    if url and url not in [s.get('uri') for s in sources]:
                        sources.append({'title': title, 'uri': url})
            if parts_text:
                text_content = "".join(parts_text)
        elif hasattr(final_step, 'text') and final_step.text:
            text_content = str(final_step.text)
        elif hasattr(final_step, 'parts') and final_step.parts:
            parts_text = []
            for p in final_step.parts:
                if hasattr(p, 'text') and p.text:
                    parts_text.append(p.text)
            if parts_text:
                text_content = "".join(parts_text)
        elif content_val and isinstance(content_val, str):
            text_content = content_val

        # Thought 과정 확인
        if hasattr(final_step, 'thought') and final_step.thought:
            thoughts.append(str(final_step.thought))

    # 검색 출처(Sources / Grounding Metadata) 추출
    try:
        for step in interaction.steps:
            if hasattr(step, 'grounding_metadata') and step.grounding_metadata:
                gm = step.grounding_metadata
                chunks = getattr(gm, 'grounding_chunks', None) or []
                for chunk in chunks:
                    web = getattr(chunk, 'web', None)
                    if web:
                        title = getattr(web, 'title', '웹 검색 결과')
                        uri = getattr(web, 'uri', '')
                        if uri and uri not in [s.get('uri') for s in sources]:
                            sources.append({'title': title, 'uri': uri})
            if hasattr(step, 'thought') and step.thought and str(step.thought) not in thoughts:
                thoughts.append(str(step.thought))
    except Exception as parse_err:
        print(f"[Grounding Parse Warning] {parse_err}")

    if not text_content:
        text_content = str(final_step)

    return {
        "text": text_content,
        "thoughts": thoughts,
        "sources": sources,
        "model": model_id,
        "raw_step": str(final_step)
    }

# API 엔드포인트들
@app.get("/api/health")
async def health_check():
    """Cloud Run Startup / Liveness 헬스체크"""
    key = get_gemini_api_key()
    return {
        "status": "ok",
        "has_api_key": bool(key),
        "service": "cloud-run"
    }

@app.get("/api/models")
async def list_models():
    """지원 AI 모델 목록"""
    return {
        "models": SUPPORTED_MODELS,
        "default": "models/gemini-3.8-flash"
    }

@app.post("/api/chat")
async def chat_interaction(request: ChatRequest):
    """Gemini Interactions 대화 생성"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다.")

    model_name = request.model or "models/gemini-3.8-flash"
    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"
    
    valid_models = ["models/gemini-3.8-flash", "models/gemini-3.7-flash"]
    if model_name not in valid_models:
        model_name = "models/gemini-3.8-flash"

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            run_gemini_interaction,
            request.message,
            model_name
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Gemini Interactions 실행 오류: {str(e)}"}
        )

# 정적 파일 서빙
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Gemini Chatbot Web Service on Cloud Run is running."}

if __name__ == "__main__":
    import uvicorn
    # Cloud Run은 환경변수 PORT를 주입합니다 (기본값: 8080)
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Cloud Run Chatbot on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
