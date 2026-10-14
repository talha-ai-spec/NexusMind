"""Streams a chat reply, falling back to the next provider when one fails.

Fallback only happens before the first token is sent; once text has reached
the client, switching models mid-answer would produce a garbled reply, so a
later failure is reported as an error instead.
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.providers.base import ProviderError
from app.providers.registry import ProviderRegistry
from app.schemas import ChatMessage, ChatRequest

logger = logging.getLogger(__name__)


@dataclass
class ChatEvent:
    type: str  # "meta" | "delta" | "error" | "done"
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        payload = json.dumps(self.data, ensure_ascii=False)
        if self.type == "delta":
            return f"data: {payload}\n\n"
        return f"event: {self.type}\ndata: {payload}\n\n"


NO_MODELS_MESSAGE = (
    "No AI model is available. Install a local model with `ollama pull llama3.2`, "
    "or add a cloud API key (Anthropic, OpenAI, Gemini, Grok or Meta) to the API's .env file."
)


NO_VISION_MESSAGE = (
    "No model that can see images is available. Install one with `ollama pull gemma3` "
    "(or `ollama pull llava`), or add a cloud API key, then try again."
)


def text_only_message(model: str) -> str:
    return (
        f'{model} can\'t see images. Pick a model marked "Sees images", '
        "or remove the photos from this chat."
    )


def _meta_event(provider: Any, model: str, failures: list[str]) -> ChatEvent:
    return ChatEvent(
        "meta",
        {
            "provider": provider.id,
            "provider_label": provider.label,
            "model": model,
            "local": provider.local,
            "fallback": bool(failures),
            "notice": "; ".join(failures) or None,
        },
    )


class ChatService:
    def __init__(self, registry: ProviderRegistry, system_prompt: str, allow_fallback: bool):
        self._registry = registry
        self._system_prompt = system_prompt
        self._allow_fallback = allow_fallback

    def _with_system(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        if not self._system_prompt or any(m.role == "system" for m in messages):
            return messages
        return [ChatMessage(role="system", content=self._system_prompt), *messages]

    async def _resolve_candidates(
        self, request: ChatRequest, vision: bool
    ) -> tuple[list[Any], str | None]:
        if vision and request.provider:
            provider = self._registry.get(request.provider)
            chosen = request.model or (provider.default_model if provider else "")
            if chosen:
                can_see, name = await self._registry.vision_check(request.provider, chosen)
                if not can_see:
                    return [], text_only_message(name)
        try:
            candidates = await self._registry.candidates(
                request.provider, request.model, self._allow_fallback, vision=vision
            )
        except ProviderError as exc:
            logger.error("[ChatService] Failed to resolve candidate models: %s", exc)
            return [], str(exc)

        if not candidates:
            message = NO_VISION_MESSAGE if vision else NO_MODELS_MESSAGE
            logger.warning("[ChatService] No candidate models available (vision=%s)", vision)
            return [], message

        return candidates, None

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatEvent]:
        # Any photo in the conversation needs a model that can read it.
        vision = any(m.images for m in request.messages)
        candidates, err_msg = await self._resolve_candidates(request, vision)
        if err_msg or not candidates:
            yield ChatEvent("error", {"message": err_msg or NO_MODELS_MESSAGE})
            return

        logger.info(
            "[ChatService] Candidate models to try: %s",
            [f"{c.provider.id}::{c.model}" for c in candidates],
        )

        messages = self._with_system(request.messages)
        failures: list[str] = []

        for candidate in candidates:
            provider, model = candidate.provider, candidate.model
            started = False
            delta_count = 0
            total_chars = 0
            cand_start = time.perf_counter()
            logger.info(
                "[ChatService] Attempting generation with provider=%s, model=%s (is_fallback=%s)",
                provider.id,
                model,
                bool(failures),
            )
            try:
                async for delta in provider.stream_chat(model, messages, request.temperature):
                    if not started:
                        started = True
                        ttft = time.perf_counter() - cand_start
                        logger.info(
                            "[ChatService] First token from %s/%s (TTFT: %.3fs)",
                            provider.id,
                            model,
                            ttft,
                        )
                        yield _meta_event(provider, model, failures)
                    delta_count += 1
                    total_chars += len(delta)
                    yield ChatEvent("delta", {"delta": delta})
            except ProviderError as exc:
                elapsed = time.perf_counter() - cand_start
                logger.warning(
                    "[ChatService] Provider %s/%s failed after %.2fs: %s",
                    provider.id,
                    model,
                    elapsed,
                    exc,
                )
                if started:
                    yield ChatEvent("error", {"message": str(exc)})
                    return
                failures.append(str(exc))
                self._registry.invalidate()
                continue

            elapsed = time.perf_counter() - cand_start
            if not started:  # provider returned an empty reply; treat as success
                logger.info(
                    "[ChatService] %s/%s returned an empty reply (took %.2fs)",
                    provider.id,
                    model,
                    elapsed,
                )
                yield _meta_event(provider, model, failures)
            else:
                rate = (delta_count / elapsed) if elapsed > 0 else 0
                logger.info(
                    "[ChatService] Stream done %s/%s: %d deltas (~%d ch) in %.2fs (%.1f d/s)",
                    provider.id,
                    model,
                    delta_count,
                    total_chars,
                    elapsed,
                    rate,
                )
            yield ChatEvent("done", {})
            return

        logger.error("[ChatService] All candidate providers failed: %s", failures)
        yield ChatEvent("error", {"message": " · ".join(failures) or NO_MODELS_MESSAGE})
