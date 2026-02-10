"""Celery integration that propagates flow context across task boundaries.

Usage::

    from penstock.contrib.celery import flow_task

    @flow("my_flow")
    class MyFlow:
        @entrypoint
        def start(self) -> None:
            process_async.delay()

    @flow_task
    def process_async() -> None:
        # Correlation ID is automatically available here
        print(current_flow_id())

The ``flow_task`` decorator wraps a Celery task so that the caller's
correlation ID is injected into the task headers and restored on the
worker side.
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from penstock._context import FlowContext, _reset_context, _set_context, current_flow_id


def flow_task(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that propagates the penstock correlation ID through Celery.

    Wraps the function so that:

    1. When the task is **called** (producer side), the current correlation ID
       is attached to the Celery message headers.
    2. When the task **executes** (worker side), the correlation ID is restored
       into a :class:`~penstock._context.FlowContext`.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Check for a correlation ID injected by the before_task_publish
        # signal or passed explicitly.
        headers: dict[str, Any] = kwargs.pop("__penstock_headers__", {})
        cid: str | None = headers.get("penstock_correlation_id")

        ctx = FlowContext(correlation_id=cid)
        _set_context(ctx)
        try:
            return fn(*args, **kwargs)
        finally:
            _reset_context()

    # Attach a helper for callers to build the headers dict.
    def _penstock_headers() -> dict[str, str]:
        cid = current_flow_id()
        if cid is not None:
            return {"penstock_correlation_id": cid}
        return {}

    wrapper._penstock_headers = _penstock_headers  # type: ignore[attr-defined]
    return wrapper


def install_celery_signals() -> None:
    """Connect Celery signals for automatic header propagation.

    Call this once at application startup (e.g. in your Celery
    ``app.on_after_configure`` handler) to enable transparent
    correlation ID propagation without manual header management.

    Requires ``celery`` to be installed.
    """
    from celery.signals import (  # type: ignore[import-not-found]
        before_task_publish,
        task_prerun,
    )

    @before_task_publish.connect  # type: ignore[untyped-decorator]
    def _inject_penstock_headers(
        headers: dict[str, Any] | None = None, **_kwargs: Any
    ) -> None:
        if headers is None:
            return
        cid = current_flow_id()
        if cid is not None:
            headers["penstock_correlation_id"] = cid

    @task_prerun.connect  # type: ignore[untyped-decorator]
    def _restore_penstock_context(sender: Any = None, **kwargs: Any) -> None:
        request = getattr(sender, "request", None)
        if request is None:
            return
        cid: str | None = getattr(request, "penstock_correlation_id", None)
        if cid is None:
            # Try headers dict
            req_headers: dict[str, Any] | None = getattr(request, "headers", None)
            if isinstance(req_headers, dict):
                cid = req_headers.get("penstock_correlation_id")
        if cid is not None:
            _set_context(FlowContext(correlation_id=cid))
