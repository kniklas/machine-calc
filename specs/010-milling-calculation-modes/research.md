# Phase 0 Research: Milling Calculation Modes

**Feature**: [spec.md](./spec.md) | **Date**: 2026-08-19

This document resolves the technical unknowns needed before Phase 1 design.
It builds directly on `specs/002-constrained-calculation-modes/research.md`
(drilling's power-constrained/fixed-RPM design, which this feature reuses
rather than reinvents) and `specs/009-milling-calculations/research.md`
(the milling formula core), neither of which is revisited here for
already-settled topics (Python version, dependencies, i18n mechanism,
formula source citation, milling module boundary).

## 1. The milling closed-form power-scaling identity holds exactly as it does for drilling

- **Decision**: Reuse drilling's exact closed-form derivation
  (`002-constrained-calculation-modes/research.md` #1) unchanged, because
  the milling formula core has the same structural property: cutting
  torque `Mc` is independent of spindle speed `n`.

  From `_shared.py`'s formulas: `vf = n * fz * zn` (linear in `n`),
  `Pc = (ap * ae * vf * kc) / (60 * 10^6)` (linear in `vf`, hence linear in
  `n`), and `Mc = (Pc * 9550) / n`. Substituting `Pc`'s linear-in-`n` form
  into `Mc`'s definition cancels `n` entirely:

  ```text
  Mc = ((ap * ae * (n * fz * zn) * kc) / (60 * 10^6)) * 9550 / n
     = (ap * ae * fz * zn * kc * 9550) / (60 * 10^6)   # n cancels
  ```

  So, exactly as for drilling, required power `Pc` scales linearly with
  spindle speed `n` for a fixed diameter/material/tool/geometry selection,
  and the power-constrained spindle speed is:

  ```text
  n_adjusted = n0 * (Pavail / Pc0)
  ```

  where `n0`/`Pc0` are the nominal (material/tool-derived) spindle speed
  and required power. Feed rate, machining time, and material removal rate
  are then recomputed from `n_adjusted` using the same formulas as the
  standard calculation; torque is unchanged (it does not depend on `n`);
  required power at `n_adjusted` equals `Pavail` exactly (within
  `math.isclose()`'s default `rel_tol=1e-9`) by construction. The
  sufficient-budget (FR-003) and infeasible-budget (FR-004) boundary rules
  are identical to drilling's.

- **Rationale**: No new derivation or independent verification is needed —
  the milling formulas already cited and verified in
  `009-milling-calculations` combine algebraically the same way drilling's
  do, and the closed-form (non-iterative) approach keeps this feature
  within Constitution Principle V's low-overhead requirement, exactly as
  it did for drilling.
- **Alternatives considered**: Re-deriving the identity from scratch with a
  fresh citation was rejected as redundant — the algebra above is a direct,
  self-contained consequence of formulas already established and cited in
  `009-milling-calculations/research.md` #1, not a new formula requiring a
  new external source.

## 2. Where the "at-RPM" refactor lives: `_shared.py`, once, not per sub-operation

- **Decision**: Factor a new helper, `calculate_milling_metrics_at_rpm(...,
  spindle_speed_rpm)`, out of the existing `calculate_milling_metrics()` in
  `operations/milling/_shared.py` — the module already shared by both
  end-milling and face-milling. This differs from drilling's equivalent
  refactor (which lived in `operations/drilling/formulas.py`, drilling's
  *only* operation) only in *where* it lives, not in structure: milling
  already centralizes its formula core in `_shared.py` precisely so a
  change like this benefits both sub-operations without duplication
  (`009-milling-calculations` FR-014's module-boundary rationale extends
  cleanly to this feature's own FR-014).
- **Rationale**: Implementing the at-RPM helper and the power-scaling
  helper once in `_shared.py` — rather than once per sub-operation — is
  what makes spec.md FR-014 ("implemented once in the shared milling
  orchestration layer") achievable without duplicating the scaling math in
  both `end_milling/formulas.py` and `face_milling/formulas.py`.
- **Alternatives considered**: Duplicating the refactor into each
  sub-operation's own `formulas.py` (mirroring drilling's file layout
  literally) was rejected — it would duplicate the identical scaling
  arithmetic twice for no benefit, working against FR-014 and Constitution
  Principle I (no duplicated logic).

## 3. Where mode dispatch lives: `_calculate.py`'s shared orchestration, once

- **Decision**: Add `mode`/`target_rpm` parameters and mode-dispatch logic
  to the shared `calculate_milling()` function in
  `operations/milling/_calculate.py` (already shared by both
  `calculate_end_milling()` and `calculate_face_milling()`), mirroring
  drilling's `_compute_metrics()` dispatch structure
  (`operations/drilling/__init__.py`). Each sub-operation's own
  `formulas.py` gains a thin `calculate_<sub-op>_metrics_at_rpm()` wrapper
  (analogous to the existing `calculate_<sub-op>_metrics()` wrapper) so the
  per-sub-operation module boundary (`009-milling-calculations` FR-014) is
  preserved for the metrics-dataclass adaptation, while the actual
  power-scaling/RPM-substitution *arithmetic* stays in `_shared.py` (topic
  2) and the mode *dispatch* stays in `_calculate.py` (this topic) —
  neither is duplicated per sub-operation.
- **Rationale**: `calculate_milling()` already injects a `compute:
  MetricsComputer` callable per sub-operation (research.md #2 of
  `009-milling-calculations`) precisely so shared orchestration logic can
  be added once without each sub-operation reimplementing it. Adding a
  second injected callable, `compute_at_rpm`, for the two new modes follows
  the same established pattern rather than introducing a new one.
- **Alternatives considered**: Duplicating mode dispatch into
  `end_milling/__init__.py` and `face_milling/__init__.py` independently
  was rejected — it is exactly the kind of duplicated cross-cutting logic
  `009-milling-calculations`' shared `_calculate.py` module exists to
  avoid, and would double the surface area for a mode-dispatch bug.

## 4. Reusing drilling's shared infrastructure unchanged

- **Decision**: `CalculationMode` (`models.py`), `CalculationResult.mode`
  (`models.py`), `validate_target_rpm()` and `validate_mode_arguments()`
  (`validation.py`), and the `INFEASIBLE_POWER_BUDGET`/
  `INVALID_TARGET_RPM`/`MODE_CONFLICT` error codes and their message-catalog
  entries are all already operation-agnostic (none of their signatures or
  logic reference drilling specifically) and are reused by milling
  **without any modification** — confirmed by inspecting their current
  implementations, which take a `CalculationMode` value and
  optional-`float` arguments generically.
- **Rationale**: This is exactly what Constitution Principle VI
  (Extensibility by Design) and spec.md's Assumptions call for: this
  feature reuses drilling's existing error codes and message-catalog
  entries rather than introducing milling-specific duplicates, since the
  underlying semantics are identical across operations.
- **Alternatives considered**: Introducing milling-specific error codes
  (e.g., `MILLING_INFEASIBLE_POWER_BUDGET`) was rejected — spec.md
  explicitly calls for reusing drilling's codes, and doing so keeps a
  single source of truth for mode-related error handling across all
  operations (spec.md SC-005).

## 5. CLI prompt-sequence and prompt-count budget impact

- **Decision**: Add one calculation-mode prompt to the shared
  `_prompt_milling_inputs()` helper (`cli.py`), placed immediately after
  the unit-system prompt and before the material-type prompt — matching
  drilling's `_prompt_mode()` placement exactly (spec.md Clarifications
  2026-08-19) — followed by mode-conditional prompts (required
  available-power for power-constrained, or target RPM plus optional
  advisory available-power for fixed-RPM), mirroring drilling's
  `_prompt_material_tool_diameter_depth()` structure
  (`cli.py` lines ~520-580). `_MillingSessionState` gains `mode: CalculationMode`,
  `previous_mode: CalculationMode`, and `target_rpm: float | None` fields,
  with the same loop-re-run clearing behavior drilling's
  `_DrillingSessionState`-equivalent already implements (spec.md FR-013).
- **Rationale**: `009-milling-calculations` centralized the milling prompt
  sequence in one shared helper for both sub-operations specifically so a
  change like this is made once (contracts/cli-repl-milling.md "Prompt
  order follows..."); this feature's mode prompt is added there, not
  duplicated into `_run_end_milling_session()`/`_run_face_milling_session()`.
- **Consequence for `009-milling-calculations`' existing SC-001**: that
  spec's prompt-count budget (14 prompts / 12 typed values, explicitly
  assuming "milling offers no calculation-mode prompt") is superseded by
  this feature for the two new modes. Standard mode's prompt count is
  unchanged (SC-004 of this feature preserves it); this feature's own
  quickstart.md documents the new counts for power-constrained and
  fixed-RPM mode explicitly, and the existing automated prompt-count
  assertion (`tests/integration/test_cli_prompt_budget.py`) MUST be updated
  to branch on mode rather than assert one fixed count for all milling
  runs.
- **Alternatives considered**: Keeping milling's mode selection
  library-API-only (no REPL prompt) was rejected — spec.md FR-001a
  explicitly requires the interactive prompt, for parity with drilling and
  per spec.md SC-005's consistency goal.
