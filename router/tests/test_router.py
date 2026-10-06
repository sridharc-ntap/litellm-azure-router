import pytest
from httpx import AsyncClient
from router.app import app
from adapters.registry import AdapterRegistry
from adapters.mock_adapter import MockAdapter

@pytest.fixture(autouse=True)
def ensure_mock_registry(monkeypatch):
    # create a registry with only MockAdapter
    reg = AdapterRegistry()
    reg.adapters = {}
    reg.default_provider = "mock"
    reg.register(MockAdapter())
    # override the singleton instance
    monkeypatch.setattr("adapters.registry.AdapterRegistry._instance", reg)
    yield

@pytest.mark.asyncio
async def test_chat_default_provider():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"model": "gpt-4o", "messages":[{"role":"user","content":"hello"}]}
        r = await ac.post("/v1/chat", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "choices" in data
        assert data["choices"][0]["message"]["content"].startswith("echo")
