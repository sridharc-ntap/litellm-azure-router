import os
from typing import Any, Dict, AsyncIterator, Optional
from openai import AsyncAzureOpenAI

from .base import BaseAdapter

class AzureAdapter(BaseAdapter):
    name = "azure"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: str = "2024-02-01",
        azure_deployment: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("AZURE_OPENAI_API_BASE")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.azure_deployment = azure_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT")

        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required")
        if not self.api_base:
            raise ValueError("AZURE_OPENAI_API_BASE is required")
        if not self.azure_deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT is required")

        # AsyncAzureOpenAI is provided by the `openai` package with azure support
        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.api_base,
            api_version=self.api_version,
        )

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        model_name = payload.get("model") or self.azure_deployment
        response = await self.client.chat.completions.create(
            model=model_name,
            messages=payload.get("messages", []),
            temperature=payload.get("temperature", 0.0),
            max_tokens=payload.get("max_tokens", 1024),
            top_p=payload.get("top_p", 1.0),
            stream=False,
        )
        # model_dump returns a serializable dict for the response object
        return response.model_dump()

    async def stream_chat_completions(self, payload: Dict[str, Any]) -> AsyncIterator[str]:
        model_name = payload.get("model") or self.azure_deployment
        stream = await self.client.chat.completions.create(
            model=model_name,
            messages=payload.get("messages", []),
            temperature=payload.get("temperature", 0.0),
            max_tokens=payload.get("max_tokens", 1024),
            top_p=payload.get("top_p", 1.0),
            stream=True,
        )

        async for chunk in stream:
            # Azure streaming chunk model: chunk.choices[0].delta.content
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                yield delta
