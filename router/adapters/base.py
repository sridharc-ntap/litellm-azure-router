from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict

class BaseAdapter(ABC):
    name: str

    @abstractmethod
    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def stream_chat_completions(self, payload: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Providers may stream token deltas. The fallback emits one structured completion
        event so clients can use the same protocol for every provider.
        """
        result = await self.chat_completions(payload)
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        role = result.get("choices", [{}])[0].get("message", {}).get("role")
        yield {"delta": content, "role": role, "provider": self.name, "done": False}
        yield {"delta": "", "role": None, "provider": self.name, "done": True}
