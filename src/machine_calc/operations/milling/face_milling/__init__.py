"""Face-milling calculations (specs/009-milling-calculations US3).

Public entry point :func:`calculate_face_milling`, plus the face-mill tool
registry helpers re-exported for convenience. See
``specs/009-milling-calculations/contracts/library-api-milling.md`` for the
full contract.
"""

from __future__ import annotations

from typing import cast

from machine_calc.models import CalculationResult, UnitSystem
from machine_calc.operations.milling._calculate import (
    MillingMetricsLike,
    calculate_milling,
)
from machine_calc.operations.milling._tool_registry import MillingTool
from machine_calc.registry import WorkpieceMaterial

from .formulas import FaceMillingMetrics, calculate_face_milling_metrics
from .tools import FaceMillTool, get_face_mill_tool, list_face_mill_tools

_ENGAGEMENT_LABEL_KEY = "cli.label.width_of_cut"


def _compute(
    geometry_mm: dict, material: WorkpieceMaterial, tool: MillingTool
) -> MillingMetricsLike:
    """Adapt the shared orchestration's inputs to ``formulas.py`` (FR-014)."""

    return calculate_face_milling_metrics(
        diameter_mm=geometry_mm["diameter_mm"],
        axial_depth_of_cut_mm=geometry_mm["axial_depth_of_cut_mm"],
        width_of_cut_mm=geometry_mm["radial_engagement_mm"],
        feed_per_tooth_mm=geometry_mm["feed_per_tooth_mm"],
        number_of_teeth=geometry_mm["number_of_teeth"],
        length_of_cut_mm=geometry_mm["length_of_cut_mm"],
        material=material,
        tool=cast(FaceMillTool, tool),
    )


def calculate_face_milling(
    diameter: float,
    axial_depth_of_cut: float,
    width_of_cut: float,
    feed_per_tooth: float,
    number_of_teeth: float,
    length_of_cut: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = "en",
    materials_config_path: str | None = None,
) -> CalculationResult:
    """Calculate face-milling parameters (FR-007, FR-011, FR-012).

    All dimensional arguments are interpreted in ``unit_system``: mm and kW
    under :attr:`~machine_calc.models.UnitSystem.METRIC`, inches and HP under
    :attr:`~machine_calc.models.UnitSystem.IMPERIAL`. Results are returned in
    the same system — feed rate in mm/min or in/min, torque in N*m or in*lb,
    power in kW or HP, material removal rate in cm^3/min or in^3/min, and
    machining time always in fractional minutes.

    Full/symmetric cutter engagement is assumed, so no chip-thinning
    correction is applied (spec.md Assumptions).

    Args:
        diameter: Face-mill cutter diameter (D). Must be > 0 and within the
            configured maximum mill diameter.
        axial_depth_of_cut: Axial depth of cut (ap). Must be > 0 and within
            the configured maximum depth of cut.
        width_of_cut: Width of cut (ae). Must be > 0 and must not exceed
            ``diameter`` (FR-009).
        feed_per_tooth: Feed per tooth / chip load (fz). Must be > 0.
        number_of_teeth: Number of inserts (zn). Must be a positive whole
            number.
        length_of_cut: Distance the cutter travels across the workpiece,
            used for machining time. Must be > 0 and within the configured
            maximum length of cut.
        material: Registered workpiece material name (see
            :func:`machine_calc.list_materials`).
        tool: Registered face-mill tool name (see
            :func:`list_face_mill_tools`).
        unit_system: Unit system for both inputs and outputs.
        available_power: Optional available machine power, used only to
            attach a feasibility warning when the required **net cutting
            power** exceeds it. Never turns a result into an error.
        config_path: Optional path to a configuration file supplying
            validation bounds.
        locale: Locale code for all human-readable messages.
        materials_config_path: Optional path to a user materials/tools
            configuration file.

    Returns:
        A :class:`~machine_calc.models.CalculationResult`. On any validation
        failure, ``error`` is populated and every numeric field — including
        ``material_removal_rate`` — is ``None``; the function does not raise
        for expected failures (FR-012).
    """

    return calculate_milling(
        diameter=diameter,
        axial_depth_of_cut=axial_depth_of_cut,
        radial_engagement=width_of_cut,
        feed_per_tooth=feed_per_tooth,
        number_of_teeth=number_of_teeth,
        length_of_cut=length_of_cut,
        material=material,
        tool=tool,
        unit_system=unit_system,
        available_power=available_power,
        config_path=config_path,
        locale=locale,
        materials_config_path=materials_config_path,
        resolve_tool=get_face_mill_tool,
        compute=_compute,
        engagement_label_key=_ENGAGEMENT_LABEL_KEY,
    )


__all__ = [
    "FaceMillTool",
    "FaceMillingMetrics",
    "calculate_face_milling",
    "calculate_face_milling_metrics",
    "get_face_mill_tool",
    "list_face_mill_tools",
]
