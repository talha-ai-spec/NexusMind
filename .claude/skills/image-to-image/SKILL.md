---
name: image-to-image
description: Add AI photo editing, style transfer, and image-to-image transformation to this chat app without requiring a local GPU. Users can attach a source photo via the composer ('Add photos') and write natural instructions ('turn this into anime', 'make this an oil painting', 'restyle this photo'). Features automatic visual intent detection, base64 image extraction from IndexedDB, temporary cloud relay upload (uguu.se with freeimage.host fallback), Pollinations.ai cloud img2img transformation, inline GeneratedImageCard rendering with one-click download, user bubble source photo preservation, and full Regenerate support with new random seeds.
---

# Image-to-Image / AI Photo Editing

A complete, production-ready AI image editing and style transfer capability tailored for chat copilots running on machines without dedicated GPUs. Enables users to upload any photo or artwork and restyle it using natural conversational prompts.

```
User attaches photo via [+] ──> Types "turn this into an anime watercolor painting"
  │
  ▼
web: use-chat.ts & helpers.ts
  ├── detectImagePrompt() matches editing pattern ("turn this into...")
  ├── Loads image blob from IndexedDB (loadImage) & converts to Base64
  └── Calls POST /api/images/generate with { prompt, image: base64Data, strength: 0.7 }
  │
  ▼
API: app/routes/images.py ──> app/services/image_gen.py
  ├── upload_temp_image(): Relays base64 to fast anonymous cloud buffer (uguu.se / freeimage.host)
  └── generate_with_pollinations(prompt, image_url=source_url): Cloud transformation runs in 5–12s
  │
  ▼ Returns Base64 edited image payload + media type + "Pollinations.ai (Image-to-Image)"
web: renders user bubble with source photo chip + assistant bubble with <GeneratedImageCard />
  ├── Actions: One-click Download (PNG/JPG) & Fullscreen View
  └── Message Actions: Regenerate button re-runs editing with a new random seed
```

---

## Why This Architecture?

* **Zero GPU Requirement**: Running local Stable Diffusion img2img or ControlNet requires a high-end NVIDIA GPU (8GB–16GB VRAM) and heavy dependencies (`diffusers`, `torch`, ~10GB model weights). This skill runs 100% in the cloud without stressing the host machine's CPU or RAM.
* **Completely Free**: Relies on Pollinations.ai cloud img2img pipeline — no subscriptions, API keys, or credit cards required.
* **Zero Disk Bloat**: Local uploads are kept ephemeral. Base64 is relayed securely to temporary storage with a 3-hour expiry.
* **Frictionless UX**: Users don't need a separate mode or dialog. They simply attach a photo and chat naturally: *"turn this into a cartoon"*, *"make this look like cyberpunk"*, *"restyle this as an oil painting"*.

---

## Workflow for Claude / Assistant

### 1. Installation

Run the automated installer script:

```bash
# Preview changes
python .claude/skills/image-to-image/scripts/install_img2img.py --project copilot-app --dry-run

# Execute installation
python .claude/skills/image-to-image/scripts/install_img2img.py --project copilot-app
```

The script will:
1. Update `api/app/services/image_gen.py` with `upload_temp_image` and `generate_image_to_image`.
2. Update `api/app/routes/images.py` request schema with `image: str | None = None`.
3. Add unit tests to `api/tests/test_image_gen.py`.
4. Update `web/lib/api.ts` with `image?: string` in `GenerateImageParams`.
5. Update `web/lib/helpers.ts` with photo editing regex patterns in `detectImagePrompt`.
6. Update `web/hooks/use-chat.ts` to convert attached images to base64 and pass to `generateImage` on `send` and `regenerate`.

For manual inspection or customized codebases, refer to [manual-edits.md](references/manual-edits.md).

### 2. Verification

Run the test suite and quality gates after installation:

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

* `assets/api/app/services/image_gen.py`: Img2img service with `upload_temp_image` relay and Pollinations transformation.
* `assets/api/app/routes/images.py`: FastAPI route supporting both text-to-image and image-to-image payloads.
* `assets/api/tests/test_image_gen.py`: Comprehensive Pytest suite for img2img endpoints and mock transfers.
* `assets/web/lib/helpers.ts`: Conversational intent detection regex patterns for restyling and editing.
* `assets/web/lib/api.ts`: API client function supporting base64 source image payloads.
* `assets/web/hooks/use-chat.ts`: Chat hook integrating photo extraction, base64 conversion, and seed randomization on regenerate.
* `scripts/install_img2img.py`: Automated installer.
* `references/architecture.md`: Detailed system architecture and sequence diagram.
* `references/manual-edits.md`: Step-by-step diffs for manual integration.
* `references/setup-guide.md`: End-user guide for photo editing prompts and capabilities.
* `references/troubleshooting.md`: Common failure modes, limits, and solutions.
