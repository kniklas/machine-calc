"""Shared milling orchestration: validation, unit conversion, result building.

Both milling sub-operations have the same public contract (see
``specs/009-milling-calculations/contracts/library-api-milling.md``) and the
same nine-step validation order (``data-model.md`` "Validation Order"); only
the tool registry they resolve against and the label used for the radial
engagement input differ. That common orchestration lives here once
(Constitution Principle VI) while each sub-operation keeps its own public
entry point, tool registry, formulas wrapper and messages.

Also implements the calculation-mode dispatch added by
``specs/010-milling-calculation-modes`` (FR-001 through FR-009, FR-014):
mode/target_rpm validation runs only after the existing nine-step geometry
validation (unchanged precedence, mirroring
``specs/002-constrained-calculation-modes``' drilling equivalent), then
dispatches to the standard, power-constrained, or fixed-RPM metrics path.

Never raises for expected validation failures: every failure path returns a
:class:`~machine_calc.models.CalculationResult` whose ``error`` is set and
whose numeric fields — including ``material_removal_rate`` — are ``None``
(FR-012).
"""

from __future__ import annotations

import math
from typing import Callable, Optional, Protocol

from machine_calc.config import Configuration, load_configuration
from machine_calc.i18n import translate
from machine_calc.models import CalculationMode, CalculationResult, ErrorInfo, UnitSystem
from machine_calc.operations.milling._shared import calculate_power_constrained_milling_metrics
from machine_calc.operations.milling._tool_registry import MillingTool
from machine_calc.registry import WorkpieceMaterial, get_material, get_material_validation
from machine_calc.units import (
    cm3_min_to_in3_min,
    hp_to_kw,
    in_to_mm,
    kw_to_hp,
    mm_to_in,
    nm_to_in_lb,
)
from machine_calc.validation import (
    validate_depth_of_cut_mm,
    validate_engagement_mm,
    validate_feed_per_tooth_mm,
    validate_length_of_cut_mm,
    validate_material_present,
    validate_mill_diameter_mm,
    validate_mill_tool_present,
    validate_mode_arguments,
    validate_target_rpm,
    validate_tooth_count,
)

#: Callable resolving a milling tool name to its registry entry (or ``None``).
ToolResolver = Callable[[str, Optional[str]], Optional[MillingTool]]


class MillingMetricsLike(Protocol):
    """Structural type shared by every sub-operation's metrics dataclass.

    ``EndMillingMetrics`` and ``FaceMillingMetrics`` are deliberately
    distinct nominal types (research.md #2), so this orchestration accepts
    them structurally rather than importing either one. Members are declared
    as read-only properties so frozen dataclasses satisfy the protocol.
    """

    @property
    def spindle_speed_rpm(self) -> float: ...

    @property
    def feed_rate_mm_min(self) -> float: ...

    @property
    def material_removal_rate_cm3_min(self) -> float: ...

    @property
    def machining_time_min(self) -> float: ...

    @property
    def torque_nm(self) -> float: ...

    @property
    def power_kw(self) -> float: ...


#: Callable computing metrics from canonical-metric geometry, material and tool.
MetricsComputer = Callable[[dict, WorkpieceMaterial, MillingTool], MillingMetricsLike]

#: Callable computing metrics at an explicit spindle speed (RPM), from
#: canonical-metric geometry, material, tool, and the target RPM
#: (``specs/010-milling-calculation-modes``' fixed-RPM mode, FR-006).
MetricsAtRpmComputer = Callable[[dict, WorkpieceMaterial, MillingTool, float], MillingMetricsLike]


def error_result(
    unit_system: UnitSystem, error: ErrorInfo, mode: CalculationMode = CalculationMode.STANDARD
) -> CalculationResult:
    """Build the canonical milling error result (all numeric fields ``None``)."""

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
        material_removal_rate=None,
    )


