# Contract Delta: Library API (Milling Calculation Modes)

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This document specifies only the *changes* to
`specs/009-milling-calculations/contracts/library-api-milling.md`; everything
not mentioned here (tool/material resolution, the nine-step validation
order, the milling-specific error codes, the never-raises contract) is
unchanged and still in effect. It mirrors
`specs/002-constrained-calculation-modes/contracts/library-api-delta.md`'s
structure exactly, applied to both milling entry points.

## Updated public surface

```python
from machine_calc import (
    calculate_end_milling,
    calculate_face_milling,
    list_end_mill_tools,
    list_face_mill_tools,
    UnitSystem,
    CalculationMode,
)

def calculate_end_milling(
    diameter: float,
    axial_depth_of_cut: float,
    radial_depth_of_cut: float,
    feed_per_tooth: float,
    number_of_teeth: float,
    length_of_cut: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = DEFAULT_LOCALE,
    materials_config_path: str | None = None,
    mode: CalculationMode = CalculationMode.STANDARD,   # NEW
    target_rpm: float | None = None,                     # NEW
) -> CalculationResult: ...

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
    locale: str = DEFAULT_LOCALE,
    materials_config_path: str | None = None,
    mode: CalculationMode = CalculationMode.STANDARD,   # NEW
    target_rpm: float | None = None,                     # NEW
) -> CalculationResult: ...
```

- Both functions continue to never raise for expected validation
  failures — this now explicitly includes the three new failure modes
  drilling already defines (`INVALID_TARGET_RPM`, `MODE_CONFLICT`,
  `INFEASIBLE_POWER_BUDGET`), reused verbatim (research.md #4).
- Callers that never pass `mode` or `target_rpm` see **zero behavior
  change** from `009-milling-calculations` (SC-004) — this is a strictly
  additive, backward-compatible signature change, exactly as drilling's
  own mode parameters were.

## Success response contract (power-constrained mode, end milling)

```python
CalculationResult(
    spindle_speed_rpm=1290.5,      # reduced from the material/tool's recommended value
    feed_rate=258.1,
    machining_time=0.39,
    torque=4.8,                     # unchanged -- torque does not depend on spindle speed (research.md #1)
    power_required=1.10,            # equals the supplied available_power (within float tolerance)
    material_removal_rate=12.9,     # recomputed consistently from the reduced feed rate
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.POWER_CONSTRAINED,
    error=None,
)
```

If the supplied `available_power` is already sufficient at the
material/tool's recommended spindle speed, the result is identical to the
`STANDARD`-mode result for the same inputs, except `mode` is
`POWER_CONSTRAINED` (FR-003) — identical to drilling's equivalent
contract.

## Success response contract (fixed-RPM mode, face milling)

```python
CalculationResult(
    spindle_speed_rpm=1500.0,       # the user-supplied target_rpm, unchanged
    feed_rate=750.0,
    machining_time=0.20,
    torque=6.2,
    power_required=0.97,
    material_removal_rate=30.0,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,        # or a warning string if power_required > available_power
    mode=CalculationMode.FIXED_RPM,
    error=None,
)
```

## New error response contracts (reused from drilling, applied to milling)

```python
# INFEASIBLE_POWER_BUDGET -- no positive spindle speed fits the supplied budget
CalculationResult(
    spindle_speed_rpm=None, feed_rate=None, machining_time=None, torque=None,
    power_required=None, material_removal_rate=None,
    unit_system=UnitSystem.METRIC, feasibility_warning=None,
    mode=CalculationMode.POWER_CONSTRAINED,
    error=ErrorInfo(code="INFEASIBLE_POWER_BUDGET", message="..."),
)

# INVALID_TARGET_RPM -- target_rpm is zero, negative, non-numeric, NaN, or Infinity
CalculationResult(..., mode=CalculationMode.FIXED_RPM,
                   error=ErrorInfo(code="INVALID_TARGET_RPM", message="..."))

# MODE_CONFLICT -- POWER_CONSTRAINED with a supplied target_rpm, or missing available_power
CalculationResult(..., mode=CalculationMode.POWER_CONSTRAINED,
                   error=ErrorInfo(code="MODE_CONFLICT", message="..."))
```

All numeric fields — including `material_removal_rate` — are `None` on
every error result, exactly as `009-milling-calculations`' existing error
contract already requires (SC-003 of that feature).
