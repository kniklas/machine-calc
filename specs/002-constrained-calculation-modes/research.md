# Phase 0 Research: Constrained Drilling Calculation Modes

**Feature**: [spec.md](./spec.md) | **Date**: 2026-07-11

This document resolves the technical unknowns needed before Phase 1 design.
Each topic follows the Decision / Rationale / Alternatives Considered format.
It builds directly on `specs/001-metal-drilling-calc/research.md`, which this
feature does not revisit for already-settled topics (Python version, runtime
dependencies, configuration format, testing/doc tooling, i18n mechanism).

## 1. Closed-form algorithm for power-constrained mode (no iterative solver)

- **Decision**: Solve for the power-constrained spindle speed algebraically,
  in a single step, rather than iterating/searching:

  Given the standard (nominal) drilling metrics at the material/tool's
  normally-recommended spindle speed `n0` — torque `Mc` (N·m) and required
  power `Pc0 = (Mc × n0) / 9550` (kW) — the base spec's formulas
  (`001-metal-drilling-calc/research.md` #4) establish that:
  - `Mc = (Kc × D² × fn) / 4000` depends only on diameter (`D`), feed per
    revolution (`fn`), and specific cutting force (`Kc`) — **not** on
    spindle speed at all.
  - `Pc = (Mc × n) / 9550` is therefore **linear in spindle speed `n`** for a
    fixed diameter/material/tool selection.

  Consequently, if the available power budget `Pavail < Pc0`, the highest
  spindle speed that keeps required power within budget is simply:

  ```text
  n_adjusted = n0 × (Pavail / Pc0)
  ```

  Feed rate and machining time are then recomputed from `n_adjusted` using
  the same formulas as the standard calculation (`vf = n × fn`,
  `tc = (depth + allowance) / vf`); torque is unchanged (it does not depend
  on `n`); required power at `n_adjusted` equals `Pavail` exactly (up to
  floating-point tolerance) by construction. If `Pavail ≥ Pc0`, no
  adjustment is applied (spec.md FR-003). If `Pavail ≤ 0`, no positive `n`
  can satisfy the budget, so the request is rejected per FR-004.

- **Rationale**: Avoids introducing a numerical solver/iteration (which
  would add code complexity, potential non-convergence edge cases, and
  runtime overhead disproportionate to a simple direct proportion) —
  directly satisfying Constitution Principle V's low-overhead requirement
  and Principle III's preference for explicit, verifiable calculations.
  The derivation reuses the exact formulas already cited and verified in
  `001-metal-drilling-calc`, so no new formula source needs to be
  independently verified.
- **Alternatives considered**: A generic root-finding/binary-search
  approach over candidate spindle speeds was rejected — unnecessary given
  the closed-form linear relationship, and would obscure (rather than
  reuse) the existing, already-verified formulas.

## 2. Refactoring `formulas.py` to share logic across all three modes

- **Decision**: Factor a new helper, `calculate_drilling_metrics_at_rpm(diameter_mm, depth_mm, material, tool, spindle_speed_rpm)`,
  out of the existing `calculate_drilling_metrics()`. The existing function
  becomes a thin wrapper: it derives the nominal spindle speed from the
  material/tool's reference cutting speed (as today), then delegates to the
  new at-RPM helper for feed rate/machining time/torque/power. Power-
  constrained mode and fixed-RPM mode both call the same at-RPM helper
  directly — power-constrained mode with `n_adjusted` (per Research #1),
  fixed-RPM mode with the caller-supplied `target_rpm`.
- **Rationale**: Satisfies Constitution Principle VI (shared behavior
  factored into reusable components rather than duplicated per mode) and
  Principle I (single-responsibility: the standard function's only new
  responsibility is deriving `n` from cutting speed; everything downstream
  of "given an RPM" lives in one place, tested once).
- **Alternatives considered**: Duplicating the feed/time/torque/power
  formulas inline for each of the three modes was rejected as a direct
  violation of Principle VI (duplicated calculation logic across modes,
  risking silent divergence if one copy is later changed without the
  others).

## 3. Mode selection and parameter shape on `calculate()`

- **Decision**: Add two new optional parameters to the existing `calculate()`
  signature: `mode: CalculationMode = CalculationMode.STANDARD` and
  `target_rpm: float | None = None`. The existing `available_power`
  parameter is reused across all three modes with mode-dependent semantics:
  advisory-only in `STANDARD` and `FIXED_RPM` modes (base spec FR-012/this
  spec FR-008), a hard constraint in `POWER_CONSTRAINED` mode (FR-002/
  FR-004). `CalculationMode` is a new enum (`STANDARD`, `POWER_CONSTRAINED`,
  `FIXED_RPM`) added to `models.py`, alongside `UnitSystem`.
- **Rationale**: Matches spec.md's Assumptions (single extended
  `calculate()` entry point, not separate functions per mode) and keeps the
  public API additive/backward-compatible — existing callers that never
  pass `mode`/`target_rpm` see zero behavior change (SC-004), satisfying
  Constitution Principle IV's guidance that additive API changes are a
  MINOR version bump, not a breaking MAJOR one.
- **Alternatives considered**: Two boolean flags (`constrain_to_power: bool`,
  `use_fixed_rpm: bool`) instead of a single `mode` enum were considered,
  but rejected — an enum makes the three-way mutual exclusivity (FR-009)
  structurally explicit (impossible to accidentally set two booleans
  true) rather than requiring a runtime check for an otherwise-representable
  invalid combination.

## 4. New structured error codes

- **Decision**: Introduce three new `ErrorInfo.code` values, distinct from
  the base spec's existing five (`MISSING_MATERIAL`, `MISSING_TOOL`,
  `INVALID_DIAMETER`, `INVALID_DEPTH`, `UNSUPPORTED_COMBINATION`):
  - `INFEASIBLE_POWER_BUDGET` — power-constrained mode requested but no
    positive spindle speed keeps required power within the supplied
    available power (FR-004).
  - `INVALID_TARGET_RPM` — fixed-RPM mode's `target_rpm` is zero, negative,
    or non-numeric (FR-007).
  - `MODE_CONFLICT` — both a power constraint and a target RPM were
    supplied for a single request (FR-009), or `POWER_CONSTRAINED` mode was
    selected without supplying `available_power`.
