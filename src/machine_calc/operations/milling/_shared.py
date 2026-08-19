"""Shared milling formula core for both milling sub-operations.

Implements the standard milling formulas published in Sandvik Coromant's
"Machining Formulas" reference — the same source already cited by
``operations/drilling/formulas.py`` (see
``specs/009-milling-calculations/research.md`` #1 for the full citation and
the derivation of each expression):

1. ``vc = reference_cutting_speed_m_min * cutting_speed_factor``
2. ``n  = (vc * 1000) / (pi * D)`` — spindle speed, RPM
3. ``vf = n * fz * zn`` — table feed rate, mm/min
4. ``Q  = (ap * ae * vf) / 1000`` — material removal rate, cm^3/min
5. ``Pc = (ap * ae * vf * kc) / (60 * 10^6)`` — net cutting power, kW
6. ``Mc = (Pc * 9550) / n`` — cutting torque, N*m
7. ``tc = length_of_cut / vf`` — machining time, minutes

``Pc`` is **net power at the cutter**: no machine drive-efficiency factor is
applied, matching the drilling module's existing convention
(``spec.md`` Assumptions).

This module is internal to ``operations.milling`` and is not part of the
public API. End milling and face milling each wrap it in their own named
metrics dataclass (research.md #2) so the two sub-operations stay
independently versionable even though the arithmetic is identical under the
full/symmetric-engagement assumption: average chip thickness equals the
feed per tooth, so neither chip thinning nor entry/exit angle enters the
calculation for either sub-operation.

All inputs and outputs here are canonical metric; imperial conversion
happens at each sub-operation's orchestration layer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from machine_calc.registry import WorkpieceMaterial

#: Conversion constant for ``Q``: (mm * mm * mm/min) -> cm^3/min.
MM3_PER_CM3 = 1000.0

#: Conversion constant for ``Pc``: (mm^2 * mm/min * N/mm^2) -> kW.
#: 60 converts per-minute to per-second, 10^6 converts N*mm/s to kW.
POWER_SCALE = 60.0 * 10**6

#: Standard kW <-> N*m/RPM torque constant (``Mc = Pc * 9550 / n``), the
#: same constant drilling already uses for ``Pc = Mc * n / 9550``.
TORQUE_POWER_CONSTANT = 9550.0


@dataclass(frozen=True)
class MillingMetrics:
    """Canonical-metric milling calculation outputs.

    Attributes:
        spindle_speed_rpm: Spindle speed (n), in RPM.
        feed_rate_mm_min: Table feed rate (vf), in mm/min.
        material_removal_rate_cm3_min: Material removal rate (Q), in
            cm^3/min.
        machining_time_min: Machining time (tc), in minutes (fractional).
        torque_nm: Cutting torque (Mc), in N*m.
        power_kw: Net cutting power (Pc), in kW.
    """

    spindle_speed_rpm: float
    feed_rate_mm_min: float
    material_removal_rate_cm3_min: float
    machining_time_min: float
    torque_nm: float
    power_kw: float


def calculate_milling_metrics(
    diameter_mm: float,
    axial_depth_of_cut_mm: float,
    radial_engagement_mm: float,
    feed_per_tooth_mm: float,
    number_of_teeth: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    cutting_speed_factor: float,
) -> MillingMetrics:
    """Compute milling parameters for validated, canonical-metric inputs.

    Args:
        diameter_mm: Tool/cutter diameter (D), in mm (already validated > 0).
        axial_depth_of_cut_mm: Axial depth of cut (ap), in mm (validated > 0).
        radial_engagement_mm: Radial engagement (ae), in mm — the radial
            depth of cut for end milling or the width of cut for face
            milling (already validated > 0 and <= ``diameter_mm``).
        feed_per_tooth_mm: Feed per tooth / chip load (fz), in mm/tooth
            (already validated > 0).
        number_of_teeth: Number of flutes/teeth/inserts (zn) (already
            validated as a positive whole number).
        length_of_cut_mm: Travel distance to be machined, in mm (validated
            > 0).
        material: The resolved workpiece material reference data, supplying
            the baseline cutting speed and the specific cutting force (kc).
        cutting_speed_factor: The selected milling tool's multiplier applied
            to the material's baseline cutting speed.

    Returns:
        The computed :class:`MillingMetrics`.
    """

    # 1. Effective cutting speed (vc), m/min.
    cutting_speed_m_min = material.reference_cutting_speed_m_min * cutting_speed_factor

    # 2. Spindle speed: n = (vc * 1000) / (pi * D)
    spindle_speed_rpm = (cutting_speed_m_min * 1000) / (math.pi * diameter_mm)

    # 3. Table feed rate: vf = n * fz * zn
    feed_rate_mm_min = spindle_speed_rpm * feed_per_tooth_mm * number_of_teeth

    # 4. Material removal rate: Q = (ap * ae * vf) / 1000
    material_removal_rate_cm3_min = (
        axial_depth_of_cut_mm * radial_engagement_mm * feed_rate_mm_min
    ) / MM3_PER_CM3

    # 5. Net cutting power: Pc = (ap * ae * vf * kc) / (60 * 10^6)
    power_kw = (
        axial_depth_of_cut_mm
        * radial_engagement_mm
        * feed_rate_mm_min
        * material.specific_cutting_force_kc
    ) / POWER_SCALE

    # 6. Torque: Mc = (Pc * 9550) / n
    torque_nm = (power_kw * TORQUE_POWER_CONSTANT) / spindle_speed_rpm

    # 7. Machining time: tc = length_of_cut / vf
    machining_time_min = length_of_cut_mm / feed_rate_mm_min

    return MillingMetrics(
        spindle_speed_rpm=spindle_speed_rpm,
        feed_rate_mm_min=feed_rate_mm_min,
        material_removal_rate_cm3_min=material_removal_rate_cm3_min,
        machining_time_min=machining_time_min,
        torque_nm=torque_nm,
        power_kw=power_kw,
    )
