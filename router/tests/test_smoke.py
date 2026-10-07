import os
import requests
import pytest

ROUTER_URL = os.environ.get("ROUTER_URL", "http://litellm-router.llm-proxy.svc.cluster.local")

def test_smoke_chat():
    payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "smoke test"}]}
    r = requests.post(f"{ROUTER_URL}/v1/chat", json=payload, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "choices" in data