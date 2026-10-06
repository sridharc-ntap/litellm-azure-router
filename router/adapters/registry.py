import os
from .mock_adapter import MockAdapter
from .azure_adapter import AzureAdapter

class AdapterRegistry:
    _instance = None

    def __init__(self):
        self.adapters = {}
        self.default_provider = "mock"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._bootstrap()
        return cls._instance

    def _bootstrap(self):
        self.register(MockAdapter())

        if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_API_BASE"):
            az = AzureAdapter(
                api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                api_base=os.environ.get("AZURE_OPENAI_API_BASE"),
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
            )
            self.register(az)
            self.default_provider = "azure"

    def register(self, adapter):
        self.adapters[adapter.name] = adapter

    def get(self, name: str):
        return self.adapters.get(name)

    def list(self):
        return list(self.adapters.keys())
