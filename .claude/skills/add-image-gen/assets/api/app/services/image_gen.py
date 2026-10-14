"""Image generation service supporting Pollinations.ai and Hugging Face Inference API.

Features:
- Pollinations.ai: Zero-config, free, high-speed image generation using FLUX/Turbo.
- Hugging Face: Official InferenceClient with user token, supports FLUX.1-schnell.
- Smart Fallback: Automatically falls back to Pollinations if HF is offline or unconfigured.
- Pure Python & async worker execution.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import urllib.parse
from typing import Literal

import httpx
from huggingface_hub import InferenceClient

logger = logging.getLogger("app.services.image_gen")

DEFAULT_HF_MODEL = "black-forest-labs/FLUX.1-schnell"


async def generate_with_pollinations(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    model: str = "flux",
    enhance: bool = False,
    image_url: str | None = None,
    request_timeout: float = 60.0,
) -> tuple[bytes, str]:
    """Generate image using Pollinations.ai (Free, zero-config, runs in cloud)."""
    clean_prompt = prompt.strip()
    encoded = urllib.parse.quote(clean_prompt)
    params = [
        f"model={model}",
        f"width={width}",
        f"height={height}",
        "nologo=true",
        "private=true",
    ]
    if image_url:
        params.append(f"image={urllib.parse.quote(image_url, safe='')}")
    if seed is not None:
        params.append(f"seed={seed}")
    if enhance:
        params.append("enhance=true")

    url = f"https://image.pollinations.ai/prompt/{encoded}?{'&'.join(params)}"
    logger.info("Calling Pollinations.ai: width=%d, height=%d, model=%s", width, height, model)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        res = await client.get(url, timeout=request_timeout)

        # If flux encounters burst limits (402/429) or temporary server cluster errors (5xx/530):
        # retry automatically with the resilient turbo model
        if (
            res.status_code in (402, 429, 500, 502, 503, 504, 520, 521, 522, 530)
            and model != "turbo"
        ):
            logger.warning(
                "Pollinations model %s returned %d, retrying with fast turbo model...",
                model,
                res.status_code,
            )
            fallback_params = [
                f"width={width}",
                f"height={height}",
                "model=turbo",
                "nologo=true",
                "private=true",
            ]
            if image_url:
                fallback_params.append(f"image={urllib.parse.quote(image_url, safe='')}")
            if seed is not None:
                fallback_params.append(f"seed={seed}")
            fallback_url = (
                f"https://image.pollinations.ai/prompt/{encoded}?{'&'.join(fallback_params)}"
            )
            res = await client.get(fallback_url, timeout=request_timeout)

        if res.status_code in (401, 402, 429):
            if image_url:
                raise RuntimeError(
                    "Cloud photo editing requires a Pollinations API key or is currently "
                    "unavailable on the free tier. Please use text prompts to generate images."
                )
            raise RuntimeError(
                "Free generation capacity temporarily busy. Please wait 30s and click Try again."
            )

        if res.status_code != 200:
            raise RuntimeError(
                f"Pollinations generation failed with status {res.status_code}: {res.text[:200]}"
            )
        media_type = res.headers.get("content-type", "image/jpeg").split(";")[0]
        return res.content, media_type


async def generate_with_huggingface(
    prompt: str,
    *,
    token: str | None = None,
    model: str = DEFAULT_HF_MODEL,
    max_retries: int = 2,
    request_timeout: float = 90.0,
) -> tuple[bytes, str]:
    """Generate image using Hugging Face official InferenceClient."""
    logger.info("Calling Hugging Face InferenceClient: model=%s", model)
    client = InferenceClient(token=token, timeout=request_timeout)

    def _sync_generate() -> bytes:
        img = client.text_to_image(prompt.strip(), model=model)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    for attempt in range(max_retries + 1):
        try:
            raw_bytes = await asyncio.to_thread(_sync_generate)
            return raw_bytes, "image/png"
        except Exception as e:
            err_str = str(e)
            if "503" in err_str and attempt < max_retries:
                logger.info(
                    "HF model is loading, waiting 15s (attempt %d)...",
                    attempt + 1,
                )
                await asyncio.sleep(15.0)
                continue
            raise RuntimeError(f"Hugging Face generation failed: {e}") from e

    raise RuntimeError("Hugging Face API timed out during model loading.")


async def generate_image(
    prompt: str,
    *,
    engine: Literal["auto", "pollinations", "huggingface"] = "auto",
    hf_token: str | None = None,
    hf_model: str = DEFAULT_HF_MODEL,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    pollinations_model: str = "flux",
) -> tuple[bytes, str, str]:
    """Unified image generation router with smart fallback."""
    # 1. Hugging Face requested explicitly
    if engine == "huggingface":
        if not hf_token:
            logger.error("Hugging Face engine selected but HUGGINGFACE_TOKEN is not configured.")
            raise RuntimeError(
                "Hugging Face token not configured. Please set HUGGINGFACE_TOKEN in api/.env"
            )
        try:
            img_bytes, media = await generate_with_huggingface(
                prompt, token=hf_token, model=hf_model
            )
            return img_bytes, media, f"Hugging Face ({hf_model.rsplit('/', maxsplit=1)[-1]})"
        except Exception as e:
            err_msg = str(e).lower()
            if "402" in err_msg or "credit" in err_msg:
                raise RuntimeError(
                    "Hugging Face returned 402: You have no remaining Inference Provider credits "
                    "for FLUX.1-schnell. Please select 'FLUX.1 (Pollinations)' or 'SD-Turbo' from "
                    "the top model picker to generate images completely free."
                ) from e
            logger.error(
                "Hugging Face generation failed (%s), falling back to Pollinations.ai",
                e,
                exc_info=True,
            )
            img_bytes, media = await generate_with_pollinations(
                prompt, width=width, height=height, seed=seed, model=pollinations_model
            )
            return img_bytes, media, "Pollinations.ai (Fallback)"

    # 2. Auto mode: Use HF if token is provided, otherwise use Pollinations
    if engine == "auto" and hf_token:
        try:
            img_bytes, media = await generate_with_huggingface(
                prompt, token=hf_token, model=hf_model
            )
            return img_bytes, media, f"Hugging Face ({hf_model.rsplit('/', maxsplit=1)[-1]})"
        except Exception as e:
            logger.warning("HF auto-call failed (%s), falling back to Pollinations.ai", e)

    # 3. Pollinations.ai (default or fallback)
    img_bytes, media = await generate_with_pollinations(
        prompt, width=width, height=height, seed=seed, model=pollinations_model
    )
    return img_bytes, media, f"Pollinations.ai ({pollinations_model.capitalize()})"


async def upload_temp_image(image_data: str) -> str:
    """Uploads a base64 image or returns a URL so cloud inference can access it."""
    if image_data.startswith(("http://", "https://")):
        return image_data

    raw_b64 = image_data
    if "," in raw_b64 and "base64" in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    raw_bytes = base64.b64decode(raw_b64)
    logger.info(
        "Relaying source image (%d bytes) to temporary public host for cloud processing...",
        len(raw_bytes),
    )

    # 1. Try uguu.se (fast, anonymous, 3h expiry)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                "https://uguu.se/upload",
                files={"files[]": ("source.jpg", raw_bytes, "image/jpeg")},
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("success") and data.get("files"):
                    uploaded_url = data["files"][0]["url"]
                    logger.info("Source image uploaded to uguu.se: %s", uploaded_url)
                    return uploaded_url
    except Exception as e:
        logger.warning("uguu.se upload failed (%s), trying freeimage.host fallback", e)

    # 2. Try freeimage.host fallback
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            form = {
                "key": "6d207e02198a847aa98d0a2a901485a5",
                "action": "upload",
                "source": base64.b64encode(raw_bytes).decode("ascii"),
                "format": "json",
            }
            res = await client.post("https://freeimage.host/api/1/upload", data=form)
            if res.status_code == 200:
                data = res.json()
                if data.get("image", {}).get("url"):
                    uploaded_url = data["image"]["url"]
                    logger.info("Source image uploaded to freeimage.host: %s", uploaded_url)
                    return uploaded_url
    except Exception as e:
        logger.warning("freeimage.host upload failed (%s)", e)

    raise RuntimeError("Failed to prepare source image for cloud processing.")


async def generate_image_to_image(
    prompt: str,
    image_input: str,
    *,
    engine: Literal["auto", "pollinations", "huggingface"] = "auto",
    hf_token: str | None = None,
    hf_model: str | None = None,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> tuple[bytes, str, str]:
    """Transform or edit an image using Pollinations with smart fallback."""
    source_url = await upload_temp_image(image_input)
    logger.info("Source image ready for img2img: %s", source_url)

    try:
        img_bytes, media = await generate_with_pollinations(
            prompt,
            width=width,
            height=height,
            seed=seed,
            image_url=source_url,
        )
        return img_bytes, media, "Pollinations.ai (Image-to-Image)"
    except Exception as e:
        logger.error("Pollinations img2img failed (%s)", e, exc_info=True)
        raise RuntimeError(f"Image editing failed: {e}") from e
