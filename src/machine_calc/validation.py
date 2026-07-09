"""Shared input validation (FR-009, FR-010, FR-018).

All validation returns :class:`~machine_calc.models.ErrorInfo` rather than
raising exceptions, per FR-015. Bounds are always expressed and checked in
canonical metric units (mm); callers convert imperial input to metric before
calling these functions.
"""

from __future__ import annotations

from machine_calc.config import Configuration
from machine_calc.models import ErrorInfo


def validate_diameter_mm(diameter_mm: float, config: Configuration) -> ErrorInfo | None:
    """Validate a drill diameter (in mm) against positivity and bounds."""

    if diameter_mm is None or diameter_mm <= 0:
        return ErrorInfo("INVALID_DIAMETER", "Drill diameter must be greater than 0.")
    if diameter_mm > config.max_diameter_mm:
        return ErrorInfo(
            "INVALID_DIAMETER",
            f"Drill diameter must not exceed {config.max_diameter_mm:g} mm.",
        )
    return None


def validate_depth_mm(depth_mm: float, config: Configuration) -> ErrorInfo | None:
    """Validate a hole depth (in mm) against positivity and bounds."""

    if depth_mm is None or depth_mm <= 0:
        return ErrorInfo("INVALID_DEPTH", "Hole depth must be greater than 0.")
    if depth_mm > config.max_depth_mm:
        return ErrorInfo(
            "INVALID_DEPTH",
            f"Hole depth must not exceed {config.max_depth_mm:g} mm.",
        )
    return None


def validate_material_present(material: str | None) -> ErrorInfo | None:
    """Validate that a material name was supplied (non-empty)."""

    if not material:
        return ErrorInfo("MISSING_MATERIAL", "A workpiece material must be selected.")
    return None


def validate_tool_present(tool: str | None) -> ErrorInfo | None:
    """Validate that a drilling tool name was supplied (non-empty)."""

    if not tool:
        return ErrorInfo("MISSING_TOOL", "A drilling tool must be selected.")
    return None
