import json
import logging
import time
from uuid import uuid4
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from .adapters.azure_adapter import AzureAdapterError
from .adapters.registry import AdapterRegistry

app = FastAPI(title="LiteLLM Router")
logger = logging.getLogger("lite_llm_router")
request_counter = Counter(
    "router_requests_total",
    "Total HTTP requests handled by the router.",
    ["method", "path", "status"],
)
request_latency = Histogram(
    "router_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
)
provider_counter = Counter(
    "router_provider_calls_total",
    "Total provider adapter calls.",
    ["provider", "operation", "status"],
)
provider_latency = Histogram(
    "router_provider_duration_seconds",
    "Provider adapter call duration in seconds.",
    ["provider", "operation"],
)

class ChatRequest(BaseModel):
    model: str
    messages: list
    temperature: float | None = 0.0
    max_tokens: int | None = 256

def get_registry():
    return AdapterRegistry.get_instance()

def format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"

@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request failed request_id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise

    elapsed = time.perf_counter() - started
    response.headers["X-Request-ID"] = request_id
    request_counter.labels(request.method, request.url.path, str(response.status_code)).inc()
    request_latency.labels(request.method, request.url.path).observe(elapsed)
    logger.info(
        "request complete request_id=%s method=%s path=%s status=%s latency_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed * 1000,
    )
    return response

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "providers": get_registry().list()}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

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
    started = time.perf_counter()
    try:
        result = await adapter.chat_completions(req.model_dump())
        provider_counter.labels(provider, "chat", "success").inc()
        return result
    except AzureAdapterError as exc:
        provider_counter.labels(provider, "chat", "error").inc()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        provider_counter.labels(provider, "chat", "error").inc()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        provider_latency.labels(provider, "chat").observe(time.perf_counter() - started)

@app.post("/v1/chat/stream")
async def chat_stream(req: ChatRequest, x_provider: str | None = Header(default=None, alias="X-Provider")):
    registry = get_registry()
    provider = x_provider or registry.default_provider
    adapter = registry.get(provider)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    async def event_generator():
        started = time.perf_counter()
        try:
            async for chunk in adapter.stream_chat_completions(req.model_dump()):
                yield format_sse(chunk)
            provider_counter.labels(provider, "stream", "success").inc()
        except AzureAdapterError as exc:
            provider_counter.labels(provider, "stream", "error").inc()
            yield format_sse({"error": str(exc), "provider": provider, "done": True})
        except Exception as exc:
            provider_counter.labels(provider, "stream", "error").inc()
            yield format_sse({"error": str(exc), "provider": provider, "done": True})
        finally:
            provider_latency.labels(provider, "stream").observe(time.perf_counter() - started)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
