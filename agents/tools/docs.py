"""Doc tools. Return dicts only — agents consume JSON."""

from pathlib import Path

from app.rag import chunk_markdown, delete_all_chunks, embed, search, upsert

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


def ingest_folder(folder: str) -> dict:
    """Read all .md files under sample_docs/<folder>, chunk, embed, INSERT.

    Args:
        folder: Path relative to sample_docs/ (example: acme-handbook).
    """
    resolved = _resolve_folder(folder)
    if isinstance(resolved, dict):
        return resolved

    md_files = sorted(resolved.glob("*.md"))
    if not md_files:
        return {"status": "error", "error": "no .md files found"}

    file_count = 0
    chunk_count = 0
    for path in md_files:
        chunks = chunk_markdown(path.read_text(encoding="utf-8"))
        if not chunks:
            continue
        upsert(path.name, chunks, embed(chunks))
        file_count += 1
        chunk_count += len(chunks)

    return {"status": "success", "files": file_count, "chunks": chunk_count}


def clear_index() -> dict:
    """Delete every row from the chunks table."""
    delete_all_chunks()
    return {"status": "success"}


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


def get_policy_text(folder: str, filename: str = "") -> dict:
    """Read handbook markdown from disk for summarization (not search).

    Args:
        folder: Path relative to sample_docs/ (example: acme-handbook).
        filename: Optional policy file or nickname (pto, security). Empty = all .md in the folder.
    """
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