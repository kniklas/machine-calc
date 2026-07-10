# Implementation Plan: Constrained Drilling Calculation Modes (Power-Limited & Fixed-RPM)

**Branch**: `feat/constrained-calculation-modes` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-constrained-calculation-modes/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend the existing drilling `calculate()` entry point (`001-metal-drilling-calc`)
with two new opt-in, mutually-exclusive calculation modes, selected via a new
`mode` parameter (and, in the interactive text interface, a new mode-selection
prompt per spec.md FR-001a): **power-constrained** (reduce spindle speed/feed
rate to the fastest settings that fit a supplied available power budget) and
**fixed-RPM** (accept a target spindle RPM directly and derive feed rate,
machining time, torque, and required power from it). Both modes reuse the
existing formulas and registries unchanged — see research.md #1 for the
closed-form (non-iterative) algorithm this relies on — and the standard
(unconstrained) mode's behavior and results are unaffected (spec.md SC-004).

## Technical Context

**Language/Version**: Python 3.9+ (unchanged from `001-metal-drilling-calc`; no new version requirement introduced)

**Primary Dependencies**: None new. Reuses the existing zero/near-zero-dependency stack (`tomli` on Python <3.11 only); new user-facing text (mode-selection prompt, adjusted-value labels, new error messages) is added to the existing pure-Python message catalog (`src/machine_calc/locales/en.py`) via `i18n.py`, per Constitution Principle VIII and spec.md FR-011.

**Storage**: N/A (stateless per-request calculations, unchanged)

