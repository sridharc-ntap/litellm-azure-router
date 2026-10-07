# LiteLLM SDK Router (Azure adapter example)

This repository contains a small FastAPI router that routes chat requests to provider adapters.
It includes an Azure OpenAI adapter with streaming support, a mock adapter for tests, and CI.

Quick start (local)
1. Create a Python venv and install deps:
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt

   Use Python 3.11 or newer. The pinned FastAPI/Pydantic versions are required for
   current Python typing behavior.

   # Optional development tools
   pip install -r requirements-dev.txt

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
- Streaming responses use Server-Sent Events. Each `data` payload includes `delta`, `role`, `provider`, and `done` fields.
- Azure request timeout and retry settings can be passed to `AzureAdapter` or supplied through injected registry configuration.

Kubernetes deployment contract
- The Jenkins pipeline deploys and smoke-tests in the `llm-proxy` namespace.
- Jenkins must have a Username with password credential named `acr-sp-credentials`. Store the service-principal client ID as the username and its client secret as the password. The pipeline passes these values to `az login`; it does not read ACR credentials from Kubernetes.
- The application Secret is named `azure-openai` by default and is consumed by the Deployment through `envFrom`. It must also exist in `llm-proxy`, unless `azure.secretName` is overridden in Helm values.
- `image.pullSecrets` is empty by default. ACR push authentication for Jenkins does not provide pod image-pull credentials; configure an image pull Secret in the release namespace or use AKS/workload identity separately.
- Argo CD remains the deployment owner: Jenkins pushes the image and updates the GitOps image tag, then Argo CD syncs the chart. Do not run a separate `helm upgrade` from Jenkins for the same release.

Example streaming client:
```bash
curl -N -X POST "http://localhost:8000/v1/chat/stream" \
   -H "Content-Type: application/json" \
   -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hello"}]}'
```

Parse each `data: ...` line as JSON. The final event has `"done": true`.

Operational endpoints
- `GET /healthz` is a readiness probe and reports the registered providers.
- `GET /metrics` exposes Prometheus request and provider-call metrics.
- Every response includes an `X-Request-ID` header. Send your own value with that header to correlate logs across services.

Injected adapter configuration
```python
registry = AdapterRegistry(config={
   "azure": {
      "api_key": "...",
      "api_base": "https://example.openai.azure.com",
      "azure_deployment": "gpt-4o",
      "request_timeout": 20.0,
      "max_retries": 3,
      "retry_base_delay": 0.25,
   }
})
```
Use values loaded from Kubernetes Secrets and ConfigMaps in place of the literals, then install the registry as the application singleton before serving requests. Environment variables remain supported as the default bootstrap path.
