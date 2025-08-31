import os
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message
from a2a.utils import new_agent_text_message

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

class MCPToolWrapper(BaseTool):
    """MCP 툴을 LangChain 형식에 맞게 래핑하는 클래스"""
    
    def __init__(self, mcp_tool, **kwargs):
        # MCP 툴에서 name과 description 추출
        tool_name = getattr(mcp_tool, 'name', 'unknown_tool')
        tool_description = getattr(mcp_tool, 'description', 'MCP tool description not available')
        
        # BaseTool 초기화
        super().__init__(
            name=tool_name,
            description=tool_description,
            **kwargs
        )
        
        # MCP 툴 인스턴스 저장
        self._mcp_tool = mcp_tool
        
    def _run(self, *args, **kwargs) -> Any:
        """동기 실행 (BaseTool 요구사항)"""
        import asyncio
        try:
            # 비동기 실행을 동기적으로 래핑
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 실행 중인 루프가 있으면 새 스레드에서 실행
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(*args, **kwargs))
                    return future.result()
            else:
                return loop.run_until_complete(self._arun(*args, **kwargs))
        except Exception as e:
            logger.error(f"툴 {self.name} 동기 실행 중 오류: {e}")
            return {"error": str(e), "type": "error"}
        
    async def _arun(self, *args, **kwargs) -> Any:
        """비동기 실행"""
        try:
            logger.info(f"툴 {self.name} 실행 중...")
            result = await self._mcp_tool.ainvoke(*args, **kwargs)
            
            # 리스트 결과를 딕셔너리로 변환 (더 강력한 변환)
            if isinstance(result, list):
                logger.info(f"툴 {self.name}에서 {len(result)}개 항목 반환")
                
                # 리스트가 비어있는 경우
                if not result:
                    return {
                        "type": "list",
                        "count": 0,
                        "items": [],
                        "summary": "데이터가 없습니다."
                    }
                
                # 첫 번째 항목의 구조를 분석하여 스키마 생성
                first_item = result[0]
                if isinstance(first_item, dict):
                    # 주요 필드들 추출
                    sample_fields = {}
                    for key, value in first_item.items():
                        if value is not None and key in ['fullname', 'id', 'primaryposition', 'status']:
                            sample_fields[key] = type(value).__name__
                    
                    return {
                        "type": "list",
                        "count": len(result),
                        "items": result,
                        "summary": f"총 {len(result)}개의 항목이 반환되었습니다.",
                        "schema": {
                            "item_type": "dict",
                            "sample_fields": sample_fields,
                            "total_items": len(result)
                        }
                    }
                else:
                    # 리스트 항목이 딕셔너리가 아닌 경우
                    return {
                        "type": "list",
                        "count": len(result),
                        "items": result,
                        "summary": f"총 {len(result)}개의 항목이 반환되었습니다.",
                        "item_type": type(result[0]).__name__ if result else "unknown"
                    }
                    
            elif isinstance(result, dict):
                logger.info(f"툴 {self.name}에서 딕셔너리 반환")
                return result
            elif result is None:
                logger.info(f"툴 {self.name}에서 None 반환")
                return {"result": None, "message": "데이터가 없습니다."}
            else:
                logger.info(f"툴 {self.name}에서 기타 타입 반환: {type(result)}")
                return {"result": str(result), "type": type(result).__name__}
                
        except Exception as e:
            logger.error(f"툴 {self.name} 실행 중 오류: {e}")
            return {
                "error": str(e),
                "type": "error",
                "message": "툴 실행 중 오류가 발생했습니다.",
                "tool_name": self.name
            }

