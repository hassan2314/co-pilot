from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    folder: str = Field(examples=["acme-handbook"])


class IngestResponse(BaseModel):
    status: str
    files: int = 0
    chunks: int = 0
    error: str | None = None


class AskRequest(BaseModel):
    question: str = Field(
        examples=[
            "How many PTO days do employees get each year?",
            "Summarize the PTO policy",
        ]
    )


class Citation(BaseModel):
    path: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    agent_trace: list[str]


class HealthResponse(BaseModel):
    api: str
    db: str