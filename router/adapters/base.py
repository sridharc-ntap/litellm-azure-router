from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional, TypedDict

class StreamChunk(TypedDict):
    delta: str
    role: Optional[str]
    provider: str
    done: bool

class BaseAdapter(ABC):
    name: str

    @abstractmethod
    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def stream_chat_completions(self, payload: Dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """
        Yield chunks with ``delta``, ``role``, ``provider``, and ``done`` fields.
        The fallback emits one completion event followed by a terminal event.
        """
        result = await self.chat_completions(payload)
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        role = result.get("choices", [{}])[0].get("message", {}).get("role")
        yield {"delta": content, "role": role, "provider": self.name, "done": False}
        yield {"delta": "", "role": None, "provider": self.name, "done": True}
