import re
from contextlib import contextmanager

import psycopg

from app.embeddings import embed_texts
from app.settings import database_url, db_connect_timeout, embed_signature, max_documents

MAX_CHARS = 900  # middle of 800–1000
EMBED_DIM = 768

LEGACY_SIGNATURE = "gemini:gemini-embedding-001"

SCHEMA_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    """
    CREATE TABLE IF NOT EXISTS chunks (
      id          BIGSERIAL PRIMARY KEY,
      path        TEXT NOT NULL,
      content     TEXT NOT NULL,
      embedding   vector(768) NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
      ON chunks USING hnsw (embedding vector_cosine_ops)
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
      path        TEXT PRIMARY KEY,
      content     TEXT NOT NULL,
      kind        TEXT NOT NULL,
      updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS index_meta (
      key    TEXT PRIMARY KEY,
      value  TEXT NOT NULL
    )
    """,
]


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
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        candidate = f"{buf}\n\n{paragraph}" if buf else paragraph
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            out.append(buf)
            buf = ""
        if len(paragraph) <= max_chars:
            buf = paragraph
        else:
            out.extend(_split_hard(paragraph, max_chars))
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
    return [part for part in parts if part]


def embed(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    return embed_texts(texts, task_type=task_type)


def _as_vector(vec: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vec) + "]"


@contextmanager
def _db():
    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    with psycopg.connect(
        url,
        connect_timeout=db_connect_timeout(),
        options="-c statement_timeout=15000",
    ) as conn:
        yield conn


def ensure_schema() -> None:
    with _db() as conn:
        with conn.cursor() as cur:
            for statement in SCHEMA_STATEMENTS:
                cur.execute(statement)
        conn.commit()


def _provider_conflict(cur) -> str | None:
    cur.execute("SELECT COUNT(*) FROM chunks")
    indexed = int(cur.fetchone()[0])
    cur.execute("SELECT value FROM index_meta WHERE key = 'embed_signature'")
    row = cur.fetchone()
    if indexed == 0 and row is None:
        return None
    existing = row[0] if row else LEGACY_SIGNATURE
    current = embed_signature()
    if existing != current:
        return (
            f"Index was built with {existing}, but this process embeds with {current}. "
            "POST /v1/reset, then upload the documents again."
        )
    return None


def _stamp_signature(cur) -> None:
    cur.execute(
        """
        INSERT INTO index_meta (key, value) VALUES ('embed_signature', %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """,
        (embed_signature(),),
    )


def assert_room(paths: list[str]) -> None:
    existing = set(document_paths())
    fresh = [path for path in paths if path not in existing]
    limit = max_documents()
    if len(existing) + len(fresh) > limit:
        raise ValueError(
            f"Document limit is {limit}. Indexed {len(existing)}, "
            f"this request adds {len(fresh)}. Delete a document or POST /v1/reset."
        )


def document_paths() -> list[str]:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT path FROM documents ORDER BY path")
            return [row[0] for row in cur.fetchall()]


def list_documents() -> list[dict]:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.path, d.kind,
                       (SELECT COUNT(*) FROM chunks c WHERE c.path = d.path) AS chunks
                FROM documents d
                ORDER BY d.path
                """
            )
            return [
                {"path": path, "kind": kind, "chunks": int(chunks)}
                for path, kind, chunks in cur.fetchall()
            ]


def list_document_texts() -> list[dict]:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT path, content, kind FROM documents ORDER BY path"
            )
            return [
                {"path": path, "content": content, "kind": kind}
                for path, content, kind in cur.fetchall()
            ]


def replace_document(
    path: str,
    content: str,
    kind: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")
    with _db() as conn:
        with conn.cursor() as cur:
            conflict = _provider_conflict(cur)
            if conflict:
                raise ValueError(conflict)
            cur.execute("DELETE FROM chunks WHERE path = %s", (path,))
            cur.execute(
                """
                INSERT INTO documents (path, content, kind, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (path) DO UPDATE
                SET content = EXCLUDED.content,
                    kind = EXCLUDED.kind,
                    updated_at = now()
                """,
                (path, content, kind),
            )
            for chunk, vec in zip(chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO chunks (path, content, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (path, chunk, _as_vector(vec)),
                )
            _stamp_signature(cur)
        conn.commit()


def delete_document(path: str) -> bool:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE path = %s", (path,))
            cur.execute("DELETE FROM documents WHERE path = %s", (path,))
            deleted = cur.rowcount > 0
            cur.execute("SELECT COUNT(*) FROM documents")
            if int(cur.fetchone()[0]) == 0:
                cur.execute("DELETE FROM index_meta WHERE key = 'embed_signature'")
        conn.commit()
    return deleted


def reset_index() -> None:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks")
            cur.execute("DELETE FROM documents")
            cur.execute("DELETE FROM index_meta")
        conn.commit()


def upsert(path: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    """Backward-compatible chunk replace. Prefer replace_document for new writes."""
    replace_document(path, "\n\n".join(chunks), "md", chunks, embeddings)


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
    reset_index()


def ping_db() -> None:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()


def database_target() -> str:
    """Host only, for logs. Never return credentials."""
    url = database_url()
    if not url:
        return "(DATABASE_URL unset)"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or "unknown"
        port = parsed.port or ""
        name = (parsed.path or "").lstrip("/") or "unknown"
        return f"{host}:{port}/{name}" if port else f"{host}/{name}"
    except Exception:
        return "(unparsed DATABASE_URL)"
