"""API routes for text-to-image generation."""

from __future__ import annotations

import base64
import logging
import time
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.image_gen import (
    DEFAULT_HF_MODEL,
    generate_image,
    generate_image_to_image,
)

logger = logging.getLogger("app.routes.images")

router = APIRouter(prefix="/images", tags=["images"])


class ImageGenRequest(BaseModel):
    prompt: str = Field(
        ..., min_length=1, max_length=2000, description="Text prompt describing the image"
    )
    image: str | None = Field(
        default=None, description="Optional base64 encoded source image or URL for image-to-image"
    )
    strength: float | None = Field(default=0.7, ge=0.0, le=1.0)
    engine: Literal["auto", "pollinations", "huggingface"] = "auto"
    model: str | None = None
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    seed: int | None = None


class GeneratedImageItem(BaseModel):
    id: str
    media_type: str
    data: str  # Base64 encoded image string
    engine: str
    prompt: str


class ImageGenResponse(BaseModel):
    image: GeneratedImageItem


class ImageGenConfigResponse(BaseModel):
    engines: list[str]
    default_engine: str
    has_huggingface_token: bool
    default_hf_model: str


@router.get("/config", response_model=ImageGenConfigResponse)
async def get_image_config() -> ImageGenConfigResponse:
    """Get image generation configuration and available engines."""
    settings = get_settings()
    hf_token = settings.hf_token_str
    logger.debug("[ImageRoute] Config requested (has_hf_token=%s)", bool(hf_token))
    return ImageGenConfigResponse(
        engines=["pollinations", "huggingface", "auto"],
        default_engine="auto",
        has_huggingface_token=bool(hf_token),
        default_hf_model=settings.default_hf_image_model or DEFAULT_HF_MODEL,
    )


@router.post("/generate", response_model=ImageGenResponse, status_code=status.HTTP_200_OK)
async def generate_image_endpoint(request: ImageGenRequest) -> ImageGenResponse:
    """Generate an image from a text prompt using Pollinations or Hugging Face."""
    settings = get_settings()
    hf_token = settings.hf_token_str
    hf_model = request.model or settings.default_hf_image_model or DEFAULT_HF_MODEL
    start_time = time.perf_counter()

    prompt_preview = (request.prompt[:60] + "...") if len(request.prompt) > 60 else request.prompt
    logger.info(
        "[ImageRoute] Starting: prompt='%s', engine='%s', model='%s', size=%dx%d, img2img=%s",
        prompt_preview,
        request.engine,
        hf_model,
        request.width,
        request.height,
        bool(request.image),
    )

    try:
        if request.image:
            raw_bytes, media_type, engine_used = await generate_image_to_image(
                request.prompt,
                request.image,
                engine=request.engine,
                hf_token=hf_token,
                hf_model=hf_model,
                width=request.width,
                height=request.height,
                seed=request.seed,
            )
        else:
            is_poll = request.engine == "pollinations"
            poll_model = request.model if is_poll and request.model else "flux"
            raw_bytes, media_type, engine_used = await generate_image(
                request.prompt,
                engine=request.engine,
                hf_token=hf_token,
                hf_model=hf_model,
                width=request.width,
                height=request.height,
                seed=request.seed,
                pollinations_model=poll_model,
            )
        elapsed = time.perf_counter() - start_time
        logger.info(
            "[ImageRoute] Image generated successfully: engine='%s', size=%.1f KB (%s) in %.2fs",
            engine_used,
            len(raw_bytes) / 1024,
            media_type,
            elapsed,
        )
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        logger.error(
            "[ImageRoute] Image generation failed after %.2fs: %s",
            elapsed,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Image generation failed: {e}",
        ) from e

    image_id = uuid.uuid4().hex
    b64_data = base64.b64encode(raw_bytes).decode("ascii")

    return ImageGenResponse(
        image=GeneratedImageItem(
            id=image_id,
            media_type=media_type,
            data=b64_data,
            engine=engine_used,
            prompt=request.prompt,
        )
    )
