import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from adapters.azure_adapter import AzureAdapter

@pytest.mark.asyncio
async def test_azure_adapter_chat_completions():
    fake_response = MagicMock()
    fake_response.model_dump.return_value = {
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "hello from azure"}}],
    }

    with patch("adapters.azure_adapter.AsyncAzureOpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # set nested async method
        mock_client.chat.completions.create = AsyncMock(return_value=fake_response)

        adapter = AzureAdapter(
            api_key="test-key",
            api_base="https://example.openai.azure.com",
            api_version="2024-02-01",
            azure_deployment="gpt-4o",
        )

        result = await adapter.chat_completions({
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
        })

        assert result["choices"][0]["message"]["content"] == "hello from azure"

@pytest.mark.asyncio
async def test_azure_adapter_streaming():
    class FakeChunk:
        def __init__(self, content):
            self.choices = [MagicMock(delta=MagicMock(content=content))]

    async def fake_stream():
        yield FakeChunk("hello")
        yield FakeChunk(" world")

    with patch("adapters.azure_adapter.AsyncAzureOpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=fake_stream())

        adapter = AzureAdapter(
            api_key="test-key",
            api_base="https://example.openai.azure.com",
            api_version="2024-02-01",
            azure_deployment="gpt-4o",
        )

        chunks = []
        async for chunk in adapter.stream_chat_completions({
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
        }):
            chunks.append(chunk)

        assert chunks == ["hello", " world"]
