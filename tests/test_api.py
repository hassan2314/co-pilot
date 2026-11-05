import sys
import time

import app.main

assert "google.adk" not in sys.modules, "importing the API should not import ADK"
assert "google.genai" not in sys.modules, "importing the API should not import Gemini"


def _upload(client, name, data, content_type="text/plain"):
    return client.post(
        "/v1/documents",
        files=[("files", (name, data, content_type))],
    )


def test_root_widget_and_health(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["health"] == "/health"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"api": "ok", "db": "ok"}

    script = client.get("/widget.js")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    body = script.text
    assert "/v1/ask" in body
    assert "data-name" in body
    assert "data-color" in body
    assert "data-logo" in body


def test_health_returns_when_database_is_unreachable(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://acme:acme@127.0.0.1:1/docs")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "1")
    started = time.perf_counter()
    response = client.get("/health")
    elapsed = time.perf_counter() - started
    assert elapsed < 5
    assert response.status_code == 200
    assert response.json()["api"] == "ok"
    assert response.json()["db"] == "error"


def test_upload_search_and_summary(client):
    pto = open("sample_docs/acme-handbook/pto-policy.md", "rb").read()
    security = open("sample_docs/acme-handbook/security.md", "rb").read()
    assert _upload(client, "pto-policy.md", pto, "text/markdown").status_code == 200
    assert _upload(client, "security.md", security, "text/markdown").status_code == 200

    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.multi_cell(
        0,
        8,
        "Remote Work Policy. ACME full-time employees may work from home up to three days each week.",
    )
    uploaded = _upload(client, "remote-work.pdf", bytes(pdf.output()), "application/pdf")
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["documents"][0]["kind"] == "pdf"

    listed = client.get("/v1/documents")
    assert listed.status_code == 200
    names = {item["path"] for item in listed.json()["documents"]}
    assert names == {"pto-policy.md", "security.md", "remote-work.pdf"}
    assert listed.json()["limit"] == 50

    answer = client.post(
        "/v1/ask",
        json={"question": "How many PTO days do employees get each year?"},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert "20" in body["answer"]
    assert not body["answer"].lstrip().startswith("#")
    assert body["citations"][0]["path"] == "pto-policy.md"
    assert body["agent_trace"] == ["local"]

    remote = client.post(
        "/v1/ask",
        json={"question": "How many days a week can employees work from home?"},
    )
    assert remote.status_code == 200, remote.text
    remote_body = remote.json()
    assert "three" in remote_body["answer"].lower()
    assert "20 days" not in remote_body["answer"].lower()
    assert [item["path"] for item in remote_body["citations"]] == ["remote-work.pdf"]

    summary = client.post("/v1/ask", json={"question": "Summarize the PTO policy"})
    assert summary.status_code == 200, summary.text
    summary_body = summary.json()
    assert any(item["path"] == "pto-policy.md" for item in summary_body["citations"])
    assert "pto-policy.md" in summary_body["answer"]


def test_rejects_bad_uploads_and_enforces_cap(client, monkeypatch):
    rejected = _upload(client, "notes.exe", b"not a document")
    assert rejected.status_code == 415

    monkeypatch.setenv("MAX_UPLOAD_BYTES", "1024")
    too_big = _upload(client, "notes.txt", b"x" * 2048)
    assert too_big.status_code == 413

    monkeypatch.setenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024))
    monkeypatch.setenv("MAX_DOCUMENTS", "1")
    first = _upload(client, "one.txt", b"First policy document about badges.")
    assert first.status_code == 200, first.text
    second = _upload(client, "two.txt", b"Second policy document about locks.")
    assert second.status_code == 400
    assert "limit" in second.json()["detail"].lower()

    removed = client.delete("/v1/documents/one.txt")
    assert removed.status_code == 200
    assert client.get("/v1/documents").json()["count"] == 0


def test_folder_ingest_still_indexes_markdown(client):
    response = client.post("/v1/ingest", json={"folder": "acme-handbook"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["files"] >= 5
    names = {item["path"] for item in client.get("/v1/documents").json()["documents"]}
    assert "pto-policy.md" in names
    assert "security.md" in names
    assert all(name.endswith(".md") for name in names)
