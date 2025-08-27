#!/usr/bin/env python3
"""
Vercel Python Runtime을 위한 MLB 이적 전문 에이전트 API 엔트리포인트
A2A 서버와 MCP 서버를 모두 호스팅하고 에이전트 카드를 제공합니다.
"""

import sys
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 프로젝트 루트 import 경로 보정
try:
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    logger.info("Import 경로 설정 완료")
except Exception as e:
    logger.error(f"Import 경로 설정 실패: {e}")

# FastAPI 및 기본 모듈 import
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    import asyncio
    import json
    from typing import Dict, Any, Optional
    logger.info("FastAPI 및 기본 모듈 import 성공")
    FASTAPI_AVAILABLE = True
except ImportError as e:
    logger.error(f"기본 모듈 import 실패: {e}")
    FASTAPI_AVAILABLE = False
    
    # FastAPI가 없으면 간단한 대체 객체 생성
    class FastAPI:
        def __init__(self, **kwargs):
            self.title = kwargs.get('title', 'MLB Agent API')
            self.description = kwargs.get('description', 'MLB Agent API')
            self.version = kwargs.get('version', '2.0.0')
            self.routes = []
            
        def add_middleware(self, *args, **kwargs):
            pass
            
        def on_event(self, event_type):
            def decorator(func):
                return func
            return decorator
            
        def get(self, path):
            def decorator(func):
                self.routes.append(('GET', path, func))
                return func
            return decorator
            
        def post(self, path):
            def decorator(func):
                self.routes.append(('POST', path, func))
                return func
            return decorator
    
    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code = status_code
            self.detail = detail
    
    class JSONResponse:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content
    
    class CORSMiddleware:
        def __init__(self, *args, **kwargs):
            pass

# 안전한 import를 위한 함수
def safe_agent_import():
    """MLB 에이전트 관련 모듈을 안전하게 import합니다."""
    try:
        from agent_executor import MLBTransferAgentExecutor
        from server import create_agent_card
        logger.info("MLB 에이전트 모듈 import 성공")
        return True
    except ImportError as e:
        logger.error(f"MLB 에이전트 모듈 import 실패: {e}")
        return False

# FastAPI 앱 생성
app = FastAPI(
    title="MLB 이적 전문 에이전트 API",
    description="MLB 선수 이적, FA 시장, 팀 전략을 전문적으로 분석하는 AI 에이전트",
    version="2.0.0"
)

# CORS 설정
if FASTAPI_AVAILABLE:
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS 미들웨어 설정 성공")
    except Exception as e:
        logger.warning(f"CORS 미들웨어 설정 실패: {e}")
else:
    logger.warning("FastAPI를 사용할 수 없어 CORS 미들웨어를 건너뜁니다")

# 에이전트 카드 및 실행기 초기화
agent_card = None
agent_executor = None

def initialize_agent():
    """에이전트를 안전하게 초기화합니다."""
    global agent_card, agent_executor
    
    try:
        if safe_agent_import():
            from server import create_agent_card
            agent_card = create_agent_card()
            logger.info("에이전트 카드 생성 성공")
            return True
        else:
            # 기본 에이전트 카드 생성
            try:
                from a2a.types import AgentCard, AgentSkill, AgentCapabilities
                agent_card = AgentCard(
                    name="MLB 이적 전문 에이전트 (제한 모드)",
                    description="MLB 이적 전문 에이전트입니다. 현재 제한된 기능으로 운영 중입니다.",
                    url="https://vercel.app/",
                    version="2.0.0",
                    default_input_modes=["text"],
                    default_output_modes=["text"],
                    capabilities=AgentCapabilities(streamable=True),
                    skills=[],
                    supports_authenticated_extended_card=False,
                )
                logger.info("기본 에이전트 카드 생성 성공")
                return True
            except ImportError:
                # a2a 모듈도 없으면 딕셔너리로 생성
                agent_card = {
                    "name": "MLB 이적 전문 에이전트 (제한 모드)",
                    "description": "MLB 이적 전문 에이전트입니다. 현재 제한된 기능으로 운영 중입니다.",
                    "url": "https://vercel.app/",
                    "version": "2.0.0",
                    "skills": []
                }
                logger.info("딕셔너리 에이전트 카드 생성 성공")
                return True
    except Exception as e:
        logger.error(f"에이전트 초기화 실패: {e}")
        return False

def get_agent_executor():
    """에이전트 실행기를 안전하게 반환합니다."""
    global agent_executor
    
    if agent_executor is None:
        try:
            if safe_agent_import():
                from agent_executor import MLBTransferAgentExecutor
                agent_executor = MLBTransferAgentExecutor()
                logger.info("MLB 에이전트 실행기 생성 성공")
            else:
                logger.warning("MLB 에이전트 실행기 생성 실패 - 제한 모드로 운영")
                agent_executor = None
        except Exception as e:
            logger.error(f"에이전트 실행기 생성 중 오류: {e}")
            agent_executor = None
    
    return agent_executor

# 앱 시작 시 에이전트 초기화
if FASTAPI_AVAILABLE:
    try:
        @app.on_event("startup")
        async def startup_event():
            """앱 시작 시 실행되는 이벤트"""
            logger.info("MLB 이적 전문 에이전트 API 시작 중...")
            initialize_agent()
            logger.info("MLB 이적 전문 에이전트 API 시작 완료")
    except Exception as e:
        logger.warning(f"startup 이벤트 설정 실패: {e}")
else:
    # FastAPI가 없으면 즉시 초기화
    logger.info("FastAPI 없이 즉시 에이전트 초기화")
    initialize_agent()

