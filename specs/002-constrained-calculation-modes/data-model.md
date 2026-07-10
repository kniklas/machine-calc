# Phase 1 Data Model: Constrained Drilling Calculation Modes

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This document extends `specs/001-metal-drilling-calc/data-model.md` with the
new entities and field additions introduced by this feature. Unmodified
entities from the base spec (`WorkpieceMaterial`, `DrillingTool`,
`MaterialToolCompatibility`, `UnitSystem`, `Configuration`, `Message Catalog`)
are not repeated here.

## CalculationMode (enum) — new

Selects which of the three ways a drilling calculation is performed
(spec.md Key Entities).

- `STANDARD` — spindle speed derived from material/tool reference values, as
  in the base spec. Default value; existing callers that never set `mode`
  get this behavior unchanged (SC-004).
- `POWER_CONSTRAINED` — spindle speed reduced (research.md #1) to fit a
  required `available_power` (FR-001, FR-002, FR-003, FR-004).
- `FIXED_RPM` — spindle speed supplied directly via `target_rpm` (FR-005,
  FR-006, FR-007, FR-008).

Exactly one mode applies per calculation request (FR-009); requesting
`POWER_CONSTRAINED` without `available_power`, or supplying `target_rpm`
together with a `POWER_CONSTRAINED`-mode power constraint, is rejected with
`ErrorInfo(code="MODE_CONFLICT")` (research.md #4).

## DrillingOperation (request) — extended

Extends the base spec's `DrillingOperation` with two new optional fields:

| Field | Type | Notes |
|---|---|---|
| `mode` | `CalculationMode` | New. Defaults to `STANDARD`. Selects which of the three calculation paths is used. |
| `target_rpm` | float \| None | New. Required when `mode is FIXED_RPM`; MUST be `None` otherwise (FR-009). Same units (RPM) under both `UnitSystem` values (base spec: RPM is unit-system-independent). |

`available_power` (already present in the base spec's `DrillingOperation`) is
reused with mode-dependent semantics:

| `mode` | `available_power` semantics |
|---|---|
| `STANDARD` | Optional; advisory-only feasibility warning if exceeded (base spec FR-012), unchanged. |
| `POWER_CONSTRAINED` | **Required.** Hard constraint: the calculation adjusts spindle speed to stay within it, or is rejected if infeasible (FR-002, FR-004). Omitting it while `mode is POWER_CONSTRAINED` is a `MODE_CONFLICT` error (research.md #4). |
| `FIXED_RPM` | Optional; advisory-only feasibility warning if exceeded at the given `target_rpm` (FR-008), same semantics as `STANDARD`. |

Validation (new, in addition to the base spec's diameter/depth/material/tool
validation, all performed before calculation per FR-015):

- `target_rpm`, when supplied, MUST be a positive, finite number; zero,
  negative, or non-numeric values are rejected with
  `ErrorInfo(code="INVALID_TARGET_RPM")` (FR-007).
- `mode is FIXED_RPM` requires `target_rpm` to be supplied; `mode` values
  other than `FIXED_RPM` require `target_rpm` to be `None`. Any mismatch is
  rejected with `ErrorInfo(code="MODE_CONFLICT")` (FR-009).
- `mode is POWER_CONSTRAINED` requires `available_power` to be supplied and
  positive; a supplied `available_power` of zero or less in this mode makes
  the request infeasible by construction and is rejected with
  `ErrorInfo(code="INFEASIBLE_POWER_BUDGET")` (FR-004), distinct from the
  "no `available_power` at all" `MODE_CONFLICT` case above.

## CalculationResult (response) — extended

Extends the base spec's `CalculationResult` with one new field:

| Field | Type | Notes |
|---|---|---|
| `mode` | `CalculationMode` | New. Echoes which mode produced this result (FR-012), so calling programs and the interactive text interface can distinguish an adjusted (`POWER_CONSTRAINED`) or user-specified (`FIXED_RPM`) spindle speed from the material/tool's own recommended one (`STANDARD`). Always set, including on error results (mirrors the requested mode, for consistency with `unit_system`'s existing always-set behavior). |

All other fields (`spindle_speed_rpm`, `feed_rate`, `machining_time`,
`torque`, `power_required`, `unit_system`, `feasibility_warning`, `error`)
are unchanged in type and meaning; in `POWER_CONSTRAINED`/`FIXED_RPM` modes
they simply reflect the adjusted/user-specified spindle speed rather than
the material/tool-derived one (research.md #1, #2).

## ErrorInfo — new codes

Extends the base spec's `ErrorInfo.code` values
(`MISSING_MATERIAL`/`MISSING_TOOL`/`INVALID_DIAMETER`/`INVALID_DEPTH`/
`UNSUPPORTED_COMBINATION`) with three new codes (research.md #4):

| Code | Trigger |
|---|---|
| `INVALID_TARGET_RPM` | `target_rpm` is zero, negative, or non-numeric (FR-007). |
| `MODE_CONFLICT` | Both a power constraint and a `target_rpm` supplied at once; or `POWER_CONSTRAINED` mode selected without `available_power`; or `target_rpm` supplied while `mode` is not `FIXED_RPM` (FR-009). |
| `INFEASIBLE_POWER_BUDGET` | `POWER_CONSTRAINED` mode requested and no positive spindle speed keeps required power within the supplied `available_power` (FR-004). |

## Power Constraint (conceptual entity, spec.md Key Entities)

Not a standalone class — represented by `available_power` on the request
when `mode is POWER_CONSTRAINED`. See `DrillingOperation` above for its
validation and the linear derivation of the adjusted spindle speed in
research.md #1.

## Spindle Speed Constraint (conceptual entity, spec.md Key Entities)

Not a standalone class — represented by `target_rpm` on the request when
`mode is FIXED_RPM`. See `DrillingOperation` above for its validation.

## Relationships (delta)

```
DrillingOperation.mode ──(selects)──▶ {STANDARD | POWER_CONSTRAINED | FIXED_RPM} calculation path
DrillingOperation.available_power ──(hard constraint, if POWER_CONSTRAINED)──▶ calculate_drilling_metrics_at_rpm(n_adjusted)
DrillingOperation.target_rpm ──(direct input, if FIXED_RPM)──▶ calculate_drilling_metrics_at_rpm(target_rpm)
CalculationResult.mode ──(echoes)──▶ DrillingOperation.mode
```

## State / Lifecycle

Unchanged from the base spec — these remain stateless value objects computed
per request; no new persistence or cross-request state is introduced.

## Message Catalog (delta)

New message keys required (FR-011; added to `locales/en.py` only, per spec
Assumptions — no new locale is introduced by this feature):

- REPL mode-selection prompt text and its three option labels (research.md #5).
- REPL follow-up prompts: required available-power prompt (power-constrained
  mode), required target-RPM prompt (fixed-RPM mode).
- A label distinguishing an adjusted/user-specified spindle speed from a
  material/tool-recommended one, for CLI display (FR-012).
- Error messages for the three new `ErrorInfo` codes above.
