"""Runtime settings. Read from the environment on each call so tests can swap them."""

import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def provider_name() -> str:
    name = env("LLM_PROVIDER", "gemini").lower()
    if name in {"gemini", "openai", "local"}:
        return name
    return "gemini"


def embed_dim() -> int:
    return 768


def max_documents() -> int:
    try:
        value = int(env("MAX_DOCUMENTS", "50") or "50")
    except ValueError:
        return 50
    return max(1, min(value, 50))


def max_upload_bytes() -> int:
    try:
        value = int(env("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)) or str(8 * 1024 * 1024))
    except ValueError:
        return 8 * 1024 * 1024
    return max(1024, value)


def db_connect_timeout() -> int:
    try:
        value = int(env("DB_CONNECT_TIMEOUT", "5") or "5")
    except ValueError:
        return 5
    return max(1, min(value, 30))


def database_url() -> str:
    url = env("DATABASE_URL")
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def cors_allow_all() -> bool:
    return env("CORS_ALLOW_ALL", "false").lower() in {"1", "true", "yes", "on"}


def cors_origins() -> list[str]:
    if cors_allow_all():
        return ["*"]
    defaults = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]
    extra = [
        item.strip()
        for item in env("CORS_ORIGINS").split(",")
        if item.strip() and item.strip() != "*"
    ]
    origins: list[str] = []
    for origin in defaults + extra:
        if origin not in origins:
            origins.append(origin)
    return origins


def embed_signature() -> str:
    provider = provider_name()
    if provider == "openai":
        model = env("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    elif provider == "local":
        model = "hashed-bow-768"
    else:
        model = env("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    return f"{provider}:{model}"


def sync_provider_keys() -> None:
    """ADK reads GOOGLE_API_KEY. Accept either Gemini env name."""
    gemini = env("GEMINI_API_KEY") or env("GOOGLE_API_KEY")
    if gemini:
        os.environ.setdefault("GEMINI_API_KEY", gemini)
        os.environ.setdefault("GOOGLE_API_KEY", gemini)


def chat_model():
    """Gemini model id, or a LiteLLM wrapper when LLM_PROVIDER=openai."""
    if provider_name() == "openai":
        from google.adk.models.lite_llm import LiteLlm

        name = env("OPENAI_MODEL", "gpt-4o-mini")
        if "/" not in name:
            name = f"openai/{name}"
        return LiteLlm(model=name)
    return env("GEMINI_MODEL", "gemini-3.1-flash-lite")