**Testing**: `pytest` with `pytest-cov`; tolerance-based float comparisons (`math.isclose`) per Constitution Principle III, including for the new closed-form power-scaling calculation (research.md #1)

**Target Platform**: Cross-platform CLI/library (unchanged from `001-metal-drilling-calc`)

**Project Type**: Single project — extends the existing Python library + thin CLI layer; no new top-level entry point (spec.md Assumptions)

**Performance Goals**: Each calculation (including the new modes) completes within the same 0.5-1.0s target as the base spec (Constitution Principle V) — the power-constrained algorithm is closed-form (research.md #1), not iterative, so it adds negligible overhead over the standard calculation

**Constraints**: Same as `001-metal-drilling-calc` (Constitution Principle V: ~64-128MB RAM, single-threaded, Debian-stable compatible); no exceptions raised for expected validation failures, including the two new failure modes this feature introduces (infeasible power budget, invalid target RPM, conflicting mode selection) — spec.md FR-004/FR-007/FR-009, base spec FR-015; invalid/blank REPL prompt entries (mode selection, required available-power) re-prompt rather than silently defaulting or erroring as MODE_CONFLICT, and a mode change on loop re-run clears mode-specific values (spec.md FR-001a, FR-013); application logging remains English-only regardless of locale (Constitution VIII)

**Scale/Scope**: Extends the single existing drilling operation (`operations/drilling`) with two new modes; no new operation, no new registries, no new top-level library entry point. Interactive text interface gains one new prompt (mode selection, FR-001a) plus mode-conditional follow-up prompts (available power as constraint, or target RPM)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Single-responsibility modules; new logic added to existing `operations/drilling` module (formulas.py/`__init__.py`), not scattered; public `calculate()` docstring updated to document `mode`/`target_rpm` and the new error codes | PASS — new mode-dispatch logic isolated in `operations/drilling/__init__.py`; RPM-based metric calculation factored into a shared helper in `formulas.py` (research.md #1) reused by standard, power-constrained, and fixed-RPM paths, avoiding duplicated formula logic |
| II. Testing Standards | Unit tests for the new closed-form power-scaling calculation (nominal/boundary/exceeds-budget/exactly-at-budget cases) and fixed-RPM calculation (nominal/boundary/invalid RPM); ≥90% coverage maintained on calculation modules | PASS — planned unit tests in `tests/unit/operations/drilling/` for the new formula helper; contract tests for the two new modes and the mutual-exclusivity/validation error paths |
| III. Calculation Robustness & Accuracy | Tolerance-based comparisons for the linear power-scaling result; validated `target_rpm`/`available_power` inputs; explicit handling of the "no positive RPM fits" edge case | PASS — research.md #1 documents the closed-form derivation (with the underlying formula citations already established in `001-metal-drilling-calc` research.md #4); FR-004's rejection path is an explicit, tested edge case |
| IV. Python Packaging & Versioning | No new dependencies; public API addition (`mode`, `target_rpm` parameters, `CalculationMode` enum, new `ErrorInfo` codes) is additive/backward-compatible → MINOR version bump, not MAJOR | PASS — data-model.md marks all new `CalculationResult`/`calculate()` fields as additive with defaults, preserving the existing call signature for callers that pass no new arguments |
| V. Resource-Constrained Compatibility | No new runtime dependencies; new calculation path is O(1) closed-form, not iterative — no additional CPU/memory burden beyond the base spec's existing profile | PASS — research.md #1 confirms a direct algebraic solution (no solver/iteration), preserving the 0.5-1.0s per-calculation target |
| VI. Extensibility by Design | New modes MUST NOT require rewriting the standard calculation path; drilling-specific formula reuse stays inside `operations/drilling` | PASS — `calculate_drilling_metrics_at_rpm()` (research.md #1) is a drilling-operation-local refactor; shared infrastructure (`models.py`, `registry.py`, `units.py`, `validation.py`, `i18n.py`, `cli.py` dispatch) is extended additively (new enum, new prompt), not restructured; a future turning/milling operation can adopt the same at-RPM/at-power pattern independently |
| VII. Documentation & Publishing | Sphinx docs and README updated to document the two new modes, the new `mode`/`target_rpm` parameters, and the new error codes | PASS (planned) — docstring updates to `calculate()` and `CalculationResult`/`ErrorInfo` feed the existing Sphinx autodoc build; no new doc toolchain needed |
| VIII. Internationalization of User-Facing Messages | All new user-facing text (mode-selection prompt, adjusted-vs-recommended labeling, new error/warning messages) MUST be sourced from the message catalog, not hard-coded; logging stays English | PASS — spec.md FR-011 explicitly requires this; new message keys added to `locales/en.py` only, consumed via `i18n.translate()` exactly like the base spec's existing messages |

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/002-constrained-calculation-modes/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   ├── library-api-delta.md
│   └── cli-repl-delta.md
├── checklists/
│   ├── requirements.md
│   ├── calculation-rigor.md
│   └── mode-ux.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── machine_calc/
    ├── models.py                     # ADD: CalculationMode enum; CalculationResult gains `mode` field (additive, default STANDARD)
    ├── validation.py                  # ADD: validate_target_rpm(), validate_mode_arguments() (mutual-exclusivity / required-argument checks, FR-007/FR-009)
    ├── locales/en.py                   # ADD: new message keys (mode prompt text, new error/label strings, FR-011)
    ├── cli.py                         # MODIFY: add mode-selection prompt (FR-001a, re-prompts on invalid entry) and mode-conditional follow-up prompts (re-prompt on blank required available-power entry, never MODE_CONFLICT); on loop re-run, clear mode-specific values when the mode changes (FR-013); no change to existing standard-mode prompt sequence when "standard" is chosen
    └── operations/
        └── drilling/
            ├── __init__.py             # MODIFY: calculate() gains `mode` and `target_rpm` parameters; dispatches to the shared at-RPM helper for power-constrained/fixed-RPM modes; new error codes (FR-004, FR-007, FR-009)
            └── formulas.py             # MODIFY: factor out calculate_drilling_metrics_at_rpm(diameter_mm, depth_mm, material, tool, spindle_speed_rpm) reused by calculate_drilling_metrics() (standard) and the two new modes; add the closed-form power-scaling helper (research.md #1)

tests/
├── contract/                        # ADD: contract tests for power-constrained mode, fixed-RPM mode, and mode-conflict rejection
├── integration/                      # ADD: end-to-end CLI flow tests for the new mode-selection prompt and its follow-up prompts
└── unit/
    └── operations/
        └── drilling/                  # ADD: unit tests for calculate_drilling_metrics_at_rpm() and the power-scaling helper (nominal/boundary/exceeds-budget/zero-or-negative-power cases)
```

**Structure Decision**: No new top-level module or package is introduced. This
feature extends the existing `operations/drilling` module (both `__init__.py`
and `formulas.py`) and the shared `models.py`/`validation.py`/`locales/en.py`/
`cli.py` files established by `001-metal-drilling-calc`, consistent with
spec.md's Assumptions ("extends the existing `calculate()` API ... does not
introduce a separate calculation engine or a new top-level entry point") and
Constitution Principle VI (drilling-specific logic stays inside
`operations/drilling`; only genuinely cross-cutting additions — the new enum,
new validation helpers, new message keys, and the new CLI prompt — touch
shared infrastructure, and all of those are additive, not restructuring).

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
