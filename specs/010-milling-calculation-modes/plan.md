# Implementation Plan: Milling Calculation Modes (Power-Constrained & Fixed-RPM)

**Branch**: `010-milling-calculation-modes` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-milling-calculation-modes/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend the existing milling entry points (`calculate_end_milling()` and
`calculate_face_milling()`, `009-milling-calculations`) with the same two
opt-in, mutually-exclusive calculation modes drilling already has
(`002-constrained-calculation-modes`): **power-constrained** (reduce
spindle speed/feed rate/material removal rate to the fastest settings that
fit a supplied available power budget) and **fixed-RPM** (accept a target
spindle RPM directly and derive feed rate, machining time, torque,
material removal rate, and required power from it). Both modes reuse
drilling's existing `CalculationMode` enum, validation helpers, and error
codes verbatim (research.md #4); the milling-specific work is a
closed-form power-scaling helper and an at-RPM helper added once to the
shared `operations/milling/_shared.py`/`_calculate.py` modules
(research.md #1-#3), plus one new CLI mode-selection prompt shared by both
milling sub-operation sessions (research.md #5). The interactive text
interface's standard-mode behavior and results are unaffected
(spec.md SC-004).

## Technical Context

**Language/Version**: Python 3.9+ (unchanged from `009-milling-calculations`; no new version requirement introduced)

**Primary Dependencies**: None new. Reuses the existing zero/near-zero-dependency stack (`tomli` on Python <3.11 only); new user-facing text (mode-selection prompt, adjusted-value labels) reuses drilling's existing message-catalog entries (`src/machine_calc/locales/en.py`) verbatim — no new catalog keys are milling-specific (research.md #4), per Constitution Principle VIII

**Storage**: N/A (stateless per-request calculations, unchanged)

**Testing**: `pytest` with `pytest-cov`; tolerance-based float comparisons (`math.isclose`) per Constitution Principle III, reusing the same closed-form power-scaling test pattern drilling's suite already established

**Target Platform**: Cross-platform CLI/library (unchanged from `009-milling-calculations`)

**Project Type**: Single project — extends the existing Python library + thin CLI layer; no new top-level entry point (spec.md Assumptions)

**Performance Goals**: Each milling calculation (including the new modes) completes within the same 0.5-1.0s target as the standard calculation (Constitution Principle V) — the power-constrained algorithm is closed-form (research.md #1), not iterative, so it adds negligible overhead

**Constraints**: Same as `009-milling-calculations` (Constitution Principle V: ~64-128MB RAM, single-threaded, Debian-stable compatible); no exceptions raised for expected validation failures, including the three reused failure modes (infeasible power budget, invalid target RPM, conflicting mode selection) — spec.md FR-004/FR-007/FR-009; invalid/blank REPL prompt entries (mode selection, required available-power) re-prompt rather than silently defaulting or erroring as `MODE_CONFLICT`, and a mode change on loop re-run clears mode-specific values per milling sub-operation session (spec.md FR-001a, FR-013); application logging remains English-only regardless of locale (Constitution VIII)

**Scale/Scope**: Extends both existing milling sub-operations (`operations/milling/end_milling`, `operations/milling/face_milling`) with two new modes, implemented once in the shared `operations/milling/_shared.py`/`_calculate.py` modules (research.md #2-#3); no new operation, no new registries, no new top-level library entry point. Interactive text interface's milling flow gains one new prompt (mode selection) plus mode-conditional follow-up prompts, shared by both sub-operation sessions via the existing `_prompt_milling_inputs()` helper

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Single-responsibility modules; new logic added once to the existing shared `operations/milling/_shared.py`/`_calculate.py` (not duplicated per sub-operation); public `calculate_end_milling()`/`calculate_face_milling()` docstrings updated to document `mode`/`target_rpm` and the reused error codes | PASS — mode dispatch isolated in `_calculate.py`; at-RPM/power-scaling arithmetic factored into `_shared.py` (research.md #2/#3), reused by both sub-operations via each one's own thin `formulas.py` wrapper (preserving the existing FR-014 module boundary) |
| II. Testing Standards | Unit tests for the new closed-form power-scaling calculation and at-RPM calculation (nominal/boundary/exceeds-budget/exactly-at-budget/invalid-RPM cases), for both end-milling and face-milling; ≥90% coverage maintained on calculation modules | PASS (planned) — unit tests in `tests/unit/operations/milling/`; contract tests for both new modes and the reused error paths, for both sub-operations |
| III. Calculation Robustness & Accuracy | Tolerance-based comparisons for the linear power-scaling result (reusing drilling's already-verified `rel_tol=1e-9` convention); validated `target_rpm`/`available_power` inputs (reusing drilling's validators unmodified); explicit handling of the "no positive RPM fits" edge case | PASS — research.md #1 shows the identity holds for milling's formulas by direct algebraic substitution from already-cited, already-verified formulas (`009-milling-calculations` research.md #1); no new external citation is needed since no new formula is introduced |
| IV. Python Packaging & Versioning | No new dependencies; public API addition (`mode`, `target_rpm` parameters on both milling entry points) is additive/backward-compatible → MINOR version bump, not MAJOR | PASS — data-model.md marks both new parameters as optional with defaults, preserving the existing call signatures for callers that pass neither |
| V. Resource-Constrained Compatibility | No new runtime dependencies; new calculation path is O(1) closed-form, not iterative — no additional CPU/memory burden beyond the existing milling profile | PASS — research.md #1 confirms the same direct algebraic solution drilling already uses, preserving the 0.5-1.0s per-calculation target |
| VI. Extensibility by Design | New modes MUST NOT require rewriting the standard milling calculation path; implemented once in shared milling infrastructure, not duplicated per sub-operation or reinvented from drilling's design | PASS — `calculate_milling_metrics_at_rpm()`/`calculate_power_constrained_milling_metrics()` (research.md #2) are additions to the already-shared `_shared.py`; `CalculationMode`, `validate_target_rpm()`, `validate_mode_arguments()`, and the three error codes are reused **unmodified** from drilling (research.md #4) rather than reimplemented — a future turning operation could adopt the identical pattern |
| VII. Documentation & Publishing | Sphinx docs and README updated to document the two new modes on both milling entry points, mirroring drilling's existing mode documentation | PASS (planned) — docstring updates to `calculate_end_milling()`/`calculate_face_milling()` and any shared `CalculationResult`/mode documentation feed the existing Sphinx autodoc build; no new doc toolchain needed |
| VIII. Internationalization of User-Facing Messages | All new user-facing text (mode-selection prompt, adjusted-vs-recommended labeling, mode-related error messages) MUST be sourced from the message catalog; this feature introduces **no new catalog keys**, reusing drilling's existing entries verbatim | PASS — spec.md FR-011 requires catalog sourcing; research.md #4 confirms the existing keys are already generic (not drilling-specific wording), so milling prompts reuse them as-is |
| IX. Automated Code Quality, Complexity & Security Gates | New/changed functions MUST stay within the configured cyclomatic-complexity/Maintainability Index thresholds; no new high/medium `bandit` findings; no new dependency vulnerabilities | PASS (planned) — mode dispatch is extracted into small, single-purpose helpers in `_calculate.py` (mirroring drilling's `_compute_metrics()`/`_validate_mode_inputs()` extraction, which was itself done to satisfy this same principle); no new dependencies introduced |

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/010-milling-calculation-modes/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   ├── library-api-milling-modes-delta.md
│   └── cli-repl-milling-modes-delta.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── machine_calc/
    ├── cli.py                         # MODIFY: add mode-selection prompt + mode-conditional follow-up prompts to _prompt_milling_inputs() (shared by both sub-operation sessions, FR-001a); _MillingSessionState gains mode/previous_mode/target_rpm fields; clear mode-specific values on mode change (FR-013)
    └── operations/
        └── milling/
            ├── _shared.py               # MODIFY: add calculate_milling_metrics_at_rpm() and calculate_power_constrained_milling_metrics() (research.md #1/#2); calculate_milling_metrics() becomes a thin wrapper delegating to the new at-RPM helper
            ├── _calculate.py            # MODIFY: calculate_milling() gains mode/target_rpm parameters and mode-dispatch logic (research.md #3), mirroring operations/drilling/__init__.py's _compute_metrics()/_validate_mode_inputs() structure; accepts a second injected compute_at_rpm callable alongside the existing compute callable
            ├── end_milling/
            │   ├── __init__.py          # MODIFY: calculate_end_milling() gains mode/target_rpm parameters, passed through to calculate_milling()
            │   └── formulas.py          # MODIFY: add calculate_end_milling_metrics_at_rpm() thin wrapper (preserves FR-014 module boundary)
            └── face_milling/
                ├── __init__.py          # MODIFY: calculate_face_milling() gains mode/target_rpm parameters, passed through to calculate_milling()
                └── formulas.py          # MODIFY: add calculate_face_milling_metrics_at_rpm() thin wrapper (preserves FR-014 module boundary)

# NOT modified (reused verbatim, research.md #4):
#   src/machine_calc/models.py           # CalculationMode, CalculationResult.mode already exist
#   src/machine_calc/validation.py       # validate_target_rpm(), validate_mode_arguments() already exist
#   src/machine_calc/locales/en.py       # existing mode/error message catalog keys already exist

tests/
├── contract/                        # ADD: contract tests for power-constrained mode, fixed-RPM mode, and mode-conflict rejection, for both calculate_end_milling() and calculate_face_milling()
├── integration/                      # MODIFY: tests/integration/test_cli_prompt_budget.py to assert per-mode prompt counts (research.md #5); ADD: end-to-end CLI flow tests for the new mode-selection prompt and its follow-up prompts in both milling sessions
└── unit/
    └── operations/
        └── milling/                   # ADD: unit tests for calculate_milling_metrics_at_rpm() and calculate_power_constrained_milling_metrics() (nominal/boundary/exceeds-budget/zero-or-negative-power cases), plus each sub-operation's thin at-RPM wrapper
```

**Structure Decision**: No new top-level module or package is introduced.
This feature extends the existing `operations/milling` package (`_shared.py`,
`_calculate.py`, and both sub-operations' thin wrappers) and the CLI's
existing shared milling prompt helper, consistent with spec.md's
Assumptions ("extends the existing `calculate_end_milling()`/
`calculate_face_milling()` library API... does not introduce a separate
calculation engine or a new top-level entry point") and Constitution
Principle VI. Genuinely cross-cutting infrastructure (`CalculationMode`,
validators, error codes, message-catalog entries) is reused **unmodified**
from `002-constrained-calculation-modes` rather than touched at all —
only the milling-specific formula/dispatch layer and the milling CLI prompt
sequence are extended.

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
