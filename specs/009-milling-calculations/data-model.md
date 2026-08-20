# Data Model: Milling Calculations Module

**Feature**: `009-milling-calculations` | **Date**: 2026-08-19

## Overview

This feature adds two new operations (end milling, face milling) under a
new `machine_calc.operations.milling` package, alongside the existing
`machine_calc.operations.drilling` package, plus a new top-level
`MachiningOperation`/`MillingSubOperation` selection concept used only by
the CLI dispatcher. It reuses, unchanged: `WorkpieceMaterial` (including its
existing `specific_cutting_force_kc` field), `UnitSystem`, `ErrorInfo`,
`Configuration`'s loader mechanism, the registry merge/override
infrastructure (`registry_config.py`), unit conversion helpers
(`units.py`), and the message-catalog/i18n mechanism.

## New / Changed Shared Entities (`models.py`)

### `MachiningOperation` (new `Enum`)

Selects which top-level operation the REPL routes into (FR-001).

| Member | Value |
|---|---|
| `DRILLING` | `"drilling"` |
| `MILLING` | `"milling"` |

Not used by the library API (each operation keeps its own `calculate()`
entry point) — this enum exists solely to drive the CLI's operation-
selection prompt and re-selection loop (FR-001, FR-017).

### `MillingSubOperation` (new `Enum`)

Selects which milling formula set applies (FR-003).

| Member | Value |
|---|---|
| `END_MILLING` | `"end-milling"` |
| `FACE_MILLING` | `"face-milling"` |

### `CalculationResult` (changed)

Add one new optional field, appended after the existing fields to preserve
positional-argument compatibility:

```python
material_removal_rate: float | None = None
```

- Units: cm^3/min (METRIC) / in^3/min (IMPERIAL). `None` for drilling
  results (drilling has no MRR concept) and for any error result.
- All existing drilling construction sites are unaffected (default `None`).

## New Entities: End Milling (`operations/milling/end_milling/`)

### `EndMillTool` (`tools.py`, mirrors `DrillingTool`)

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Unique display name, e.g. `"Carbide"`. |
| `cutting_speed_factor` | `float` | Multiplier applied to the material's `reference_cutting_speed_m_min`; must be `> 0`. |
| `unit_system` | `str` | `"metric"` \| `"imperial"`; stored/displayed only (no independent conversion — dimensionless ratio, same rationale as `DrillingTool.unit_system`). |
| `translations` | `dict[str, str]` | Locale -> translated display name. |