def _resolve_material_and_tool(
    material: str,
    tool: str,
    unit_system: UnitSystem,
    locale: str,
    resolve_tool: ToolResolver,
    materials_config_path: str | None,
    mode: CalculationMode = CalculationMode.STANDARD,
) -> CalculationResult | tuple[WorkpieceMaterial, MillingTool]:
    """Validate and resolve the material/tool names (validation steps 1-2).

    Returns a :class:`CalculationResult` on failure, or the tuple
    ``(resolved_material, resolved_tool)`` on success. Mirrors drilling's
    ``_resolve_material_and_tool`` precedence exactly, including that an
    unusable material (FR-010 — e.g. a missing or non-positive specific
    cutting force, which milling torque and power depend on) is reported as
    ``UNUSABLE_MATERIAL`` rather than a milling-specific code.
    """

    material_error = validate_material_present(material, locale)
    if material_error:
        return error_result(unit_system, material_error, mode)

    tool_error = validate_mill_tool_present(tool, locale)
    if tool_error:
        return error_result(unit_system, tool_error, mode)

    resolved_material = get_material(material, materials_config_path)
    if resolved_material is None:
        return error_result(
            unit_system,
            ErrorInfo(
                "MISSING_MATERIAL", translate(locale, "error.unknown_material", material=material)
            ),
            mode,
        )
    if not resolved_material.is_usable:
        validation = get_material_validation(material, materials_config_path)
        details = "; ".join(validation.issues) if validation is not None else ""
        return error_result(
            unit_system,
            ErrorInfo(
                "UNUSABLE_MATERIAL",
                translate(locale, "error.unusable_material", material=material, details=details),
            ),
            mode,
        )

    resolved_tool = resolve_tool(tool, materials_config_path)
    if resolved_tool is None:
        return error_result(
            unit_system,
            ErrorInfo("MISSING_TOOL", translate(locale, "error.unknown_mill_tool", tool=tool)),
            mode,
        )

    return resolved_material, resolved_tool


def _to_metric(value: float, unit_system: UnitSystem) -> float:
    """Convert a length input to canonical mm when the caller used imperial.

    Non-numeric, ``None``, and ``bool`` values are passed through
    unconverted rather than fed to :func:`~machine_calc.units.in_to_mm`,
    which would either raise (``None``/strings) or silently coerce
    (``True``/``False``). Leaving them unconverted lets the downstream
    ``_is_positive_finite_number``-based validators reject them with the
    documented structured error instead (FR-012).
    """

    if unit_system is not UnitSystem.IMPERIAL:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return in_to_mm(value)


def _validate_geometry(
    geometry_mm: dict,
    config: Configuration,
    unit_system: UnitSystem,
    locale: str,
    engagement_label_key: str,
    mode: CalculationMode = CalculationMode.STANDARD,
) -> CalculationResult | None:
    """Run validation steps 3-8 in the documented order.

    Returns a :class:`CalculationResult` for the first failure, or ``None``
    when every input is valid. The engagement input's catalog label key is
    supplied by the caller so end milling reports "Radial depth of cut" and
    face milling reports "Width of cut" (FR-006, FR-007).
    """

    checks = (
        validate_mill_diameter_mm(geometry_mm["diameter_mm"], config, locale),
        validate_depth_of_cut_mm(
            geometry_mm["axial_depth_of_cut_mm"], config, locale, "cli.label.axial_depth_of_cut"
        ),
        validate_depth_of_cut_mm(
            geometry_mm["radial_engagement_mm"], config, locale, engagement_label_key
        ),
        validate_engagement_mm(
            geometry_mm["radial_engagement_mm"],
            geometry_mm["diameter_mm"],
            locale,
            engagement_label_key,
        ),
        validate_feed_per_tooth_mm(geometry_mm["feed_per_tooth_mm"], locale),
        validate_tooth_count(geometry_mm["number_of_teeth"], locale),
        validate_length_of_cut_mm(geometry_mm["length_of_cut_mm"], config, locale),
    )
    for error in checks:
        if error is not None:
            return error_result(unit_system, error, mode)
    return None


def _validate_mode_inputs(
    mode: CalculationMode,
    available_power: float | None,
    target_rpm: float | None,
    unit_system: UnitSystem,
    locale: str,
) -> CalculationResult | None:
    """Validate the mode-specific arguments (``target_rpm``/``available_power``).

    Returns a :class:`CalculationResult` if invalid, or ``None`` on success.
    Runs only after the existing nine-step geometry validation — unchanged
    precedence, mirroring drilling's ``_validate_mode_inputs``
    (``specs/002-constrained-calculation-modes``,
    ``specs/010-milling-calculation-modes`` data-model.md "Validation
    order").
    """

    if mode is CalculationMode.FIXED_RPM:
        target_rpm_error = validate_target_rpm(target_rpm, locale)
        if target_rpm_error:
            return error_result(unit_system, target_rpm_error, mode)
        if target_rpm is None:
            return error_result(
                unit_system,
                ErrorInfo("INVALID_TARGET_RPM", translate(locale, "error.invalid_target_rpm")),
                mode,
            )

    mode_error = validate_mode_arguments(mode, available_power, target_rpm, locale)
    if mode_error:
        return error_result(unit_system, mode_error, mode)

    return None


