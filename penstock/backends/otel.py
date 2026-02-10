"""OpenTelemetry tracing backend.

Requires ``opentelemetry-api`` and ``opentelemetry-sdk`` to be installed.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from penstock.backends.base import TracingBackend

try:
    from opentelemetry import trace  # type: ignore[import-not-found]

    _HAS_OTEL = True
except ImportError:  # pragma: no cover
    _HAS_OTEL = False


class OTelBackend(TracingBackend):
    """Emits real OpenTelemetry spans for each flow step.

    Requires ``opentelemetry-api`` to be installed.  Raises
    :class:`RuntimeError` at construction time if the package is missing.
    """

    def __init__(self, tracer_name: str = "penstock") -> None:
        if not _HAS_OTEL:
            raise RuntimeError(
                "opentelemetry-api is required for OTelBackend. "
                "Install it with: pip install opentelemetry-api opentelemetry-sdk"
            )
        self._tracer = trace.get_tracer(tracer_name)

    @contextmanager
    def span(self, step_name: str, flow_name: str, **attrs: Any) -> Iterator[None]:
        with self._tracer.start_as_current_span(
            step_name,
            attributes={"penstock.flow": flow_name, **attrs},
        ):
            yield

    def get_correlation_id(self) -> str:
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx is not None and ctx.trace_id:
            return format(ctx.trace_id, "032x")
        return ""
