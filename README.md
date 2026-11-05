# Acme Docs Copilot API

[![Upload, ask, and the chat widget](docs/screenshots/demo.gif)](docs/screenshots/demo.gif)

FastAPI knowledge API for a docs chatbot. Upload PDF, TXT, or Markdown, then ask questions and get answers with file citations. A coordinator agent (Google ADK) searches Postgres + pgvector.

The React console and the embeddable widget live in [co-pilot-ui](https://github.com/hassan2314/co-pilot-ui).

```text
Browser / widget.js / curl
        │
        ▼
   FastAPI
   POST /v1/documents  → upload PDF, TXT, MD (max 50)
   POST /v1/ingest     → index sample_docs/<folder>/*.md
   POST /v1/ask        → cited answer
   GET  /widget.js     → chat-only embed (no upload UI)
   GET  /health
        │
        ▼
   PostgreSQL + pgvector
   documents(path, content) + chunks(path, content, embedding)
```

## What you can run

| Call | What it does |
|------|----------------|
| `POST /v1/documents` | Multipart upload. `.pdf`, `.txt`, `.md`, `.markdown`. Replaces a file when the name already exists. |
| `GET /v1/documents` | Indexed files, kind, and chunk counts. |
| `DELETE /v1/documents/{name}` | Remove one file and its chunks. |
| `POST /v1/reset` | Clear the index. Required after changing embedding provider. |
| `POST /v1/ingest` | Index `sample_docs/<folder>/*.md` (the sample handbook). |
| `POST /v1/ask` | Cited answer. Summaries read the full stored text. |
| `GET /widget.js` | Floating chat button. Branding via `data-name`, `data-color`, `data-logo`. |
| `GET /health` | API process plus `SELECT 1`. Returns in a few seconds even when Postgres is down. |

The library cap is 50 documents (`MAX_DOCUMENTS`, hard ceiling 50). Each upload is limited to 8 MB (`MAX_UPLOAD_BYTES`).

Screenshots below were taken locally against the ACME handbook with `LLM_PROVIDER=local` (retrieved sentences, no hosted model). Gemini is still the default. Citations are the stored file names.

![Indexed PDF, TXT, and Markdown](docs/screenshots/library.png)

![Chat widget citing remote-work.pdf](docs/screenshots/widget.png)

## Setup

Python 3.12+, Docker or any Postgres with pgvector, and a [Gemini API key](https://aistudio.google.com/apikey). OpenAI is optional.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
docker compose up -d
uvicorn app.main:app --reload --port 8001
```

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://acme:acme@localhost:5432/docs
```

`GOOGLE_API_KEY` is what ADK reads. The app copies `GEMINI_API_KEY` into it when only one is set.

Swagger: http://127.0.0.1:8001/docs

```bash
curl -F "files=@sample_docs/acme-handbook/pto-policy.md" \
     -F "files=@sample_docs/acme-handbook/remote-work.pdf" \
     -F "files=@sample_docs/acme-handbook/holiday-calendar.txt" \
     http://127.0.0.1:8001/v1/documents

curl -X POST http://127.0.0.1:8001/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"How many PTO days do employees get each year?"}'
```

A cited answer looks like:

```json
{
  "answer": "Full-time employees receive 20 days of paid time off (PTO) each calendar year.",
  "citations": [{ "path": "pto-policy.md", "score": 0.82 }],
  "agent_trace": ["coordinator", "qa_agent"]
}
```

Folder ingest still works for the sample markdown:

```bash
curl -X POST http://127.0.0.1:8001/v1/ingest \
  -H 'Content-Type: application/json' \
  -d '{"folder":"acme-handbook"}'
```

`folder` is relative to `sample_docs/`. Postman: import `postman_collection.json` (base URL `http://127.0.0.1:8001`).

Tests:

```bash
pip install -r requirements-dev.txt
pytest
```

## Providers

`LLM_PROVIDER` selects the chat model and the embedding model.

| Value | Chat | Embeddings |
|-------|------|------------|
| `gemini` (default) | ADK agent, `GEMINI_MODEL` (default `gemini-3.1-flash-lite`) | `GEMINI_EMBED_MODEL` at 768 dims |
| `openai` | ADK via LiteLLM, `OPENAI_MODEL` (default `gpt-4o-mini`) | `text-embedding-3-small` at 768 dims. Needs `OPENAI_API_KEY`. |
| `local` | Quotes the best retrieved sentences. No API key. | Hashed bag-of-words, 768 dims. For demos and tests. |

The pgvector column is `vector(768)` for every provider. Switching provider changes the vector space. `POST /v1/reset`, then upload again. A mismatch returns HTTP 409 instead of silent bad citations.

ADK is imported on the first Gemini or OpenAI question, not at process start, so `/health` stays light.

## Embeddable chat

The widget only chats. It has no upload form.

Preferred snippet (UI iframe, works with the Netlify `/api` proxy, no extra CORS):

```html
<script
  src="https://acme-copilot.netlify.app/widget.js"
  data-name="Handbook"
  data-color="#2f5d50"
  data-logo="https://example.com/logo.png"
  defer
></script>
```

`data-color` is a `#rgb` or `#rrggbb` hex. `data-logo` is an `http(s)` URL or a root-relative path on the UI host. Preview on a plain page: `/widget-demo.html` in the UI repo.

API-hosted alternative. The script runs on the customer origin and calls `POST /v1/ask`, so the API must allow that browser origin (`CORS_ALLOW_ALL=true`, or list the origin in `CORS_ORIGINS`):

```html
<script
  src="https://co-pilot.fastapicloud.dev/widget.js"
  data-name="Handbook"
  data-color="#2f5d50"
  data-api="https://co-pilot.fastapicloud.dev"
  defer
></script>
```

## Agents

| Agent | Tools | Role |
|-------|--------|------|
| `coordinator` | — | Routes summaries vs questions |
| `qa_agent` | `search_docs` | Top-k chunks, answer with citations |
| `summarize_folder_agent` | `get_policy_text` | Full text of an indexed file |

With Gemini or OpenAI, `agent_trace` names those agents. With `local`, the trace is `local` and no hosted model is called.

`adk web . --port 8000` still opens the agent debugger. Keep FastAPI on 8001.

## Deploy

### UI

[co-pilot-ui](https://github.com/hassan2314/co-pilot-ui) is a Vite app. `netlify.toml` builds `npm run build`, publishes `dist`, and proxies `/api/*` to this API. The live site is https://acme-copilot.netlify.app (same title, fonts, and bundle as this UI). Rebuilds come from the Netlify site linked to that repo. This API does not deploy the UI.

### API (FastAPI Cloud)

The app entrypoint is `app/main.py` (`app`), which FastAPI Cloud auto-detects. GitHub records a successful deploy of `co-pilot` on 2026-09-11 (`2352b455`).

Checked on 2026-11-05: `https://co-pilot.fastapicloud.dev/health` completes TLS (Cloudflare, certificate `*.fastapicloud.dev`) and then returns no bytes until the client times out. `https://acme-copilot.netlify.app/api/health` hangs the same way, because `netlify.toml` proxies `/api` to that host. Plain `http://` on the API host returns Cloudflare's redirect immediately, so the edge is up and the origin is not answering.

Hobby apps scale to zero. The previous process blocked startup on `ping_db()` with no connect timeout, and it imported ADK before it could listen. A cold start waiting on Postgres (paused database, a URL that never answers, or a missing `DATABASE_URL`) never becomes ready, and Cloudflare waits until the browser gives up.

This branch listens even when the database is down, uses a 5 second connect timeout, and loads ADK on the first question. `/health` then returns `{"api":"ok","db":"error"}` instead of hanging. That does not wake the current deployment. Production stays on the old image until the connected branch is redeployed.

Needs Hassan's FastAPI Cloud account (dashboard for app `co-pilot`):

1. Confirm secrets. `DATABASE_URL` must be a Postgres instance with pgvector that FastAPI Cloud can reach. `localhost` will not work. The Supabase integration in FastAPI Cloud can create this variable. Run `CREATE EXTENSION IF NOT EXISTS vector;` if the role is allowed to, or enable pgvector in the database UI. The app also creates `documents` and `index_meta` on startup.
2. Set `GEMINI_API_KEY` and `GOOGLE_API_KEY` to the same key, or set `LLM_PROVIDER=openai` and `OPENAI_API_KEY`.
3. For the API-hosted widget on other websites, set `CORS_ALLOW_ALL=true`. The Netlify iframe widget does not need that.
4. Redeploy from the connected branch after this change is on that branch. Pushing a pull request branch does not replace production. Runtime logs: the deployment recorded on GitHub points at `https://dashboard.fastapicloud.com/hassandevelpor-ad6a16f5/apps/co-pilot`.
5. If the app was suspended, resume it before expecting `/health` to answer. A code change cannot resume a stopped account.

After redeploy, `GET /health` should answer quickly. `db` stays `error` until `DATABASE_URL` points at a reachable pgvector database.

## Sample documents

`sample_docs/acme-handbook/` is a fictional handbook: PTO, security, onboarding, incidents, engineering practices, plus `remote-work.pdf` and `holiday-calendar.txt` for upload. No auth in this version.
