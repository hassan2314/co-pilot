from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from agents.tools.docs import ingest_folder
from app.adk_runtime import build_runner, run_ask
from app.rag import ping_db
from app.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ping_db()
    app.state.runner = build_runner()  # one Runner, reused
    yield


app = FastAPI(title="Acme Docs Copilot API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        ping_db()
        db = "ok"
    except Exception:
        db = "error"
    return HealthResponse(api="ok", db=db)


@app.post("/v1/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    result = ingest_folder(req.folder)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return IngestResponse(**result)


@app.post("/v1/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    try:
        result = await run_ask(app.state.runner, req.question)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AskResponse(**result)