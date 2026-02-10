"""structlog processor that injects the penstock flow ID into log entries.

Usage::

    import structlog
    from penstock.contrib.structlog import flow_processor

    structlog.configure(
        processors=[
            flow_processor,
            structlog.dev.ConsoleRenderer(),
        ]
    )

Every log entry emitted while a flow is active will automatically include
a ``flow_id`` key with the current correlation ID.
"""

from __future__ import annotations

from typing import Any

from penstock._context import current_flow_id


def flow_processor(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor that adds ``flow_id`` to every log event.

    When no flow is active the key is omitted rather than set to ``None``,
    keeping logs clean outside of flow contexts.
    """
    cid = current_flow_id()
    if cid is not None:
        event_dict["flow_id"] = cid
    return event_dict
