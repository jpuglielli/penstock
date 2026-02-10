"""Tests for penstock._decorators."""

from __future__ import annotations

import asyncio

import pytest

from penstock._context import current_flow_id, get_flow_context
from penstock._decorators import (
    _normalize_after,
    entrypoint,
    flow,
    step,
)
from penstock._registry import _registry


# ---------------------------------------------------------------------------
# @flow
# ---------------------------------------------------------------------------


class TestFlow:
    def test_stamps_attribute(self) -> None:
        @flow("my_flow")
        class MyFlow:
            pass

        assert MyFlow.__penstock_flow__ == "my_flow"  # type: ignore[attr-defined]

    def test_returns_class_unchanged(self) -> None:
        @flow("f")
        class MyFlow:
            x = 1

        assert MyFlow.x == 1
        assert isinstance(MyFlow(), MyFlow)

    def test_registers_marked_methods(self) -> None:
        @flow("order")
        class OrderFlow:
            @entrypoint
            def start(self) -> None:
                pass

            @step(after="start")
            def process(self) -> None:
                pass

        info = _registry.get_flow("order")
        assert "start" in info.steps
        assert "process" in info.steps
        assert info.steps["start"].is_entrypoint is True
        assert info.steps["process"].after == ("start",)


# ---------------------------------------------------------------------------
# @entrypoint
# ---------------------------------------------------------------------------


class TestEntrypoint:
    def test_creates_flow_context(self) -> None:
        @flow("ep_flow")
        class F:
            @entrypoint
            def run(self) -> str | None:
                return current_flow_id()

        cid = F().run()
        assert isinstance(cid, str)
        assert len(cid) == 32

    def test_resets_context_after(self) -> None:
        @flow("ep_flow2")
        class F:
            @entrypoint
            def run(self) -> None:
                pass

        F().run()
        assert get_flow_context() is None

    def test_resets_context_on_exception(self) -> None:
        @flow("ep_flow3")
        class F:
            @entrypoint
            def run(self) -> None:
                raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            F().run()
        assert get_flow_context() is None

    def test_with_custom_name(self) -> None:
        @flow("f")
        class F:
            @entrypoint(name="custom_start")
            def run(self) -> None:
                pass

        info = _registry.get_flow("f")
        assert "custom_start" in info.steps

    def test_registered_as_entrypoint(self) -> None:
        @flow("f")
        class F:
            @entrypoint
            def run(self) -> None:
                pass

        info = _registry.get_flow("f")
        assert info.steps["run"].is_entrypoint is True


# ---------------------------------------------------------------------------
# @step
# ---------------------------------------------------------------------------


class TestStep:
    def test_reuses_context(self) -> None:
        @flow("step_flow")
        class F:
            @entrypoint
            def start(self) -> str | None:
                cid = current_flow_id()
                self.process()
                return cid

            @step(after="start")
            def process(self) -> None:
                # Should still have the same context
                assert current_flow_id() is not None

        cid = F().start()
        assert cid is not None

    def test_step_outside_context_raises(self) -> None:
        @flow("step_flow2")
        class F:
            @step
            def process(self) -> None:
                pass

        with pytest.raises(RuntimeError, match="outside of a flow context"):
            F().process()

    def test_registered_as_non_entrypoint(self) -> None:
        @flow("f")
        class F:
            @step(after="start")
            def process(self) -> None:
                pass

        info = _registry.get_flow("f")
        assert info.steps["process"].is_entrypoint is False

    def test_step_with_after_string(self) -> None:
        @flow("f")
        class F:
            @step(after="validate")
            def process(self) -> None:
                pass

        info = _registry.get_flow("f")
        assert info.steps["process"].after == ("validate",)


# ---------------------------------------------------------------------------
# after= normalization
# ---------------------------------------------------------------------------


class TestNormalizeAfter:
    def test_none(self) -> None:
        assert _normalize_after(None) == ()

    def test_string(self) -> None:
        assert _normalize_after("validate") == ("validate",)

    def test_callable(self) -> None:
        def my_func() -> None:
            pass

        assert _normalize_after(my_func) == ("my_func",)

    def test_list_mixed(self) -> None:
        def my_func() -> None:
            pass

        result = _normalize_after(["validate", my_func])
        assert result == ("validate", "my_func")

    def test_list_strings(self) -> None:
        assert _normalize_after(["a", "b"]) == ("a", "b")


# ---------------------------------------------------------------------------
# Async support
# ---------------------------------------------------------------------------


class TestAsync:
    def test_async_entrypoint(self) -> None:
        @flow("async_flow")
        class F:
            @entrypoint
            async def start(self) -> str | None:
                return current_flow_id()

        cid = asyncio.run(F().start())
        assert isinstance(cid, str)
        assert len(cid) == 32
        # Context should be reset after
        assert get_flow_context() is None

    def test_async_step(self) -> None:
        @flow("async_flow2")
        class F:
            @entrypoint
            async def start(self) -> str | None:
                cid = current_flow_id()
                await self.process()
                return cid

            @step(after="start")
            async def process(self) -> None:
                assert current_flow_id() is not None

        cid = asyncio.run(F().start())
        assert cid is not None

    def test_async_step_outside_context_raises(self) -> None:
        @flow("async_flow3")
        class F:
            @step
            async def process(self) -> None:
                pass

        with pytest.raises(RuntimeError, match="outside of a flow context"):
            asyncio.run(F().process())


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_flow_without_steps(self) -> None:
        @flow("empty")
        class F:
            pass

        assert F.__penstock_flow__ == "empty"  # type: ignore[attr-defined]
        # Flow is not in the registry since no steps were registered
        with pytest.raises(KeyError):
            _registry.get_flow("empty")

    def test_bare_decorators(self) -> None:
        """@entrypoint and @step can be used without parentheses."""

        @flow("bare")
        class F:
            @entrypoint
            def start(self) -> None:
                pass

            @step
            def process(self) -> None:
                pass

        info = _registry.get_flow("bare")
        assert "start" in info.steps
        assert "process" in info.steps
