"""Django middleware that creates a flow context per request.

Add to your ``MIDDLEWARE`` setting::

    MIDDLEWARE = [
        "penstock.contrib.django.FlowMiddleware",
        ...
    ]

Each incoming request gets a :class:`~penstock._context.FlowContext` with a
fresh correlation ID.  The ID is available throughout the request via
:func:`~penstock.current_flow_id` and is attached as the
``X-Correlation-ID`` response header.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from penstock._context import FlowContext, _reset_context, _set_context


class FlowMiddleware:
    """WSGI middleware that wraps each request in a penstock flow context."""

    def __init__(self, get_response: Callable[..., Any]) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        ctx = FlowContext()
        _set_context(ctx)
        try:
            response = self.get_response(request)
            response["X-Correlation-ID"] = ctx.correlation_id
            return response
        finally:
            _reset_context()
