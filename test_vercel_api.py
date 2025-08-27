#!/usr/bin/env python3
"""
Vercel API를 로컬에서 테스트하는 스크립트
"""

import asyncio
import httpx
import json

async def test_vercel_api():
    """Vercel API 엔드포인트들을 테스트합니다."""
    
    base_url = "http://localhost:8000"
    
    print("🚀 MLB 이적 전문 에이전트 Vercel API 테스트")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. 루트 엔드포인트 테스트
        print("\n📋 1. 루트 엔드포인트 테스트")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 성공: {data['name']}")
                print(f"📝 설명: {data['description']}")
                print(f"🔧 스킬: {', '.join(data['skills'])}")
            else:
                print(f"❌ 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        # 2. 에이전트 카드 테스트
        print("\n📋 2. 에이전트 카드 테스트")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/.well-known/agent.json")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ A2A 프로토콜 에이전트 카드 성공")
                print(f"📝 이름: {data['name']}")
                print(f"🔧 스킬 수: {len(data['skills'])}")
            else:
                print(f"❌ 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        # 3. API 에이전트 카드 테스트
        print("\n📋 3. API 에이전트 카드 테스트")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/api/agent/card")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API 에이전트 카드 성공")
                print(f"📝 이름: {data['name']}")
                print(f"🔧 스킬 수: {len(data['skills'])}")
            else:
                print(f"❌ 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        # 4. 스킬 목록 테스트
        print("\n📋 4. 스킬 목록 테스트")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/api/agent/skills")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 스킬 목록 성공")
                for skill in data['skills']:
                    print(f"  - {skill['name']}: {skill['description']}")
            else:
                print(f"❌ 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        # 5. 헬스 체크 테스트
        print("\n📋 5. 헬스 체크 테스트")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 헬스 체크 성공: {data['status']}")
            else:
                print(f"❌ 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        # 6. MCP 상태 테스트
        print("\n📋 6. MCP 상태 테스트")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/api/mcp/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ MCP 상태 확인 성공: {data['status']}")
                if data['status'] == 'connected':
                    print(f"🔧 연결된 툴 수: {data['tool_count']}")
                    print(f"📝 툴 목록: {', '.join(data['tools'])}")
            else:
                print(f"❌ 실패: {response.status_code}")
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        # 7. 채팅 테스트 (간단한 메시지)
        print("\n📋 7. 채팅 테스트")
        print("-" * 40)
        try:
            chat_data = {"message": "양키스 투수진 보강을 위한 선수 영입 제안을 해주세요"}
            response = await client.post(f"{base_url}/api/chat", json=chat_data)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 채팅 성공: {data['status']}")
                if 'response' in data:
                    response_text = data['response']
                    if len(response_text) > 100:
                        print(f"📝 응답: {response_text[:100]}...")
                    else:
                        print(f"📝 응답: {response_text}")
            else:
                print(f"❌ 실패: {response.status_code}")
                print(f"📝 오류 내용: {response.text}")
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    print("⚠️  먼저 서버를 실행해야 합니다:")
    print("   uvicorn api.index:app --reload --port 8000")
    print()
    
    # 서버가 실행 중인지 확인
    try:
        asyncio.run(test_vercel_api())
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        print("💡 서버가 실행 중인지 확인해주세요.") 