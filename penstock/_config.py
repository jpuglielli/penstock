"""Global backend configuration (thread-safe)."""

from __future__ import annotations

import threading

from penstock.backends.base import TracingBackend

_lock = threading.Lock()
_backend: TracingBackend | None = None
_configured = False


def configure(backend: TracingBackend | str = "auto") -> None:
    """Set the global tracing backend.

    *backend* can be:
    - A :class:`TracingBackend` instance
    - ``"logging"`` — use the built-in :class:`LoggingBackend`
    - ``"otel"`` — reserved for future OpenTelemetry support
    - ``"auto"`` — try OTel, fall back to logging
    """
    global _backend, _configured
    with _lock:
        if isinstance(backend, TracingBackend):
            _backend = backend
        elif backend == "logging":
            from penstock.backends.logging import LoggingBackend

            _backend = LoggingBackend()
        elif backend == "otel":
            from penstock.backends.otel import OTelBackend

            _backend = OTelBackend()
        elif backend == "auto":
            _backend = _auto_detect()
        else:
            raise ValueError(f"Unknown backend: {backend!r}")
        _configured = True


def get_backend() -> TracingBackend:
    """Return the configured backend, auto-detecting on first call."""
    global _backend, _configured
    if _configured:
        assert _backend is not None
        return _backend
    with _lock:
        if _configured:
            assert _backend is not None
            return _backend
        _backend = _auto_detect()
        _configured = True
        return _backend


def reset() -> None:
    """Reset configuration to unconfigured state. Intended for testing."""
    global _backend, _configured
    with _lock:
        _backend = None
        _configured = False


def _auto_detect() -> TracingBackend:
    """Try to import OTel; fall back to LoggingBackend."""
    try:
        from penstock.backends.otel import OTelBackend

        return OTelBackend()
    except RuntimeError:
        from penstock.backends.logging import LoggingBackend

        return LoggingBackend()
