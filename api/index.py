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


def mount_local_mcp_subapp(app) -> bool:
    """
    리포 내 동봉된 mlb-api-mcp를 탐색해 FastAPI subapp을 /mlb 경로에 마운트.
    성공 시 True, 실패 시 False.
    """
    base = Path(__file__).resolve().parent.parent  # 프로젝트 루트 기준
    candidates = [
        base / "third_party" / "mlb-api-mcp" / "main.py",
        base / "third_party" / "mlb_api_mcp" / "main.py",
        base / "mlb-api-mcp" / "main.py",
        base / "mlb_api_mcp" / "main.py",
        base / "packages" / "mlb-api-mcp" / "main.py",
        base / "packages" / "mlb_api_mcp" / "main.py",
    ]

    mcp_app = None
for main_py in candidates:
    if main_py.exists():
        spec = importlib.util.spec_from_file_location("mlb_api_mcp_main", str(main_py))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)  # type: ignore

        # 1) 이미 FastAPI app을 노출했다면 사용
        mcp_app = getattr(m, "app", None)
        # 2) 팩토리 함수라면 호출
        if not mcp_app:
            factory = getattr(m, "create_app", None) or getattr(m, "build_app", None)
            if callable(factory):
                mcp_app = factory()
        # 3) FastMCP 객체(mcp)가 있다면, 여기서 직접 http_app을 생성(가장 확실!)
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

            # /mcp → /mcp/ 리다이렉트(Starlette Mount 트레일링 슬래시 워크어라운드)
            class MCPPathRedirect:
                def __init__(self, app):
                    self.app = app
                async def __call__(self, scope, receive, send):
                    if scope.get("type") == "http" and scope.get("path") == "/mcp":
                        scope["path"] = "/mcp/"
                        scope["raw_path"] = b"/mcp/"
                    await self.app(scope, receive, send)
            mcp_app = MCPPathRedirect(mcp_app)

        if mcp_app:
            break

if not mcp_app:
    raise RuntimeError("mlb-api-mcp FastAPI app entrypoint를 찾지 못함")

app.mount("/mlb", mcp_app)
logger.info("✅ MCP mounted at /mlb")

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
        # 0) third_party를 import 경로에 추가
        project_root = Path(__file__).resolve().parents[1]
        third_party = project_root / "third_party"
        if third_party.exists():
            p = str(third_party)
            if p not in sys.path:
                sys.path.insert(0, p)

        # 1) 패키지 방식으로 먼저 시도: third_party/mlb_api_mcp/main.py를 패키지로 import
        try:
            from mlb_api_mcp import main as mcp_main
            mcp_app = (
                getattr(mcp_main, "app", None)
                or (callable(getattr(mcp_main, "create_app", None)) and mcp_main.create_app())
                or (hasattr(mcp_main, "mcp") and callable(getattr(mcp_main.mcp, "http_app", None)) and mcp_main.mcp.http_app())
            )
            if not mcp_app:
                raise RuntimeError("mlb_api_mcp.main에서 app/create_app/mcp.http_app을 찾지 못함")

        except Exception:
            # 2) 파일 경로 동적 로딩 (하이픈/언더스코어 모두 탐색)
            import importlib.util
            candidates = [
                project_root / "third_party" / "mlb_api_mcp" / "main.py",
                project_root / "third_party" / "mlb-api-mcp" / "main.py",
                project_root / "mlb_api_mcp" / "main.py",
                project_root / "mlb-api-mcp" / "main.py",
            ]
            mcp_app = None
            for main_py in candidates:
                if main_py.exists():
                    spec = importlib.util.spec_from_file_location("mlb_api_mcp_main", str(main_py))
                    m = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(m)  # type: ignore

                    mcp_app = (
                        getattr(m, "app", None)
                        or (callable(getattr(m, "create_app", None)) and m.create_app())
                        or (hasattr(m, "mcp") and callable(getattr(m.mcp, "http_app", None)) and m.mcp.http_app())
                    )
                    if mcp_app:
                        logger.info(f"✅ MCP subapp resolved from {main_py}")
                        break

            if not mcp_app:
                raise RuntimeError("mlb-api-mcp FastAPI app entrypoint를 찾지 못함")

        # 3) /mlb로 마운트
        app.mount("/mlb", mcp_app)
        logger.info("✅ MCP mounted at /mlb")

    except Exception as ie:
        logger.exception(f"❌ MCP subapp import failed: {ie}")
        return app
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