def _compute_metrics(
    mode: CalculationMode,
    geometry_mm: dict,
    resolved_material: WorkpieceMaterial,
    resolved_tool: MillingTool,
    available_power_kw: float | None,
    target_rpm: float | None,
    compute: MetricsComputer,
    compute_at_rpm: MetricsAtRpmComputer,
    unit_system: UnitSystem,
    locale: str,
) -> MillingMetricsLike | CalculationResult:
    """Dispatch to the mode-specific metrics calculation.

    Returns a metrics object on success, or a :class:`CalculationResult`
    carrying an ``INFEASIBLE_POWER_BUDGET`` error if ``POWER_CONSTRAINED``
    mode cannot produce a feasible result. Mirrors drilling's
    ``_compute_metrics`` dispatch structure
    (``operations/drilling/__init__.py``).
    """

    if mode is CalculationMode.POWER_CONSTRAINED:
        # available_power_kw is guaranteed non-None here (validate_mode_arguments
        # rejects POWER_CONSTRAINED without it as MODE_CONFLICT).
        assert available_power_kw is not None
        if available_power_kw <= 0:
            return error_result(
                unit_system,
                ErrorInfo(
                    "INFEASIBLE_POWER_BUDGET",
                    translate(locale, "error.infeasible_power_budget"),
                ),
                mode,
            )
        metrics = calculate_power_constrained_milling_metrics(
            diameter_mm=geometry_mm["diameter_mm"],
            axial_depth_of_cut_mm=geometry_mm["axial_depth_of_cut_mm"],
            radial_engagement_mm=geometry_mm["radial_engagement_mm"],
            feed_per_tooth_mm=geometry_mm["feed_per_tooth_mm"],
            number_of_teeth=geometry_mm["number_of_teeth"],
            length_of_cut_mm=geometry_mm["length_of_cut_mm"],
            material=resolved_material,
            cutting_speed_factor=resolved_tool.cutting_speed_factor,
            available_power_kw=available_power_kw,
        )
        if not math.isfinite(metrics.spindle_speed_rpm) or metrics.spindle_speed_rpm <= 0:
            return error_result(
                unit_system,
                ErrorInfo(
                    "INFEASIBLE_POWER_BUDGET",
                    translate(locale, "error.infeasible_power_budget"),
                ),
                mode,
            )
        return metrics

    if mode is CalculationMode.FIXED_RPM:
        # target_rpm is guaranteed non-None here (INVALID_TARGET_RPM is
        # returned earlier by _validate_mode_inputs when it is None for
        # this mode).
        assert target_rpm is not None
        rpm_metrics: MillingMetricsLike = compute_at_rpm(
            geometry_mm, resolved_material, resolved_tool, target_rpm
        )
        return _reject_if_overflowed(rpm_metrics, unit_system, mode, locale)

    standard_metrics: MillingMetricsLike = compute(geometry_mm, resolved_material, resolved_tool)
    return _reject_if_overflowed(standard_metrics, unit_system, mode, locale)


def _reject_if_overflowed(
    metrics: MillingMetricsLike,
    unit_system: UnitSystem,
    mode: CalculationMode,
    locale: str,
) -> MillingMetricsLike | CalculationResult:
    """Guard against an extreme-but-individually-valid input (e.g. an
    unbounded ``feed_per_tooth``/``target_rpm``, per FR-008/FR-018's
    explicit no-upper-bound design) producing a non-finite downstream
    result.

    ``validate_feed_per_tooth_mm()``/``validate_target_rpm()`` deliberately
    impose no upper bound, so a physically-absurd but "valid" input can
    still make ``feed_rate_mm_min = spindle_speed_rpm * feed_per_tooth_mm *
    number_of_teeth`` (or a value derived from it) overflow to ``inf``.
    Rather than surface a result that mixes finite and ``inf``/``nan``
    fields, report it as a structured error (FR-012/FR-015 never-raises
    contract) — mirrors the ``POWER_CONSTRAINED`` branch's own
    finiteness check above, generalized to the other two modes' metrics.
    """

    if all(
        math.isfinite(value)
        for value in (
            metrics.spindle_speed_rpm,
            metrics.feed_rate_mm_min,
            metrics.material_removal_rate_cm3_min,
            metrics.machining_time_min,
            metrics.torque_nm,
            metrics.power_kw,
        )
    ):
        return metrics
    return error_result(
        unit_system,
        ErrorInfo("CALCULATION_OVERFLOW", translate(locale, "error.calculation_overflow")),
        mode,
    )


def _build_result(
    metrics: MillingMetricsLike,
    unit_system: UnitSystem,
    available_power_kw: float | None,
    mode: CalculationMode,
    locale: str,
) -> CalculationResult:
    """Convert metrics to the caller's unit system and apply the power check.

    The feasibility comparison is made on the same **net cutting power**
    basis the module reports (spec.md Assumptions): no drive-efficiency
    factor is applied to either side. In ``POWER_CONSTRAINED`` mode,
    ``available_power_kw`` is already a hard constraint enforced by
    :func:`_compute_metrics` — it is never re-checked as an advisory warning
    here (mirrors drilling's ``_build_result``).
    """

    feasibility_warning = None
    if (
        available_power_kw is not None
        and mode is not CalculationMode.POWER_CONSTRAINED
        and metrics.power_kw > available_power_kw
    ):
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
        material_removal_rate = cm3_min_to_in3_min(metrics.material_removal_rate_cm3_min)
    else:
        feed_rate = metrics.feed_rate_mm_min
        torque = metrics.torque_nm
        power_required = metrics.power_kw
        material_removal_rate = metrics.material_removal_rate_cm3_min

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
        material_removal_rate=material_removal_rate,
    )


