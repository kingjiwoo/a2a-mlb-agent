#!/usr/bin/env python3
"""
MCP 툴 직접 테스트 스크립트
"""

import asyncio
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_tools():
    """MCP 툴을 직접 테스트하는 함수"""
    try:
        logger.info("MCP 클라이언트 초기화 중...")
        
        # MCP 클라이언트 생성
        client = MultiServerMCPClient(
            {
                "mlb": {
                    "transport": "streamable_http",
                    "url": "http://localhost:8000/mcp/",
                }
            }
        )
        
        logger.info("MCP 툴 목록 가져오는 중...")
        
        # 툴 목록 가져오기
        tools = await client.get_tools()
        logger.info(f"발견된 툴 수: {len(tools)}")
        
        # 각 툴 정보 출력
        for tool_name, tool in tools.items():
            logger.info(f"\n툴: {tool_name}")
            logger.info(f"설명: {getattr(tool, 'description', '설명 없음')}")
            logger.info(f"타입: {type(tool)}")
            
            # 툴의 메서드 확인
            methods = [method for method in dir(tool) if not method.startswith('_')]
            logger.info(f"사용 가능한 메서드: {methods}")
        
        # 특정 툴 테스트 (get_mlb_roster가 있다면)
        if 'get_mlb_roster' in tools:
            logger.info("\n=== get_mlb_roster 툴 테스트 ===")
            roster_tool = tools['get_mlb_roster']
            
            try:
                # 툴 실행 (예: 양키스 팀 ID 147)
                logger.info("양키스 로스터 조회 중...")
                result = await roster_tool.ainvoke({"team_id": 147})
                
                logger.info(f"결과 타입: {type(result)}")
                if isinstance(result, list):
                    logger.info(f"리스트 길이: {len(result)}")
                    if result:
                        logger.info(f"첫 번째 항목: {result[0]}")
                elif isinstance(result, dict):
                    logger.info(f"딕셔너리 키: {list(result.keys())}")
                else:
                    logger.info(f"기타 타입 결과: {result}")
                    
            except Exception as e:
                logger.error(f"툴 실행 중 오류: {e}")
        
        logger.info("\nMCP 툴 테스트 완료!")
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        logger.error("MLB API MCP 서버가 실행 중인지 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools()) 