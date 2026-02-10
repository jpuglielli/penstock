"""Logging-based tracing backend (zero external dependencies)."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from penstock._context import _get_or_create_context, current_flow_id
from penstock.backends.base import TracingBackend

logger = logging.getLogger("penstock")


class LoggingBackend(TracingBackend):
    """Emits structured log records for each span start/end."""

    @contextmanager
    def span(self, step_name: str, flow_name: str, **attrs: Any) -> Iterator[None]:
        correlation_id = self.get_correlation_id()
        extra = {
            "flow": flow_name,
            "step": step_name,
            "correlation_id": correlation_id,
            **attrs,
        }
        logger.info("step.start", extra=extra)
        start = time.monotonic()
        try:
            yield
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "step.end",
                extra={**extra, "duration_ms": duration_ms},
            )

    def get_correlation_id(self) -> str:
        cid = current_flow_id()
        if cid is not None:
            return cid
        return _get_or_create_context().correlation_id
