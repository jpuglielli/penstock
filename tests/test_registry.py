"""Tests for penstock._registry."""

from __future__ import annotations

import threading

import pytest

from penstock._registry import _registry
from penstock._types import StepInfo


def _step(
    name: str = "s",
    flow: str = "f",
    after: tuple[str, ...] = (),
    entry: bool = False,
) -> StepInfo:
    return StepInfo(name=name, flow_name=flow, after=after, is_entrypoint=entry)


class TestRegister:
    def test_basic(self) -> None:
        _registry.register(_step())
        flow = _registry.get_flow("f")
        assert "s" in flow.steps

    def test_idempotent(self) -> None:
        info = _step()
        _registry.register(info)
        _registry.register(info)  # no error
        assert len(_registry.get_flow("f").steps) == 1

    def test_conflict_raises(self) -> None:
        _registry.register(_step(entry=False))
        with pytest.raises(ValueError, match="Conflicting"):
            _registry.register(_step(entry=True))

    def test_multiple_steps(self) -> None:
        _registry.register(_step(name="a", entry=True))
        _registry.register(_step(name="b", after=("a",)))
        flow = _registry.get_flow("f")
        assert len(flow.steps) == 2
        assert flow.entrypoints == frozenset({"a"})


class TestGetFlow:
    def test_missing_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            _registry.get_flow("missing")


class TestGetAllFlowNames:
    def test_empty(self) -> None:
        assert _registry.get_all_flow_names() == []

    def test_populated(self) -> None:
        _registry.register(_step(flow="x"))
        _registry.register(_step(flow="y"))
        names = _registry.get_all_flow_names()
        assert sorted(names) == ["x", "y"]


class TestValidateFlow:
    def test_valid(self) -> None:
        _registry.register(_step(name="a", entry=True))
        _registry.register(_step(name="b", after=("a",)))
        _registry.validate_flow("f")  # no error

    def test_invalid_reference(self) -> None:
        _registry.register(_step(name="a", after=("missing",)))
        with pytest.raises(ValueError, match="unknown step 'missing'"):
            _registry.validate_flow("f")

    def test_missing_flow(self) -> None:
        with pytest.raises(KeyError):
            _registry.validate_flow("nope")


class TestClear:
    def test_clear(self) -> None:
        _registry.register(_step())
        _registry.clear()
        assert _registry.get_all_flow_names() == []


class TestThreadSafety:
    def test_concurrent_registration(self) -> None:
        errors: list[Exception] = []

        def register_steps(prefix: str) -> None:
            try:
                for i in range(50):
                    _registry.register(_step(name=f"{prefix}_{i}", flow="concurrent"))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=register_steps, args=(f"t{t}",)) for t in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        flow = _registry.get_flow("concurrent")
        assert len(flow.steps) == 200
