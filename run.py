import sys
import os
import time
import webbrowser
import threading
import uvicorn

# Windows 콘솔 utf-8 인코딩 지원
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def open_browser():
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n[Browser] Opening web browser: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    print("=" * 65)
    print("Google Gemini Web Chatbot Service (with Google Search Grounding)")
    print("Supported Models: Gemini 3.8 Flash (Default), Gemini 3.7 Flash")
    print("Access URL: http://127.0.0.1:8000")
    print("=" * 65)

    # 브라우저 자동 오픈 백그라운드 스레드
    threading.Thread(target=open_browser, daemon=True).start()

    # FastAPI 서버 구동
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )
