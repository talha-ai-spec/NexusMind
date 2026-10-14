# AI Assistant — API

FastAPI backend. Local Ollama models are used first; cloud providers
(Anthropic, OpenAI, Gemini, Grok, Meta Llama) are the fallback.

## Run

```bash
uv sync
cp .env.example .env          # add any cloud API keys you have
uv run fastapi dev app/main.py   # http://localhost:8000/docs
```

## Quality

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/models?refresh=true` | Installed Ollama models + cloud models, grouped by provider, with the default pick, the default pick for photos (`default_vision`) and the photo limits. Each model has `vision: true/false` |
| POST | `/api/chat` | Streams a reply as server-sent events |

`POST /api/chat` body:

```json
{ "messages": [{"role": "user", "content": "Hi"}], "provider": "ollama", "model": "llama3.2:latest" }
```

A user message can carry photos (JPEG, PNG, WebP or GIF, base64 or a `data:` URL; the
real format is read from the file itself):

```json
{ "role": "user", "content": "What's on this receipt?", "images": [{"media_type": "image/jpeg", "data": "/9j/4AAQ..."}] }
```

`provider` and `model` are optional; without them the API picks the first
local model, then the first configured cloud provider.

Stream events:

```
event: meta
data: {"provider":"ollama","model":"llama3.2:latest","local":true,"fallback":false,"notice":null}

data: {"delta":"Hello"}

event: done        (or)   event: error
data: {}                  data: {"message":"..."}
```

To answer from documents, add `rag` to the chat body. The reply streams as
usual, then a `sources` event carries the text with `[n]` citation markers and
the passages:

```json
{ "messages": [...], "rag": { "collections": ["<collection id>"], "files": ["<file id>"], "chat_id": "<chat id>" } }
```

```
event: sources
data: {"cited_text":"Up to 5 days carry over.[1]","grounded":true,"sources":[{"number":1,"title":"Handbook.pdf","text":"...","page":2,"cited":true,"document_id":"...","kind":"library","collection":"HR"}]}
```

## Files and the Library (RAG)

- **Engine.** `app/library/engine.py` defines `RagEngine`: `ensure_store`,
  `store_info`, `add_document`, `delete_document`, `purge`, and `stream` (text
  deltas, then one `Answer` with sources). `gemini.py` implements it with
  Gemini File Search (`google-genai`); `RAG_ENGINE=offline` uses a local
  keyword-search stand-in with the same SDK types, for development and tests.
  A self-hosted engine (LangChain/LangGraph + Ollama + pgvector/Qdrant)
  implements the same protocol and is chosen in `build_engine`. Documents
  indexed by a different engine are re-indexed on start.
- **Isolation.** One index ("store") for the app. Every document carries
  metadata `scope` (`c:<collection>` or `chat:<chat id>`) and `doc` (its id),
  and the server builds the filter from ids it has looked up, never from
  client text. Files must belong to the request's `chat_id`; ids of deleted or
  expired files are skipped with a note, so an old file never breaks a chat.
- **Indexing** runs in a background queue (`RAG_INDEX_CONCURRENCY`), resumes
  after a restart, and removes any copy an interrupted or timed-out upload left
  in the index (`purge`, matched by `doc` metadata).
- **Storage.** Originals and a SQLite database live in `LIBRARY_DATA_DIR`
  (`data/library`). Gemini deletes raw uploads after 48 hours but keeps the
  index; the originals are what "Open original" and re-indexing use.
- **Limits.** Library files up to 100 MB (File Search's maximum), chat files
  25 MB, 10 per message; chat files are kept `CHAT_FILE_RETENTION_DAYS` (30)
  after they were last cited. Supported: PDF, Word, Excel, PowerPoint, ODT,
  text, CSV, Markdown, HTML, JSON and common code files. Photos go through
  Add photos instead.
- **Owner access.** `LIBRARY_TOKEN` (Bearer) protects `/api/library/*` except
  `config`. Unset: open in development, locked (403) in production.
- **Answering.** Gemini answers only from the File Search results and says
  "I couldn't find that in the documents." otherwise; `RAG_MODEL`,
  `RAG_TOP_K`, `RAG_CHUNK_TOKENS` and `RAG_CHUNK_OVERLAP` tune it. Searching
  files always uses the RAG model, and the reply says so if another model was
  picked.

## How fallback works

1. The model picked in the UI is tried first.
2. If it fails **before** sending any text, the API tries the first installed
   Ollama model, then each cloud provider in `CLOUD_PRIORITY` order.
3. The `meta` event says which model actually answered (`fallback: true`, with
   the reason in `notice`) so the UI can tell the user.
4. If a model fails mid-answer, the API reports an error rather than switching,
   so replies never mix two models.

Set `ALLOW_CLOUD_FALLBACK=false` to keep everything on the chosen model.

## Photos

- Limits: `MAX_IMAGES_PER_MESSAGE` (5), `MAX_IMAGES_PER_REQUEST` (20, the whole
  history) and `MAX_IMAGE_BYTES` (10 MB). Breaking one returns 422 with a readable `detail`.
  `/api/models` returns them as `image_limits` so the web app follows your settings.
- Request bodies over the photo budget are refused with 413 while they stream in,
  and at most 100 photos per request are ever decoded.
- Ollama says which models can see images (`ollama show` capabilities). Cloud models
  are matched by name (`app/vision.py`); `VISION_MODELS` adds patterns.
- When any message has photos, Auto and fallback use only models that can see. A
  chosen text-only model gets an `error` event instead of a reply that ignores the photo.
- Photos go to Ollama as raw bytes (never strings: the Ollama SDK reads a string
  that looks like a path from disk), to Anthropic as image blocks (5 MB each at
  most; larger ones fall back to another model) and to OpenAI-compatible APIs as
  `image_url` parts. Nothing is written to disk.
- Try it locally: `ollama pull gemma3` (or `llava`, `qwen2.5vl`).

## Layout

```
app/
  main.py              app factory, CORS, lifespan
  core/config.py       settings from env / .env
  schemas.py           request/response models
  deps.py              FastAPI dependencies
  routes/              health, models, chat
  providers/
    base.py            Provider interface
    ollama.py          local models (ollama SDK)
    anthropic.py       Claude (anthropic SDK)
    openai_compat.py   OpenAI, Gemini, Grok, Meta (OpenAI-compatible APIs)
    registry.py        builds providers, lists models, picks candidates
  services/chat.py     streaming + fallback logic
tests/                 pytest suite with fake providers (no network needed)
```