def calculate_milling(
    diameter: float,
    axial_depth_of_cut: float,
    radial_engagement: float,
    feed_per_tooth: float,
    number_of_teeth: float,
    length_of_cut: float,
    material: str,
    tool: str,
    unit_system: UnitSystem,
    available_power: float | None,
    config_path: str | None,
    locale: str,
    materials_config_path: str | None,
    resolve_tool: ToolResolver,
    compute: MetricsComputer,
    engagement_label_key: str,
    compute_at_rpm: MetricsAtRpmComputer,
    mode: CalculationMode = CalculationMode.STANDARD,
    target_rpm: float | None = None,
) -> CalculationResult:
    """Validate, calculate, and build a milling :class:`CalculationResult`.

    Shared by :func:`machine_calc.calculate_end_milling` and
    :func:`machine_calc.calculate_face_milling`; see
    ``contracts/library-api-milling.md`` and
    ``specs/010-milling-calculation-modes/contracts/library-api-milling-modes-delta.md``
    for the full contract those two functions expose.

    Args:
        radial_engagement: The radial depth of cut (end milling) or width of
            cut (face milling), in the units of ``unit_system``.
        resolve_tool: The sub-operation's ``get_*_tool`` lookup.
        compute: The sub-operation's ``formulas.py`` adapter; keeping the
            formula call injected preserves the per-sub-operation module
            boundary required by FR-014.
        engagement_label_key: Message-catalog key naming the radial
            engagement input in validation messages.
        compute_at_rpm: The sub-operation's ``formulas.py`` at-RPM adapter,
            used by fixed-RPM mode (FR-006 of
            ``specs/010-milling-calculation-modes``); preserves the same
            per-sub-operation module boundary as ``compute`` (FR-014).
        mode: Which calculation mode to use (``STANDARD``,
            ``POWER_CONSTRAINED``, or ``FIXED_RPM``). Defaults to
            ``STANDARD``, unchanged from ``009-milling-calculations``
            (SC-004).
        target_rpm: Required when ``mode is CalculationMode.FIXED_RPM``.
            Ignored (not an error) when ``mode is CalculationMode.STANDARD``.
            Supplying it together with ``mode is
            CalculationMode.POWER_CONSTRAINED`` is a ``MODE_CONFLICT``
            (FR-009).

    Returns:
        A :class:`CalculationResult`; never raises for expected validation
        failures (FR-012).
    """

    config = load_configuration(config_path)

    resolved = _resolve_material_and_tool(
        material, tool, unit_system, locale, resolve_tool, materials_config_path, mode
    )
    if isinstance(resolved, CalculationResult):
        return resolved
    resolved_material, resolved_tool = resolved

    geometry_mm = {
        "diameter_mm": _to_metric(diameter, unit_system),
        "axial_depth_of_cut_mm": _to_metric(axial_depth_of_cut, unit_system),
        "radial_engagement_mm": _to_metric(radial_engagement, unit_system),
        "feed_per_tooth_mm": _to_metric(feed_per_tooth, unit_system),
        "number_of_teeth": number_of_teeth,
        "length_of_cut_mm": _to_metric(length_of_cut, unit_system),
    }

    geometry_error = _validate_geometry(
        geometry_mm, config, unit_system, locale, engagement_label_key, mode
    )
    if geometry_error is not None:
        return geometry_error

    mode_input_error = _validate_mode_inputs(mode, available_power, target_rpm, unit_system, locale)
    if mode_input_error is not None:
        return mode_input_error

    available_power_kw = None
    if available_power is not None:
        available_power_kw = (
            hp_to_kw(available_power) if unit_system is UnitSystem.IMPERIAL else available_power
        )

    metrics_or_error = _compute_metrics(
        mode,
        geometry_mm,
        resolved_material,
        resolved_tool,
        available_power_kw,
        target_rpm,
        compute,
        compute_at_rpm,
        unit_system,
        locale,
    )
    if isinstance(metrics_or_error, CalculationResult):
        return metrics_or_error

    return _build_result(metrics_or_error, unit_system, available_power_kw, mode, locale)


__all__ = [
    "MetricsAtRpmComputer",
    "MetricsComputer",
    "MillingMetricsLike",
    "ToolResolver",
    "calculate_milling",
    "error_result",
]
