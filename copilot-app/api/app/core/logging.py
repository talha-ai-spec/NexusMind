"""Central logging setup with console formatting, file rotation, and in-memory buffer."""

from __future__ import annotations

import contextvars
import itertools
import logging
import sys
from collections import deque
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# ContextVar for request tracking across async execution
current_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_request_id", default=None
)

# In-memory buffer of recent logs for live inspection / dashboard
MAX_BUFFER_LOGS = 1000
_log_buffer: deque[dict[str, Any]] = deque(maxlen=MAX_BUFFER_LOGS)
_counter = itertools.count(1)


class StructuredFormatter(logging.Formatter):
    """Formats log records with timestamp, level, logger name, and optional request ID."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", None) or current_request_id.get()
        record.req_tag = f" [{req_id}]" if req_id else ""
        return super().format(record)


class InMemoryLogHandler(logging.Handler):
    """Buffers recent log entries in memory for API inspection."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            req_id = getattr(record, "request_id", None) or current_request_id.get()
            msg = record.getMessage()
            entry = {
                "id": next(_counter),
                "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": msg,
                "request_id": req_id,
            }
            _log_buffer.append(entry)
        except Exception:
            self.handleError(record)


def configure_logging(level: str = "INFO", log_dir: str | Path | None = None) -> None:
    """Configures root logger with console output, rotating file handler, and in-memory buffer."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers to avoid duplicates on reload
    for h in list(root.handlers):
        root.removeHandler(h)

    # 1. Console Handler (stdout)
    console_format = "%(asctime)s %(levelname)-7s [%(name)s]%(req_tag)s: %(message)s"
    console_formatter = StructuredFormatter(console_format, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root.addHandler(console_handler)

    # 2. Rotating File Handler
    try:
        if log_dir:
            resolved_log_dir = Path(log_dir)
        else:
            resolved_log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        resolved_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = resolved_log_dir / "copilot.log"

        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(console_formatter)
        root.addHandler(file_handler)
    except Exception as exc:
        sys.stderr.write(f"Warning: Could not initialize log file handler: {exc}\n")

    # 3. In-Memory Buffer Handler (for /api/logs inspection)
    memory_handler = InMemoryLogHandler()
    memory_handler.setLevel(logging.DEBUG)  # capture all levels in buffer
    root.addHandler(memory_handler)

    # Quiet external noisy libraries unless in DEBUG
    if log_level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("watchfiles").setLevel(logging.WARNING)
    else:
        logging.getLogger("httpx").setLevel(logging.INFO)


def get_recent_logs(
    limit: int = 100,
    min_level: str = "DEBUG",
    search: str | None = None,
    request_id: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve filtered recent logs from in-memory buffer."""
    level_order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "WARN": 30, "ERROR": 40, "CRITICAL": 50}
    min_val = level_order.get(min_level.upper(), 10)

    results: list[dict[str, Any]] = []
    # Read from newest to oldest
    for item in reversed(_log_buffer):
        if level_order.get(item["level"], 20) < min_val:
            continue
        if request_id and item.get("request_id") != request_id:
            continue
        if search:
            query = search.lower()
            if query not in item["message"].lower() and query not in item["logger"].lower():
                continue
        results.append(item)
        if len(results) >= limit:
            break

    results.reverse()  # chronological order
    return results


def clear_log_buffer() -> None:
    """Clear all in-memory logs."""
    _log_buffer.clear()