class MLBTransferAgent:
    """MLB 이적 전문 에이전트 - create_react_agent 기반"""
    
    def __init__(self):
        # 환경변수에서 API 키 확인
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        
        # LLM 초기화
        self.llm = ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_retries=3,
            temperature=0
        )
        
        # MCP 클라이언트 초기화
        self.mcp_client = MultiServerMCPClient(
            {
                "mlb": {
                    "transport": "streamable_http",
                    "url": "http://localhost:8000/mcp/",
                }
            }
        )
        
        # 프롬프트 로드
        self.prompts = self._load_prompts()
        
        # 툴과 에이전트 초기화
        self.tools = None
        self.agent = None
        logger.info("MLB 이적 전문 에이전트 초기화 완료")

    def _load_prompts(self) -> Dict[str, str]:
        """프롬프트 파일들을 로드합니다."""
        prompts = {}
        prompt_dir = "prompts"
        
        try:
            # 시스템 프롬프트
            with open(f"{prompt_dir}/system_prompt.txt", "r", encoding="utf-8") as f:
                prompts["system"] = f.read()
            
            # 구단 관계자 프롬프트
            with open(f"{prompt_dir}/club_official_prompt.txt", "r", encoding="utf-8") as f:
                prompts["club_official"] = f.read()
            
            # 선수 프롬프트
            with open(f"{prompt_dir}/player_prompt.txt", "r", encoding="utf-8") as f:
                prompts["player"] = f.read()
            
            # 팬 프롬프트
            with open(f"{prompt_dir}/fan_prompt.txt", "r", encoding="utf-8") as f:
                prompts["fan"] = f.read()
                
            logger.info("프롬프트 파일 로드 완료")
            
        except FileNotFoundError as e:
            logger.warning(f"프롬프트 파일을 찾을 수 없습니다: {e}")
            # 기본 프롬프트 설정
            prompts["system"] = "당신은 MLB 이적 전문가입니다."
            prompts["club_official"] = "구단 관계자를 위한 선수 영입 제안을 제공하세요."
            prompts["player"] = "선수를 위한 커리어 발전 상담을 제공하세요."
            prompts["fan"] = "팬을 위한 이적 이유 설명을 제공하세요."
        
        return prompts

    async def _initialize_agent(self):
        """MCP 툴을 로드하고 create_react_agent를 초기화합니다."""
        if self.tools is None:
            try:
                logger.info("MCP 툴 로드 중...")
                raw_tools = await self.mcp_client.get_tools()
                logger.info(f"원시 MCP 툴 {len(raw_tools)}개 발견")
                
                # raw_tools가 리스트인 경우 딕셔너리로 변환
                if isinstance(raw_tools, list):
                    logger.info("MCP 툴을 딕셔너리 형태로 변환 중...")
                    tools_dict = {}
                    for i, tool in enumerate(raw_tools):
                        if hasattr(tool, 'name'):
                            tools_dict[tool.name] = tool
                        else:
                            tools_dict[f"tool_{i}"] = tool
                    raw_tools = tools_dict
                    logger.info(f"변환 완료: {len(raw_tools)}개 툴")
                
                # MCP 툴들을 LangChain 툴로 래핑
                self.tools = []
                if raw_tools:
                    logger.info(f"총 {len(raw_tools)}개의 툴을 래핑 중...")
                    
                    for tool_name, mcp_tool in raw_tools.items():
                        try:
                            # MCP 툴의 필수 속성 확인
                            if hasattr(mcp_tool, 'name') and hasattr(mcp_tool, 'description'):
                                wrapped_tool = MCPToolWrapper(mcp_tool)
                                self.tools.append(wrapped_tool)
                                logger.info(f"✅ 툴 {tool_name} 래핑 성공")
                            else:
                                logger.warning(f"⚠️ 툴 {tool_name}에 필수 속성이 없어 건너뜀")
                        except Exception as e:
                            logger.error(f"❌ 툴 {tool_name} 래핑 중 오류: {e}")
                            continue
                    
                    logger.info(f"총 {len(self.tools)}개의 툴이 성공적으로 래핑되었습니다.")
                else:
                    logger.warning("⚠️ 사용 가능한 MCP 툴이 없습니다.")
                
                # create_react_agent 생성
                self._create_react_agent()
                
            except Exception as e:
                logger.error(f"에이전트 초기화 중 오류: {e}")
                logger.info("기본 create_react_agent 생성 (툴 없이)")
                self._create_react_agent()

    def _create_react_agent(self):
        """create_react_agent를 생성합니다."""
        logger.info("create_react_agent 생성 중...")
        
        if self.tools:
            # 툴이 있는 경우 ReAct 에이전트 사용
            self.agent = create_react_agent(
                model=self.llm, 
                tools=self.tools
            )
        else:
            # 툴이 없는 경우 기본 에이전트
            self.agent = create_react_agent(
                model=self.llm, 
                tools=[]
            )
        
        logger.info("create_react_agent 생성 완료")

    async def invoke(self, user_message: str) -> str:
        """사용자 메시지를 처리하고 응답을 반환합니다."""
        try:
            # 에이전트 초기화
            await self._initialize_agent()
            
            # 사용자 의도에 따른 프롬프트 선택
            enhanced_message = self._enhance_message_with_prompt(user_message)
            
            # create_react_agent 실행
            logger.info("create_react_agent 실행 중...")
            response = await self.agent.ainvoke(
                {"messages": [("user", enhanced_message)]}
            )
            
            result = response["messages"][-1].content
            logger.info("에이전트 응답 생성 완료")
            return result
            
        except Exception as e:
            error_msg = f"에이전트 실행 중 오류가 발생했습니다: {str(e)}"
            logger.error(error_msg)
            
            # 재귀 제한 오류인 경우 특별한 안내 메시지
            if "Recursion limit" in str(e) or "GraphRecursionError" in str(e):
                return (
                    "MLB 데이터 분석 중 복잡한 요청으로 인해 처리 시간이 초과되었습니다. "
                    "더 구체적이고 간단한 질문으로 다시 시도해주세요. "
                    "예: '양키스의 주요 선수는 누구인가요?' 또는 '다저스의 2024년 성적은?'"
                )
            
            # 툴 관련 오류인 경우
            if "ToolException" in str(e) or "structured_content" in str(e):
                return (
                    "MLB 데이터 조회 중 툴 실행 오류가 발생했습니다. "
                    "잠시 후 다시 시도하거나 다른 질문을 해주세요. "
                    "예: '양키스 팀 정보' 또는 'MLB 주요 선수들'"
                )
            
            # 타임아웃 오류인 경우
            if "timeout" in str(e).lower():
                return (
                    "MLB 데이터 분석에 시간이 너무 오래 걸렸습니다. "
                    "더 간단한 질문으로 다시 시도해주세요."
                )
            
            return error_msg

    def _enhance_message_with_prompt(self, user_message: str) -> str:
        """사용자 메시지에 적절한 프롬프트를 추가합니다."""
        # 시스템 프롬프트로 시작
        enhanced_message = f"{self.prompts['system']}\n\n"
        
        # 사용자 메시지 분석하여 적절한 프롬프트 추가
        message_lower = user_message.lower()
        
        if any(keyword in message_lower for keyword in ["영입", "보강", "계약", "투수진", "타선"]):
            enhanced_message += f"{self.prompts['club_official']}\n\n"
            enhanced_message += f"사용자 질문: {user_message}\n\n"
            enhanced_message += "위의 구단 관계자 플로우에 따라 응답해주세요."
            
        elif any(keyword in message_lower for keyword in ["커리어", "발전", "새로운 도전", "이적 고려"]):
            enhanced_message += f"{self.prompts['player']}\n\n"
            enhanced_message += f"사용자 질문: {user_message}\n\n"
            enhanced_message += "위의 선수 플로우에 따라 응답해주세요."
            
        elif any(keyword in message_lower for keyword in ["떠난다", "떠나는", "이유", "아쉽", "이해"]):
            enhanced_message += f"{self.prompts['fan']}\n\n"
            enhanced_message += f"사용자 질문: {user_message}\n\n"
            enhanced_message += "위의 팬 플로우에 따라 응답해주세요."
            
        else:
            # 기본적으로 구단 관계자 플로우 사용
            enhanced_message += f"{self.prompts['club_official']}\n\n"
            enhanced_message += f"사용자 질문: {user_message}\n\n"
            enhanced_message += "위의 구단 관계자 플로우에 따라 응답해주세요."
        
        return enhanced_message

class MLBTransferAgentExecutor(A2AAgentExecutor):
    """MLB 이적 전문 에이전트 실행자"""
    
    def __init__(self):
        super().__init__()
        self.agent = MLBTransferAgent()
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> str:
        """에이전트를 실행합니다."""
        try:
            # 사용자 메시지 추출
            user_message = context.messages[-1].content if context.messages else "안녕하세요"
            
            # 에이전트 실행
            response = await self.agent.invoke(user_message)
            
            return response
            
        except Exception as e:
            logger.error(f"에이전트 실행 중 오류: {e}")
            return f"에이전트 실행 중 오류가 발생했습니다: {str(e)}" 
        
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """에이전트 실행을 취소합니다."""
        try:
            logger.info("에이전트 실행 취소 요청됨")
            # 필요한 정리 작업 수행
            if hasattr(self.agent, 'cancel'):
                await self.agent.cancel()
            logger.info("에이전트 실행 취소 완료")
        except Exception as e:
            logger.error(f"에이전트 실행 취소 중 오류: {e}") 
        