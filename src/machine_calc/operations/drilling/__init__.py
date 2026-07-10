"""Drilling operation: public entry point (FR-001 through FR-018).

Re-exported at the top level as ``machine_calc.calculate`` since drilling is
currently the module's only operation (contracts/library-api.md). Future
operations (turning, milling, ...) add their own sibling
``machine_calc.operations.<operation>`` module with an analogous
``calculate()`` without changing this contract.
"""

from __future__ import annotations

import math

from machine_calc.config import load_configuration
from machine_calc.i18n import DEFAULT_LOCALE, translate
from machine_calc.models import CalculationMode, CalculationResult, ErrorInfo, UnitSystem
from machine_calc.registry import get_material
from machine_calc.units import (
    hp_to_kw,
    in_to_mm,
    kw_to_hp,
    mm_to_in,
    nm_to_in_lb,
)
from machine_calc.validation import (
    validate_depth_mm,
    validate_diameter_mm,
    validate_material_present,
    validate_mode_arguments,
    validate_target_rpm,
    validate_tool_present,
)

from .formulas import (
    calculate_drilling_metrics,
    calculate_drilling_metrics_at_rpm,
    calculate_power_constrained_metrics,
)
from .tools import get_tool


def _error_result(
    unit_system: UnitSystem, error: ErrorInfo, mode: CalculationMode = CalculationMode.STANDARD
) -> CalculationResult:
    return CalculationResult(
        spindle_speed_rpm=None,
        feed_rate=None,
        machining_time=None,
        torque=None,
        power_required=None,
        unit_system=unit_system,
        feasibility_warning=None,
        error=error,
        mode=mode,
    )


