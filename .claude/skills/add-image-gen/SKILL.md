---
name: add-image-gen
description: Add production-ready text-to-image generation to this chat app using free cloud engines (Pollinations.ai and Hugging Face Serverless Inference API). Designed specifically for machines without dedicated GPUs. Features zero-config Pollinations.ai (FLUX/Turbo), official Hugging Face InferenceClient with cold-start retry, smart automatic fallback, seamless model picker integration in the header, conversational intent detection ("generate a picture of...", "/imagine"), inline GeneratedImageCard rendering with one-click download, and full Regenerate support with new seeds.
---

# Add Image Generation (Free Online Engines)

A complete, production-grade text-to-image generation capability tailored for systems without dedicated GPUs (e.g. standard laptops with integrated graphics). Generates high-fidelity images in 5–12 seconds without loading local diffusion weights or stressing CPU/RAM.

```
Header Model Picker (Select "FLUX.1" or "SD-Turbo")  OR  Natural Chat ("generate a picture of...")
  │
  ▼
web: use-chat.ts detects intent (or explicit image model)
  │
  ▼ calls POST /api/images/generate
API: app/routes/images.py ──> app/services/image_gen.py
       ├── Engine "huggingface"   ──> HF InferenceClient (FLUX.1-schnell / SDXL with user token)
       ├── Engine "pollinations"  ──> Pollinations.ai (FLUX / Turbo, zero config, free)
       └── Auto Mode              ──> HF if token configured, auto-fallback to Pollinations on 503/429
  │
  ▼ Returns Base64 image payload + media type + engine tag
web: renders <GeneratedImageCard /> inline in assistant message bubble
  ├── Hover actions: One-click Download (PNG/JPG) & Fullscreen View
  └── Message actions: Regenerate button re-calls /api/images/generate with a fresh random seed
```

---

## Why This Architecture?

* **Zero GPU Requirement**: Generates images in 5–12 seconds in the cloud without loading heavy local models (`torch`, `diffusers`, multi-gigabyte safetensors).
* **100% Free**: Pollinations.ai requires no API keys or accounts. Hugging Face serverless tier is free with user access token.
* **Unified Model Selector**: Image models are integrated directly into the header dropdown alongside LLMs under an **Image Generation** group.
* **Conversational AI Flow**: Users don't need separate modal dialogs or sub-menus. They can simply ask *"generate a picture of a cyberpunk samurai"* in normal chat or switch the model picker directly.
* **Smart Fallback**: If Hugging Face is cold (503) or busy, the backend automatically falls back to Pollinations.ai so requests never fail.
* **Regenerate Support**: Clicking the assistant message regenerate button reruns image generation with a new seed instead of erroneously sending the prompt to the text LLM.

---

## Workflow for Claude / Assistant

### 1. Installation

Run the automated installer script:

```bash
# Preview changes
python .claude/skills/add-image-gen/scripts/install_image_gen.py --project copilot-app --dry-run

# Apply changes
python .claude/skills/add-image-gen/scripts/install_image_gen.py --project copilot-app
```

The script will:
1. Copy `config.py`, `images.py`, `image_gen.py`, and `test_image_gen.py` to `api/`.
2. Copy `generated-image-card.tsx`, `model-picker.tsx`, `use-chat.ts`, `helpers.ts`, `types.ts`, and `api.ts` to `web/`.
3. Patch `api/app/main.py` and `api/app/schemas.py`.
4. Patch `web/components/chat/message.tsx` to render `<GeneratedImageCard />`.

If customizing manually, follow [manual-edits.md](references/manual-edits.md).

### 2. Configuration (Optional)

In `copilot-app/api/.env`:

```env
# Optional: Hugging Face Token (if omitted, Pollinations.ai FLUX/Turbo is used automatically)
HUGGINGFACE_TOKEN=hf_your_token_here
DEFAULT_HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell
```

> **Note on Settings loading**: In `api/app/core/config.py`, ensure `load_dotenv(find_dotenv(usecwd=True))` is invoked before `BaseSettings` instantiates so `.env` values are immediately available to `get_settings().hf_token_str`.

### 3. Verification

Always run the quality gates after installation:

```bash
# 1. Backend tests & linting
cd copilot-app/api
uv run pytest tests/test_image_gen.py
uv run pytest
uv run ruff check .
uv run ruff format --check .

# 2. Frontend typecheck & build
cd ../web
npm run typecheck
npm run build
```

---

## Key Assets in this Skill

* `assets/api/app/services/image_gen.py`: Core generation service with Pollinations.ai & Hugging Face `InferenceClient`.
* `assets/api/app/routes/images.py`: FastAPI router with `POST /images/generate` and `GET /images/config`.
* `assets/api/app/core/config.py`: Application settings with `huggingface_token` and `default_hf_image_model`.
* `assets/api/tests/test_image_gen.py`: Pytest test suite covering endpoints and mock generations.
* `assets/web/components/chat/generated-image-card.tsx`: React UI component for message bubbles with one-click download.
* `assets/web/components/chat/model-picker.tsx`: Header model selector containing text models and verified image models.
* `assets/web/hooks/use-chat.ts`: Seamless chat loop handling image models, intent routing, and regenerate logic.
* `assets/web/lib/helpers.ts`: Conversational intent detection regex patterns (`detectImagePrompt`).
* `assets/web/lib/types.ts`: `GeneratedImage` & `VERIFIED_IMAGE_MODELS` definitions.
* `assets/web/lib/api.ts`: Frontend client calling `POST /api/images/generate`.
* `scripts/install_image_gen.py`: Automated installer script.
* `references/setup-guide.md`: User guide for selecting models and adding HF tokens.
* `references/manual-edits.md`: Exact code diffs for reference.
* `references/architecture.md`: Detailed architecture and lifecycle diagram.
