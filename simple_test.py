#!/usr/bin/env python3
"""
MLB 이적 전문 에이전트 간단 테스트 스크립트
create_react_agent 기반 프롬프트 시스템 테스트
"""

import asyncio
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

async def test_react_agent():
    """create_react_agent 기반 에이전트를 테스트하는 함수"""
    print("🚀 MLB 이적 전문 에이전트 create_react_agent 테스트 시작")
    print("=" * 60)
    
    try:
        # 에이전트 import
        from agent_executor import MLBTransferAgent
        
        print("✅ 모듈 import 성공")
        
        # 에이전트 인스턴스 생성
        agent = MLBTransferAgent()
        print("✅ MLBTransferAgent 인스턴스 생성 성공")
        
        # 각 플로우별 테스트
        test_scenarios = [
            {
                "name": "🏟️ 구단 관계자 플로우",
                "message": "양키스가 투수진을 보강하고 싶은데, 어떤 선수를 영입하면 좋을까요?",
                "expected_flow": "club_official"
            },
            {
                "name": "⚾ 선수 플로우", 
                "message": "현재 팀에서 더 이상 발전할 수 없을 것 같아요. 새로운 도전을 위해 이적을 고려하고 있어요.",
                "expected_flow": "player"
            },
            {
                "name": "💙 팬 플로우",
                "message": "우리 팀의 에이스가 떠난다고 하던데, 왜 이적하는 건가요? 너무 아쉽네요.",
                "expected_flow": "fan"
            },
            {
                "name": "📊 현재 가치 평가 테스트",
                "message": "오타니의 2024년 현재 가치는 어느 정도인가요?",
                "expected_flow": "club_official"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n📋 테스트 시나리오 {i}: {scenario['name']}")
            print(f"🎯 예상 플로우: {scenario['expected_flow']}")
            print(f"💬 테스트 메시지: {scenario['message']}")
            print("-" * 50)
            
            try:
                # 에이전트 실행
                print("🔄 에이전트 실행 중...")
                response = await agent.invoke(scenario['message'])
                
                print("✅ 에이전트 응답 성공!")
                print(f"🤖 응답 내용:\n{response}")
                
                # 응답에 특정 키워드가 포함되어 있는지 확인
                if "구단 영입 제안서" in response:
                    print("✅ 구단 관계자 플로우 응답 감지")
                elif "커리어 발전 상담 결과" in response:
                    print("✅ 선수 플로우 응답 감지")
                elif "팬을 위한 이적 설명" in response:
                    print("✅ 팬 플로우 응답 감지")
                else:
                    print("⚠️ 플로우 응답 패턴을 찾을 수 없음")
                
                # 현재 시점 가치 평가 포함 여부 확인
                if "현재 시점 가치 평가 완료" in response:
                    print("✅ 현재 시점 가치 평가 포함")
                else:
                    print("⚠️ 현재 시점 가치 평가 누락")
                
            except Exception as e:
                print(f"❌ 에이전트 실행 오류: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 50)
        
        print("\n🎉 모든 테스트 완료!")
        
        # 테스트 결과 요약
        print("\n📊 테스트 결과 요약:")
        print("🏟️ 구단 관계자 플로우: 선수 영입 제안, 팀 약점 분석, 연봉 규모 검토")
        print("⚾ 선수 플로우: 이적 필요성 제시, 적합한 팀 탐색, 이적 설득")
        print("💙 팬 플로우: 감정 공감, 논리적 이유 설명, 새로운 비전 제시")
        print("📊 공통: 현재 시점 가치 평가 (최신 데이터 기반)")
        
        print("\n🔧 기술적 특징:")
        print("- LangGraph create_react_agent 기반")
        print("- 프롬프트 파일 기반 상황별 맞춤형 응답")
        print("- MCP 툴 통합 (mlb-api-mcp)")
        print("- 사용자 의도 자동 인식 및 플로우 선택")
        print("- A2A 프로토콜 지원")
        
    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        print("💡 의존성 설치가 필요할 수 있습니다: uv sync")
    except Exception as e:
        print(f"❌ 전체 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

async def test_prompts():
    """프롬프트 파일 로드 테스트"""
    print("\n📝 프롬프트 파일 테스트")
    print("=" * 40)
    
    try:
        from agent_executor import MLBTransferAgent
        
        agent = MLBTransferAgent()
        
        # 프롬프트 확인
        print("📋 로드된 프롬프트:")
        for prompt_type, content in agent.prompts.items():
            print(f"- {prompt_type}: {len(content)}자")
            print(f"  미리보기: {content[:100]}...")
        
        print("\n✅ 프롬프트 로드 성공")
        
    except Exception as e:
        print(f"❌ 프롬프트 테스트 오류: {e}")

async def test_environment():
    """환경 설정 테스트"""
    print("\n🔧 환경 설정 테스트")
    print("=" * 30)
    
    # 환경 변수 확인
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model = os.getenv("ANTHROPIC_MODEL")
    
    print(f"ANTHROPIC_API_KEY: {'✅ 설정됨' if anthropic_key else '❌ 설정되지 않음'}")
    print(f"ANTHROPIC_MODEL: {anthropic_model or '❌ 설정되지 않음'}")
    
    if not anthropic_key:
        print("⚠️ ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("💡 .env 파일에 API 키를 추가해주세요.")
    
    if not anthropic_model:
        print("⚠️ ANTHROPIC_MODEL이 설정되지 않았습니다.")
        print("💡 .env 파일에 모델명을 추가해주세요.")

if __name__ == "__main__":
    print("⚾ MLB 이적 전문 에이전트 통합 테스트")
    print("=" * 60)
    
    # 환경 설정 테스트
    asyncio.run(test_environment())
    
    # 프롬프트 테스트
    asyncio.run(test_prompts())
    
    # create_react_agent 에이전트 테스트
    asyncio.run(test_react_agent()) 