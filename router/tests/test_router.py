import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from router.app import app
from router.adapters.registry import AdapterRegistry
from router.adapters.mock_adapter import MockAdapter

@pytest.fixture(autouse=True)
def ensure_mock_registry(monkeypatch):
    # create a registry with only MockAdapter
    reg = AdapterRegistry()
    reg.adapters = {}
    reg.default_provider = "mock"
    reg.register(MockAdapter())
    # override the singleton instance
    monkeypatch.setattr("router.adapters.registry.AdapterRegistry._instance", reg)
    yield

@pytest.mark.asyncio
async def test_chat_default_provider():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"model": "gpt-4o", "messages":[{"role":"user","content":"hello"}]}
        r = await ac.post("/v1/chat", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "choices" in data
        assert data["choices"][0]["message"]["content"].startswith("echo")

@pytest.mark.asyncio
async def test_chat_stream_returns_sse_events():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]}
        response = await ac.post("/v1/chat/stream", json=payload)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert '"provider": "mock"' in response.text
        assert '"done": true' in response.text

@pytest.mark.asyncio
async def test_registry_closes_adapters():
    reg = AdapterRegistry()
    close = AsyncMock()
    adapter = MockAdapter()
    adapter.close = close
    reg.register(adapter)

    await reg.close()

    close.assert_awaited_once_with()