Built from bundled `operations/milling/end_milling/data/tools.toml` merged
with an optional user override via the existing
`registry_config.load_and_merge()`, exactly like `DrillingTool`, but using
the distinct `table_key` `"end_mill_tools"` (research.md #3) — **not**
drilling's `"tools"`. Reusing `"tools"` would merge user-supplied end-mill
entries into the drilling registry, where the mandatory `feed_factor` field
is absent and `RegistryConfigError` would break the existing drilling flow
(FR-015, SC-005). No `feed_factor` field on this entity (research.md #4 —
feed per tooth is a direct per-calculation input, not registry-derived).

### Registry `table_key` allocation (normative)

| Registry | Module | `table_key` |
|---|---|---|
| Materials (existing, shared) | `registry.py` | `materials` |
| Drilling tools (existing, unchanged) | `operations/drilling/tools.py` | `tools` |
| End-mill tools (new) | `operations/milling/end_milling/tools.py` | `end_mill_tools` |
| Face-mill tools (new) | `operations/milling/face_milling/tools.py` | `face_mill_tools` |

Every key MUST be distinct and each registry MUST ignore array-of-tables it
does not own, so that a user config file containing any subset of these
sections loads cleanly for every operation. Pre-existing user config files
(which contain only `[[materials]]` and/or `[[tools]]`) therefore remain
valid and keep affecting drilling only.

### End Milling Calculation Inputs

| Field | Unit (metric) | Validation |
|---|---|---|
| `diameter_mm` | mm | `> 0`, `<= Configuration.max_mill_diameter_mm` |
| `axial_depth_of_cut_mm` (ap) | mm | `> 0`, `<= Configuration.max_depth_of_cut_mm` |
| `radial_depth_of_cut_mm` (ae) | mm | `> 0`, `<= diameter_mm` (FR-009), `<= Configuration.max_depth_of_cut_mm` |
| `feed_per_tooth_mm` (fz) | mm/tooth | `> 0` |
| `number_of_teeth` (zn) | count (int-valued float) | `> 0` **and whole-numbered** — a value such as `4.5` is rejected (FR-008) |
| `length_of_cut_mm` | mm | `> 0`, `<= Configuration.max_length_of_cut_mm` |
| `material` | `WorkpieceMaterial` | must resolve and be `is_usable` |
| `tool` | `EndMillTool` | must resolve |
| `available_power_kw` | kW | optional; feasibility check only (FR-011) |

### `EndMillingMetrics` (`formulas.py`, mirrors `DrillingMetrics`)

```python
@dataclass(frozen=True)
class EndMillingMetrics:
    spindle_speed_rpm: float
    feed_rate_mm_min: float
    material_removal_rate_cm3_min: float
    machining_time_min: float
    torque_nm: float
    power_kw: float
```

Computed by the shared core (`operations/milling/_shared.py`,
`calculate_milling_metrics()` — research.md #1, #2) using `ap =
axial_depth_of_cut_mm`, `ae = radial_depth_of_cut_mm`.

## New Entities: Face Milling (`operations/milling/face_milling/`)

### `FaceMillTool` (`tools.py`)

Identical shape to `EndMillTool` (`name`, `cutting_speed_factor`,
`unit_system`, `translations`); a distinct registry/table (research.md #3)
built from `operations/milling/face_milling/data/tools.toml` and loaded with
the distinct `table_key` `"face_mill_tools"`.

### Face Milling Calculation Inputs

Same shape as end milling, with `radial_depth_of_cut_mm` renamed
`width_of_cut_mm` (ae) — validated `> 0` and `<= diameter_mm` (FR-009 /
User Story 3 Acceptance Scenario 3) — and `tool: FaceMillTool` instead of
`EndMillTool`. `axial_depth_of_cut_mm`, `feed_per_tooth_mm`,
`number_of_teeth`, `length_of_cut_mm` are identical in shape/validation to
end milling.

### `FaceMillingMetrics` (`formulas.py`)

Same shape as `EndMillingMetrics`, computed by the same shared core with
`ae = width_of_cut_mm`.

## Shared Core Formula (`operations/milling/_shared.py`)

```python
def calculate_milling_metrics(
    diameter_mm: float,
    axial_depth_of_cut_mm: float,
    radial_engagement_mm: float,  # ae: radial depth of cut or width of cut
    feed_per_tooth_mm: float,
    number_of_teeth: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    cutting_speed_factor: float,
) -> MillingMetrics:
    ...
```

Internal-only (not part of the public API); `end_milling/formulas.py` and
`face_milling/formulas.py` each call it and re-wrap the result as their own
named metrics dataclass (research.md #2), so the two sub-operations remain
independently versionable modules even though the arithmetic is shared.

`MillingMetrics` (the shared, private return shape) has the same five
fields as `EndMillingMetrics`/`FaceMillingMetrics` above.

### Formulas (research.md #1; Sandvik Coromant "Machining Formulas")

1. `vc = material.reference_cutting_speed_m_min * cutting_speed_factor`
2. `n = (vc * 1000) / (pi * diameter_mm)` — spindle speed, RPM
3. `vf = n * feed_per_tooth_mm * number_of_teeth` — table feed rate, mm/min
4. `Q = (axial_depth_of_cut_mm * radial_engagement_mm * vf) / 1000` — MRR, cm^3/min
5. `Pc = (axial_depth_of_cut_mm * radial_engagement_mm * vf * material.specific_cutting_force_kc) / (60 * 10**6)` — net power, kW
6. `Mc = (Pc * 9550) / n` — torque, Nm
7. `tc = length_of_cut_mm / vf` — machining time, minutes

## New Error Codes (extending `ErrorInfo.code`)

Reuses existing codes where the semantics match exactly, and adds new ones
where the input differs from drilling's:

| Code | Trigger |
|---|---|
| `MISSING_MATERIAL` | (reused, unchanged) |
| `UNUSABLE_MATERIAL` | (reused, unchanged) |
| `MISSING_TOOL` | (reused; applies to end-mill/face-mill tool names too) |
| `INVALID_DIAMETER` | (reused; tool/cutter diameter <= 0 or exceeds bound) |
| `INVALID_DEPTH_OF_CUT` | axial or radial/width depth of cut <= 0, non-numeric, or exceeds bound |
| `INVALID_ENGAGEMENT` | radial depth of cut (end milling) or width of cut (face milling) exceeds tool/cutter diameter (FR-009) |
| `INVALID_FEED_PER_TOOTH` | feed per tooth <= 0 or non-numeric |
| `INVALID_TOOTH_COUNT` | number of teeth/flutes/inserts <= 0, non-numeric, or not a whole number (FR-008) |
| `INVALID_LENGTH_OF_CUT` | length of cut <= 0, non-numeric, or exceeds bound |

Milling defines **no** per-material/per-tool combination reference table, so
there is no milling equivalent of a "combination not supported" error: every
registered milling tool is usable with every material whose reference data is
valid. FR-010's failure mode is therefore fully covered by the reused
`UNUSABLE_MATERIAL` code, raised when the selected material's
`specific_cutting_force_kc` is missing or non-positive (milling torque/power
depend on it). No new error code is introduced for this case.

All error paths return a `CalculationResult` with `error` set and every
numeric field (including `material_removal_rate`) `None` — never raise
(FR-012, consistent with drilling's FR-015).

## Configuration (`config.py`, extended)

New optional fields on `Configuration`, loaded from the same TOML file
drilling already supports (FR-018; research.md #8 records why these
particular defaults were chosen):

| Field | Default | Meaning |
|---|---|---|
| `max_mill_diameter_mm` | `200.0` | Upper bound for end-mill/face-mill cutter diameter. |
| `max_depth_of_cut_mm` | `50.0` | Upper bound for axial depth of cut and radial depth/width of cut. |
| `max_length_of_cut_mm` | `1000.0` | Upper bound for length of cut. |

## Validation Order (mirrors drilling's established precedence)

1. Material present -> resolves -> `is_usable`.
2. Tool (end-mill/face-mill) present -> resolves.
3. Diameter valid.
4. Axial depth of cut valid.
5. Radial depth of cut / width of cut valid, then checked `<=` diameter.
6. Feed per tooth valid.
7. Number of teeth valid.
8. Length of cut valid.
9. Optional `available_power` feasibility check (never blocks the result).

## Relationship to Existing Entities

```text
WorkpieceMaterial (registry.py, unchanged)
  ├── used by operations/drilling  (existing)
  ├── used by operations/milling/end_milling   (new)
  └── used by operations/milling/face_milling  (new)

CalculationResult (models.py, + material_removal_rate)
  ├── returned by operations/drilling.calculate()          (unchanged shape)
  ├── returned by operations/milling/end_milling.calculate() (new)
  └── returned by operations/milling/face_milling.calculate() (new)
```
