"""Abstract base class for tracing backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class TracingBackend(ABC):
    """Interface that all penstock tracing backends must implement."""

    @abstractmethod
    @contextmanager
    def span(self, step_name: str, flow_name: str, **attrs: Any) -> Iterator[None]:
        """Open a tracing span for the duration of a step."""

    @abstractmethod
    def get_correlation_id(self) -> str:
        """Return the current correlation ID."""
