"""Shared input validation (FR-009, FR-010, FR-018).

All validation returns :class:`~machine_calc.models.ErrorInfo` rather than
raising exceptions, per FR-015. Bounds are always expressed and checked in
canonical metric units (mm); callers convert imperial input to metric before
calling these functions.

All error messages are sourced from the message catalog (FR-019a-e) via
:mod:`machine_calc.i18n`; the optional ``locale`` parameter defaults to
English (T033a).
"""

from __future__ import annotations

from machine_calc.config import Configuration
from machine_calc.i18n import DEFAULT_LOCALE, translate
from machine_calc.models import ErrorInfo


def validate_diameter_mm(
    diameter_mm: float, config: Configuration, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate a drill diameter (in mm) against positivity and bounds."""

    if diameter_mm is None or diameter_mm <= 0:
        return ErrorInfo("INVALID_DIAMETER", translate(locale, "error.invalid_diameter.zero"))
    if diameter_mm > config.max_diameter_mm:
        return ErrorInfo(
            "INVALID_DIAMETER",
            translate(
                locale,
                "error.invalid_diameter.max",
                max_diameter_mm=config.max_diameter_mm,
            ),
        )
    return None


def validate_depth_mm(
    depth_mm: float, config: Configuration, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate a hole depth (in mm) against positivity and bounds."""

    if depth_mm is None or depth_mm <= 0:
        return ErrorInfo("INVALID_DEPTH", translate(locale, "error.invalid_depth.zero"))
    if depth_mm > config.max_depth_mm:
        return ErrorInfo(
            "INVALID_DEPTH",
            translate(locale, "error.invalid_depth.max", max_depth_mm=config.max_depth_mm),
        )
    return None


def validate_material_present(
    material: str | None, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate that a material name was supplied (non-empty)."""

    if not material:
        return ErrorInfo("MISSING_MATERIAL", translate(locale, "error.missing_material"))
    return None


def validate_tool_present(tool: str | None, locale: str = DEFAULT_LOCALE) -> ErrorInfo | None:
    """Validate that a drilling tool name was supplied (non-empty)."""

    if not tool:
        return ErrorInfo("MISSING_TOOL", translate(locale, "error.missing_tool"))
    return None
