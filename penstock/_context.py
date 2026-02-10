"""Flow context propagation via contextvars."""

from __future__ import annotations

import copy
import uuid
from contextvars import ContextVar
from typing import Any


class FlowContext:
    """Carries a correlation ID and arbitrary metadata through a flow execution.

    Thread-safe and async-safe via ``contextvars``.  Use :meth:`fork` to
    create a child context that shares the correlation ID but gets an
    independent deep-copy of metadata (useful for Celery / cross-process).
    """

    __slots__ = ("_metadata", "correlation_id")

    def __init__(
        self,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.correlation_id: str = correlation_id or uuid.uuid4().hex
        self._metadata: dict[str, Any] = metadata if metadata is not None else {}

    # -- value helpers --------------------------------------------------------

    def get_value(self, key: str, default: Any = None) -> Any:
        """Return a metadata value, or *default* if the key is absent."""
        return self._metadata.get(key, default)

    def set_value(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        self._metadata[key] = value

    def delete_value(self, key: str) -> None:
        """Remove a metadata key. Raises ``KeyError`` if absent."""
        del self._metadata[key]

    @property
    def metadata(self) -> dict[str, Any]:
        """Read-only snapshot of the current metadata."""
        return dict(self._metadata)

    # -- forking --------------------------------------------------------------

    def fork(self) -> FlowContext:
        """Create a child context sharing the correlation ID.

        Metadata is deep-copied so mutations in the child do not affect the
        parent (and vice-versa).
        """
        return FlowContext(
            correlation_id=self.correlation_id,
            metadata=copy.deepcopy(self._metadata),
        )


# ---------------------------------------------------------------------------
# ContextVar holding the current FlowContext (None when outside a flow)
# ---------------------------------------------------------------------------

_flow_context_var: ContextVar[FlowContext | None] = ContextVar(
    "penstock_flow_context", default=None
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_or_create_context() -> FlowContext:
    """Return the current FlowContext, creating one if none exists."""
    ctx = _flow_context_var.get()
    if ctx is None:
        ctx = FlowContext()
        _flow_context_var.set(ctx)
    return ctx


def _set_context(ctx: FlowContext) -> None:
    """Replace the current FlowContext."""
    _flow_context_var.set(ctx)


def _reset_context() -> None:
    """Clear the current FlowContext (set to ``None``)."""
    _flow_context_var.set(None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def current_flow_id() -> str | None:
    """Return the current correlation ID, or ``None`` if outside a flow."""
    ctx = _flow_context_var.get()
    return ctx.correlation_id if ctx is not None else None


def get_flow_context() -> FlowContext | None:
    """Return the current :class:`FlowContext`, or ``None``."""
    return _flow_context_var.get()


def set_flow_context_value(key: str, value: Any) -> None:
    """Set a metadata value on the current flow context.

    Creates a new context automatically if none exists.
    """
    _get_or_create_context().set_value(key, value)


def get_flow_context_value(key: str, default: Any = None) -> Any:
    """Get a metadata value from the current flow context.

    Returns *default* if there is no active context or the key is absent.
    """
    ctx = _flow_context_var.get()
    if ctx is None:
        return default
    return ctx.get_value(key, default)
