"""Thread-safe flow registry for import-time DAG construction."""

from __future__ import annotations

import threading

from penstock._types import FlowInfo, StepInfo


class FlowRegistry:
    """Stores step metadata registered by decorators and resolves full flows."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._steps: dict[str, dict[str, StepInfo]] = {}

    def register(self, info: StepInfo) -> None:
        """Register a step. Idempotent for identical info, raises on conflict."""
        with self._lock:
            flow_steps = self._steps.setdefault(info.flow_name, {})
            existing = flow_steps.get(info.name)
            if existing is not None:
                if existing != info:
                    raise ValueError(
                        f"Conflicting registration for step '{info.name}' "
                        f"in flow '{info.flow_name}'"
                    )
                return
            flow_steps[info.name] = info

    def get_flow(self, name: str) -> FlowInfo:
        """Return resolved FlowInfo. Raises KeyError if flow not found."""
        with self._lock:
            steps = self._steps.get(name)
            if steps is None:
                raise KeyError(f"Flow '{name}' not found")
            entrypoints = frozenset(s.name for s in steps.values() if s.is_entrypoint)
            return FlowInfo(name=name, steps=dict(steps), entrypoints=entrypoints)

    def get_all_flow_names(self) -> list[str]:
        """Return names of all registered flows."""
        with self._lock:
            return list(self._steps.keys())

    def validate_flow(self, name: str) -> None:
        """Verify all ``after`` references resolve to registered step names.

        Raises ``ValueError`` with details on missing references.
        Raises ``KeyError`` if the flow itself is not registered.
        """
        flow = self.get_flow(name)
        missing: list[str] = [
            f"Step '{step.name}' references unknown step '{ref}'"
            for step in flow.steps.values()
            for ref in step.after
            if ref not in flow.steps
        ]
        if missing:
            raise ValueError(
                f"Flow '{name}' has invalid references:\n"
                + "\n".join(f"  - {m}" for m in missing)
            )

    def clear(self) -> None:
        """Remove all registered flows. Intended for testing."""
        with self._lock:
            self._steps.clear()


_registry = FlowRegistry()
