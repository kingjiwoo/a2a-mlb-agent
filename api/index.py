#!/usr/bin/env python3
"""
Vercel Python Runtime을 위한 MLB 이적 전문 에이전트 API 엔트리포인트
server.py를 직접 사용하여 A2A 서버를 호스팅합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트 import 경로 보정
sys.path.append(str(Path(__file__).resolve().parent.parent))

# server.py에서 app 객체를 직접 import
try:
    from server import app
    print("✅ server.py에서 app 객체 import 성공")
except ImportError as e:
    print(f"❌ server.py import 실패: {e}")
    # fallback: 간단한 FastAPI 앱 생성
    try:
        from fastapi import FastAPI
        app = FastAPI(
            title="MLB 이적 전문 에이전트 API (Fallback)",
            description="MLB 이적 전문 에이전트입니다",
            version="2.0.0"
        )
        
        @app.get("/")
        async def root():
            return {"message": "MLB Agent API (Fallback Mode)", "status": "limited"}
            
        @app.get("/.well-known/agent.json")
        async def agent_card():
            return {"name": "MLB 이적 전문 에이전트", "status": "fallback"}
            
    except ImportError:
        # FastAPI도 없으면 에러
        raise ImportError("FastAPI를 사용할 수 없습니다")

# Vercel이 인식하는 ASGI 앱 객체
# 이 변수가 있어야 Vercel Python Runtime이 인식합니다 