# LiteLLM SDK Router (Azure adapter example)

This repository contains a small FastAPI router that routes chat requests to provider adapters.
It includes an Azure OpenAI adapter with streaming support, a mock adapter for tests, and CI.

Quick start (local)
1. Create a Python venv and install deps:
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt

2. Set environment variables (see .env.example) or export real Azure values:
   export AZURE_OPENAI_API_KEY="..."
   export AZURE_OPENAI_API_BASE="https://<resource>.openai.azure.com"
   export AZURE_OPENAI_DEPLOYMENT="gpt-4o"

3. Run the server:
   uvicorn router.app:app --reload --port 8000

4. Call the API:
   curl -X POST "http://localhost:8000/v1/chat" -H "Content-Type: application/json" -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hello"}]}'

Run tests:
   pytest -q

Notes
- For production you should supply secrets via Kubernetes Secrets or a secret manager rather than env vars.
- The Azure adapter uses the `openai` Python package AsyncAzureOpenAI client. Adjust if you use other SDK versions.
