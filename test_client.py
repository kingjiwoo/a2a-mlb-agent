import asyncio
import aiohttp
import json
from a2a.client import A2ACardResolver
from a2a.client.client_factory import ClientFactory
from a2a.client.client import ClientConfig
from a2a.types import Message
from a2a.utils import get_message_text
import httpx

def create_user_message(text: str, message_id: str = None) -> Message:
    """A2A 사용자 메시지 생성 함수"""
    from a2a.types import Message
    return Message(
        role="user",
        parts=[{"kind": "text", "text": text}],
        messageId=message_id or "test_message"
    )

async def test_mlb_transfer_agent():
    """MLB 이적 전문 에이전트를 A2A 클라이언트로 테스트하는 함수"""
    
    # A2A 서버 URL
    base_url = "http://localhost:9999"
    
    # 테스트 메시지들 (각 플로우별로)
    test_cases = [
        {
            "name": "🏟️ 구단 관계자 플로우 - 선수 영입 문의",
            "message": "양키스가 투수진을 보강하고 싶은데, 어떤 선수를 영입하면 좋을까요?",
            "expected_flow": "club_official"
        },
        {
            "name": "⚾ 선수 플로우 - 커리어 발전 상담",
            "message": "현재 팀에서 더 이상 발전할 수 없을 것 같아요. 새로운 도전을 위해 이적을 고려하고 있어요.",
            "expected_flow": "player"
        },
        {
            "name": "💙 팬 플로우 - 이적 이유 문의",
            "message": "우리 팀의 에이스가 떠난다고 하던데, 왜 이적하는 건가요? 너무 아쉽네요.",
            "expected_flow": "fan"
        },
        {
            "name": "📊 현재 가치 평가 테스트",
            "message": "오타니의 2024년 현재 가치는 어느 정도인가요?",
            "expected_flow": "club_official"
        }
    ]
    
    print("⚾ MLB 이적 전문 에이전트 A2A 클라이언트 테스트 시작")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        try:
            # A2A 카드 리졸버 생성
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
            )
            
            # 에이전트 카드 가져오기
            print("에이전트 카드를 가져오는 중...")
            agent_card = await resolver.get_agent_card()
            print(f"✅ 에이전트 이름: {agent_card.name}")
            print(f"✅ 에이전트 설명: {agent_card.description}")
            print(f"✅ 지원 스킬: {[skill.name for skill in agent_card.skills]}")
            print()
            
            # A2A 클라이언트 생성
            non_streaming_config = ClientConfig(httpx_client=httpx_client, streaming=False)
            non_streaming_factory = ClientFactory(non_streaming_config)
            non_streaming_client = non_streaming_factory.create(agent_card)
            
            streaming_config = ClientConfig(httpx_client=httpx_client, streaming=True)
            streaming_factory = ClientFactory(streaming_config)
            streaming_client = streaming_factory.create(agent_card)
            
            # 각 테스트 케이스 실행
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n📋 테스트 케이스 {i}: {test_case['name']}")
                print(f"🎯 예상 플로우: {test_case['expected_flow']}")
                print(f"💬 테스트 메시지: {test_case['message']}")
                print("-" * 50)
                
                try:
                    # 사용자 메시지 생성
                    user_message = create_user_message(test_case['message'])
                    
                    # 비스트리밍 메시지 테스트
                    print("🔄 비스트리밍 응답 대기 중...")
                    async for event in non_streaming_client.send_message(user_message):
                        if hasattr(event, 'parts') and event.parts:
                            response_text = get_message_text(event)
                            print(f"🤖 에이전트 응답:\n{response_text}")
                            
                            # 응답에 특정 키워드가 포함되어 있는지 확인
                            if "구단 영입 제안서" in response_text:
                                print("✅ 구단 관계자 플로우 응답 감지")
                            elif "커리어 발전 상담 결과" in response_text:
                                print("✅ 선수 플로우 응답 감지")
                            elif "팬을 위한 이적 설명" in response_text:
                                print("✅ 팬 플로우 응답 감지")
                            else:
                                print("⚠️ 플로우 응답 패턴을 찾을 수 없음")
                            
                            # 현재 시점 가치 평가 포함 여부 확인
                            if "현재 시점 가치 평가 완료" in response_text:
                                print("✅ 현재 시점 가치 평가 포함")
                            else:
                                print("⚠️ 현재 시점 가치 평가 누락")
                            
                            break
                    
                except Exception as e:
                    print(f"❌ 테스트 실행 중 오류: {e}")
                    import traceback
                    traceback.print_exc()
                
                print("-" * 50)
            
            print("\n🎉 A2A 클라이언트 테스트 완료!")
            
        except Exception as e:
            print(f"❌ A2A 클라이언트 초기화 중 오류: {e}")
            print("서버가 실행 중인지 확인해주세요.")
            import traceback
            traceback.print_exc()

async def test_agent_directly():
    """에이전트를 직접 테스트하는 함수 (A2A 서버 없이)"""
    print("\n🔧 직접 에이전트 테스트")
    print("=" * 40)
    
    try:
        from agent_executor import MLBTransferAgent
        
        # 에이전트 인스턴스 생성
        agent = MLBTransferAgent()
        print("✅ MLBTransferAgent 인스턴스 생성 성공")
        
        # 각 플로우별 테스트
        test_messages = [
            "양키스 투수진 보강을 위한 선수 영입 제안을 해주세요",
            "커리어 발전을 위해 이적을 고려하고 있어요",
            "우리 팀 선수가 떠나는 이유를 설명해주세요"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 테스트 {i}: {message}")
            print("-" * 30)
            
            try:
                response = await agent.invoke(message)
                print(f"🤖 에이전트 응답:\n{response}")
            except Exception as e:
                print(f"❌ 에이전트 실행 오류: {e}")
            
            print("-" * 30)
            
    except ImportError as e:
        print(f"❌ Import 오류: {e}")
    except Exception as e:
        print(f"❌ 에이전트 테스트 오류: {e}")

if __name__ == "__main__":
    print("🚀 MLB 이적 전문 에이전트 통합 테스트")
    
    # A2A 클라이언트 테스트 (권장)
    asyncio.run(test_mlb_transfer_agent())
    
    # 직접 에이전트 테스트 (백업)
    asyncio.run(test_agent_directly())