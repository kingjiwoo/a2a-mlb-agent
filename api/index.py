#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

from importlib.util import spec_from_file_location, module_from_spec
import importlib.util
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 프로젝트 루트 import 경로 보정
sys.path.append(str(Path(__file__).resolve().parent.parent))

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import MLBTransferAgentExecutor


def mount_local_mcp_subapp() -> object:
    import importlib

    # 경로 후보 구성
    repo_root = Path(__file__).resolve().parents[2]  # repository root
    pkg_root = Path(__file__).resolve().parents[1]   # mlb_agent
    third_party_root = pkg_root / "third_party"

    for p in [str(repo_root), str(pkg_root), str(third_party_root)]:
        if p not in sys.path:
            sys.path.insert(0, p)

    module_candidates = [
        "third_party.mlb_api_mcp.main",        # mlb_agent/third_party 기준 import
        "mlb_agent.third_party.mlb_api_mcp.main",  # repo root 기준 import
        "mlb_api_mcp.main",                    # third_party가 sys.path에 직접 추가된 경우
    ]

    last_err = None
    for modname in module_candidates:
        try:
            m = importlib.import_module(modname)

            # 1) FastAPI app을 직접 노출?
            mcp_app = getattr(m, "app", None)

            # 2) 팩토리 함수?
            if not mcp_app:
                factory = getattr(m, "create_app", None) or getattr(m, "build_app", None)
                if callable(factory):
                    mcp_app = factory()

            # 3) FastMCP 객체(mcp)에서 http_app을 생성
            if not mcp_app and hasattr(m, "mcp"):
                cors = Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["GET", "POST", "OPTIONS"],
                    allow_headers=["*"],
                    expose_headers=["mcp-session-id"],
                    max_age=86400,
                )
                mcp_app = m.mcp.http_app(middleware=[cors])

                # /mcp -> /mcp/ 보정
                class MCPPathRedirect:
                    def __init__(self, app): self.app = app
                    async def __call__(self, scope, receive, send):
                        if scope.get("type") == "http" and scope.get("path") == "/mcp":
                            scope["path"] = "/mcp/"; scope["raw_path"] = b"/mcp/"
                        await self.app(scope, receive, send)
                mcp_app = MCPPathRedirect(mcp_app)

            if mcp_app:
                logger.info(f"✅ MCP subapp loaded via {modname}")
                return mcp_app
        except Exception as e:
            last_err = e

    logger.error(f"❌ mlb-api-mcp 패키지 import 실패: {last_err}")
    return None

def create_agent_card() -> AgentCard:
    transfer_analysis_skill = AgentSkill(
        id="mlb_transfer_analysis",
        name="MLB 이적 분석",
        description="구단 관계자를 위한 선수 영입 제안, 팀 약점 분석, 연봉 규모 검토를 제공합니다",
        tags=["mlb", "transfer", "baseball", "analysis", "club_official"],
        examples=["양키스 투수진 보강 제안", "다저스 타선 보강 분석", "FA 시장 주요 선수 영입 전략"],
        input_modes=["text"],
        output_modes=["text"],
    )
    career_consulting_skill = AgentSkill(
        id="career_consulting",
        name="선수 커리어 상담",
        description="선수들을 위한 이적 필요성 제시, 적합한 팀 탐색, 이적 설득을 제공합니다",
        tags=["mlb", "career", "player", "consulting", "transfer"],
        examples=["커리어 발전을 위한 이적 상담", "새로운 도전 기회 탐색", "최적 이적 후보 팀 분석"],
        input_modes=["text"],
        output_modes=["text"],
    )
    fan_communication_skill = AgentSkill(
        id="fan_communication",
        name="팬 소통 및 이적 설명",
        description="팬 감정에 공감하고 이적의 논리적 이유와 새로운 팀에서의 비전을 제시합니다",
        tags=["mlb", "fan", "communication", "explanation", "vision"],
        examples=["이적 이유 설명", "새 팀 비전 제시", "응원 독려"],
        input_modes=["text"],
        output_modes=["text"],
    )
    value_assessment_skill = AgentSkill(
        id="current_value_assessment",
        name="현재 시점 가치 평가",
        description="최신 성적과 세이버메트릭스로 선수 가치를 객관적으로 분석합니다",
        tags=["mlb", "value", "assessment", "sabermetrics", "current"],
        examples=["2024년 현재 선수 가치", "최신 성적 기반 평가", "세이버메트릭스 분석"],
        input_modes=["text"],
        output_modes=["text"],
    )
    return AgentCard(
        name="MLB 이적 전문 에이전트",
        description="MLB 이적/FA/팀 전략 분석. 구단/선수/팬 관점 맞춤 제안 및 가치 평가 제공.",
        url="https://a2a-mlb-agent.vercel.app/",
        version="2.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streamable=True),
        skills=[
            transfer_analysis_skill,
            career_consulting_skill,
            fan_communication_skill,
            value_assessment_skill,
        ],
        supports_authenticated_extended_card=False,
    )


