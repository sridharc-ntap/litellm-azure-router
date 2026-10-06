import inspect
import os
from typing import Any, Mapping, Optional
from .mock_adapter import MockAdapter
from .azure_adapter import AzureAdapter

class AdapterRegistry:
    _instance = None

    def __init__(self, adapters: Optional[Mapping[str, Any]] = None, config: Optional[Mapping[str, Any]] = None):
        self.adapters = {}
        self.default_provider = "mock"
        self.config = dict(config or {})
        if adapters:
            for adapter in adapters.values():
                self.register(adapter)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._bootstrap()
        return cls._instance

    def _bootstrap(self):
        if self.adapters:
            return
        self.register(MockAdapter())

        azure_config = dict(self.config.get("azure", {}))
        azure_config.setdefault("api_key", os.getenv("AZURE_OPENAI_API_KEY"))
        azure_config.setdefault("api_base", os.getenv("AZURE_OPENAI_API_BASE"))
        azure_config.setdefault("api_version", os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"))
        azure_config.setdefault("azure_deployment", os.getenv("AZURE_OPENAI_DEPLOYMENT"))
        if azure_config["api_key"] and azure_config["api_base"]:
            az = AzureAdapter(**azure_config)
            self.register(az)
            self.default_provider = "azure"

    def register(self, adapter):
        self.adapters[adapter.name] = adapter

    def get(self, name: str):
        return self.adapters.get(name)

    def list(self):
        return list(self.adapters.keys())

    async def close(self):
        for adapter in self.adapters.values():
            cleanup = getattr(adapter, "async_close", None)
            if cleanup is None:
                cleanup = getattr(adapter, "close", None)
            if cleanup is None:
                continue

            result = cleanup()
            if inspect.isawaitable(result):
                await result