def calculate(
    diameter: float,
    depth: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = DEFAULT_LOCALE,
    mode: CalculationMode = CalculationMode.STANDARD,
    target_rpm: float | None = None,
) -> CalculationResult:
    """Calculate drilling parameters for the given inputs.

    Never raises for expected validation failures (invalid input,
    missing/unknown material or tool, unsupported combination, exceeded
    power rating) — always returns a :class:`CalculationResult` instead
    (FR-015). See ``contracts/library-api.md`` and
    ``specs/002-constrained-calculation-modes/contracts/library-api-delta.md``
    for the full contract and error codes.

    Args:
        diameter: Drill diameter, in the units of ``unit_system`` (mm for
            METRIC, inches for IMPERIAL).
        depth: Hole depth, in the units of ``unit_system``.
        material: A workpiece material name from :func:`list_materials`.
        tool: A drilling tool name from :func:`list_tools`.
        unit_system: The unit system for both input parsing and output
            formatting (FR-017). Defaults to ``UnitSystem.METRIC``.
        available_power: Optional available machine power, in the power
            unit of ``unit_system`` (kW for METRIC, HP for IMPERIAL).
            Semantics depend on ``mode``: in ``STANDARD`` and
            ``FIXED_RPM`` modes it is optional/advisory — an exceeded
            budget sets a ``feasibility_warning`` (FR-012 of the base
            spec, FR-008 of this feature) without altering the result. In
            ``POWER_CONSTRAINED`` mode it is a **required** hard
            constraint (FR-002).
        config_path: Optional path to a TOML file overriding the default
            diameter/depth validation bounds (FR-018).
        locale: Optional locale used to translate ``ErrorInfo.message`` and
            ``feasibility_warning`` text (FR-019d). Defaults to English; an
            empty string is treated the same as omitting it. Falls back to
            English for any locale or message key not present in the
            requested catalog (FR-019e).
        mode: Which calculation mode to use (``STANDARD``,
            ``POWER_CONSTRAINED``, or ``FIXED_RPM``). Defaults to
            ``STANDARD``, which is byte-for-byte identical to
            ``001-metal-drilling-calc``'s behavior (SC-004).
        target_rpm: Required when ``mode is CalculationMode.FIXED_RPM``:
            the caller-supplied spindle speed (RPM) to calculate from,
            instead of deriving it from the material/tool. Ignored (not an
            error) when ``mode is CalculationMode.STANDARD``. Supplying it
            together with ``mode is CalculationMode.POWER_CONSTRAINED`` is
            a ``MODE_CONFLICT`` (FR-009).

    Returns:
        A :class:`CalculationResult`. On success, ``error`` is ``None`` and:

        - ``spindle_speed_rpm`` is in RPM (identical under both unit
          systems).
        - ``feed_rate`` is in mm/min (METRIC) or in/min (IMPERIAL).
        - ``machining_time`` is in minutes (fractional), identical under
          both unit systems.
        - ``torque`` is in N*m (METRIC) or in-lb (IMPERIAL).
        - ``power_required`` is in kW (METRIC) or HP (IMPERIAL).
        - ``mode`` echoes the requested mode (FR-012).

        On failure, ``error`` is set (one of the base spec's five codes,
        or this feature's ``INVALID_TARGET_RPM``, ``MODE_CONFLICT``, or
        ``INFEASIBLE_POWER_BUDGET``) and all numeric fields above are
        ``None``.
    """

    # An empty string is treated the same as omitting locale (FR-019d).
    locale = locale or DEFAULT_LOCALE

    config = load_configuration(config_path)

    material_error = validate_material_present(material, locale)
    if material_error:
        return _error_result(unit_system, material_error, mode)

    tool_error = validate_tool_present(tool, locale)
    if tool_error:
        return _error_result(unit_system, tool_error, mode)

    resolved_material = get_material(material)
    if resolved_material is None:
        return _error_result(
            unit_system,
            ErrorInfo(
                "MISSING_MATERIAL",
                translate(locale, "error.unknown_material", material=material),
            ),
            mode,
        )

    resolved_tool = get_tool(tool)
    if resolved_tool is None:
        return _error_result(
            unit_system,
            ErrorInfo("MISSING_TOOL", translate(locale, "error.unknown_tool", tool=tool)),
            mode,
        )

    # Convert inputs to canonical metric before validation/calculation.
    diameter_mm = in_to_mm(diameter) if unit_system is UnitSystem.IMPERIAL else diameter
    depth_mm = in_to_mm(depth) if unit_system is UnitSystem.IMPERIAL else depth

    diameter_error = validate_diameter_mm(diameter_mm, config, locale)
    if diameter_error:
        return _error_result(unit_system, diameter_error, mode)

    depth_error = validate_depth_mm(depth_mm, config, locale)
    if depth_error:
        return _error_result(unit_system, depth_error, mode)

    # Mode-argument validation runs only after the base spec's existing
    # material/tool/diameter/depth checks — unchanged order/precedence
    # (/speckit.analyze finding U1; data-model.md Validation order).
    if mode is CalculationMode.FIXED_RPM:
        target_rpm_error = validate_target_rpm(target_rpm, locale)
        if target_rpm_error:
            return _error_result(unit_system, target_rpm_error, mode)
        if target_rpm is None:
            return _error_result(
                unit_system,
                ErrorInfo("INVALID_TARGET_RPM", translate(locale, "error.invalid_target_rpm")),
                mode,
            )

    mode_error = validate_mode_arguments(mode, available_power, target_rpm, locale)
    if mode_error:
        return _error_result(unit_system, mode_error, mode)

    available_power_kw = None
    if available_power is not None:
        available_power_kw = (
            hp_to_kw(available_power) if unit_system is UnitSystem.IMPERIAL else available_power
        )

    if mode is CalculationMode.POWER_CONSTRAINED:
        # available_power_kw is guaranteed non-None here (validate_mode_arguments
        # rejects POWER_CONSTRAINED without it as MODE_CONFLICT).
        if available_power_kw <= 0:
            return _error_result(
                unit_system,
                ErrorInfo(
                    "INFEASIBLE_POWER_BUDGET",
                    translate(locale, "error.infeasible_power_budget"),
                ),
                mode,
            )
        metrics = calculate_power_constrained_metrics(
            diameter_mm, depth_mm, resolved_material, resolved_tool, available_power_kw
        )
        if not math.isfinite(metrics.spindle_speed_rpm) or metrics.spindle_speed_rpm <= 0:
            return _error_result(
                unit_system,
                ErrorInfo(
                    "INFEASIBLE_POWER_BUDGET",
                    translate(locale, "error.infeasible_power_budget"),
                ),
                mode,
            )
    elif mode is CalculationMode.FIXED_RPM:
        metrics = calculate_drilling_metrics_at_rpm(
            diameter_mm, depth_mm, resolved_material, resolved_tool, target_rpm
        )
    else:
        metrics = calculate_drilling_metrics(diameter_mm, depth_mm, resolved_material, resolved_tool)

    feasibility_warning = None
    if available_power_kw is not None and mode is not CalculationMode.POWER_CONSTRAINED:
        if metrics.power_kw > available_power_kw:
            feasibility_warning = translate(
                locale,
                "warning.feasibility",
                required_kw=metrics.power_kw,
                available_kw=available_power_kw,
            )

    if unit_system is UnitSystem.IMPERIAL:
        feed_rate = mm_to_in(metrics.feed_rate_mm_min)
        torque = nm_to_in_lb(metrics.torque_nm)
        power_required = kw_to_hp(metrics.power_kw)
    else:
        feed_rate = metrics.feed_rate_mm_min
        torque = metrics.torque_nm
        power_required = metrics.power_kw

    return CalculationResult(
        spindle_speed_rpm=metrics.spindle_speed_rpm,
        feed_rate=feed_rate,
        machining_time=metrics.machining_time_min,
        torque=torque,
        power_required=power_required,
        unit_system=unit_system,
        feasibility_warning=feasibility_warning,
        error=None,
        mode=mode,
    )
