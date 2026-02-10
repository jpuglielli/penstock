"""Tests for penstock.contrib.celery.flow_task."""

from __future__ import annotations

import contextlib

from penstock._context import (
    FlowContext,
    _set_context,
    current_flow_id,
    get_flow_context,
)
from penstock.contrib.celery import flow_task


class TestFlowTask:
    def test_sets_context_during_execution(self) -> None:
        captured: list[str | None] = []

        @flow_task
        def my_task() -> None:
            captured.append(current_flow_id())

        my_task()
        assert len(captured) == 1
        assert isinstance(captured[0], str)
        assert len(captured[0]) == 32

    def test_resets_context_after_execution(self) -> None:
        @flow_task
        def my_task() -> None:
            pass

        my_task()
        assert get_flow_context() is None

    def test_resets_context_on_exception(self) -> None:
        @flow_task
        def my_task() -> None:
            raise ValueError("boom")

        with contextlib.suppress(ValueError):
            my_task()
        assert get_flow_context() is None

    def test_restores_correlation_id_from_headers(self) -> None:
        captured: list[str | None] = []

        @flow_task
        def my_task() -> None:
            captured.append(current_flow_id())

        my_task(__penstock_headers__={"penstock_correlation_id": "injected-cid"})
        assert captured[0] == "injected-cid"

    def test_generates_new_id_without_headers(self) -> None:
        captured: list[str | None] = []

        @flow_task
        def my_task() -> None:
            captured.append(current_flow_id())

        my_task()
        # Should get a fresh UUID, not None
        assert captured[0] is not None

    def test_penstock_headers_helper(self) -> None:
        @flow_task
        def my_task() -> None:
            pass

        # Outside a flow context, headers should be empty
        headers = my_task._penstock_headers()  # type: ignore[attr-defined]
        assert headers == {}

        # Inside a flow context, should contain the correlation ID
        _set_context(FlowContext(correlation_id="test-cid"))
        headers = my_task._penstock_headers()  # type: ignore[attr-defined]
        assert headers == {"penstock_correlation_id": "test-cid"}

    def test_preserves_return_value(self) -> None:
        @flow_task
        def my_task() -> str:
            return "result"

        assert my_task() == "result"

    def test_preserves_function_name(self) -> None:
        @flow_task
        def my_task() -> None:
            pass

        assert my_task.__name__ == "my_task"
