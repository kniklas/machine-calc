# Contract: Milling Library API

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

The public contract exposed by `machine_calc` for the two new milling
sub-operations (FR-004 through FR-012), consumable independent of the CLI,
following the same "never raises for expected validation failures" contract
as `contracts/library-api.md` (`001-metal-drilling-calc`) (FR-012 of this
feature).

## Public surface

```python
from machine_calc import (
    calculate_end_milling,
    calculate_face_milling,
    list_end_mill_tools,
    list_face_mill_tools,
    UnitSystem,
)
```

`calculate_end_milling()` and `calculate_face_milling()` are implemented in
`machine_calc.operations.milling.end_milling` and
`machine_calc.operations.milling.face_milling` respectively, and re-exported
at the top level alongside the existing drilling `calculate()` (which is
unchanged — FR-002). `list_materials()` / `list_material_types()` (shared,
unchanged) continue to enumerate workpiece materials for both new
sub-operations.

```python
def calculate_end_milling(
    diameter: float,
    axial_depth_of_cut: float,
    radial_depth_of_cut: float,
    feed_per_tooth: float,
    number_of_teeth: float,   # accepted as float for caller convenience;
                              # rejected unless whole-numbered (FR-008)
    length_of_cut: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = DEFAULT_LOCALE,
    materials_config_path: str | None = None,
) -> CalculationResult: ...

def calculate_face_milling(
    diameter: float,
    axial_depth_of_cut: float,
    width_of_cut: float,
    feed_per_tooth: float,
    number_of_teeth: float,   # same whole-number rule as end milling
    length_of_cut: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = DEFAULT_LOCALE,
    materials_config_path: str | None = None,
) -> CalculationResult: ...

def list_end_mill_tools(config_path: str | None = None) -> list[str]: ...
def list_face_mill_tools(config_path: str | None = None) -> list[str]: ...
```

- Both `calculate_*` functions MUST NOT raise for expected validation
  failures (invalid/missing input, missing/unknown material or tool,
  unsupported material/tool combination, engagement exceeding diameter,
  exceeded power rating). They MUST always return a `CalculationResult`
  (data-model.md), mirroring drilling's `calculate()` contract (FR-012).
- All parameters are in the units of `unit_system` (mm/mm-per-tooth for
  METRIC, inches/inches-per-tooth for IMPERIAL); `available_power` follows
  the same kW/HP convention as drilling.
- `locale` and `materials_config_path` behave identically to their drilling
  counterparts (FR-013, FR-015, FR-016).

## Success response contract

```python
CalculationResult(
    spindle_speed_rpm=4775.4,
    feed_rate=1146.1,           # mm/min (METRIC) / in/min (IMPERIAL)
    machining_time=0.87,        # minutes, identical under both unit systems
    torque=8.5,                 # N*m (METRIC) / in-lb (IMPERIAL)
    power_required=4.28,        # kW (METRIC) / HP (IMPERIAL)
    material_removal_rate=24.0, # cm^3/min (METRIC) / in^3/min (IMPERIAL) -- new field
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,   # or a string if available_power exceeded
    error=None,
    mode=CalculationMode.STANDARD,  # echoed for shape-compatibility; milling
                                     # does not use POWER_CONSTRAINED/FIXED_RPM
)
```

`material_removal_rate` is `None` on any drilling `CalculationResult`
(unaffected by this feature) and on any milling error result. The examples in
this document are written with keyword arguments for readability; in the
actual `CalculationResult` dataclass `material_removal_rate` is declared
**last**, after every pre-existing field, so that positional construction in
existing drilling code and tests keeps working unchanged (research.md #7).

`power_required` is **net cutting power** at the cutter — no machine
drive-efficiency factor is applied — consistent with drilling and with
`spec.md` Assumptions.

## Error response contract

```python
CalculationResult(
    spindle_speed_rpm=None,
    feed_rate=None,
    machining_time=None,
    torque=None,
    power_required=None,
    material_removal_rate=None,
    unit_system=UnitSystem.METRIC,
    feasibility_warning=None,
    error=ErrorInfo(code="INVALID_ENGAGEMENT", message="..."),
    mode=CalculationMode.STANDARD,
)
```

See `data-model.md` "New Error Codes" for the full list, including reused
drilling codes (`MISSING_MATERIAL`, `UNUSABLE_MATERIAL`, `MISSING_TOOL`,
`INVALID_DIAMETER`) and milling-specific additions (`INVALID_DEPTH_OF_CUT`,
`INVALID_ENGAGEMENT`, `INVALID_FEED_PER_TOOTH`, `INVALID_TOOTH_COUNT`,
`INVALID_LENGTH_OF_CUT`).

## Identical-results guarantee (FR-012, User Story 4)

For identical inputs, `calculate_end_milling()` / `calculate_face_milling()`
MUST return byte-for-byte identical `CalculationResult` values whether
invoked directly (User Story 4) or via the CLI's milling sub-flows (User
Stories 2/3), since the CLI performs no calculation of its own — mirroring
drilling's existing identical-results contract test pattern
(`tests/contract/` in `001-metal-drilling-calc`).
