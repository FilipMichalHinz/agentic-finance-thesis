import os
from dataclasses import dataclass
from typing import List, Optional, Sequence


DEFAULT_VERTEX_LOCATION = "global"
DEFAULT_AGENT_MODEL = "gemini-3-pro-preview"


@dataclass(frozen=True)
class GoogleGenAISettings:
    vertexai: bool
    api_key: Optional[str]
    project: Optional[str]
    location: Optional[str]


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def use_vertexai_backend() -> bool:
    raw = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    if raw is not None:
        return _parse_bool(raw)
    return bool(os.getenv("GOOGLE_CLOUD_PROJECT"))


def _resolve_developer_api_key() -> Optional[str]:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def _resolve_vertex_api_key() -> Optional[str]:
    # In Vertex mode prefer ADC unless a Vertex-specific key is supplied explicitly.
    return os.getenv("VERTEX_API_KEY")


def resolve_google_genai_settings() -> GoogleGenAISettings:
    if use_vertexai_backend():
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise RuntimeError(
                "Missing GOOGLE_CLOUD_PROJECT for Vertex AI. "
                "Set GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_CLOUD_PROJECT, "
                "then authenticate with Application Default Credentials "
                "(recommended) or VERTEX_API_KEY."
            )
        return GoogleGenAISettings(
            vertexai=True,
            api_key=_resolve_vertex_api_key(),
            project=project,
            location=os.getenv("GOOGLE_CLOUD_LOCATION") or DEFAULT_VERTEX_LOCATION,
        )

    api_key = _resolve_developer_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing Google GenAI credentials. "
            "Set GOOGLE_API_KEY (or GEMINI_API_KEY) for Gemini Developer API, "
            "or set GOOGLE_GENAI_USE_VERTEXAI=true with GOOGLE_CLOUD_PROJECT "
            "for Vertex AI."
        )
    return GoogleGenAISettings(
        vertexai=False,
        api_key=api_key,
        project=None,
        location=None,
    )


def build_chat_model(model: str, temperature: float = 0, **kwargs):
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = resolve_google_genai_settings()
    params = {
        "model": model,
        "temperature": temperature,
        **kwargs,
    }
    if settings.vertexai:
        params["vertexai"] = True
        params["project"] = settings.project
        params["location"] = settings.location
        if settings.api_key:
            params["api_key"] = settings.api_key
    else:
        params["api_key"] = settings.api_key
    return ChatGoogleGenerativeAI(**params)


def build_default_agent_llm(temperature: float = 0, **kwargs):
    return build_chat_model(
        model=os.getenv("GOOGLE_LLM_MODEL") or DEFAULT_AGENT_MODEL,
        temperature=temperature,
        **kwargs,
    )


def build_genai_client(timeout_seconds: int = 300):
    from google import genai

    settings = resolve_google_genai_settings()
    params = {
        "http_options": {"timeout": int(timeout_seconds * 1000)},
    }
    if settings.vertexai:
        params["vertexai"] = True
        params["project"] = settings.project
        params["location"] = settings.location
        if settings.api_key:
            params["api_key"] = settings.api_key
    else:
        params["api_key"] = settings.api_key
    return genai.Client(**params)


def response_content_to_text(content) -> str:
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()
    if content is None:
        return ""
    return str(content)


def _looks_like_single_input_embedding_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "single input",
            "single text",
            "one input",
            "one text",
            "one instance",
        )
    )


def embed_texts(
    client,
    texts: Sequence[str],
    *,
    model_name: str,
    task_type: str,
    output_dimensionality: int = 768,
) -> List[Optional[List[float]]]:
    from google.genai import types

    if not texts:
        return []

    try:
        response = client.models.embed_content(
            model=model_name,
            contents=list(texts),
            config=types.EmbedContentConfig(
                output_dimensionality=output_dimensionality,
                task_type=task_type,
            ),
        )
        return [embedding.values for embedding in response.embeddings]
    except Exception as exc:
        if len(texts) == 1 or not _looks_like_single_input_embedding_error(exc):
            raise

    vectors: List[Optional[List[float]]] = []
    for text in texts:
        response = client.models.embed_content(
            model=model_name,
            contents=[text],
            config=types.EmbedContentConfig(
                output_dimensionality=output_dimensionality,
                task_type=task_type,
            ),
        )
        embeddings = response.embeddings or []
        vectors.append(embeddings[0].values if embeddings else None)
    return vectors
