import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from router.adapters.azure_adapter import AzureAdapter

@pytest.mark.asyncio
async def test_azure_adapter_chat_completions():
    fake_response = MagicMock()
    fake_response.model_dump.return_value = {
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "hello from azure"}}],
    }

    with patch("router.adapters.azure_adapter.AsyncAzureOpenAI") as mock_client_cls:
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
            delta = MagicMock()
            delta.content = content
            delta.role = None
            self.choices = [MagicMock(delta=delta)]

    async def fake_stream():
        yield FakeChunk("hello")
        yield FakeChunk(" world")

    with patch("router.adapters.azure_adapter.AsyncAzureOpenAI") as mock_client_cls:
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

        assert chunks == [
            {"delta": "hello", "role": None, "provider": "azure", "done": False},
            {"delta": " world", "role": None, "provider": "azure", "done": False},
            {"delta": "", "role": None, "provider": "azure", "done": True},
        ]

@pytest.mark.asyncio
async def test_azure_adapter_closes_client():
    with patch("router.adapters.azure_adapter.AsyncAzureOpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.aclose = AsyncMock()

        adapter = AzureAdapter(
            api_key="test-key",
            api_base="https://example.openai.azure.com",
            azure_deployment="gpt-4o",
        )

        await adapter.close()

        mock_client.aclose.assert_awaited_once_with()

@pytest.mark.asyncio
async def test_azure_adapter_retries_transient_errors():
    class TransientError(Exception):
        status_code = 503

    fake_response = MagicMock()
    fake_response.model_dump.return_value = {"choices": []}

    with patch("router.adapters.azure_adapter.AsyncAzureOpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[TransientError(), fake_response]
        )

        adapter = AzureAdapter(
            api_key="test-key",
            api_base="https://example.openai.azure.com",
            azure_deployment="gpt-4o",
            retry_base_delay=0,
        )

        result = await adapter.chat_completions({"messages": []})

        assert result == {"choices": []}
        assert mock_client.chat.completions.create.await_count == 2
        mock_client_cls.assert_called_once_with(
            api_key="test-key",
            azure_endpoint="https://example.openai.azure.com",
            api_version="2024-02-01",
            timeout=30.0,
            max_retries=0,
        )
