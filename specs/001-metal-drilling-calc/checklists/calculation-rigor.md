# Specification Quality Checklist: Calculation Correctness & Engineering Rigor

**Purpose**: "Unit tests for requirements" — validate that spec.md, plan.md,
research.md, and data-model.md define the drilling calculation logic
(formulas, units, tolerances, reference data, edge cases) with enough
completeness, clarity, consistency, and measurability to be implemented and
tested correctly, per Constitution Principle III (Calculation Robustness &
Accuracy).

**Created**: 2026-07-09
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [research.md](../research.md) | [data-model.md](../data-model.md)
**Focus**: Calculation correctness & engineering rigor (formulas, units, tolerances, edge cases)

## Requirement Completeness

- CHK001 - ~~Are requirements defined for what happens when calculated feed rate or spindle speed would exceed practical machine limits, distinct from the power-feasibility check in FR-012?~~ **RESOLVED** (2026-07-09 clarification): explicitly out of scope — only the FR-012 power feasibility check applies; see spec.md Edge Cases and Assumptions. [Spec §Edge Cases, §Assumptions]
- CHK002 - ~~Does the spec (or plan) specify the exact rule for combining a workpiece material's reference cutting speed/feed with a drilling tool's cutting/feed factors...~~ **RESOLVED** (2026-07-09 clarification): multiplicative — formalized in FR-006/FR-007. [Spec §FR-006/FR-007]
- CHK003 - Are rounding/precision requirements defined for displayed and returned numeric results (e.g., decimal places for RPM, torque, power)? [Gap]
- CHK004 - Are requirements defined for how many/which reference materials and drilling tools must ship in the initial release, beyond the illustrative "e.g." list in Assumptions? [Completeness, Spec §Assumptions]
- CHK005 - Is there a requirement identifying the specific authoritative published reference (or references) against which SC-002's "5% of published industry reference values" will be measured/tested? [Gap, Spec §SC-002]

## Requirement Clarity

- CHK006 - ~~Is "within 5%" in SC-002 clarified as applying independently to each of spindle speed, feed rate, torque, and power, or as an aggregate/average tolerance across all four?~~ **RESOLVED** (2026-07-09 clarification): applies independently to each value. [Spec §SC-002]
- CHK007 - Is the machining-time "standard allowance for drill point engagement" (FR-008) quantified in the spec/plan as a normative requirement, rather than only appearing as an implementation detail in research.md? [Clarity, Spec §FR-008]
- CHK008 - Is "extremely large" input (mentioned in Edge Cases) fully reconciled with the concrete numeric bounds now defined in FR-009, leaving no residual vague language? [Clarity, Spec §Edge Cases]
- CHK009 - Are the default validation bounds (100mm diameter / 500mm depth) accompanied by a stated rationale or reference (e.g., typical twist-drill capacity) so reviewers can judge whether they are realistic, not arbitrary? [Clarity, Spec §FR-009]

## Requirement Consistency

- CHK010 - Do spec.md's Key Entities and data-model.md's entity definitions use consistent field-level semantics for material/tool reference values (e.g., is "reference cutting speed" always vc and never conflated with spindle speed)? [Consistency, Spec §Key Entities]
- CHK011 - Is the torque/power calculation's dependency on a material-specific specific cutting force (Kc) reflected back in spec.md's WorkpieceMaterial description, or only introduced later in data-model.md/research.md? [Consistency, Spec §Key Entities]
- CHK012 - Are the units asserted for torque and power consistent across spec.md (FR-011/FR-013), data-model.md, and contracts/library-api.md (N·m/kW vs. in-lb/HP) with no contradicting unit mentioned anywhere? [Consistency]

## Acceptance Criteria Quality

- CHK013 - Can SC-002 be objectively tested without additional interpretation (i.e., does it specify enough — reference source, tolerance basis, which parameters) to write a deterministic pass/fail test? [Measurability, Spec §SC-002]
- CHK014 - Is SC-005 ("same amount of time as users who do provide it") measurable, or does it rely on a subjective/qualitative comparison that a test cannot assert deterministically? [Measurability, Spec §SC-005]
- CHK015 - Are acceptance scenarios present for a material/drilling-tool combination that is explicitly unsupported (no reference parameters defined), matching the FR-010 rejection behavior? [Coverage, Spec §Acceptance Scenarios]

## Edge Case & Tolerance Coverage

- CHK016 - Are boundary-value requirements explicit for diameter/depth exactly at the configured maximum (inclusive vs. exclusive limit), not just "exceeds the maximum"? [Gap, Spec §FR-009]
- CHK017 - Is there a requirement addressing what tolerance/behavior applies when a user-supplied `available_power` exactly equals the calculated `power_required` (boundary case for the feasibility warning in FR-012)? [Gap, Spec §FR-012]
- CHK018 - Are floating-point comparison expectations (tolerance-based, per Constitution Principle III) reflected anywhere in spec-level acceptance criteria, or only assumed to be handled at the test-implementation level? [Coverage, Constitution III]

## Dependencies & Assumptions

- CHK019 - Does the spec/plan validate the assumption that "conventional twist-drill drilling on a rigid setup" formulas (research.md #4) remain accurate at the outer edge of the configured diameter/depth bounds (100mm/500mm), or is this an unverified extrapolation? [Assumption, Spec §Assumptions]
- CHK020 - Is the dependency on an external formula reference (Sandvik Coromant / Machinery's Handbook, research.md #4) captured as a traceable citation requirement in spec.md itself, per Constitution Principle III's "MUST cite that source" rule, rather than only in research.md? [Dependency, Constitution III]

## Ambiguities & Conflicts

- CHK021 - Is there any remaining conflict between FR-010's "no defined reference parameters" rejection path and the Assumptions section's statement that "the exact list can be extended later without changing core module behavior" (i.e., does extension risk silently creating new unsupported-combination cases without a defined handling path)? [Conflict, Spec §FR-010 vs §Assumptions]
- CHK022 - Are there unresolved terms describing calculation confidence (e.g., "planning estimates, not certified engineering values" in Assumptions) that could conflict with SC-002's precise 5% accuracy claim? [Ambiguity, Spec §Assumptions vs §SC-002]

## Notes

- This checklist targets requirements quality (spec/plan/research/data-model
  wording), not implementation verification — it does not duplicate the
  test tasks already defined in tasks.md (T014-T018, T027-T031).
- Items marked [Gap] indicate missing normative text, not necessarily missing
  design intent (design intent may already exist informally in research.md).
- Recommended next step if addressing these: run `/speckit.clarify` for any
  item requiring a spec.md decision (e.g., CHK001, CHK006, CHK002), or
  amend research.md/data-model.md directly for implementation-level items.
