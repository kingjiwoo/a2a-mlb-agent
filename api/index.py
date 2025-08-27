#!/usr/bin/env python3
"""
Vercel Python Runtime을 위한 MLB 이적 전문 에이전트 API 엔트리포인트
A2A 서버와 MCP 서버를 모두 호스팅하고 에이전트 카드를 제공합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트 import 경로 보정
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import Dict, Any, Optional

# MLB 에이전트 관련 import
from agent_executor import MLBTransferAgentExecutor
from server import create_agent_card

# FastAPI 앱 생성
app = FastAPI(
    title="MLB 이적 전문 에이전트 API",
    description="MLB 선수 이적, FA 시장, 팀 전략을 전문적으로 분석하는 AI 에이전트",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 에이전트 카드 생성
agent_card = create_agent_card()

# 에이전트 실행기 인스턴스 (메모리 기반)
agent_executor = None

def get_agent_executor():
    """에이전트 실행기 인스턴스를 반환합니다."""
    global agent_executor
    if agent_executor is None:
        agent_executor = MLBTransferAgentExecutor()
    return agent_executor

@app.get("/")
async def root():
    """루트 엔드포인트 - 에이전트 정보 반환"""
    return {
        "name": agent_card.name,
        "description": agent_card.description,
        "version": agent_card.version,
        "skills": [skill.name for skill in agent_card.skills],
        "status": "running"
    }

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """에이전트 카드 정보를 반환합니다 (A2A 프로토콜 표준)"""
    return agent_card.dict()

@app.get("/api/agent/card")
async def get_agent_card_api():
    """에이전트 카드 정보를 API 형태로 반환합니다"""
    return agent_card.dict()

@app.get("/api/agent/skills")
async def get_agent_skills():
    """에이전트가 지원하는 스킬 목록을 반환합니다"""
    return {
        "skills": [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "tags": skill.tags,
                "examples": skill.examples
            }
            for skill in agent_card.skills
        ]
    }

@app.post("/api/chat")
async def chat_with_agent(request: Dict[str, Any]):
    """에이전트와 채팅을 수행합니다"""
    try:
        message = request.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="메시지가 필요합니다")
        
        # 에이전트 실행기 가져오기
        executor = get_agent_executor()
        
        # 에이전트 실행
        response = await executor.invoke(message)
        
        return {
            "response": response,
            "status": "success"
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "status": "error"
            }
        )

@app.post("/api/chat/stream")
async def chat_with_agent_stream(request: Dict[str, Any]):
    """에이전트와 스트리밍 채팅을 수행합니다"""
    try:
        message = request.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="메시지가 필요합니다")
        
        # 에이전트 실행기 가져오기
        executor = get_agent_executor()
        
        # 스트리밍 응답 생성
        async def generate_response():
            try:
                response = await executor.invoke(message)
                # 응답을 청크로 분할하여 스트리밍
                chunks = response.split()
                for chunk in chunks:
                    yield f"data: {json.dumps({'chunk': chunk, 'status': 'streaming'})}\n\n"
                    await asyncio.sleep(0.1)  # 자연스러운 스트리밍을 위한 지연
                
                # 완료 신호
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "status": "error"
            }
        )

@app.get("/api/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "MLB 이적 전문 에이전트",
        "version": "2.0.0"
    }

@app.get("/api/mcp/status")
async def mcp_status():
    """MCP 서버 상태를 확인합니다"""
    try:
        executor = get_agent_executor()
        if executor.tools:
            return {
                "status": "connected",
                "tool_count": len(executor.tools),
                "tools": [tool.name for tool in executor.tools[:5]]  # 처음 5개만 표시
            }
        else:
            return {
                "status": "no_tools",
                "message": "MCP 툴이 로드되지 않았습니다"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Vercel이 인식하는 ASGI/WGSI 엔트리포인트
# 이 변수가 있어야 Vercel Python Runtime이 인식합니다
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 