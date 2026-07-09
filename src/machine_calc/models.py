"""Shared, operation-agnostic data structures.

These types are used by every `machine_calc.operations.*` module (currently
only drilling) and by the CLI layer. See
``specs/001-metal-drilling-calc/data-model.md`` for the authoritative field
definitions this module implements.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UnitSystem(Enum):
    """Selects the unit system used for calculation input/output.

    Attributes:
        METRIC: Diameter/depth in mm, feed rate in mm/min, torque in N*m,
            power in kW. Spindle speed (RPM) and machining time (minutes)
            are unit-system independent.
        IMPERIAL: Diameter/depth in inches, feed rate in in/min, torque in
            in-lb, power in HP. Spindle speed (RPM) and machining time
            (minutes) are unit-system independent.
    """

    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass(frozen=True)
class ErrorInfo:
    """A structured, machine-readable validation/error result.

    Attributes:
        code: Machine-readable identifier, e.g. ``"INVALID_DIAMETER"``,
            ``"INVALID_DEPTH"``, ``"MISSING_MATERIAL"``, ``"MISSING_TOOL"``,
            ``"UNSUPPORTED_COMBINATION"``.
        message: Human-readable explanation suitable for CLI display.
    """

    code: str
    message: str


@dataclass(frozen=True)
class CalculationResult:
    """The structured result returned by every operation's ``calculate()``.

    Field names are intentionally unit-agnostic; the ``unit_system`` field
    indicates which units apply to each numeric field:

    - ``spindle_speed_rpm``: RPM. Identical under METRIC and IMPERIAL (not a
      unit-system-dependent quantity).
    - ``feed_rate``: mm/min under METRIC, in/min under IMPERIAL.
    - ``machining_time``: Minutes (fractional). Identical under METRIC and
      IMPERIAL per the spec clarification (machining time is always reported
      in minutes regardless of unit system).
    - ``torque``: N*m under METRIC, in-lb under IMPERIAL.
    - ``power_required``: kW under METRIC, HP under IMPERIAL.

    When ``error`` is set, all numeric fields above MUST be ``None`` — this
    type is always returned, never raised, for expected validation failures
    (FR-015).
    """

    spindle_speed_rpm: float | None
    feed_rate: float | None
    machining_time: float | None
    torque: float | None
    power_required: float | None
    unit_system: UnitSystem
    feasibility_warning: str | None = None
    error: ErrorInfo | None = None
