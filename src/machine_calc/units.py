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


def _scratch_over_complex(a, b, c, d, e, f, g, h, i, j, k):
    """Scratch function for T020: deliberately over cyclomatic-complexity threshold."""
    total = 0
    if a:
        total += 1
    if b:
        total += 1
    if c:
        total += 1
    if d:
        total += 1
    if e:
        total += 1
    if f:
        total += 1
    if g:
        total += 1
    if h:
        total += 1
    if i:
        total += 1
    if j:
        total += 1
    if k:
        total += 1
    return total
