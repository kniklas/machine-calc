"""Shared metric<->imperial conversion helpers (FR-017; research.md #4).

All calculations are performed canonically in metric internally; these
helpers convert user-supplied imperial inputs to metric before calculation,
and convert metric results to imperial for display/output when
``UnitSystem.IMPERIAL`` is selected.
"""

from __future__ import annotations

MM_PER_INCH = 25.4
NM_PER_IN_LB = 1.0 / 8.850745791327185
HP_PER_KW = 1.3410220895


def mm_to_in(value_mm: float) -> float:
    """Convert millimeters to inches."""

    return value_mm / MM_PER_INCH


def in_to_mm(value_in: float) -> float:
    """Convert inches to millimeters."""

    return value_in * MM_PER_INCH


def nm_to_in_lb(value_nm: float) -> float:
    """Convert newton-meters to inch-pounds."""

    return value_nm * 8.850745791327185


def in_lb_to_nm(value_in_lb: float) -> float:
    """Convert inch-pounds to newton-meters."""

    return value_in_lb * NM_PER_IN_LB


def kw_to_hp(value_kw: float) -> float:
    """Convert kilowatts to horsepower."""

    return value_kw * HP_PER_KW


def hp_to_kw(value_hp: float) -> float:
    """Convert horsepower to kilowatts."""

    return value_hp / HP_PER_KW


def _scratch_type_error_probe() -> int:
    """Deliberately wrong type annotation for T021 validation (to be removed)."""
    value: int = "not an int"
    return value


def _scratch_bandit_probe(cmd: str) -> None:
    """Deliberately unsafe subprocess shell=True for T021 validation (to be removed)."""
    import subprocess

    subprocess.call(cmd, shell=True)  # nosec-free on purpose: should trip bandit (High)
