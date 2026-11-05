import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

load_dotenv()

from app.rag import database_target, ensure_schema, ping_db
from app.schemas import (
    AskRequest,
    AskResponse,
    DocumentListResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    ResetResponse,
)
from app.settings import cors_allow_all, cors_origins, provider_name, sync_provider_keys

sync_provider_keys()

log = logging.getLogger("uvicorn.error")
WIDGET_JS = Path(__file__).resolve().parent / "static" / "widget.js"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Listen even if Postgres is down. A blocking connect here is what makes
    # a cold start (FastAPI Cloud scales to zero) sit until the proxy times out.
    app.state.runner = None
    log.info("provider=%s database=%s", provider_name(), database_target())
    try:
        ensure_schema()
        log.info("database schema ready")
    except Exception as exc:
        log.warning("database not ready at startup; /health will report it: %s", exc)
    yield


app = FastAPI(title="Acme Docs Copilot API", lifespan=lifespan)

_origins = cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=None if cors_allow_all() else r"https://.*\.(netlify\.app|netlify\.com)",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _raise_for_result(result: dict) -> None:
    if result.get("status") == "success":
        return
    raise HTTPException(
        status_code=int(result.get("code") or 400),
        detail=result.get("error") or "request failed",
    )


def _runner():
    if app.state.runner is None:
        from app.adk_runtime import build_runner

        app.state.runner = build_runner()
    return app.state.runner


@app.get("/")
def root() -> dict:
    return {
        "service": "Acme Docs Copilot API",
        "health": "/health",
        "docs": "/docs",
        "widget": "/widget.js",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        ping_db()
        db = "ok"
    except Exception:
        db = "error"
    return HealthResponse(api="ok", db=db)


@app.get("/widget.js")
def widget_script() -> FileResponse:
    return FileResponse(
        WIDGET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.post("/v1/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    from agents.tools.docs import ingest_folder

    result = ingest_folder(req.folder)
    _raise_for_result(result)
    return IngestResponse(**result)


@app.post("/v1/documents", response_model=IngestResponse)
async def upload_documents(
    files: list[UploadFile] = File(description="PDF, TXT, or Markdown files"),
) -> IngestResponse:
    from agents.tools.docs import ingest_files

    payloads: list[tuple[str, bytes]] = []
    for item in files:
        payloads.append((item.filename or "upload.txt", await item.read()))
    result = ingest_files(payloads)
    _raise_for_result(result)
    return IngestResponse(**result)


@app.get("/v1/documents", response_model=DocumentListResponse)
def documents() -> DocumentListResponse:
    from agents.tools.docs import indexed_documents

    result = indexed_documents()
    _raise_for_result(result)
    return DocumentListResponse(
        documents=result["documents"],
        count=result["count"],
        limit=result["limit"],
    )


@app.delete("/v1/documents/{path}", response_model=ResetResponse)
def delete_one(path: str) -> ResetResponse:
    from agents.tools.docs import remove_document

    result = remove_document(path)
    _raise_for_result(result)
    return ResetResponse(status="success")


@app.post("/v1/reset", response_model=ResetResponse)
def reset() -> ResetResponse:
    from agents.tools.docs import clear_index

    result = clear_index()
    _raise_for_result(result)
    return ResetResponse(status="success")


@app.post("/v1/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    try:
        if provider_name() == "local":
            from app.local_qa import answer_locally

            result = answer_locally(req.question)
        else:
            from app.adk_runtime import run_ask

            result = await run_ask(_runner(), req.question)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AskResponse(**result)
