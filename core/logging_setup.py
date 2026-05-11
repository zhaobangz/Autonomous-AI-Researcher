"""
core/logging_setup.py — Logging configuration for the entire application.

Call `configure_logging()` once at process startup (e.g. at the top of
api/server.py and ui/app.py).  Every other module then uses a standard:

    import logging
    logger = logging.getLogger(__name__)

Features:
  - Human-readable console format in development (log_json=False)
  - JSON-line format in production / Docker (log_json=True)
  - Suppresses noisy third-party loggers at WARNING level
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------
class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Attach any extra fields attached via logger.info("…", extra={…})
        _std = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, val in record.__dict__.items():
            if key not in _std and not key.startswith("_"):
                payload[key] = val
        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Human-readable formatter
# ---------------------------------------------------------------------------
_CONSOLE_FMT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
_CONSOLE_DATE = "%H:%M:%S"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_configured = False


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Configure root logger. Safe to call multiple times (idempotent)."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_CONSOLE_FMT, datefmt=_CONSOLE_DATE))
    root.addHandler(handler)

    # Quiet the chattiest third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3", "asyncio",
                  "sentence_transformers", "transformers", "torch"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — equivalent to logging.getLogger(name)."""
    return logging.getLogger(name)
