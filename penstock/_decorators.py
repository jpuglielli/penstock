"""User-facing decorators: @flow, @entrypoint, @step."""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, TypeVar, overload

from penstock._config import get_backend
from penstock._context import (
    FlowContext,
    _reset_context,
    _set_context,
    get_flow_context,
)
from penstock._registry import _registry
from penstock._types import P, R, StepInfo

_STEP_MARKER = "__penstock_step__"

C = TypeVar("C", bound=type)


# ---------------------------------------------------------------------------
# after= normalization
# ---------------------------------------------------------------------------


def _normalize_after(
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None,
) -> tuple[str, ...]:
    if after is None:
        return ()
    if isinstance(after, str):
        return (after,)
    if callable(after):
        return (after.__name__,)
    result: list[str] = []
    for item in after:
        if isinstance(item, str):
            result.append(item)
        else:
            result.append(item.__name__)
    return tuple(result)


# ---------------------------------------------------------------------------
# @flow(name)
# ---------------------------------------------------------------------------


def flow(name: str) -> Callable[[C], C]:
    """Class decorator that marks a class as a penstock flow.

    Scans the class for methods decorated with ``@entrypoint`` or ``@step``
    and registers them in the global registry.
    """

    def decorator(cls: C) -> C:
        cls.__penstock_flow__ = name  # type: ignore[attr-defined]

        for attr_name in list(vars(cls)):
            obj = vars(cls)[attr_name]
            marker = getattr(obj, _STEP_MARKER, None)
            if marker is not None:
                step_name: str = marker["name"]
                after: tuple[str, ...] = marker["after"]
                is_entrypoint: bool = marker["is_entrypoint"]
                info = StepInfo(
                    name=step_name,
                    flow_name=name,
                    after=after,
                    is_entrypoint=is_entrypoint,
                )
                _registry.register(info)
                _flow_name_cache[id(obj)] = name

        return cls

    return decorator


# ---------------------------------------------------------------------------
# @entrypoint
# ---------------------------------------------------------------------------


@overload
def entrypoint(fn: Callable[P, R]) -> Callable[P, R]: ...


@overload
def entrypoint(
    *,
    name: str | None = ...,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None = ...,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def entrypoint(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None = None,
) -> Any:
    """Mark a method as a flow entrypoint.

    Can be used bare (``@entrypoint``) or with arguments
    (``@entrypoint(name="custom")``).
    """
    if fn is not None:
        return _make_entrypoint(fn, name=None, after=None)

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        return _make_entrypoint(f, name=name, after=after)

    return decorator


def _make_entrypoint(
    fn: Callable[..., Any],
    *,
    name: str | None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None,
) -> Callable[..., Any]:
    step_name = name or fn.__name__
    after_tuple = _normalize_after(after)

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _set_context(FlowContext())
            backend = get_backend()
            try:
                with backend.span(step_name, _resolve_flow_name(async_wrapper)):
                    return await fn(*args, **kwargs)
            finally:
                _reset_context()

        setattr(
            async_wrapper,
            _STEP_MARKER,
            {
                "name": step_name,
                "after": after_tuple,
                "is_entrypoint": True,
            },
        )
        return async_wrapper

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _set_context(FlowContext())
        backend = get_backend()
        try:
            with backend.span(step_name, _resolve_flow_name(wrapper)):
                return fn(*args, **kwargs)
        finally:
            _reset_context()

    setattr(
        wrapper,
        _STEP_MARKER,
        {
            "name": step_name,
            "after": after_tuple,
            "is_entrypoint": True,
        },
    )
    return wrapper


# ---------------------------------------------------------------------------
# @step
# ---------------------------------------------------------------------------


@overload
def step(fn: Callable[P, R]) -> Callable[P, R]: ...


@overload
def step(
    *,
    name: str | None = ...,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None = ...,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def step(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None = None,
) -> Any:
    """Mark a method as a flow step.

    Can be used bare (``@step``) or with arguments
    (``@step(after="validate")``).
    """
    if fn is not None:
        return _make_step(fn, name=None, after=None)

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        return _make_step(f, name=name, after=after)

    return decorator


def _make_step(
    fn: Callable[..., Any],
    *,
    name: str | None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None,
) -> Callable[..., Any]:
    step_name = name or fn.__name__
    after_tuple = _normalize_after(after)

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = get_flow_context()
            if ctx is None:
                raise RuntimeError(
                    f"@step '{step_name}' called outside of a flow context. "
                    "Ensure an @entrypoint has been called first."
                )
            backend = get_backend()
            with backend.span(step_name, _resolve_flow_name(async_wrapper)):
                return await fn(*args, **kwargs)

        setattr(
            async_wrapper,
            _STEP_MARKER,
            {
                "name": step_name,
                "after": after_tuple,
                "is_entrypoint": False,
            },
        )
        return async_wrapper

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = get_flow_context()
        if ctx is None:
            raise RuntimeError(
                f"@step '{step_name}' called outside of a flow context. "
                "Ensure an @entrypoint has been called first."
            )
        backend = get_backend()
        with backend.span(step_name, _resolve_flow_name(wrapper)):
            return fn(*args, **kwargs)

    setattr(
        wrapper,
        _STEP_MARKER,
        {
            "name": step_name,
            "after": after_tuple,
            "is_entrypoint": False,
        },
    )
    return wrapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Maps wrapper function id -> flow_name (populated by @flow at class creation)
_flow_name_cache: dict[int, str] = {}


def _resolve_flow_name(wrapper: Callable[..., Any]) -> str:
    """Look up the flow name for a wrapper.

    Falls back to qualname parsing if not in cache (shouldn't happen in
    normal usage since @flow populates the cache).
    """
    fid = id(wrapper)
    cached = _flow_name_cache.get(fid)
    if cached is not None:
        return cached

    # Try to find the flow name from the qualname (ClassName.method_name)
    qualname = getattr(wrapper, "__qualname__", "")
    parts = qualname.rsplit(".", 1)
    if len(parts) == 2:
        return parts[0]
    return "<unknown>"
