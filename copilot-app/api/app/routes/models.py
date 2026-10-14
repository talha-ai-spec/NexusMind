import logging

from fastapi import APIRouter, Query

from app.deps import RegistryDep, SettingsDep
from app.schemas import ImageLimits, ModelsResponse

logger = logging.getLogger("app.routes.models")

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelsResponse)
async def list_models(
    registry: RegistryDep,
    settings: SettingsDep,
    refresh: bool = Query(default=False, description="Bypass the short-lived model cache"),
) -> ModelsResponse:
    """Local Ollama models plus models from every configured cloud provider."""
    logger.info("[ModelsRoute] Listing available models (refresh=%s)", refresh)
    response = await registry.models_response(refresh=refresh)
    response.image_limits = ImageLimits(
        per_message=settings.max_images_per_message,
        per_request=settings.max_images_per_request,
        max_bytes=settings.max_image_bytes,
    )
    total_models = sum(len(p.models) for p in response.providers)
    default_name = response.default.name if response.default else "None"
    logger.info(
        "[ModelsRoute] Resolved %d models across %d providers (local=%s, default='%s')",
        total_models,
        len(response.providers),
        response.has_local_models,
        default_name,
    )
    return response
