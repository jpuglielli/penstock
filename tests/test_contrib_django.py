"""Tests for penstock.contrib.django.FlowMiddleware."""

from __future__ import annotations

import contextlib
from typing import Any

from penstock._context import current_flow_id, get_flow_context
from penstock.contrib.django import FlowMiddleware


class _FakeResponse(dict[str, str]):
    """Minimal dict-like object to simulate an HttpResponse."""


def _make_middleware(
    view_return: Any = None,
    view_side_effect: type[BaseException] | None = None,
) -> tuple[FlowMiddleware, list[str | None]]:
    """Build a FlowMiddleware with a fake get_response.

    Returns the middleware and a list that captures the correlation IDs
    seen inside the view.
    """
    captured: list[str | None] = []

    def get_response(_request: Any) -> _FakeResponse:
        captured.append(current_flow_id())
        if view_side_effect is not None:
            raise view_side_effect()
        return _FakeResponse() if view_return is None else view_return

    mw = FlowMiddleware(get_response)
    return mw, captured


class TestFlowMiddleware:
    def test_sets_context_during_request(self) -> None:
        mw, captured = _make_middleware()
        mw(object())  # fake request
        assert len(captured) == 1
        assert isinstance(captured[0], str)
        assert len(captured[0]) == 32  # uuid hex

    def test_resets_context_after_request(self) -> None:
        mw, _ = _make_middleware()
        mw(object())
        assert get_flow_context() is None

    def test_resets_context_on_exception(self) -> None:
        mw, _ = _make_middleware(view_side_effect=ValueError)
        with contextlib.suppress(ValueError):
            mw(object())
        assert get_flow_context() is None

    def test_adds_correlation_id_header(self) -> None:
        mw, captured = _make_middleware()
        response = mw(object())
        assert response["X-Correlation-ID"] == captured[0]

    def test_each_request_gets_unique_id(self) -> None:
        mw, captured = _make_middleware()
        mw(object())
        mw(object())
        assert len(captured) == 2
        assert captured[0] != captured[1]
