"""Core type definitions for penstock flow metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True, slots=True)
class StepInfo:
    """Metadata for a single step within a flow."""

    name: str
    flow_name: str
    after: tuple[str, ...]
    is_entrypoint: bool


@dataclass(frozen=True, slots=True)
class FlowInfo:
    """Resolved metadata for a complete flow."""

    name: str
    steps: dict[str, StepInfo]
    entrypoints: frozenset[str]