- **Rationale**: Base spec FR-015/FR-016 require structured, never-raised
  results with clear codes; distinct codes let calling programs
  programmatically distinguish these three new failure reasons from each
  other and from the five existing codes, per spec.md FR-004's explicit
  "distinct from the existing codes" requirement.
- **Alternatives considered**: Reusing a single generic
  `INVALID_MODE_ARGUMENTS` code for all three cases was rejected — it would
  force calling programs to parse the human-readable message to distinguish
  an infeasible power budget (a physical/domain condition) from a simple
  malformed-input condition (`INVALID_TARGET_RPM`) or a request-shape
  conflict (`MODE_CONFLICT`), reducing the contract's usefulness.

## 5. Interactive text interface: mode-selection prompt placement

- **Decision**: Per spec.md's resolved clarification (FR-001a), add exactly
  one new REPL prompt, positioned immediately after the existing unit-system
  prompt and before material/tool/diameter/depth, offering `standard` /
  `power-constrained` / `fixed-rpm`. The prompt's answer determines which
  later prompts appear: `standard` keeps today's exact sequence (including
  the existing optional advisory available-power prompt); `power-constrained`
  replaces that optional prompt with a required available-power prompt;
  `fixed-rpm` adds a required target-RPM prompt (in place of computing RPM
  from material/tool) while keeping the optional advisory available-power
  prompt.
- **Rationale**: A single upfront mode choice keeps the REPL's linear,
  sequential prompt style (established in `001-metal-drilling-calc`
  research.md #2's rejection of a heavier CLI framework) rather than
  requiring conditional backtracking or re-prompting after the fact.
- **Alternatives considered**: See spec.md Clarifications (2026-07-10) for
  the two alternatives considered and rejected during `/speckit.clarify`
  (overloading the existing available-power prompt with a hidden toggle;
  deferring REPL support to a later feature).

## Outcome

All technical unknowns for this feature are resolved above. No open
`NEEDS CLARIFICATION` items remain blocking Phase 1 design.
