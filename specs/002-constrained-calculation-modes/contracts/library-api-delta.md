# Contract Delta: Library API

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This document specifies only the *changes* to
`specs/001-metal-drilling-calc/contracts/library-api.md`; everything not
mentioned here (e.g., `list_materials()`, `list_tools()`, the base five error
codes, the never-raises contract for expected validation failures) is
unchanged and still in effect.

## Updated public surface

```python
from machine_calc import calculate, list_materials, list_tools, UnitSystem, CalculationMode

def calculate(
    diameter: float,
    depth: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = DEFAULT_LOCALE,
    mode: CalculationMode = CalculationMode.STANDARD,   # NEW
    target_rpm: float | None = None,                     # NEW
) -> CalculationResult: ...
```

- `calculate(...)` continues to never raise for expected validation
  failures — this now explicitly includes the three new failure modes this
  feature introduces (`INVALID_TARGET_RPM`, `MODE_CONFLICT`,
  `INFEASIBLE_POWER_BUDGET`).
- Callers that never pass `mode` or `target_rpm` see **zero behavior
  change** from `001-metal-drilling-calc` (SC-004) — this is a strictly
  additive, backward-compatible signature change.

## Success response contract (power-constrained mode)

```python
CalculationResult(
    spindle_speed_rpm=810.3,      # reduced from the material/tool's recommended value
    feed_rate=32.5,
    machining_time=0.70,
    torque=3.1,                    # unchanged — torque does not depend on spindle speed (research.md #1)
    power_required=0.30,           # equals the supplied available_power (within float tolerance)
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.POWER_CONSTRAINED,
    error=None,
)
```

If the supplied `available_power` is already sufficient at the
material/tool's recommended spindle speed, the result is identical to the
`STANDARD`-mode result for the same inputs, except `mode` is
`POWER_CONSTRAINED` (FR-003).

## Success response contract (fixed-RPM mode)

```python
CalculationResult(
    spindle_speed_rpm=1200.0,     # caller-supplied target_rpm, echoed back
    feed_rate=48.0,
    machining_time=0.47,
    torque=3.1,
    power_required=0.39,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,      # or set, per FR-008, if power_required > available_power
    mode=CalculationMode.FIXED_RPM,
    error=None,
)
```

## Error response contracts (new codes)

```python
# Fixed-RPM mode, target_rpm <= 0 or non-numeric (FR-007)
CalculationResult(
    spindle_speed_rpm=None, feed_rate=None, machining_time=None,
    torque=None, power_required=None,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.FIXED_RPM,
    error=ErrorInfo(code="INVALID_TARGET_RPM", message="Target spindle speed must be greater than 0."),
)

# Power-constrained mode, no positive RPM fits the budget (FR-004)
CalculationResult(
    spindle_speed_rpm=None, feed_rate=None, machining_time=None,
    torque=None, power_required=None,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.POWER_CONSTRAINED,
    error=ErrorInfo(code="INFEASIBLE_POWER_BUDGET", message="No spindle speed keeps required power within the available power budget."),
)

# Both a power constraint and a target RPM supplied, or POWER_CONSTRAINED
# mode selected without available_power (FR-009)
CalculationResult(
    spindle_speed_rpm=None, feed_rate=None, machining_time=None,
    torque=None, power_required=None,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    mode=CalculationMode.POWER_CONSTRAINED,  # or FIXED_RPM, whichever was requested
    error=ErrorInfo(code="MODE_CONFLICT", message="Power-constrained and fixed-RPM modes cannot be combined in one request."),
)
```

### New error codes summary (research.md #4)

| Code | Trigger |
|---|---|
| `INVALID_TARGET_RPM` | `target_rpm` is zero, negative, or non-numeric (FR-007) |
| `MODE_CONFLICT` | Conflicting/incomplete mode arguments (FR-009) |
| `INFEASIBLE_POWER_BUDGET` | No positive spindle speed satisfies the power budget (FR-004) |

## Identical-results guarantee (FR-016, unchanged contract)

The CLI and library MUST continue to produce identical `CalculationResult`
values for identical inputs, now including identical `mode`/`target_rpm`
selections — the interactive text interface's new mode-selection prompt
(FR-001a) is purely an input-gathering step that ultimately calls the same
`calculate()` function with the same arguments a library caller would use.
