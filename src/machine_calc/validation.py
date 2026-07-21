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

import math

from machine_calc.config import Configuration
from machine_calc.i18n import DEFAULT_LOCALE, translate
from machine_calc.models import CalculationMode, ErrorInfo


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


def validate_target_rpm(target_rpm: float | None, locale: str = DEFAULT_LOCALE) -> ErrorInfo | None:
    """Validate a supplied target spindle RPM (fixed-RPM mode, FR-007).

    ``target_rpm`` MUST be a positive, finite number. Zero, negative,
    non-numeric, ``NaN``, and ``Infinity`` values are all rejected under
    the same ``INVALID_TARGET_RPM`` code (spec.md Clarifications
    2026-07-11) — the same validation posture as diameter/depth in the
    base drilling spec. No additional maximum/minimum range validation or
    clamping is applied beyond finiteness and positivity (spec.md
    Clarifications 2026-07-11 second checklist follow-up); a ``None``
    value (not supplied) is not an error here — callers decide whether a
    missing ``target_rpm`` is itself an error (e.g. required in fixed-RPM
    mode) via :func:`validate_mode_arguments`.
    """

    if target_rpm is None:
        return None
    if not isinstance(target_rpm, (int, float)) or isinstance(target_rpm, bool):
        return ErrorInfo("INVALID_TARGET_RPM", translate(locale, "error.invalid_target_rpm"))
    if not math.isfinite(target_rpm) or target_rpm <= 0:
        return ErrorInfo("INVALID_TARGET_RPM", translate(locale, "error.invalid_target_rpm"))
    return None


def validate_mode_arguments(
    mode: CalculationMode,
    available_power: float | None,
    target_rpm: float | None,
    locale: str = DEFAULT_LOCALE,
) -> ErrorInfo | None:
    """Validate mode/target_rpm/available_power mutual-exclusivity (FR-009).

    The supplied ``mode`` is authoritative (spec.md FR-009, Clarifications
    2026-07-11 second checklist follow-up):

    - ``CalculationMode.STANDARD`` (the default) ignores any supplied
      ``target_rpm``/``available_power`` — never a conflict.
    - ``CalculationMode.POWER_CONSTRAINED`` requires ``available_power`` to
      be supplied, and rejects a request that also supplies ``target_rpm``
      (power-constrained mode derives spindle speed; it does not accept
      one directly) — both cases are ``MODE_CONFLICT``.
    - ``CalculationMode.FIXED_RPM`` requires ``target_rpm`` to be supplied;
      a missing ``target_rpm`` in this mode is reported as
      ``INVALID_TARGET_RPM`` (FR-007) by the caller, not here.
      ``available_power`` remains optional/advisory in this mode (FR-008)
      and is never a conflict.
    """

    if mode is CalculationMode.STANDARD:
        return None

    if mode is CalculationMode.POWER_CONSTRAINED:
        if target_rpm is not None:
            return ErrorInfo("MODE_CONFLICT", translate(locale, "error.mode_conflict"))
        if available_power is None:
            return ErrorInfo("MODE_CONFLICT", translate(locale, "error.mode_conflict"))
        return None

    # mode is CalculationMode.FIXED_RPM
    return None
