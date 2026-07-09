"""Drilling-specific drill-tool registry (FR-005).

Factors are relative to the HSS baseline (factor 1.0) stored in
``machine_calc.registry``'s material reference values; see research.md #4.
Typical multiplier ranges are drawn from general-purpose machining
references (Machinery's Handbook / Sandvik Coromant): carbide tooling
tolerates substantially higher cutting speeds than HSS, cobalt moderately
higher.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrillingTool:
    """Reference data for a selectable drill bit type.

    Attributes:
        name: Unique display name, e.g. ``"Carbide"``.
        cutting_speed_factor: Multiplier applied to the material's reference
            cutting speed.
        feed_factor: Multiplier applied to the material's reference feed per
            revolution.
    """

    name: str
    cutting_speed_factor: float
    feed_factor: float


def _validate(tool: DrillingTool) -> None:
    if tool.cutting_speed_factor <= 0:
        raise ValueError(f"{tool.name}: cutting_speed_factor must be positive")
    if tool.feed_factor <= 0:
        raise ValueError(f"{tool.name}: feed_factor must be positive")


_TOOLS: list[DrillingTool] = [
    DrillingTool("HSS", 1.0, 1.0),
    DrillingTool("Cobalt", 1.15, 1.0),
    DrillingTool("Carbide", 2.5, 1.1),
]

TOOL_REGISTRY: dict[str, DrillingTool] = {}
for _t in _TOOLS:
    _validate(_t)
    if _t.name in TOOL_REGISTRY:
        raise ValueError(f"Duplicate drilling tool name in registry: {_t.name}")
    TOOL_REGISTRY[_t.name] = _t


def list_tools() -> list[str]:
    """Return the currently registered drilling tool names (FR-005)."""

    return list(TOOL_REGISTRY.keys())


def get_tool(name: str) -> DrillingTool | None:
    """Look up a registered drilling tool by name, or ``None`` if unknown."""

    return TOOL_REGISTRY.get(name)
