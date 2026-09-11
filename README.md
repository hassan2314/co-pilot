# Acme Docs Copilot API

Internal knowledge assistant as a FastAPI product: a multi-agent [Google ADK](https://google.github.io/adk-docs/) team searches **Postgres + pgvector** and returns answers with citations.

Ingest company markdown, ask questions over HTTP, get cited answers.

```text
Client (React UI in sibling repo `co-pilot-ui` / curl / Postman / Swagger)
        │
        ▼
   FastAPI
   POST /v1/ingest   → ingest_folder (chunk → embed → upsert, no LLM)
   POST /v1/ask      → ADK Runner (coordinator → qa_agent | summarize_folder_agent)
   GET  /health
        │
        ▼
   PostgreSQL + pgvector
   chunks(path, content, embedding)
```

## Why this project

This is the backend-shaped version of a docs copilot:

- **API first** — Swagger at `/docs`, not only `adk web`
- **Persistent memory** — embeddings live in Postgres, not in the prompt
- **Grounded answers** — `path` and `score` come from the search tool, not the LLM
- **Clear roles** — ingest is a pipeline; Q&A and summaries are agentic

## Architecture

| Surface | What it does |
|---------|----------------|
| `POST /v1/ingest` | Calls `ingest_folder` directly (no LLM). Reads `sample_docs/<folder>/*.md`. |
| `POST /v1/ask` | Reuses one ADK `Runner`. Coordinator transfers to `qa_agent` or `summarize_folder_agent`. |
| `GET /health` | API process + `SELECT 1` against Postgres |

| Agent | Tools | Role |
|-------|--------|------|
| `coordinator` | — | Routes summaries vs specific questions |
| `summarize_folder_agent` | `get_policy_text` | Reads source markdown and writes a short recap |
| `qa_agent` | `search_docs` | Retrieve top-k chunks and answer with citations |

Tools own the filesystem and database. FastAPI does not reimplement RAG.

## Project layout

```text
co-pilot/
├── README.md
├── docker-compose.yml
├── sql/init.sql
├── sample_docs/acme-handbook/
├── app/
│   ├── main.py           # FastAPI
│   ├── schemas.py        # request/response models
│   ├── rag.py            # chunk, embed, upsert, search
│   └── adk_runtime.py    # Runner + event → answer/citations/trace
├── agents/
│   ├── agent.py          # root_agent for adk web + /ask
│   └── tools/docs.py
└── postman_collection.json
```

## Prerequisites

- Python 3.12+
- Docker (Postgres + pgvector)
- A [Gemini API key](https://aistudio.google.com/apikey)

## Setup

```bash
git clone <your-repo-url>
cd co-pilot

python -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -r requirements.txt

cp .env.example .env
```

Put your Gemini key in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://acme:acme@localhost:5432/docs
```

Never commit `.env`.

Start the database (publishes host port 5432):

```bash
docker compose up -d --force-recreate
docker compose ps
```

`PORTS` should show `0.0.0.0:5432->5432/tcp`.

## Run the API

```bash
uvicorn app.main:app --reload --port 8001
```

Swagger: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

```bash
curl http://127.0.0.1:8001/health

curl -X POST http://127.0.0.1:8001/v1/ingest \
  -H 'Content-Type: application/json' \
  -d '{"folder":"acme-handbook"}'

curl -X POST http://127.0.0.1:8001/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"How many PTO days do employees get each year?"}'

curl -X POST http://127.0.0.1:8001/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Summarize the PTO policy"}'
```

A successful ask looks like:

```json
{
  "answer": "Full-time employees receive 20 days of PTO each calendar year.",
  "citations": [{"path": "pto-policy.md", "score": 0.75}],
  "agent_trace": ["coordinator", "qa_agent"]
}
```

A summary uses the same endpoint; `agent_trace` should include `summarize_folder_agent` and citations come from the source files (`score` is `1.0` because the whole file was read, not searched).

`folder` is relative to `sample_docs/` (use `acme-handbook`, not a full path).

Or import `postman_collection.json` into Postman (base URL `http://127.0.0.1:8001`). Run **Health → Ingest → Ask PTO → Summarize PTO**.

## UI (separate repo)

The React app lives next to this backend:

```text
ACME/
├── co-pilot/       this API
└── co-pilot-ui/    React UI
```

```bash
cd ../co-pilot-ui
cp .env.example .env   # VITE_API_URL=http://127.0.0.1:8001
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). CORS already allows that origin.

## Optional: debug agents

```bash
adk web . --port 8000
```

Select the `agents` app. FastAPI should stay on **8001** so the two servers do not collide.

## Sample domain

Fake ACME handbook: onboarding, PTO, security, engineering practices, incidents.

## Out of v1

Auth, Notion sync, PDFs, and cloud deploy are intentionally omitted.
