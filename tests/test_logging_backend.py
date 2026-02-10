"""Tests for penstock.backends.logging.LoggingBackend."""

from __future__ import annotations

import logging

import pytest

from penstock._context import FlowContext, _set_context
from penstock.backends.logging import LoggingBackend


class TestSpan:
    def test_emits_start_and_end(self, caplog: pytest.LogCaptureFixture) -> None:
        _set_context(FlowContext(correlation_id="test-cid"))
        backend = LoggingBackend()

        with (
            caplog.at_level(logging.INFO, logger="penstock"),
            backend.span("my_step", "my_flow"),
        ):
            pass

        assert len(caplog.records) == 2
        start, end = caplog.records

        assert start.message == "step.start"
        assert start.flow == "my_flow"  # type: ignore[attr-defined]
        assert start.step == "my_step"  # type: ignore[attr-defined]
        assert start.correlation_id == "test-cid"  # type: ignore[attr-defined]

        assert end.message == "step.end"
        assert hasattr(end, "duration_ms")
        assert end.duration_ms >= 0

    def test_extra_attrs_forwarded(self, caplog: pytest.LogCaptureFixture) -> None:
        _set_context(FlowContext(correlation_id="cid"))
        backend = LoggingBackend()

        with (
            caplog.at_level(logging.INFO, logger="penstock"),
            backend.span("s", "f", custom_key="custom_val"),
        ):
            pass

        start = caplog.records[0]
        assert start.custom_key == "custom_val"  # type: ignore[attr-defined]

    def test_duration_ms_present(self, caplog: pytest.LogCaptureFixture) -> None:
        _set_context(FlowContext(correlation_id="cid"))
        backend = LoggingBackend()

        with caplog.at_level(logging.INFO, logger="penstock"), backend.span("s", "f"):
            pass

        end = caplog.records[1]
        assert isinstance(end.duration_ms, float)  # type: ignore[attr-defined]

    def test_span_logs_on_exception(self, caplog: pytest.LogCaptureFixture) -> None:
        _set_context(FlowContext(correlation_id="cid"))
        backend = LoggingBackend()

        with caplog.at_level(logging.INFO, logger="penstock"):
            try:
                with backend.span("s", "f"):
                    raise ValueError("boom")
            except ValueError:
                pass

        # Both start and end should still be logged
        assert len(caplog.records) == 2
        assert caplog.records[1].message == "step.end"


class TestGetCorrelationId:
    def test_returns_current_flow_id(self) -> None:
        _set_context(FlowContext(correlation_id="abc"))
        backend = LoggingBackend()
        assert backend.get_correlation_id() == "abc"

    def test_creates_context_if_missing(self) -> None:
        backend = LoggingBackend()
        cid = backend.get_correlation_id()
        assert isinstance(cid, str)
        assert len(cid) == 32  # uuid4 hex