@app.get("/")
async def root():
    """루트 엔드포인트 - 에이전트 정보 반환"""
    try:
        if agent_card:
            if isinstance(agent_card, dict):
                return {
                    "name": agent_card.get("name", "MLB 이적 전문 에이전트"),
                    "description": agent_card.get("description", "서비스 초기화 중입니다."),
                    "version": agent_card.get("version", "2.0.0"),
                    "skills": agent_card.get("skills", []),
                    "status": "running"
                }
            else:
                return {
                    "name": agent_card.name,
                    "description": agent_card.description,
                    "version": agent_card.version,
                    "skills": [skill.name for skill in agent_card.skills] if hasattr(agent_card, 'skills') else [],
                    "status": "running"
                }
        else:
            return {
                "name": "MLB 이적 전문 에이전트",
                "description": "서비스 초기화 중입니다. 잠시 후 다시 시도해주세요.",
                "status": "initializing"
            }
    except Exception as e:
        logger.error(f"루트 엔드포인트 오류: {e}")
        return {
            "name": "MLB 이적 전문 에이전트",
            "description": "일시적인 오류가 발생했습니다.",
            "status": "error",
            "error": str(e)
        }

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """에이전트 카드 정보를 반환합니다 (A2A 프로토콜 표준)"""
    try:
        if agent_card:
            if isinstance(agent_card, dict):
                return agent_card
            else:
                return agent_card.dict() if hasattr(agent_card, 'dict') else agent_card
        else:
            raise HTTPException(status_code=503, detail="에이전트가 아직 초기화되지 않았습니다")
    except Exception as e:
        logger.error(f"에이전트 카드 반환 오류: {e}")
        raise HTTPException(status_code=500, detail=f"에이전트 카드 반환 중 오류: {str(e)}")

@app.get("/api/agent/card")
async def get_agent_card_api():
    """에이전트 카드 정보를 API 형태로 반환합니다"""
    try:
        if agent_card:
            if isinstance(agent_card, dict):
                return agent_card
            else:
                return agent_card.dict() if hasattr(agent_card, 'dict') else agent_card
        else:
            raise HTTPException(status_code=503, detail="에이전트가 아직 초기화되지 않았습니다")
    except Exception as e:
        logger.error(f"API 에이전트 카드 반환 오류: {e}")
        raise HTTPException(status_code=500, detail=f"API 에이전트 카드 반환 중 오류: {str(e)}")

@app.get("/api/agent/skills")
async def get_agent_skills():
    """에이전트가 지원하는 스킬 목록을 반환합니다"""
    try:
        if agent_card:
            if isinstance(agent_card, dict):
                skills = agent_card.get("skills", [])
                return {"skills": skills}
            elif hasattr(agent_card, 'skills'):
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
            else:
                return {"skills": [], "message": "스킬 정보를 불러올 수 없습니다"}
        else:
            return {"skills": [], "message": "에이전트가 초기화되지 않았습니다"}
    except Exception as e:
        logger.error(f"스킬 목록 반환 오류: {e}")
        return {"skills": [], "error": str(e)}

@app.post("/api/chat")
async def chat_with_agent(request: Dict[str, Any]):
    """에이전트와 채팅을 수행합니다"""
    try:
        message = request.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="메시지가 필요합니다")
        
        # 에이전트 실행기 가져오기
        executor = get_agent_executor()
        
        if executor is None:
            return {
                "response": "죄송합니다. 현재 에이전트가 제한 모드로 운영 중입니다. 잠시 후 다시 시도해주세요.",
                "status": "limited"
            }
        
        # 에이전트 실행
        response = await executor.invoke(message)
        
        return {
            "response": response,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"채팅 오류: {e}")
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
        
        if executor is None:
            return {
                "response": "죄송합니다. 현재 에이전트가 제한 모드로 운영 중입니다. 잠시 후 다시 시도해주세요.",
                "status": "limited"
            }
        
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
        logger.error(f"스트리밍 채팅 오류: {e}")
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
    try:
        return {
            "status": "healthy",
            "service": "MLB 이적 전문 에이전트",
            "version": "2.0.0",
            "agent_initialized": agent_card is not None,
            "fastapi_available": FASTAPI_AVAILABLE
        }
    except Exception as e:
        logger.error(f"헬스 체크 오류: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/mcp/status")
async def mcp_status():
    """MCP 서버 상태를 확인합니다"""
    try:
        executor = get_agent_executor()
        if executor and executor.tools:
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
        logger.error(f"MCP 상태 확인 오류: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/test")
async def test_endpoint():
    """간단한 테스트 엔드포인트"""
    return {
        "message": "API가 정상적으로 작동합니다!",
        "status": "success",
        "timestamp": "2024-01-01T00:00:00Z",
        "fastapi_available": FASTAPI_AVAILABLE
    }

@app.get("/api/debug")
async def debug_info():
    """디버그 정보를 반환합니다"""
    try:
        return {
            "status": "debug",
            "agent_card_initialized": agent_card is not None,
            "agent_executor_initialized": agent_executor is not None,
            "import_status": {
                "agent_modules": safe_agent_import(),
                "fastapi_available": FASTAPI_AVAILABLE
            },
            "python_version": sys.version,
            "sys_path": str(sys.path)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Vercel이 인식하는 ASGI/WGSI 엔트리포인트
# 이 변수가 있어야 Vercel Python Runtime이 인식합니다
if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError:
        print("uvicorn이 설치되지 않았습니다. pip install uvicorn으로 설치해주세요.") 