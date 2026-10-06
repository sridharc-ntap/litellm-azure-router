from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAdapter(ABC):
    name: str

    @abstractmethod
    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def stream_chat_completions(self, payload):
        """
        Optional: providers that support streaming should implement this as an async iterator.
        Default implementation falls back to non-streaming behaviour.
        """
        result = await self.chat_completions(payload)
        # naive fallback: yield final content once
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        yield content
