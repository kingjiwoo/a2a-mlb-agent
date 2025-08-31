#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

from importlib.util import spec_from_file_location, module_from_spec

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

    for main_py in candidates:
        if main_py.exists():
            try:
                spec = spec_from_file_location("mlb_mcp_main", str(main_py))
                m = module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(m)

                # 1) main.py 가 FastAPI app 을 직접 노출
                mcp_app = getattr(m, "app", None)

                # 2) 팩토리 함수 패턴 시도
                if mcp_app is None:
                    factory = getattr(m, "build_app", None) or getattr(m, "create_app", None)
                    if callable(factory):
                        mcp_app = factory()

                # 3) FastMCP 객체(mcp)를 노출하고 그 안에 app 이 있는 패턴
                if mcp_app is None:
                    mcp = getattr(m, "mcp", None)
                    if mcp is not None and hasattr(mcp, "app"):
                        mcp_app = getattr(mcp, "app")

                if mcp_app is None:
                    raise RuntimeError("mlb-api-mcp FastAPI app entrypoint를 찾지 못했습니다.")

                app.mount("/mlb", mcp_app)
                logger.info(f"✅ MCP subapp mounted at /mlb (from {main_py})")
                return True

            except Exception as e:
                logger.error(f"❌ MCP mount attempt failed at {main_py}: {e}")

    logger.error("❌ mlb-api-mcp main.py를 찾지 못했습니다. 탐색 경로를 확인하세요.")
    return False

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

    # ✅ 여기에서 MCP 마운트 시도
    try:
        # 1) 패키지 임포트 경로
        from mlb_api_mcp.app import app as mcp_app
    except Exception:
        try:
            # 2) 동적 임포트 경로 (하이픈/언더스코어 모두 탐색)
            import importlib.util
            project_root = Path(__file__).resolve().parents[1]
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
                    mcp_app = getattr(m, "app", None) \
                              or (callable(getattr(m, "create_app", None)) and m.create_app()) \
                              or (hasattr(m, "server") and getattr(m, "server").build())
                    if mcp_app:
                        break
            if not mcp_app:
                raise RuntimeError("mlb-api-mcp FastAPI app entrypoint를 찾지 못함")
        except Exception as ie:
            logger.exception(f"❌ MCP subapp import failed: {ie}")
            return app  # MCP 없이도 A2A는 동작

    # 충돌 방지용 서브경로
    app.mount("/mlb", mcp_app)
    logger.info("✅ MCP mounted at /mlb")
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
