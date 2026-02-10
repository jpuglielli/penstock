"""Tests for penstock._config."""

from __future__ import annotations

import pytest

from penstock._config import configure, get_backend, reset
from penstock.backends.logging import LoggingBackend


class TestConfigure:
    def test_configure_with_string_logging(self) -> None:
        configure("logging")
        backend = get_backend()
        assert isinstance(backend, LoggingBackend)

    def test_configure_with_instance(self) -> None:
        instance = LoggingBackend()
        configure(instance)
        assert get_backend() is instance

    def test_configure_otel_without_package_raises(self) -> None:
        # Without opentelemetry installed, OTelBackend raises RuntimeError
        with pytest.raises(RuntimeError, match="opentelemetry-api is required"):
            configure("otel")

    def test_configure_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown backend"):
            configure("bogus")

    def test_configure_auto(self) -> None:
        configure("auto")
        backend = get_backend()
        # Without opentelemetry installed, should fall back to logging
        assert isinstance(backend, LoggingBackend)


class TestGetBackend:
    def test_auto_detection_on_first_call(self) -> None:
        # No configure() call — get_backend should auto-detect
        backend = get_backend()
        assert isinstance(backend, LoggingBackend)

    def test_returns_same_instance(self) -> None:
        b1 = get_backend()
        b2 = get_backend()
        assert b1 is b2


class TestReset:
    def test_reset_clears_backend(self) -> None:
        configure("logging")
        b1 = get_backend()
        reset()
        b2 = get_backend()
        # After reset, a new backend is auto-detected
        assert b1 is not b2
