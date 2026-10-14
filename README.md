# NexusMind — Multi-Modal Local-First AI Platform

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-16.3-black?style=for-the-badge&logo=next.js" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/React-19.2-blue?style=for-the-badge&logo=react" alt="React 19" />
  <img src="https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python-3.13-yellow?style=for-the-badge&logo=python" alt="Python 3.13" />
  <img src="https://img.shields.io/badge/Ollama-Local_First-white?style=for-the-badge&logo=ollama" alt="Ollama" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

> **NexusMind** is an enterprise-grade, privacy-centric AI platform that bridges local edge intelligence with cloud foundation models. It delivers a unified workspace for **Text Chat**, **Vision Reasoning**, **Real-Time WebRTC Voice Mode**, **Generative Image Synthesis & Editing**, **Document RAG with Citations**, and **Live Fullstack Observability**.

---

## Key Highlights

* **Local-First, Cloud-Fallback**: Default to zero-cost, private models running on device via [Ollama](https://ollama.ai) (`llama3.2`, `gemma3:1b`). If local resources are unavailable or fail before the first token, the system seamlessly and automatically fails over to cloud providers ([OpenAI](https://openai.com), [Anthropic](https://anthropic.com), [Google Gemini](https://ai.google.dev), [xAI Grok](https://x.ai), and [Meta](https://meta.com)).
* **Real-Time WebRTC Voice Mode**: Natural, low-latency, bidirectional audio conversations powered by LiveKit and Silero Voice Activity Detection (VAD).
* **Multi-Modal Vision**: Drag-and-drop photos directly into the conversation for visual reasoning, OCR, and diagram explanations.
* **AI Image Studio (Text-to-Image & Image-to-Image)**: Natural language in-chat triggering (`"Generate a logo for..."` or `"Edit this photo..."`) with an automated fallback pipeline (Pollinations FLUX.1 $\rightarrow$ Hugging Face GPU API) and anonymous temporary public relay bridges (`uguu.se` / `freeimage.host`).
* **Dual-Engine Document RAG**: Ground responses in PDFs, Word documents, text, and markdown files. Choose between completely offline SQLite + hybrid BM25/vector search or cloud-managed Google Gemini File Search, complete with interactive source citation pills (`[^1]`).
* **Live Observability Dashboard**: Trace every request with ASGI `X-Request-ID` correlation, view recent logs in a 1,000-entry in-memory ring buffer, audit rotating disk logs, and monitor live events via the interactive browser UI at `/api/logs/view`.
* **Modular Skills Framework**: Reusable capabilities packaged cleanly under [`.claude/skills/`](.claude/skills/) (`add-image-gen`, `image-to-image`, `livekit-voice-mode`, `add-files-library`).

---

## System Architecture

```
+----------------------------------------------------------------------------------+
|                            FRONTEND (Port 3000)                                  |
|   Next.js 16 (App Router) * React 19 * TypeScript 7 * Tailwind CSS * Lucide UI   |
+----------------------------------------------------------------------------------+
                                        |  HTTP / SSE / WebSockets / WebRTC
                                        v
+----------------------------------------------------------------------------------+
|                            BACKEND (Port 8000)                                   |
|       FastAPI * Python 3.13 * Pydantic v2 * Uvicorn (ASGI) * AsyncIO             |
+----------------------------------------------------------------------------------+
         |                        |                       |                |
         v                        v                       v                v
+------------------+    +-------------------+    +------------------+  +-----------+
| Local AI Engine  |    | Cloud Providers   |    | Image Engines    |  | WebRTC    |
| Ollama (:11434)  |    | OpenAI, Anthropic |    | Pollinations.ai  |  | LiveKit   |
| llama3.2, gemma3 |    | Gemini, Grok, Meta|    | Hugging Face Hub |  | Cloud     |
+------------------+    +-------------------+    +------------------+  +-----------+
```

---

## Directory Structure

```
.
├── .claude/
│   └── skills/                  # Modular skill packages (voice, images, RAG, vision)
├── copilot-app/
│   ├── api/                     # FastAPI backend (Python 3.13, uv, ruff, pytest)
│   │   ├── app/
│   │   │   ├── core/            # Logging, middleware, body limit, config
│   │   │   ├── library/         # Dual-engine RAG (offline SQLite + Gemini)
│   │   │   ├── providers/       # Ollama, OpenAI, Anthropic, Gemini, Grok, Meta
│   │   │   ├── routes/          # chat, images, voice, library, models, logs
│   │   │   └── services/        # Chat streaming, image generation & relay
│   │   ├── logs/                # Rotating disk log files (copilot.log)
│   │   └── tests/               # Unit and integration test suites
│   ├── web/                     # Next.js 16 frontend (React 19, TypeScript 7)
│   │   ├── app/                 # App Router (chat, library, layout, globals)
│   │   ├── components/          # Chat, Composer, Voice, Photos, Library, UI
│   │   ├── hooks/               # useChat, useVoice, useAttachments, useModels
│   │   └── lib/                 # API client, config, types, helpers
│   └── docker-compose.yml       # Containerized deployment orchestration
├── PROJECT_DOCUMENTATION.md     # In-depth technical architecture document
└── README.md                    # Project documentation
```

---

## Quickstart Guide

### Prerequisites
* **Python**: 3.13+ with [uv](https://docs.astral.sh/uv/) installed.
* **Node.js**: 20.9+ with `npm`.
* **Ollama** *(Optional for local AI)*: Download from [ollama.ai](https://ollama.ai).

---

### Step 1: Start Local AI (Recommended)
Pull your preferred local model:
```bash
ollama pull llama3.2
```

---

### Step 2: Launch Backend API
```bash
cd copilot-app/api

# Install dependencies with uv
uv sync

# Configure environment variables (optional cloud keys)
cp .env.example .env

# Run FastAPI development server (Port 8000)
uv run fastapi dev
```

* **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Live Log Dashboard**: [http://localhost:8000/api/logs/view](http://localhost:8000/api/logs/view)
* **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Step 3: Launch LiveKit Voice Agent Worker
In a third terminal (enables real-time WebRTC voice conversations):
```bash
cd copilot-app/agent

# Install voice worker dependencies
uv sync

# Configure LiveKit credentials (match with api/.env)
cp .env.example .env

# Run LiveKit Voice Agent in development mode
uv run python voice_agent.py dev
```

---

### Step 4: Launch Frontend Web UI
In a fourth terminal:
```bash
cd copilot-app/web

# Install npm dependencies
npm install

# Start Next.js development server (Port 3000)
npm run dev
```

* **Web Application**: [http://localhost:3000](http://localhost:3000)

---

### Step 5: Docker Compose (Alternative — All-in-One)
Run the entire platform (API, Voice Agent, and Web) simultaneously:
```bash
cd copilot-app
cp api/.env.example api/.env
cp agent/.env.example agent/.env
docker compose up --build
```

---

## Core Workflows

### 1. Multi-Modal Streaming Chat
Type your message or attach images. The system evaluates whether the model supports vision, queries Ollama, measures **Time-To-First-Token (TTFT)**, and streams Server-Sent Events (SSE) directly into the syntax-highlighted markdown chat. If Ollama is offline or uninstalled, it routes to configured cloud models transparently.

### 2. Generative Image Studio
* **Text-to-Image**: Say `"Generate an image of a cybernetic tiger in neon Tokyo"` or click the image icon in the composer.
* **Image-to-Image**: Attach a picture and type `"Transform this into an oil painting"`. The backend uploads the source photo to an anonymous short-lived relay (`uguu.se`), passes the public URL to the diffusion engine, and returns high-resolution base64 media.
* **Fallback Strategy**: Automatically attempts free Pollinations (FLUX.1) first, falling back to Hugging Face Hub if rate-limited.

### 3. Real-Time WebRTC Voice Mode
Click the microphone button to initiate a WebRTC audio channel with LiveKit. Silero Voice Activity Detection (VAD) detects when you stop speaking, immediately executing speech-to-text, LLM generation, and text-to-speech with natural latency.

### 4. Dual-Engine Document RAG
Upload PDFs, Word files, or Markdown notes into Collections. 
* **Offline Mode**: Uses local SQLite indexing, chunking (500 tokens with 50-token overlap), and vector cosine similarity.
* **Cloud Mode**: Delegates to Google Gemini File Search for enterprise document corpora.
* **Citations**: Injects interactive source badges (`[^1]`) linking directly to source excerpts.

---

## Observability & Live Logging

NexusMind features full-stack observability designed for debugging and transparency:

| Log Channel | Description | Access / Location |
| :--- | :--- | :--- |
| **Console Output** | Formatted stdout with timestamp, level, logger, request tag | Terminal running FastAPI |
| **Rotating Log Files** | 10 MB per file, 5 rotated backups, UTF-8 encoded | `copilot-app/api/logs/copilot.log` |
| **In-Memory Ring Buffer** | Holds the 1,000 most recent log entries with zero disk overhead | Memory (`_log_buffer`) |
| **Interactive Web Viewer** | Real-time auto-refresh, search filter, level selector, copy-to-clipboard | [http://localhost:8000/api/logs/view](http://localhost:8000/api/logs/view) |
| **REST API** | Programmatic log access in JSON or plain text | `GET /api/logs?format=json` |

---

## Quality Checks & Testing

The project enforces clean code, complete type safety, and automated test coverage:

```bash
# Backend unit tests (Chat, Image Gen, Logging, Models)
cd copilot-app/api
uv run pytest tests/test_logging.py tests/test_chat.py tests/test_image_gen.py tests/test_models.py

# Python linting & formatting (Ruff)
uv run ruff check .
uv run ruff format --check .

# Frontend TypeScript verification
cd ../web
npm run typecheck
```

---

## Configuration & Credentials Guide

### 1. Where to Obtain API Keys

| Service / Provider | Purpose | Where to Get | Required / Optional |
| :--- | :--- | :--- | :--- |
| **Ollama** | Local zero-cost LLM (`llama3.2`, `gemma3`) | [ollama.ai](https://ollama.ai) (Run locally) | **Recommended (Default)** |
| **LiveKit Cloud** | WebRTC Real-Time Voice Mode & Audio Transport | [cloud.livekit.io](https://cloud.livekit.io) (Project Settings $\rightarrow$ Keys) | Required for Voice Mode |
| **Hugging Face Hub** | GPU Diffusion Image Generation Fallback | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | Optional (Pollinations is default free) |
| **Google Gemini** | Dual-Engine RAG File Search & Cloud LLM | [aistudio.google.com](https://aistudio.google.com) | Optional (Offline RAG is default free) |
| **OpenAI** | Cloud LLM Fallback (`gpt-4o`, `gpt-4o-mini`) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Optional Fallback |
| **Anthropic** | Cloud LLM Fallback (`claude-3-5-sonnet`) | [console.anthropic.com](https://console.anthropic.com) | Optional Fallback |
| **xAI Grok** | Cloud LLM Fallback (`grok-2`) | [console.x.ai](https://console.x.ai) | Optional Fallback |
| **Meta Llama** | Cloud LLM Fallback (`llama-3.3-70b`) | [llama.meta.com](https://llama.meta.com) | Optional Fallback |

---

### 2. Backend Environment (`copilot-app/api/.env`)
Copy `copilot-app/api/.env.example` to `copilot-app/api/.env`:

```ini
# Core
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
ALLOW_CLOUD_FALLBACK=true

# Local AI (First Priority)
OLLAMA_ENABLED=true
OLLAMA_HOST=http://localhost:11434

# Voice Mode (LiveKit WebRTC) — must match agent/.env
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
VOICE_AGENT_NAME=my-agent
VOICE_AGENT_TOKEN=optional_shared_secret

# Image Generation
HF_TOKEN=your_huggingface_read_token
DEFAULT_HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell

# Document RAG (Google Gemini File Search)
GEMINI_API_KEY=your_gemini_api_key
RAG_MODEL=gemini-3.8-flash

# Cloud LLM Fallbacks (Optional)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROK_API_KEY=your_grok_key
META_API_KEY=your_meta_key
```

---

### 3. Voice Agent Environment (`copilot-app/agent/.env`)
Copy `copilot-app/agent/.env.example` to `copilot-app/agent/.env`:

```ini
# LiveKit Cloud (must match the API settings above)
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
VOICE_AGENT_NAME=my-agent

# Agent Brain (Routes through backend API for unified models & Ollama)
VOICE_LLM=app
API_URL=http://localhost:8000
VOICE_AGENT_TOKEN=optional_shared_secret

# Speech Pipeline Models (LiveKit Inference)
VOICE_STT_MODEL=assemblyai/universal-3-5-pro
VOICE_STT_LANGUAGE=en
VOICE_TTS_MODEL=fishaudio/s2.1-pro
VOICE_NOISE_CANCELLATION=true
VOICE_GREETING=Hi! What can I help you with?
```

---

### 4. Web Frontend Environment (`copilot-app/web/.env.local`)
Copy `copilot-app/web/.env.example` to `copilot-app/web/.env.local`:

```ini
# URL of the FastAPI backend (rewrites /api/* calls)
API_URL=http://localhost:8000
```

---

## Technical Documentation

For an exhaustive architectural deep dive, sequence diagrams, design decisions, and scaling strategies, see:
* **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)**

---

## License

This project is licensed under the [MIT License](LICENSE).