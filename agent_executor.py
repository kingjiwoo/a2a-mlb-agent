import os
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message
from a2a.utils import new_agent_text_message
from memory import ConversationMemoryStore

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
        # Vercel 환경에서는 퍼블릭 URL을 기준으로 자체 마운트된 MCP 엔드포인트(/mlb/mcp/)로 연결
        def _default_mcp_url() -> str:
            # 우선순위 1: 명시적 환경변수
            env_url = os.getenv("MLB_MCP_SERVER_URL")
            if env_url:
                return env_url
            # 우선순위 2: Vercel 배포 URL 자동 구성 (예: a2a-mlb-agent.vercel.app)
            vercel_host = os.getenv("VERCEL_URL")
            if vercel_host:
                scheme = "https://"
                # VERCEL_URL 값이 이미 스킴을 포함한다면 중복 방지
                if vercel_host.startswith("http://") or vercel_host.startswith("https://"):
                    base = vercel_host
                else:
                    base = f"{scheme}{vercel_host}"
                return f"{base}/mlb/mcp"
            # 로컬 개발 기본값
            return "http://localhost:8000/mlb/mcp"

        mcp_url = _default_mcp_url()
        if not mcp_url.endswith('/'):
            mcp_url += "/"
        logger.info(f"MCP URL resolved: {mcp_url}")
        self.mcp_client = MultiServerMCPClient({
            "mlb": {"transport": "streamable_http", "url": mcp_url}
        })
        
        # 프롬프트 로드
        self.prompts = self._load_prompts()

        # 툴과 에이전트 초기화
        self.tools = None
        self.agent = None
        self.agent_with_memory = None
        self._init_lock = asyncio.Lock()
        # 대화 메모리 저장소 (Redis 사용 가능, 미설정 시 메모리)
        self._memory_store = ConversationMemoryStore()
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
        """MCP 툴 로드 + create_react_agent 생성(항상 self.agent 보장)"""
        if self.agent is not None:
            return
        async with self._init_lock:
            if self.agent is not None:  # 다른 코루틴이 먼저 만들었으면 종료
                return
            try:
                logger.info("MCP 연결 및 툴 로드 시작...")
                # 연결 (너무 오래 붙잡지 않도록 짧은 타임아웃)
                try:
                    # 일부 구현은 명시적 연결이 필요 없으므로, 메서드가 없으면 건너뛰고 계속 진행
                    if hasattr(self.mcp_client, 'connect_all'):
                        await asyncio.wait_for(self.mcp_client.connect_all(), timeout=5.0)
                    elif hasattr(self.mcp_client, 'connect'):
                        await asyncio.wait_for(self.mcp_client.connect(), timeout=5.0)
                    else:
                        logger.warning("MCP 클라이언트에 연결 메서드가 없습니다 - 툴 조회로 진행합니다")
                except Exception as ce:
                    logger.warning(f"MCP 연결 실패(무시하고 툴 없이 진행): {ce}")
                    # 연결 실패해도 HTTP 기반 클라이언트는 툴 조회가 가능할 수 있으므로 계속 진행
                
                # 툴 가져오기
                try:
                    raw_tools = None
                    has_any_list_method = any([
                        hasattr(self.mcp_client, 'get_tools'),
                        hasattr(self.mcp_client, 'list_tools'),
                        hasattr(self.mcp_client, 'list_all_tools')
                    ])
                    if not has_any_list_method:
                        logger.warning("MCP 클라이언트에 툴 조회 메서드가 없습니다")
                        self.tools = []
                        return

                    # 다양한 버전 호환: get_tools / list_tools / list_all_tools 등 시도
                    if hasattr(self.mcp_client, 'get_tools'):
                        maybe = self.mcp_client.get_tools()
                        raw_tools = await maybe if asyncio.iscoroutine(maybe) else maybe
                    if not raw_tools and hasattr(self.mcp_client, 'list_tools'):
                        maybe = self.mcp_client.list_tools()
                        raw_tools = await maybe if asyncio.iscoroutine(maybe) else maybe
                    if not raw_tools and hasattr(self.mcp_client, 'list_all_tools'):
                        maybe = self.mcp_client.list_all_tools()
                        raw_tools = await maybe if asyncio.iscoroutine(maybe) else maybe
                        
                    logger.info(f"원시 MCP 툴 {len(raw_tools) if hasattr(raw_tools,'__len__') else 'N/A'}개 발견")
                    
                    # dict/list 모두 허용 → dict로 정규화
                    if isinstance(raw_tools, list):
                        tools_dict = {}
                        for i, tool in enumerate(raw_tools):
                            name = getattr(tool, "name", f"tool_{i}")
                            tools_dict[name] = tool
                        raw_tools = tools_dict
                    
                    # 래핑
                    wrapped = []
                    for tool_name, mcp_tool in (raw_tools or {}).items():
                        if hasattr(mcp_tool, "name") and hasattr(mcp_tool, "description"):
                            try:
                                wrapped.append(MCPToolWrapper(mcp_tool))
                                logger.info(f"✅ 툴 {tool_name} 래핑 성공")
                            except Exception as we:
                                logger.warning(f"툴 {tool_name} 래핑 실패: {we}")
                    self.tools = wrapped
                    
                except Exception as e:
                    logger.error(f"툴 로드 중 오류: {e}")
                    self.tools = []
                    
            except Exception as e:
                logger.error(f"에이전트 초기화 중 오류(툴 없이 진행): {e}")
                self.tools = []
            finally:
                # 어떤 경우에도 agent는 반드시 생성
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
        
        # 메모리 래퍼 구성
        def get_session_history(config) -> BaseChatMessageHistory:
            cfg = (config or {}).get("configurable") or {}
            session_id = cfg.get("session_id") or "default"
            return self._memory_store.get_history(session_id)

        self.agent_with_memory = RunnableWithMessageHistory(
            self.agent,
            get_session_history,
            input_messages_key="messages",
            history_messages_key="messages",
        )

        logger.info("create_react_agent 생성 완료")

    async def invoke(self, user_message: str, session_id: Optional[str] = None) -> str:
        """사용자 메시지를 처리하고 응답을 반환합니다."""
        try:
            # 에이전트 초기화
            await self._initialize_agent()
            if self.agent is None:
                self._create_react_agent()
            
            # 사용자 의도에 따른 프롬프트 선택
            enhanced_message = self._enhance_message_with_prompt(user_message)
            
            # create_react_agent 실행
            logger.info("create_react_agent 실행 중...")
            target = self.agent_with_memory or self.agent
            response = await target.ainvoke(
                {"messages": [HumanMessage(content=enhanced_message)]},
                config={"configurable": {"session_id": session_id or "default"}},
            )
            
            # LangGraph create_react_agent returns a dict with "messages"
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

    async def cancel(self):
        """에이전트 실행을 취소합니다."""
        try:
            logger.info("에이전트 실행 취소 요청됨")
            # 필요한 정리 작업 수행
            if hasattr(self.agent, 'cancel'):
                await self.agent.cancel()
            logger.info("에이전트 실행 취소 완료")
        except Exception as e:
            logger.error(f"에이전트 실행 취소 중 오류: {e}")

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

    def _extract_user_text(self, context: RequestContext) -> str:
        """A2A RequestContext에서 user 텍스트를 안전하게 추출"""
        # 1) 권장: context.message.parts 에서 {kind:"text"} 찾기
        msg = getattr(context, "message", None)
        if msg and getattr(msg, "parts", None):
            for p in msg.parts or []:
                # dict or object 모두 대응
                kind = getattr(p, "kind", None) if not isinstance(p, dict) else p.get("kind")
                if kind == "text":
                    text = getattr(p, "text", None) if not isinstance(p, dict) else p.get("text")
                    if text:
                        return text
        # 2) fallback: message.content (혹시 문자열이면)
        if msg and isinstance(getattr(msg, "content", None), str):
            return msg.content
        # 3) 최후: raw request(dict) 경로로 파싱
        req = getattr(context, "request", None)
        try:
            params = req.get("params") or {}
            parts = (params.get("message") or {}).get("parts") or []
            for p in parts:
                if p.get("kind") == "text" and p.get("text"):
                    return p["text"]
        except Exception:
            pass
        return "안녕하세요"

    def _extract_session_id(self, context: RequestContext) -> str:
        """세션/대화 식별자 추출 (없으면 messageId나 기본값)."""
        # 1) 요청 params에서 시도
        try:
            req = getattr(context, "request", None) or {}
            params = req.get("params") or {}
            for k in ("session_id", "sessionId", "conversation_id", "conversationId"):
                if params.get(k):
                    return str(params.get(k))
        except Exception:
            pass
        # 2) 메시지 ID 활용
        msg = getattr(context, "message", None)
        mid = getattr(msg, "messageId", None)
        if mid:
            return str(mid)
        return "default"
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        try:
            user_text = self._extract_user_text(context)
            session_id = self._extract_session_id(context)
            result_text = await self.agent.invoke(user_text, session_id=session_id)

            msg: Message = new_agent_text_message(result_text)
            await event_queue.enqueue_event(msg)  # ✅ 여기만 호출하면 됨

        except Exception as e:
            logger.exception("에이전트 실행 중 오류")
            await event_queue.enqueue_event(
                new_agent_text_message(f"에이전트 실행 중 오류가 발생했습니다: {e}")
            )

        
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
        
