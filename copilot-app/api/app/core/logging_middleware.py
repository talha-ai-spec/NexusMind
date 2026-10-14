"""ASGI middleware for structured request/response lifecycle logging with correlation IDs."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import current_request_id

logger = logging.getLogger("app.http")


class RequestLoggingMiddleware:
    """Logs incoming HTTP requests, response status codes, execution duration, and attaches IDs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        # Check if client provided X-Request-ID, otherwise generate one
        client_req_id = headers.get(b"x-request-id")
        req_id = (
            client_req_id.decode("utf-8", errors="replace")
            if client_req_id
            else f"req-{uuid.uuid4().hex[:8]}"
        )

        token = current_request_id.set(req_id)
        start_time = time.perf_counter()

        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        query = scope.get("query_string", b"").decode("utf-8", errors="replace")
        query_str = f"?{query}" if query else ""

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        # Log incoming request
        logger.info("--> [HTTP] %s %s%s from %s", method, path, query_str, client_ip)

        status_code = 500  # fallback in case response start is never called

        async def logging_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                # Inject X-Request-ID header into outgoing response
                resp_headers = list(message.get("headers") or [])
                resp_headers.append((b"x-request-id", req_id.encode("utf-8")))
                message["headers"] = resp_headers
            await send(message)

        try:
            await self.app(scope, receive, logging_send)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_level = logging.WARNING if status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                "<-- [HTTP] %s %s%s [%d] in %.1fms",
                method,
                path,
                query_str,
                status_code,
                duration_ms,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "<XX [HTTP] %s %s%s FAILED after %.1fms: %s",
                method,
                path,
                query_str,
                duration_ms,
                exc,
            )
            raise
        finally:
            current_request_id.reset(token)
