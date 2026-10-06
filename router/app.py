import json
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .adapters.azure_adapter import AzureAdapterError
from .adapters.registry import AdapterRegistry

app = FastAPI(title="LiteLLM Router")

class ChatRequest(BaseModel):
    model: str
    messages: list
    temperature: float | None = 0.0
    max_tokens: int | None = 256

def get_registry():
    return AdapterRegistry.get_instance()

def format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"

@app.on_event("shutdown")
async def close_adapters():
    await get_registry().close()

@app.post("/v1/chat")
async def chat(req: ChatRequest, x_provider: str | None = Header(default=None, alias="X-Provider")):
    registry = get_registry()
    provider = x_provider or registry.default_provider
    adapter = registry.get(provider)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    try:
        result = await adapter.chat_completions(req.model_dump())
        return result
    except AzureAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/v1/chat/stream")
async def chat_stream(req: ChatRequest, x_provider: str | None = Header(default=None, alias="X-Provider")):
    registry = get_registry()
    provider = x_provider or registry.default_provider
    adapter = registry.get(provider)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    async def event_generator():
        try:
            async for chunk in adapter.stream_chat_completions(req.model_dump()):
                yield format_sse(chunk)
        except AzureAdapterError as exc:
            yield format_sse({"error": str(exc), "provider": provider, "done": True})
        except Exception as exc:
            yield format_sse({"error": str(exc), "provider": provider, "done": True})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