def build_a2a_app():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Missing ANTHROPIC_API_KEY")

    agent_card = create_agent_card()
    executor = MLBTransferAgentExecutor()
    handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())
    server = A2AFastAPIApplication(agent_card=agent_card, http_handler=handler)

    app = server.build()
    logger.info("✅ A2A app built (executor attached)")

    try:
        # Vercel 용량 제한 회피: 기본은 로컬 MCP 비활성화. 필요 시 ENABLE_LOCAL_MCP=true 설정
        enable_local_mcp = os.getenv("ENABLE_LOCAL_MCP", "").lower() in ("1", "true", "yes")
        if enable_local_mcp:
            mcp_app = mount_local_mcp_subapp()
            if mcp_app:
                app.mount("/mlb", mcp_app)
                logger.info("✅ MCP mounted at /mlb (local)")
            else:
                logger.warning("⚠️ MCP subapp을 찾지 못함 - /mlb 엔드포인트 비활성화")
        else:
            logger.info("ℹ️ Local MCP disabled (set ENABLE_LOCAL_MCP=true to enable)")

    except Exception as ie:
        logger.exception(f"❌ MCP subapp import failed: {ie}")
        # MCP 실패해도 메인 앱은 계속 동작
    # --- 간단한 UI 라우트 추가 (/, /chat) ---
    try:
        from fastapi import Request
        from fastapi.responses import HTMLResponse, JSONResponse

        @app.get("/", response_class=HTMLResponse)
        async def chat_ui_root():
            return """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>MLB Agent Chat</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 32px auto; padding: 0 16px; }
    h1 { font-size: 20px; }
    #log { border: 1px solid #ddd; padding: 12px; border-radius: 8px; min-height: 240px; }
    .msg { margin: 8px 0; }
    .u { color: #333; }
    .a { color: #0b6; }
    form { display: flex; gap: 8px; margin-top: 12px; }
    input[type=text] { flex: 1; padding: 8px; }
    small { color: #777; }
  </style>
  </head>
  <body>
    <h1>MLB 이적 전문 에이전트</h1>
    <small>세션은 브라우저 탭 기준으로 유지됩니다.</small>
    <div id=\"log\"></div>
    <form id=\"f\">
      <input id=\"t\" type=\"text\" placeholder=\"메시지를 입력하세요...\" required />
      <button>Send</button>
    </form>
    <script>
      const log = document.getElementById('log');
      const form = document.getElementById('f');
      const input = document.getElementById('t');
      const sid = sessionStorage.getItem('mlb_sid') || (Date.now().toString(36)+Math.random().toString(36).slice(2));
      sessionStorage.setItem('mlb_sid', sid);
      function add(role, text){
        const div = document.createElement('div');
        div.className = 'msg ' + (role === 'user' ? 'u' : 'a');
        div.textContent = (role === 'user' ? '나: ' : '에이전트: ') + text;
        log.appendChild(div); log.scrollTop = log.scrollHeight;
      }
      form.addEventListener('submit', async (e)=>{
        e.preventDefault(); const text = input.value.trim(); if(!text) return; input.value=''; add('user', text);
        try{
          const res = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ text, session_id: sid }) });
          const j = await res.json(); add('agent', j.reply || j.error || '[no reply]');
        }catch(err){ add('agent', '에러: ' + (err?.message||err)); }
      });
    </script>
  </body>
</html>
            """

        @app.post("/chat")
        async def chat_api(req: Request):
            body = await req.json()
            text = (body or {}).get("text") or ""
            session_id = (body or {}).get("session_id") or "default"
            if not text:
                return JSONResponse({"error": "text is required"}, status_code=400)
            try:
                # 내부 실행자 재사용 (메모리 포함)
                out = await executor.agent.invoke(text, session_id=session_id)
                return JSONResponse({"reply": out})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        # 이전 경로와의 호환성을 위해 /ui/chat도 유지
        @app.post("/ui/chat")
        async def chat_api_legacy(req: Request):
            return await chat_api(req)
    except Exception:
        # UI 실패해도 앱은 유지
        pass

    return app


# ---- 모듈 레벨에서 앱 생성 (Vercel은 module-level 'app'을 찾음) ----
try:
    app = build_a2a_app()
except Exception as e:
    logger.exception(f"A2A app build failed, falling back to FastAPI: {e}")
    from fastapi import FastAPI

    app = FastAPI(
        title="MLB 이적 전문 에이전트 API (Fallback)",
        description="A2A 빌드 실패로 제한 모드",
        version="2.0.0",
    )

    @app.get("/")
    async def root():
        return {"message": "MLB Agent API (Fallback Mode)", "status": "limited"}

    @app.get("/.well-known/agent.json")
    async def agent_json():
        # 최소 카드 형태라도 노출
        return {"name": "MLB 이적 전문 에이전트", "status": "fallback"}
