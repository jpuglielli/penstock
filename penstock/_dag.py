"""DAG generation and visualization for registered flows."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, overload

from penstock._registry import _registry


@overload
def generate_dag(
    flow_name: str,
    *,
    format: Literal["mermaid"] = ...,
    output: None = ...,
) -> str: ...


@overload
def generate_dag(
    flow_name: str,
    *,
    format: Literal["mermaid"] = ...,
    output: str,
) -> None: ...


def generate_dag(
    flow_name: str,
    *,
    format: Literal["mermaid"] = "mermaid",
    output: str | None = None,
) -> str | None:
    """Generate a DAG diagram for a registered flow.

    Parameters
    ----------
    flow_name:
        Name of the flow (as passed to ``@flow(name)``).
    format:
        Output format. Currently only ``"mermaid"`` is supported.
    output:
        Optional file path. When provided the diagram is written to this path
        and the function returns ``None``. Otherwise the diagram string is
        returned.

    Raises
    ------
    KeyError
        If the flow has not been registered.
    ValueError
        If *format* is not supported.
    """
    if format != "mermaid":
        raise ValueError(f"Unsupported format: {format!r}")

    info = _registry.get_flow(flow_name)
    lines: list[str] = ["graph TD"]

    # Collect edges from the `after` relationships.
    edges: list[tuple[str, str]] = [
        (predecessor, step.name)
        for step in info.steps.values()
        for predecessor in step.after
    ]

    # Sort for deterministic output.
    edges.sort()

    if not edges:
        # Flow with steps but no edges — list each step as a standalone node.
        lines.extend(f"    {name}" for name in sorted(info.steps))
    else:
        for src, dst in edges:
            lines.append(f"    {src} --> {dst}")

    diagram = "\n".join(lines) + "\n"

    if output is not None:
        Path(output).write_text(diagram)
        return None

    return diagram
