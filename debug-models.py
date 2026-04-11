#Just a helper to see what models are available with the current key

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

try:
    from src.integrations.google_genai import (
        DEFAULT_AGENT_MODEL,
        build_genai_client,
        embed_texts,
        resolve_google_genai_settings,
    )
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from src.integrations.google_genai import (
        DEFAULT_AGENT_MODEL,
        build_genai_client,
        embed_texts,
        resolve_google_genai_settings,
    )

load_dotenv()

try:
    settings = resolve_google_genai_settings()
    client = build_genai_client(timeout_seconds=60)
except RuntimeError as exc:
    print(f"❌ CRITICAL: {exc}")
    raise SystemExit(1)

print(f"🔧 Backend: {'Vertex AI' if settings.vertexai else 'Gemini Developer API'}")
if settings.project:
    print(f"📦 Project: {settings.project}")
if settings.api_key:
    print(f"🔑 Key found: {settings.api_key[:5]}...{settings.api_key[-5:]}")
else:
    print("🔐 Using Application Default Credentials")

print("\n🔍 ASKING GOOGLE: 'What models can I use?'")
print("-" * 40)

try:
    found_any = False
    for model in client.models.list():
        supported_actions = getattr(model, "supported_actions", []) or []
        if "generateContent" in supported_actions:
            print(f"✅ AVAILABLE: {model.name}")
            found_any = True

    if not found_any:
        print("⚠️  No chat-capable models were returned for this backend.")
except Exception as e:
    print(f"❌ CONNECTION ERROR: {e}")
    raise SystemExit(1)

chat_model = os.getenv("GOOGLE_LLM_MODEL") or DEFAULT_AGENT_MODEL
print("\n🧪 TESTING GENERATION")
print("-" * 40)
try:
    response = client.models.generate_content(
        model=chat_model,
        contents="Reply with exactly the word pong.",
    )
    response_text = (response.text or "").strip()
    print(f"✅ Generation succeeded with {chat_model}")
    print(f"   Response: {response_text or '[empty text response]'}")
except Exception as e:
    print(f"❌ Generation failed for {chat_model}: {e}")

embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
print("\n🧪 TESTING EMBEDDINGS")
print("-" * 40)
try:
    vectors = embed_texts(
        client,
        ["Vertex connection smoke test"],
        model_name=embedding_model,
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768,
    )
    vector = vectors[0] if vectors else None
    if not vector:
        raise RuntimeError("Embedding response was empty")
    print(f"✅ Embeddings succeeded with {embedding_model}")
    print(f"   Vector size: {len(vector)}")
except Exception as e:
    print(f"❌ Embeddings failed for {embedding_model}: {e}")
