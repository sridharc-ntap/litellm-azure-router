import asyncio
import os
from typing import Any, AsyncIterator, Dict, Optional
from openai import AsyncAzureOpenAI

from .base import BaseAdapter

class AzureAdapterError(RuntimeError):
    status_code = 502

class AzureAdapter(BaseAdapter):
    name = "azure"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: str = "2024-02-01",
        azure_deployment: Optional[str] = None,
        request_timeout: float = 30.0,
        max_retries: int = 2,
        retry_base_delay: float = 0.5,
    ):
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("AZURE_OPENAI_API_BASE")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.azure_deployment = azure_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        self.request_timeout = request_timeout
        self.max_retries = max(0, max_retries)
        self.retry_base_delay = max(0.0, retry_base_delay)

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
            timeout=self.request_timeout,
            max_retries=0,
        )

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        status_code = getattr(error, "status_code", None)
        error_name = type(error).__name__
        return (
            status_code == 408
            or status_code == 429
            or isinstance(status_code, int) and 500 <= status_code < 600
            or error_name in {"APITimeoutError", "APIConnectionError"}
        )

    async def _create_completion(self, **kwargs: Any) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                return await self.client.chat.completions.create(**kwargs)
            except Exception as exc:
                if attempt >= self.max_retries or not self._is_retryable(exc):
                    raise AzureAdapterError("Azure OpenAI request failed") from exc
                await asyncio.sleep(self.retry_base_delay * (2 ** attempt))

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        model_name = payload.get("model") or self.azure_deployment
        response = await self._create_completion(
            model=model_name,
            messages=payload.get("messages", []),
            temperature=payload.get("temperature", 0.0),
            max_tokens=payload.get("max_tokens", 1024),
            top_p=payload.get("top_p", 1.0),
            stream=False,
        )
        # model_dump returns a serializable dict for the response object
        return response.model_dump()

    async def stream_chat_completions(self, payload: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        model_name = payload.get("model") or self.azure_deployment
        stream = await self._create_completion(
            model=model_name,
            messages=payload.get("messages", []),
            temperature=payload.get("temperature", 0.0),
            max_tokens=payload.get("max_tokens", 1024),
            top_p=payload.get("top_p", 1.0),
            stream=True,
        )

        try:
            async for chunk in stream:
                choice = chunk.choices[0]
                delta = getattr(choice.delta, "content", None) or ""
                role = getattr(choice.delta, "role", None)
                yield {"delta": delta, "role": role, "provider": self.name, "done": False}
        except Exception as exc:
            raise AzureAdapterError("Azure OpenAI stream failed") from exc

        yield {"delta": "", "role": None, "provider": self.name, "done": True}
