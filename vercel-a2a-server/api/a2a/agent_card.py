from http.server import BaseHTTPRequestHandler
import json
from typing import Dict, Any

# MLB 이적 전문 에이전트 카드
def create_agent_card() -> Dict[str, Any]:
    """MLB 이적 전문 에이전트 카드를 만드는 함수"""
    
    # MLB 이적 분석 스킬 (구단 관계자 플로우)
    transfer_analysis_skill = {
        "id": "mlb_transfer_analysis",
        "name": "MLB 이적 분석",
        "description": "구단 관계자를 위한 선수 영입 제안, 팀 약점 분석, 연봉 규모 검토를 제공합니다",
        "tags": ["mlb", "transfer", "baseball", "analysis", "club_official"],
        "examples": ["양키스 투수진 보강 제안", "다저스 타선 보강 분석", "FA 시장 주요 선수 영입 전략"],
        "input_modes": ["text"],
        "output_modes": ["text"],
    }

    # 선수 커리어 상담 스킬 (선수 플로우)
    career_consulting_skill = {
        "id": "career_consulting",
        "name": "선수 커리어 상담",
        "description": "선수들을 위한 이적 필요성 제시, 적합한 팀 탐색, 이적 설득을 제공합니다",
        "tags": ["mlb", "career", "player", "consulting", "transfer"],
        "examples": ["커리어 발전을 위한 이적 상담", "새로운 도전 기회 탐색", "최적 이적 후보 팀 분석"],
        "input_modes": ["text"],
        "output_modes": ["text"],
    }

    # 팬 소통 스킬 (팬 플로우)
    fan_communication_skill = {
        "id": "fan_communication",
        "name": "팬 소통 및 이적 설명",
        "description": "팬들의 감정에 공감하고 이적의 논리적 이유를 설명하며 새로운 팀에서의 비전을 제시합니다",
        "tags": ["mlb", "fan", "communication", "explanation", "vision"],
        "examples": ["이적 이유에 대한 팬 설명", "새로운 팀에서의 기대감 제시", "변함없는 응원 독려"],
        "input_modes": ["text"],
        "output_modes": ["text"],
    }

    # 현재 시점 가치 평가 스킬 (공통)
    value_assessment_skill = {
        "id": "current_value_assessment",
        "name": "현재 시점 가치 평가",
        "description": "최신 성적 추이와 세이버메트릭스를 기반으로 선수의 현재 시점 가치를 객관적으로 분석합니다",
        "tags": ["mlb", "value", "assessment", "sabermetrics", "current"],
        "examples": ["2024년 현재 선수 가치 분석", "최신 성적 기반 가치 평가", "세이버메트릭스 기반 객관적 분석"],
        "input_modes": ["text"],
        "output_modes": ["text"],
    }

    # 에이전트 카드 객체 생성
    agent_card = {
        "name": "MLB 이적 전문 에이전트",
        "description": "MLB 선수 이적, FA 시장, 팀 전략을 전문적으로 분석하는 AI 에이전트입니다. "
                    "구단 관계자, 선수, 팬 각각의 관점에서 맞춤형 분석과 제안을 제공하며, "
                    "최신 데이터와 세이버메트릭스를 기반으로 객관적인 가치 평가를 수행합니다.",
        "url": "https://your-vercel-domain.vercel.app/",
        "version": "2.0.0",
        "default_input_modes": ["text"],
        "default_output_modes": ["text"],
        "capabilities": {"streamable": True},
        "skills": [
            transfer_analysis_skill, 
            career_consulting_skill, 
            fan_communication_skill,
            value_assessment_skill
        ],
        "supports_authenticated_extended_card": False,
    }
    return agent_card

# Vercel Function 핸들러
class AgentCardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET 요청 처리 (에이전트 카드 제공)"""
        try:
            agent_card = create_agent_card()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(agent_card, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())

# Vercel Function 진입점
def handler(request, context):
    """Vercel Function 메인 핸들러"""
    if request.method == 'GET':
        return AgentCardHandler().do_GET()
    else:
        return {"error": "Method not allowed"}, 405 