"""Embedding providers. The pgvector column is 768 floats for every provider."""

import hashlib
import math
import os
import time

from app.settings import embed_dim, embed_signature, provider_name

EMBED_DIM = 768


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    if not texts:
        return []
    provider = provider_name()
    if provider == "local":
        return [_hash_embed(text) for text in texts]
    if provider == "openai":
        return _openai_embed(texts)
    return _gemini_embed(texts, task_type)


def _hash_embed(text: str) -> list[float]:
    """Feature hashing so local demos can retrieve without an API key."""
    vec = [0.0] * EMBED_DIM
    tokens = [tok for tok in _tokens(text)]
    if not tokens:
        tokens = ["empty"]
    for tok in tokens:
        digest = hashlib.sha256(tok.encode()).digest()
        bucket = int.from_bytes(digest[:4], "little") % EMBED_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vec)) or 1.0
    return [value / norm for value in vec]


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    word = []
    for char in text.lower():
        if char.isalnum():
            word.append(char)
        elif word:
            out.append("".join(word))
            word = []
    if word:
        out.append("".join(word))
    return out


def _gemini_embed(texts: list[str], task_type: str) -> list[list[float]]:
    from google import genai
    from google.genai import errors as genai_errors
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.models.embed_content(
                model=model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=embed_dim(),
                ),
            )
            vectors = [list(item.values) for item in response.embeddings]
            _check_dims(vectors)
            return vectors
        except genai_errors.ServerError as exc:
            last_error = exc
            time.sleep(1.2 * (attempt + 1))
    raise last_error or RuntimeError("embed failed")


def _openai_embed(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    client = OpenAI()
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    response = client.embeddings.create(model=model, input=texts, dimensions=embed_dim())
    ordered = sorted(response.data, key=lambda item: item.index)
    vectors = [list(item.embedding) for item in ordered]
    _check_dims(vectors)
    return vectors


def _check_dims(vectors: list[list[float]]) -> None:
    dim = embed_dim()
    for vec in vectors:
        if len(vec) != dim:
            raise ValueError(f"expected {dim} dims, got {len(vec)} ({embed_signature()})")
