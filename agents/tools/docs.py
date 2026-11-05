"""Doc tools. Return dicts only — agents consume JSON."""

from pathlib import Path

from app.extract import UploadError, prepare_upload
from app.rag import (
    chunk_markdown,
    delete_document,
    embed,
    ensure_schema,
    list_document_texts,
    list_documents,
    replace_document,
    reset_index,
    search,
)
from app.settings import max_documents

DOCS_ROOT = Path(__file__).resolve().parents[2] / "sample_docs"

# Nicknames the summarize agent might pass instead of a real filename.
POLICY_ALIASES = {
    "pto": "pto-policy.md",
    "pto-policy": "pto-policy.md",
    "vacation": "pto-policy.md",
    "leave": "pto-policy.md",
    "time-off": "pto-policy.md",
    "security": "security.md",
    "phishing": "security.md",
    "onboarding": "onboarding.md",
    "incidents": "incidents.md",
    "incident": "incidents.md",
    "eng": "eng-practices.md",
    "engineering": "eng-practices.md",
    "eng-practices": "eng-practices.md",
}


def _resolve_folder(folder: str) -> Path | dict:
    """Only allow folders inside sample_docs/. Block ../ and absolute paths."""
    if not folder or not str(folder).strip():
        return {"status": "error", "error": "folder is required"}
    root = DOCS_ROOT.resolve()
    candidate = (root / folder).resolve()
    if not candidate.is_relative_to(root):
        return {"status": "error", "error": "folder must stay under sample_docs/"}
    if not candidate.is_dir():
        return {"status": "error", "error": f"not a directory: {folder}"}
    return candidate


def _alias_names(filename: str) -> set[str]:
    raw = filename.strip()
    name = Path(raw).name
    key = name.lower().replace(" ", "-").replace("_", "-")
    stem = key[:-3] if key.endswith(".md") else key.rsplit(".", 1)[0] if "." in key else key
    mapped = POLICY_ALIASES.get(stem) or POLICY_ALIASES.get(key)
    names = {name, key}
    if mapped:
        names.add(mapped)
    else:
        names.add(f"{stem}.md")
    return {item for item in names if item}


def _resolve_policy_file(folder: Path, filename: str) -> Path | dict:
    """Map a policy nickname to a .md file inside folder. No path traversal."""
    raw = filename.strip()
    if not raw:
        return {"status": "error", "error": "filename is required"}

    name = Path(raw).name
    key = name.lower().replace(" ", "-").replace("_", "-")
    if key.endswith(".md"):
        key = key[:-3]
    mapped = POLICY_ALIASES.get(key, name if name.endswith(".md") else f"{key}.md")

    candidate = (folder / mapped).resolve()
    if not candidate.is_relative_to(folder.resolve()):
        return {"status": "error", "error": "file must stay in the folder"}
    if not candidate.is_file():
        available = ", ".join(p.name for p in sorted(folder.glob("*.md"))) or "(none)"
        return {
            "status": "error",
            "error": f"not a file: {mapped}. available: {available}",
        }
    return candidate


def _store_text(path: str, kind: str, text: str) -> dict:
    chunks = chunk_markdown(text)
    if not chunks:
        return {"status": "error", "error": f"no text to index in {path}"}
    try:
        replace_document(path, text, kind, chunks, embed(chunks))
    except ValueError as exc:
        return {"status": "error", "error": str(exc), "code": 409}
    except Exception as exc:
        return {"status": "error", "error": f"{path}: {exc}"}
    return {"path": path, "kind": kind, "chunks": len(chunks)}


def ingest_folder(folder: str) -> dict:
    """Read all .md files under sample_docs/<folder>, chunk, embed, and store.

    Args:
        folder: Path relative to sample_docs/ (example: acme-handbook).
    """
    resolved = _resolve_folder(folder)
    if isinstance(resolved, dict):
        return resolved

    md_files = sorted(resolved.glob("*.md"))
    if not md_files:
        return {"status": "error", "error": "no .md files found"}

    try:
        ensure_schema()
        from app.rag import assert_room

        assert_room([path.name for path in md_files])
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    stored = []
    for path in md_files:
        result = _store_text(path.name, "md", path.read_text(encoding="utf-8"))
        if result.get("status") == "error":
            return result
        stored.append(result)

    return {
        "status": "success",
        "files": len(stored),
        "chunks": sum(item["chunks"] for item in stored),
        "documents": stored,
    }


