"""Shared workpiece material registry (FR-004).

Reference cutting-speed/feed values are canonical-metric, HSS-baseline
figures drawn from widely published machining data (Machinery's Handbook /
Sandvik Coromant general-purpose reference ranges for twist drilling); see
``specs/001-metal-drilling-calc/research.md`` #4. Drilling-tool factors
(``operations/drilling/tools.py``) multiply these baseline values.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkpieceMaterial:
    """Reference machining data for a selectable workpiece material.

    Attributes:
        name: Unique display name, e.g. ``"Mild Steel"``.
        reference_cutting_speed_m_min: HSS-baseline cutting speed (vc) in
            m/min.
        reference_feed_per_rev_mm: HSS-baseline feed per revolution (fn) in
            mm/rev.
        specific_cutting_force_kc: Specific cutting force (Kc) in N/mm^2,
            used in torque/power calculations.
    """

    name: str
    reference_cutting_speed_m_min: float
    reference_feed_per_rev_mm: float
    specific_cutting_force_kc: float


def _validate(material: WorkpieceMaterial) -> None:
    if material.reference_cutting_speed_m_min <= 0:
        raise ValueError(f"{material.name}: reference_cutting_speed_m_min must be positive")
    if material.reference_feed_per_rev_mm <= 0:
        raise ValueError(f"{material.name}: reference_feed_per_rev_mm must be positive")
    if material.specific_cutting_force_kc <= 0:
        raise ValueError(f"{material.name}: specific_cutting_force_kc must be positive")


_MATERIALS: list[WorkpieceMaterial] = [
    WorkpieceMaterial("Mild Steel", 25.0, 0.20, 1900.0),
    WorkpieceMaterial("Stainless Steel", 15.0, 0.15, 2400.0),
    WorkpieceMaterial("Aluminum", 60.0, 0.25, 700.0),
    WorkpieceMaterial("Cast Iron", 20.0, 0.20, 1500.0),
    WorkpieceMaterial("Brass", 45.0, 0.20, 800.0),
    WorkpieceMaterial("Titanium", 12.0, 0.10, 2100.0),
]

MATERIAL_REGISTRY: dict[str, WorkpieceMaterial] = {}
for _m in _MATERIALS:
    _validate(_m)
    if _m.name in MATERIAL_REGISTRY:
        raise ValueError(f"Duplicate material name in registry: {_m.name}")
    MATERIAL_REGISTRY[_m.name] = _m


def list_materials() -> list[str]:
    """Return the currently registered workpiece material names (FR-004)."""

    return list(MATERIAL_REGISTRY.keys())


def get_material(name: str) -> WorkpieceMaterial | None:
    """Look up a registered material by name, or ``None`` if unknown."""

    return MATERIAL_REGISTRY.get(name)
