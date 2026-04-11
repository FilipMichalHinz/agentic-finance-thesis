# Vertex Gemini Setup

This repository is configured to run Gemini through Vertex AI.

Recommended auth method: Application Default Credentials (ADC).

## What The Repo Uses

- Shared Google/Vertex config lives in `src/integrations/google_genai.py`
- Agent LLM construction is centralized there via `build_default_agent_llm(...)`
- Raw Google client construction is also centralized there via `build_genai_client(...)`
- In Vertex mode, the repo prefers ADC by default
- `VERTEX_API_KEY` is supported, but is optional and not the recommended path

## `.env` Setup

Add these values to `.env`:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=agentic-ai-finance
GOOGLE_CLOUD_LOCATION=us-central1
```

Do not put shell commands in `.env`.

Do not put these in `.env`:

- `export ...`
- `gcloud auth application-default login`

If you want to force pure Vertex via ADC, do not set:

```dotenv
GOOGLE_API_KEY=
GEMINI_API_KEY=
VERTEX_API_KEY=
```

## One-Time Local Auth Setup

Run these in your terminal:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project agentic-ai-finance
gcloud auth application-default set-quota-project agentic-ai-finance
```

Notes:

- `gcloud auth login` sets the CLI account
- `gcloud auth application-default login` sets the ADC account used by Python libraries
- These can be different accounts, which causes confusing failures
- Make sure both use the Google account that has access to the Vertex project

If `set-quota-project` fails, the logged-in account is missing permission on the project.
The common missing permission is `serviceusage.services.use`.

## Python Environment

Use the project virtualenv:

```bash
source venv/bin/activate
```

or run commands directly with:

```bash
venv/bin/python ...
```

## Connection Smoke Test

Run:

```bash
venv/bin/python debug-models.py
```

Expected success signals:

- `Backend: Vertex AI`
- `Using Application Default Credentials`
- `Generation succeeded with gemini-2.5-flash`
- `Embeddings succeeded with gemini-embedding-001`

The line below is not a failure by itself:

- `No chat-capable models were returned for this backend`

That listing is less reliable on Vertex than an actual generation call. The generation and embedding checks are the real smoke tests.

## End-To-End App Test

Run:

```bash
venv/bin/python main.py
```

If the setup is correct, the graph should complete agent nodes and finish with:

```text
Simulation Complete.
```

## How To Prove It Is Vertex, Not Gemini Developer API

In the same terminal where you run the app:

```bash
unset GOOGLE_API_KEY
unset GEMINI_API_KEY
unset VERTEX_API_KEY
```

Then check the resolved settings:

```bash
venv/bin/python - <<'PY'
from src.integrations.google_genai import resolve_google_genai_settings
print(resolve_google_genai_settings())
PY
```

For pure Vertex + ADC, the result should look like:

```python
GoogleGenAISettings(
    vertexai=True,
    api_key=None,
    project='agentic-ai-finance',
    location='us-central1',
)
```

The important part is:

- `vertexai=True`
- `api_key=None`

That means the repo is using Vertex with ADC, not a Gemini Developer API key.

## Troubleshooting

### `No module named 'langchain_google_genai'`

Install the missing package in the venv:

```bash
venv/bin/pip install "langchain-google-genai>=4.0.0"
```

### `aiplatform.googleapis.com API requires a quota project`

Set the quota project:

```bash
gcloud auth application-default set-quota-project agentic-ai-finance
```

If that fails, the logged-in account does not have the needed permission on the project.

### Wrong Google account is being used

Check accounts:

```bash
gcloud auth list
```

If needed, reset and log in again:

```bash
gcloud auth logout
gcloud auth application-default revoke
gcloud auth login
gcloud auth application-default login
```

## Current Default Models

- Agent model: `gemini-2.5-flash`
- Embedding model: `gemini-embedding-001`

The agent model can be overridden with:

```dotenv
GOOGLE_LLM_MODEL=gemini-2.5-flash
```
