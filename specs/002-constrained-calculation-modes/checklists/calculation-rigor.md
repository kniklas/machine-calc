# Specification Quality Checklist: Constrained Modes Calculation Correctness & Numerical Edge Cases

**Purpose**: "Unit tests for requirements" — validate that spec.md, plan.md,
research.md, and data-model.md define the power-constrained and fixed-RPM
calculation logic (the closed-form power-scaling derivation, boundary
conditions, and numerical edge cases) with enough completeness, clarity,
consistency, and measurability to be implemented and tested correctly, per
Constitution Principle III (Calculation Robustness & Accuracy).

**Created**: 2026-07-11
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [research.md](../research.md) | [data-model.md](../data-model.md)
**Focus**: Calculation correctness & numerical edge cases for the two new modes (power-constrained, fixed-RPM)

## Requirement Completeness

- CHK001 - Are requirements defined for the exact tolerance used to judge "required power does not exceed available power" (SC-003), given that the adjusted spindle speed is derived via floating-point arithmetic (research.md #1)? [Gap, Spec §SC-003]
- CHK002 - Is a requirement stated for what precision/rounding applies to a caller-supplied `target_rpm` before it is used directly as spindle speed (e.g., is an extremely high-precision float accepted as-is, truncated, or validated only for sign/finiteness)? [Gap, Spec §FR-007]
- CHK003 - Are requirements defined for the specific behavior when `available_power` supplied in power-constrained mode is exactly equal to the power required at the nominal (unconstrained) spindle speed — is this treated as FR-002 (reduce) or FR-003 (no-op)? [Gap, Spec §FR-002 vs §FR-003]
- CHK004 - Does the spec define what "no positive spindle speed can bring the required power within budget" (FR-004) means numerically — is `available_power <= 0` the only trigger, or could floating-point rounding near zero also trigger it, and is that distinction normatively stated? [Gap, Spec §FR-004]
- CHK005 - Is a requirement stated for the maximum/minimum practically meaningful `target_rpm` value the module must handle without overflow or precision loss (e.g., extremely large target RPM values feeding into feed-rate/power formulas)? [Gap, Spec §Edge Cases]

## Requirement Clarity

- CHK006 - Is FR-002's "highest value at which the required power no longer exceeds the available power" clarified as an exact/closed-form solution (per research.md #1) rather than an approximation, so a test can assert exact equality within float tolerance rather than "close enough"? [Clarity, Spec §FR-002, research.md #1]
- CHK007 - Is it explicit in the spec (not only research.md) that torque is mathematically independent of spindle speed, which is the load-bearing assumption behind the entire power-constrained derivation? [Clarity, Spec §FR-002 vs research.md #1]
- CHK008 - Is "clear, structured error" in FR-004 and FR-007 clarified with a specific, stable error code (rather than only descriptive prose), consistent with how the base spec's FR-009/FR-010 name their codes explicitly? [Clarity, Spec §FR-004, §FR-007]

## Requirement Consistency

- CHK009 - Are the units and independence-from-unit-system claims for `target_rpm` (spec.md Edge Cases: "RPM itself is unit-system-independent") consistent with how `CalculationResult.spindle_speed_rpm` is documented in data-model.md and the base spec's data-model.md? [Consistency, Spec §Edge Cases]
- CHK010 - Is the power-constrained mode's claim that "only spindle speed... is adjusted; the underlying material and drilling-tool reference values themselves are never altered" (Assumptions) consistent with FR-002's description of what gets recomputed (feed rate, machining time, torque)? [Consistency, Spec §Assumptions vs §FR-002]
- CHK011 - Do FR-004's and FR-009's descriptions of "distinct from existing/other error codes" align with the actual three new codes defined in data-model.md (`INVALID_TARGET_RPM`, `MODE_CONFLICT`, `INFEASIBLE_POWER_BUDGET`) without overlap or ambiguity about which code applies to which condition? [Consistency, Spec §FR-004/§FR-009 vs data-model.md]

## Acceptance Criteria Quality

- CHK012 - Can SC-003 ("100% of power-constrained results have a required power that does not exceed the supplied available power... within floating-point tolerance") be tested deterministically, or does "within floating-point tolerance" need a concrete numeric tolerance value stated somewhere (spec, plan, or data-model)? [Measurability, Spec §SC-003]
- CHK013 - Is SC-002's "same response time as a standard calculation" for fixed-RPM mode measurable/testable, or is it a qualitative claim lacking a numeric threshold (contrast with the base spec's SC-001's explicit 30-second bound)? [Measurability, Spec §SC-002]
- CHK014 - Are acceptance scenarios present for the exact boundary case where `available_power` equals the nominal required power (see CHK003), matching whatever FR-002/FR-003 boundary rule is intended? [Coverage, Spec §Acceptance Scenarios]

## Edge Case & Tolerance Coverage

- CHK015 - Is there an explicit requirement or acceptance scenario for a `target_rpm` supplied as `NaN` or `Infinity` (distinct from "non-numeric" in the conventional sense), given FR-007 only names "zero, negative, or non-numeric"? [Gap, Spec §FR-007]
- CHK016 - Is there a requirement addressing floating-point comparison expectations (tolerance-based, per Constitution Principle III) specifically for the new linear power-scaling calculation, mirroring how the base spec's Constitution alignment is already established for its own formulas? [Coverage, Constitution III]
- CHK017 - Does the spec address whether an extremely small (but positive) adjusted spindle speed from power-constrained mode (e.g., resulting in machining time of hours) requires any advisory note to the user, or is this fully covered by the existing Edge Cases statement that no minimum floor is imposed? [Gap, Spec §Edge Cases]

## Dependencies & Assumptions

- CHK018 - Does the spec/research validate the assumption that the closed-form linear power-scaling relationship (research.md #1) holds across the *entire* configured diameter/depth range (inherited from the base spec's 100mm/500mm bounds), or could it break down at those boundary extremes? [Assumption, research.md #1]
- CHK019 - Is the dependency of the power-constrained derivation on the base spec's specific formula set (torque independent of RPM) captured as a traceable, testable assumption in this feature's spec.md, rather than only inferred from `001-metal-drilling-calc`'s research.md #4? [Dependency, Spec §Assumptions]

## Ambiguities & Conflicts

- CHK020 - Is there any residual ambiguity between FR-008 ("feasibility warning... without altering the user-specified RPM") and FR-012 ("clearly indicate which mode produced it") regarding whether a fixed-RPM result with an active feasibility warning must additionally be visually distinguished from a fixed-RPM result without one? [Ambiguity, Spec §FR-008 vs §FR-012]
- CHK021 - Are there unresolved terms describing "adjusted" vs. "reduced" spindle speed (FR-002 uses "reduce", contracts/cli-repl-delta.md example uses "adjusted to fit available power") that could create inconsistent terminology between spec-level requirements and CLI-facing labels? [Ambiguity, Spec §FR-002 vs contracts/cli-repl-delta.md]

## Notes

- This checklist targets requirements quality (spec/plan/research/data-model
  wording), not implementation verification — it does not duplicate the
  test tasks already defined in tasks.md (T008, T010-T012, T017-T019).
- Items marked [Gap] indicate missing normative text, not necessarily missing
  design intent (design intent may already exist informally in research.md).
- Recommended next step if addressing these: run `/speckit.clarify` for any
  item requiring a spec.md decision (e.g., CHK003's boundary rule, CHK012's
  tolerance value), or amend research.md/data-model.md directly for
  implementation-level items (e.g., CHK002, CHK015).
