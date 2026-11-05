from pathlib import Path

from app.rag import chunk_markdown


def test_chunks_cover_pto_policy():
    text = Path("sample_docs/acme-handbook/pto-policy.md").read_text(encoding="utf-8")
    chunks = chunk_markdown(text)
    assert chunks
    assert any("20 days" in chunk for chunk in chunks)
    assert all(len(chunk) <= 900 for chunk in chunks)


def test_plain_text_is_split_on_length():
    chunks = chunk_markdown("word " * 500)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
