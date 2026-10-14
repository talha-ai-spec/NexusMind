# Image Generation Setup Guide

This guide walks you through configuring, using, and getting the highest quality images out of the image generation feature in your copilot application.

---

## 1. Engine Options & Comparison

The system supports two free cloud engines with automatic failover:

| Engine | Setup Needed | Speed | Quality | Notes |
|---|---|---|---|---|
| **FLUX.1-schnell** *(Hugging Face)* | Free HF API Token | 8–18 seconds | ★★★★★ (Ultra High) | Official state-of-the-art 12B parameter FLUX model hosted on Hugging Face Inference API. |
| **FLUX.1** *(Pollinations.ai)* | **None** (Zero config) | 8–15 seconds | ★★★★★ (Ultra High) | Top quality cloud FLUX.1. Runs free without keys or registration. |
| **SD-Turbo** *(Pollinations.ai)* | **None** (Zero config) | 2–4 seconds | ★★★☆☆ (Fast Draft) | Instant real-time single-step generation for quick mockups. |

> **Smart Fallback**: If you configure a Hugging Face token and the HF model is temporarily warming up (503) or rate-limited (429), the backend automatically falls back to Pollinations.ai so the user never gets an error.

---

## 2. Setting Up Hugging Face (Recommended for Best Quality)

To connect your own Hugging Face token:

1. Create a free account at [huggingface.co](https://huggingface.co).
2. Go to **Settings $\rightarrow$ Access Tokens** ([huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)).
3. Click **Create new token**, choose **Read** role, and copy the generated token (`hf_...`).
4. In `copilot-app/api/.env`, add:
   ```env
   # Hugging Face Token for serverless inference
   HUGGINGFACE_TOKEN=hf_your_actual_token_here
   DEFAULT_HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell
   ```
5. Restart or reload the FastAPI backend:
   ```bash
   cd copilot-app/api
   uv run fastapi dev
   ```
6. The app will immediately recognize the token and prioritize official FLUX.1-schnell inference.

---

## 3. How to Use in the Web App

The application provides two intuitive, frictionless ways to generate images:

### Method A — Select Model in Header Dropdown
1. Click the top model picker in the header (where you select Ollama or cloud models).
2. Scroll to the **Image Generation** section and pick:
   - **FLUX.1-schnell (Hugging Face)**
   - **FLUX.1 (Pollinations)**
   - **SD-Turbo (Pollinations)**
3. The prompt button turns into an amber Sparkles icon (`✨`).
4. Type any description (e.g. *"futuristic cyberpunk city with flying vehicles, octane render, 8k"*) and press Enter.
5. The image is generated and displayed directly in the chat!

### Method B — Conversational Trigger in Normal Chat
You don't even have to change models in the dropdown! While chatting with any text model, simply write naturally:
- *"generate a picture of a cute red panda wearing glasses"*
- *"draw a medieval castle on a misty cliff"*
- *"create an image of a vintage 1980s computer workstation"*
- or use slash commands: `/imagine a neon hologram cat` or `/image cozy coffee shop rainy day`

The app automatically intercepts the visual intent, generates the image in the chat stream, and displays the card.

---

## 4. Features & Actions

* **One-Click Download**: Hover over the image and click the **Download** button to save the full-resolution PNG/JPG directly to your computer.
* **Fullscreen Viewer**: Click the **View** button or tap the image to open it fullscreen with zoom and pan controls.
* **Regenerate Button**: Click the refresh/regenerate icon below the assistant message to re-generate the image with a brand new random seed.

---

## 5. Testing the API Directly

You can test the endpoint using curl or HTTP tools:

```bash
# Test with Pollinations.ai (zero config, no key needed)
curl -X POST http://localhost:8000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A serene mountain lake at sunrise, oil painting", "engine": "pollinations"}'

# Test with Hugging Face (requires token in api/.env)
curl -X POST http://localhost:8000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Detailed portrait of an astronaut exploring Mars", "engine": "huggingface"}'

# Check configuration status
curl http://localhost:8000/api/images/config
```
