# Phase 1 Data Model: Milling Calculation Modes

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This document extends `specs/009-milling-calculations/data-model.md` (the
milling entities) using the calculation-mode model already defined in
`specs/002-constrained-calculation-modes/data-model.md`. Unmodified entities
(`WorkpieceMaterial`, `EndMillTool`, `FaceMillTool`, `UnitSystem`,
`Configuration`, `Message Catalog`, and the `CalculationMode` enum itself,
which is reused **verbatim**, no new members) are not repeated here.

## CalculationMode (enum) — reused unchanged

No changes. `STANDARD` / `POWER_CONSTRAINED` / `FIXED_RPM` retain exactly the
definitions and semantics `002-constrained-calculation-modes/data-model.md`
already gives them; end-milling and face-milling requests now also carry
this same enum value (research.md #4).

## EndMillingOperation / FaceMillingOperation (request) — extended

Both `calculate_end_milling()` and `calculate_face_milling()` gain the same
two new optional parameters, with identical semantics to drilling's
equivalent extension:

| Field | Type | Notes |
|---|---|---|
| `mode` | `CalculationMode` | New. Defaults to `STANDARD`. Selects which of the three calculation paths is used. Identical semantics to `002-constrained-calculation-modes`' `mode`. |
| `target_rpm` | float \| None | New. Required when `mode is FIXED_RPM`; MUST be `None` otherwise (FR-009). Same units (RPM) under both `UnitSystem` values (RPM is unit-system-independent, per `009-milling-calculations`). |

`available_power` (already present in both milling entry points since
`009-milling-calculations`) is reused with the same mode-dependent semantics
drilling already established:

| `mode` | `available_power` semantics |
|---|---|
| `STANDARD` | Optional; advisory-only feasibility warning if exceeded (`009-milling-calculations` behavior), unchanged. |
| `POWER_CONSTRAINED` | **Required.** Hard constraint: the calculation adjusts spindle speed (and its dependents) to stay within it, or is rejected if infeasible (FR-002, FR-004). Omitting it while `mode is POWER_CONSTRAINED` is a `MODE_CONFLICT` error. |
| `FIXED_RPM` | Optional; advisory-only feasibility warning if exceeded at the given `target_rpm` (FR-008), same semantics as `STANDARD`. |

**Validation order**: `009-milling-calculations`' existing nine-step
validation order (material present → tool present → material resolved/usable
→ tool resolved → diameter → axial depth of cut → radial engagement/width of
cut bound → radial engagement `<=` diameter → feed per tooth → tooth count →
length of cut) runs first, unchanged. Mode-argument validation
(`target_rpm`/`available_power`/mutual-exclusivity) runs **after** all nine
existing checks, mirroring drilling's own precedence
(`002-constrained-calculation-modes/data-model.md`, `/speckit.analyze`
finding U1) — a milling-specific failure (e.g., `INVALID_DIAMETER`,
`UNSUPPORTED_COMBINATION`) is always returned before any mode-argument
check runs.

- `target_rpm`, when supplied, MUST be a positive, finite number; zero,
  negative, non-numeric, `NaN`, or `Infinity` values are all rejected under
  `ErrorInfo(code="INVALID_TARGET_RPM")` (FR-007) — reusing
  `validate_target_rpm()` **unmodified** (research.md #4).
- `mode`/`target_rpm`/`available_power` mutual exclusivity is validated by
  reusing `validate_mode_arguments()` **unmodified** (research.md #4):
  `POWER_CONSTRAINED` requires `available_power` and rejects a supplied
  `target_rpm`; both violations are `ErrorInfo(code="MODE_CONFLICT")`.

## MillingMetrics (internal, `_shared.py`) — extended

`operations/milling/_shared.py` gains two new functions alongside the
existing `calculate_milling_metrics()` (unchanged; now a thin wrapper, per
research.md #1 of `009-milling-calculations`'s pattern for factoring shared
arithmetic):

- `calculate_milling_metrics_at_rpm(diameter_mm, axial_depth_of_cut_mm,
  radial_engagement_mm, feed_per_tooth_mm, number_of_teeth,
  length_of_cut_mm, material, spindle_speed_rpm) -> MillingMetrics` — new.
  Computes every `MillingMetrics` field for an explicit spindle speed
  instead of deriving it from `cutting_speed_factor` (research.md #2/#3).
  `calculate_milling_metrics()` becomes a thin wrapper: it derives the
  nominal `spindle_speed_rpm` from `cutting_speed_factor` and delegates
  here, exactly mirroring
  `operations/drilling/formulas.py::calculate_drilling_metrics_at_rpm()`.
- `calculate_power_constrained_milling_metrics(diameter_mm, ...,
  available_power_kw) -> MillingMetrics` — new. Implements the closed-form
  scaling derivation (research.md #1): returns the nominal metrics
  unchanged when `available_power_kw` is already sufficient (including
  exact equality, within `math.isclose()`'s default tolerance — FR-003),
  or the metrics recomputed at the algebraically reduced `n_adjusted` (FR-002).

Both sub-operations' `formulas.py` (`end_milling/formulas.py`,
`face_milling/formulas.py`) gain a matching thin wrapper,
`calculate_<sub-op>_metrics_at_rpm(...)`, adapting the shared core's inputs
into their own named metrics dataclass exactly as their existing
`calculate_<sub-op>_metrics()` wrapper already does — preserving the
`009-milling-calculations` FR-014 module boundary (research.md #3). Neither
sub-operation implements the scaling arithmetic itself.

## Error Codes

This feature reuses drilling's existing `INFEASIBLE_POWER_BUDGET`,
`INVALID_TARGET_RPM`, and `MODE_CONFLICT` codes and their existing
message-catalog entries verbatim (research.md #4), in addition to the
milling-specific codes `009-milling-calculations` already defines
(`MISSING_MATERIAL`, `MISSING_TOOL`, `UNUSABLE_MATERIAL`,
`INVALID_DIAMETER`, `INVALID_DEPTH_OF_CUT`, `INVALID_ENGAGEMENT`,
`INVALID_FEED_PER_TOOTH`, `INVALID_TOOTH_COUNT`, `INVALID_LENGTH_OF_CUT`,
`UNSUPPORTED_COMBINATION`), which are unaffected by this feature.

Two new error codes were introduced during implementation for
milling-specific edge cases not covered by drilling's reused set:
`INVALID_AVAILABLE_POWER` (a non-numeric, non-finite, or non-positive
`available_power` in power-constrained mode) and `CALCULATION_OVERFLOW`
(an otherwise-valid extreme input that overflows an intermediate
calculation). Both have their own message-catalog entries
(`error.invalid_available_power`, `error.calculation_overflow`).

## CalculationResult — reused unchanged

No new fields. `mode: CalculationMode` (added by
`002-constrained-calculation-modes`) and `material_removal_rate` (added by
`009-milling-calculations`) already coexist on the same dataclass; milling
results produced in power-constrained or fixed-RPM mode populate both
fields simultaneously — `mode` reflects the requested mode and
`material_removal_rate` continues to reflect the (possibly mode-adjusted)
feed rate, exactly as the two features' fields were each designed to be
independent/additive.

## `_MillingSessionState` (CLI, internal) — extended

`cli.py`'s `_MillingSessionState` dataclass gains the same three fields
drilling's session state already carries for its own mode support:

| Field | Type | Notes |
|---|---|---|
| `mode` | `CalculationMode` | New. Defaults to `CalculationMode.STANDARD`. Editable default across loop iterations, per sub-operation session (`009-milling-calculations` FR-017). |
| `previous_mode` | `CalculationMode` | New. Tracks the prior iteration's mode so a change is detected and mode-specific values are cleared (FR-013). |
| `target_rpm` | float \| None | New. Cleared (reset to `None`) whenever `mode != previous_mode` (FR-013), never carried over across a mode change. |

`available_power`'s existing field is reused with the same
mode-dependent required/optional/advisory semantics described above; it is
also cleared on a mode change when it was entered as a power-constrained
hard constraint (FR-013), consistent with drilling's existing behavior.
