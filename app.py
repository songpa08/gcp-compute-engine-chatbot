import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from google import genai

# .env 환경변수 로드
load_dotenv()

app = FastAPI(title="Google Gemini Interactions Web Chatbot")

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

@app.get("/api/models")
async def get_models():
    return {
        "models": SUPPORTED_MODELS,
        "default": "models/gemini-3.8-flash"
    }

@app.get("/api/health")
async def health():
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return {"status": "ok", "has_api_key": has_key}

def run_gemini_interaction(user_input: str, model_name: str):
    """
    사용자가 지정한 interactions.create 코드를 정확히 실행하는 챗봇 엔진 함수
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되어 있지 않습니다.")

    # 1. Client 초기화
    client = genai.Client(
        api_key=api_key,
    )

    # 2. Tools 설정 (구글 검색)
    tools = [
        {
            'type': 'google_search',
        },
    ]

    # 3. Generation Config 설정
    generation_config = {
        'max_output_tokens': 65536,
        'thinking_level': 'medium',
    }

    # 4. Interactions API 호출
    interaction = client.interactions.create(
        model=model_name,
        input=user_input,
        tools=tools,
        generation_config=generation_config,
    )

    # 5. 결과 파싱 (interaction.steps 분석)
    last_step = interaction.steps[-1]
    print(f"[Interaction Result] Last step type: {getattr(last_step, 'type', 'unknown')}")

    # 최종 텍스트 추출
    reply_text = ""
    if hasattr(last_step, "content") and last_step.content:
        for c in last_step.content:
            if hasattr(c, "text") and c.text:
                reply_text += c.text
    elif hasattr(last_step, "text") and last_step.text:
        reply_text = last_step.text

    # 검색 출처 및 추론(Thinking) 과정 추출
    sources = []
    thoughts = []
    seen_uris = set()

    for step in interaction.steps:
        step_type = getattr(step, 'type', '')

        # Thinking 추출
        if step_type == 'thought':
            if hasattr(step, 'content'):
                for c in step.content:
                    if hasattr(c, 'text') and c.text:
                        thoughts.append(c.text)

        # 검색 결과 추출
        if hasattr(step, 'content'):
            for c in step.content:
                if hasattr(c, 'annotations') and c.annotations:
                    # annotations 내 출처 정보 확인
                    for ann in c.annotations:
                        uri = getattr(ann, 'uri', None)
                        title = getattr(ann, 'title', None) or uri
                        if uri and uri not in seen_uris:
                            seen_uris.add(uri)
                            sources.append({"title": title, "uri": uri})

    return {
        "text": reply_text,
        "thoughts": thoughts,
        "sources": sources,
        "steps_count": len(interaction.steps),
    }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """사용자가 지정한 client.interactions.create 로직으로 응답 생성"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다.")

    # 모델 ID 표준화
    model_name = request.model
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
    return {"message": "Gemini Chatbot Web Service is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
