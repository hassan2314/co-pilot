import os
import re
import time
from contextlib import contextmanager

import psycopg
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

MAX_CHARS = 900  # middle of 800–1000
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768

_client = None

def chunk_markdown(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    sections = re.split(r"(?=^##\s)", text, flags=re.MULTILINE)
    chunks: list[str] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        chunks.extend(_cap_chars(section, max_chars))
    return chunks


def _cap_chars(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    out, buf = [], ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        candidate = f"{buf}\n\n{p}" if buf else p
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            out.append(buf)
            buf = ""
        if len(p) <= max_chars:
            buf = p
        else:
            out.extend(_split_hard(p, max_chars))
    if buf:
        out.append(buf)
    return out


def _split_hard(text: str, max_chars: int) -> list[str]:
    parts = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]


def _gemini() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def embed(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    if not texts:
        return []

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = _gemini().models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBED_DIM,
                ),
            )
            vectors = [list(item.values) for item in response.embeddings]
            for vec in vectors:
                if len(vec) != EMBED_DIM:
                    raise ValueError(f"expected {EMBED_DIM} dims, got {len(vec)}")
            return vectors
        except genai_errors.ServerError as exc:
            last_error = exc
            time.sleep(1.2 * (attempt + 1))
    raise last_error or RuntimeError("embed failed")


def _as_vector(vec: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vec) + "]"


@contextmanager
def _db():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        yield conn


def upsert(path: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE path = %s", (path,))
            for content, vec in zip(chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO chunks (path, content, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (path, content, _as_vector(vec)),
                )
        conn.commit()


def search(query: str, k: int = 5) -> list[tuple[str, str, float]]:
    qvec = embed([query], task_type="RETRIEVAL_QUERY")[0]
    literal = _as_vector(qvec)
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT path, content, 1 - (embedding <=> %s::vector) AS score
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (literal, literal, k),
            )
            return cur.fetchall()
            
def delete_all_chunks() -> None:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks")
        conn.commit()

def ping_db() -> None:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()