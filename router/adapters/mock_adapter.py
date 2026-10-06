import asyncio
from typing import Dict, Any
from .base import BaseAdapter

class MockAdapter(BaseAdapter):
    name = "mock"

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.01)
        user_text = payload.get("messages", [{}])[-1].get("content", "")
        return {
            "id": "mock-1",
            "object": "chat.completion",
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": f"echo: {user_text}"}}
            ]
        }
