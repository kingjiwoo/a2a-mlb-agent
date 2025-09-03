import json
import os
import time
from typing import Dict, List

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage


def _serialize_message(msg: BaseMessage) -> Dict:
    if isinstance(msg, HumanMessage):
        role = "human"
    elif isinstance(msg, AIMessage):
        role = "ai"
    elif isinstance(msg, SystemMessage):
        role = "system"
    else:
        role = msg.type or "unknown"
    return {"role": role, "content": msg.content}


def _deserialize_message(data: Dict) -> BaseMessage:
    role = data.get("role")
    content = data.get("content", "")
    if role == "human":
        return HumanMessage(content=content)
    if role == "ai":
        return AIMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    # fallback
    return HumanMessage(content=content)


class RedisChatHistory(BaseChatMessageHistory):
    """간단한 Redis 기반 채팅 히스토리.

    구조: key_prefix:session_id -> JSON list of messages
    """

    def __init__(self, client, key: str):
        self.client = client
        self.key = key

    def add_message(self, message: BaseMessage) -> None:
        existing = self.client.get(self.key)
        arr: List[Dict] = json.loads(existing) if existing else []
        arr.append(_serialize_message(message))
        self.client.set(self.key, json.dumps(arr))

    def clear(self) -> None:
        self.client.delete(self.key)

    @property
    def messages(self) -> List[BaseMessage]:
        existing = self.client.get(self.key)
        arr: List[Dict] = json.loads(existing) if existing else []
        return [_deserialize_message(x) for x in arr]

    def add_messages(self, messages: List[BaseMessage]) -> None:  # optional perf helper
        existing = self.client.get(self.key)
        arr: List[Dict] = json.loads(existing) if existing else []
        arr.extend(_serialize_message(m) for m in messages)
        self.client.set(self.key, json.dumps(arr))


class ConversationMemoryStore:
    """세션별 히스토리 저장소 (인메모리/Redis 선택)."""

    def __init__(self):
        self._inmemory: Dict[str, InMemoryChatMessageHistory] = {}
        self._backend = os.getenv("MEMORY_BACKEND", "auto").lower()
        self._redis = None

        if self._backend in ("auto", "redis") and os.getenv("REDIS_URL"):
            try:
                import redis  # type: ignore
                self._redis = redis.Redis.from_url(os.getenv("REDIS_URL"))
                # ping to ensure availability
                self._redis.ping()
                self._backend = "redis"
            except Exception:
                self._redis = None
                if self._backend == "redis":
                    # explicit redis request but not available
                    raise
                self._backend = "memory"
        else:
            self._backend = "memory"

    def get_history(self, session_id: str) -> BaseChatMessageHistory:
        if not session_id:
            session_id = "default"

        if self._backend == "redis" and self._redis is not None:
            key = f"mlb_agent:chat_history:{session_id}"
            return RedisChatHistory(self._redis, key)

        # memory backend
        if session_id not in self._inmemory:
            self._inmemory[session_id] = InMemoryChatMessageHistory()
        return self._inmemory[session_id]

