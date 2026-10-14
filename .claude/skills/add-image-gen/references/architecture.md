# Image Generation Architecture

This document describes the architectural flow for text-to-image generation in the copilot application.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Next.js Frontend                              │
│                                                                        │
│  ModelPicker: Header dropdown allows selecting FLUX.1 / SD-Turbo       │
│  Composer: User submits prompt or types "generate a picture of..."     │
│                              │                                         │
│                              ▼                                         │
│  use-chat.ts:                                                          │
│  - Checks if image model is active OR detectImagePrompt(text) matches  │
│  - Appends user message & pending assistant message bubble             │
│  - Calls generateImage() in web/lib/api.ts                             │
│  - On success: sets message.generatedImage = img                       │
│  - On regenerate(): re-runs with fresh random seed                     │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                               │ HTTP POST /api/images/generate
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Backend                               │
│                                                                        │
│  app/routes/images.py                                                  │
│  - ImageGenRequest: validates prompt, engine, model, width, height     │
│  - Checks app/core/config.py for HUGGINGFACE_TOKEN                     │
│                              │                                         │
│                              ▼                                         │
│  app/services/image_gen.py                                             │
│  - Smart Fallback Router:                                              │
└───────────────┬───────────────────────────────────────┬────────────────┘
                │                                       │
    (Default / Fallback)                        (If HF token set)
                │                                       │
                ▼                                       ▼
┌───────────────────────────────┐       ┌────────────────────────────────┐
│        Pollinations.ai        │       │  Hugging Face InferenceClient  │
│                               │       │                                │
│ - Zero-config, completely free│       │ - Uses user token from .env    │
│ - Models: FLUX.1, SD-Turbo    │       │ - Model: FLUX.1-schnell (12B)  │
│ - Async HTTP GET stream       │       │ - Cloud serverless GPU worker  │
│ - Speed: 5–12 seconds         │       │ - Retries 503 cold starts      │
│ - Automatic 402/429 retry     │       │ - Automatic fallback on error  │
└───────────────────────────────┘       └────────────────────────────────┘
```

---

## 1. Intent Detection vs Explicit Selection

The system provides dual-mode triggering:
1. **Explicit Mode**: User selects an image model from the header `ModelPicker`. The send button switches to an amber Sparkles icon (`✨`). Every message sent in this state is treated as an image prompt.
2. **Implicit Conversational Mode**: User stays on their favorite text model (e.g. `gemma3:1b` or `claude-3-7-sonnet`). When they write conversational phrases like *"generate a picture of..."*, *"draw a..."*, or slash commands like `/imagine`, the app routes that specific turn to image generation while keeping the conversation intact.

---

## 2. Serverless Execution & Zero Local Resource Footprint

Standard laptops running integrated graphics cannot run 12B parameter FLUX models locally without freezing or running out of RAM.
- **Zero local weight loading**: The Python backend requires no PyTorch or CUDA.
- **Non-blocking async HTTP**: All generation requests stream through `httpx.AsyncClient` or offloaded thread pools (`asyncio.to_thread`).
- **Memory safety**: Generated images are transmitted as base64 in the response payload and loaded directly into HTML `<img>` elements without persistent disk bloat.