def ingest_files(items: list[tuple[str, bytes]]) -> dict:
    """Index uploaded PDF, TXT, and Markdown bytes. Caps the library at 50 docs."""
    if not items:
        return {"status": "error", "error": "at least one file is required"}
    limit = max_documents()
    if len(items) > limit:
        return {"status": "error", "error": f"upload at most {limit} files at a time"}

    prepared: list[tuple[str, str, str]] = []
    try:
        for name, data in items:
            prepared.append(prepare_upload(name, data))
    except UploadError as exc:
        return {"status": "error", "error": str(exc), "code": exc.code}

    names = [item[0] for item in prepared]
    if len(names) != len(set(names)):
        return {"status": "error", "error": "duplicate filenames in one upload"}

    try:
        ensure_schema()
        from app.rag import assert_room

        assert_room(names)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    stored = []
    for path, kind, text in prepared:
        result = _store_text(path, kind, text)
        if result.get("status") == "error":
            return result
        stored.append(result)

    return {
        "status": "success",
        "files": len(stored),
        "chunks": sum(item["chunks"] for item in stored),
        "documents": stored,
    }


def clear_index() -> dict:
    """Delete every indexed document and chunk."""
    try:
        ensure_schema()
        reset_index()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "success"}


def remove_document(path: str) -> dict:
    safe = Path(path or "").name
    if not safe or safe != path or "/" in path or "\\" in path:
        return {"status": "error", "error": "invalid document name"}
    try:
        ensure_schema()
        deleted = delete_document(safe)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    if not deleted:
        return {"status": "error", "error": f"not indexed: {safe}", "code": 404}
    return {"status": "success", "path": safe}


def indexed_documents() -> dict:
    try:
        ensure_schema()
        documents = list_documents()
    except Exception as exc:
        return {"status": "error", "error": str(exc), "documents": []}
    return {
        "status": "success",
        "documents": documents,
        "count": len(documents),
        "limit": max_documents(),
    }


def search_docs(query: str, k: int = 5) -> dict:
    """Search indexed handbook chunks by cosine similarity.

    Args:
        query: Natural language question.
        k: How many hits to return.
    """
    if not query or not str(query).strip():
        return {"status": "error", "error": "query is required"}

    try:
        rows = search(query.strip(), k=max(1, min(int(k), 20)))
    except Exception as exc:
        return {"status": "error", "error": str(exc), "hits": []}

    return {
        "status": "success",
        "hits": [
            {"path": path, "content": content, "score": float(score)}
            for path, content, score in rows
        ],
    }


def get_policy_text(folder: str = "acme-handbook", filename: str = "") -> dict:
    """Read indexed document text for summarization (not search).

    Args:
        folder: Legacy sample folder, used only when nothing is indexed yet.
        filename: Document name or nickname (pto, security, remote-work.pdf). Empty reads the library.
    """
    try:
        ensure_schema()
        rows = list_document_texts()
    except Exception as exc:
        rows = None
        db_error = str(exc)
    else:
        db_error = None

    if rows:
        chosen = _filter_indexed(rows, filename)
        if isinstance(chosen, dict):
            return chosen
        return {
            "status": "success",
            "files": [
                {"path": item["path"], "content": item["content"][:20000]}
                for item in chosen[:20]
            ],
        }

    disk = _policy_from_disk(folder, filename)
    if db_error and isinstance(disk, dict) and disk.get("status") == "error":
        disk["error"] = db_error
    return disk


def _filter_indexed(rows: list[dict], filename: str) -> list[dict] | dict:
    if not filename or not str(filename).strip():
        return rows
    wanted = _alias_names(filename)
    stems = {Path(name).stem.lower() for name in wanted}
    match = [
        item
        for item in rows
        if item["path"] in wanted or Path(item["path"]).stem.lower() in stems
    ]
    if not match:
        available = ", ".join(item["path"] for item in rows) or "(none)"
        return {
            "status": "error",
            "error": f"not indexed: {filename}. available: {available}",
        }
    return match


def _policy_from_disk(folder: str, filename: str) -> dict:
    resolved = _resolve_folder(folder)
    if isinstance(resolved, dict):
        return resolved

    if filename and str(filename).strip():
        policy = _resolve_policy_file(resolved, filename)
        if isinstance(policy, dict):
            return policy
        md_files = [policy]
    else:
        md_files = sorted(resolved.glob("*.md"))
        if not md_files:
            return {"status": "error", "error": "no .md files found"}

    return {
        "status": "success",
        "files": [
            {"path": path.name, "content": path.read_text(encoding="utf-8")}
            for path in md_files
        ],
    }
