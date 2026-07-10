# Specification Quality Checklist: Mode-Selection UX & Validation-Error Completeness

**Purpose**: "Unit tests for requirements" — validate that spec.md,
data-model.md, and contracts/cli-repl-delta.md/library-api-delta.md define
the mode-selection interaction (REPL prompt flow) and the three new
validation/error paths (mutual exclusivity, infeasible power budget,
invalid target RPM) with enough completeness, clarity, consistency, and
measurability to be implemented and tested correctly.

**Created**: 2026-07-11
**Feature**: [spec.md](../spec.md) | [data-model.md](../data-model.md) | [contracts/cli-repl-delta.md](../contracts/cli-repl-delta.md) | [contracts/library-api-delta.md](../contracts/library-api-delta.md)
**Focus**: Mode-selection UX & validation-error completeness (mutual exclusivity, prompts, error codes)

## Requirement Completeness

- CHK001 - ~~Are requirements defined for what happens if a user enters an invalid/unrecognized value at the new calculation-mode prompt (FR-001a) — is a default assumed, or must it re-prompt like material/tool selection?~~ **RESOLVED** (2026-07-11 clarification): re-prompt, same as material/tool selection; no silent default fallback. [Spec §Clarifications, §FR-001a]
- CHK002 - ~~Are requirements defined for whether the mode-selection prompt (FR-001a) itself has a re-prompt-on-invalid-input requirement, analogous to the existing material/tool "re-prompt on invalid/empty entry" behavior?~~ **RESOLVED** (2026-07-11 clarification): yes, explicitly required in FR-001a. [Spec §FR-001a]
- CHK003 - ~~Is there a requirement covering what the REPL displays if the user changes the calculation mode on a loop re-run (FR-014 of the base spec) — are previously entered mode-specific values (e.g., a target RPM) cleared, retained, or invalid in the new mode?~~ **RESOLVED** (2026-07-11 clarification): new FR-013 requires clearing mode-specific values on a mode change; shared inputs remain editable defaults. [Spec §FR-013]
- CHK004 - Are requirements defined for the exact wording/distinction between the three new error codes' user-facing messages (`INVALID_TARGET_RPM`, `MODE_CONFLICT`, `INFEASIBLE_POWER_BUDGET`) so a user can tell which condition occurred without reading the code? [Gap, Spec §FR-004/FR-007/FR-009]
- CHK005 - Does the spec define whether the library API's `MODE_CONFLICT` case (supplying both `target_rpm` and a power constraint) is validated before or independently of the "power-constrained mode without `available_power`" `MODE_CONFLICT` sub-case, so both are unambiguously distinguishable from a caller's perspective? [Gap, data-model.md ErrorInfo]

## Requirement Clarity

- CHK006 - Is "required available-power prompt" (FR-001a, power-constrained mode) clarified as to what constitutes a valid entry (e.g., must be a positive number; is zero/blank explicitly rejected with which code)? [Clarity, Spec §FR-001a, §FR-002]
- CHK007 - Is FR-009's "supplying inputs for both at once" precisely defined for the library API — does merely passing a non-default `mode` alongside a non-`None` `target_rpm` count as "supplying," even if the mode is `STANDARD`, or only when `mode` is explicitly `POWER_CONSTRAINED`/`FIXED_RPM` and conflicts with the other input? [Clarity, Spec §FR-009, data-model.md]
- CHK008 - Is "clearly and structurally indicate which mode produced it" (FR-012) clarified with a concrete field name/type expectation beyond data-model.md's informal example, so client code integrating against the library has a stable contract to target? [Clarity, Spec §FR-012]

## Requirement Consistency

- CHK009 - Are the mode-selection prompt option labels ("standard"/"power-constrained"/"fixed-rpm") consistent in spelling/casing between spec.md (FR-001a), contracts/cli-repl-delta.md's example sessions, and data-model.md's `CalculationMode` enum member names? [Consistency, Spec §FR-001a vs data-model.md vs contracts/cli-repl-delta.md]
- CHK010 - Is the requirement that fixed-RPM mode's available-power prompt remains "optional/advisory" (FR-008, same as standard mode) consistently reflected in both the CLI contract delta and the library API delta's parameter semantics table? [Consistency, contracts/cli-repl-delta.md vs contracts/library-api-delta.md]
- CHK011 - Do FR-004 ("distinct from the existing... codes") and FR-009 ("distinct from a feasibility warning") both consistently treat `feasibility_warning` as categorically different from an `ErrorInfo` code, with no requirement blurring the two? [Consistency, Spec §FR-004 vs §FR-009]

## Acceptance Criteria Quality

- CHK012 - Are there acceptance scenarios (not just functional requirements) covering the interactive-text-interface path for FR-009's mutual-exclusivity rejection, or only the library-level Acceptance Scenarios (which are written mode-agnostically)? [Coverage, Spec §Acceptance Scenarios]
- CHK013 - Can "the module rejects the request with a clear, structured error" (used identically in FR-004, FR-007, and FR-009) be tested as three *distinguishable* pass/fail conditions, or does the repeated identical phrasing risk under-specifying which specific code/message each MUST produce? [Measurability, Spec §FR-004/§FR-007/§FR-009]

## Scenario Coverage

- CHK014 - Is there a requirement or acceptance scenario for supplying `available_power` in `STANDARD` mode together with `target_rpm` set to `None` and `mode` left at its default — confirming this is unambiguously *not* a `MODE_CONFLICT` case? [Edge Case, Gap]
- CHK015 - ~~Is there a requirement covering what happens if a user selects `power-constrained` mode at the REPL prompt but then leaves the now-required available-power prompt blank — is blank treated as `MODE_CONFLICT`, a re-prompt, or a distinct validation message?~~ **RESOLVED** (2026-07-11 clarification): re-prompt as a validation failure, never `MODE_CONFLICT`. [Spec §Clarifications, §FR-001a]
- CHK016 - Are non-interactive/programmatic (library API) and interactive (REPL) mode-conflict rejection paths both explicitly required to produce the same `MODE_CONFLICT` code (FR-016's identical-results guarantee), or is this only implied by cross-reference to the base spec? [Coverage, Spec §FR-010]

## Dependencies & Assumptions

- CHK017 - Does the spec's Assumption that "a calculation request that specifies neither an available-power constraint nor a target RPM behaves exactly as the existing... standard calculation" (SC-004) explicitly account for a request that specifies `mode=STANDARD` explicitly (not merely omitted), confirming these are equivalent? [Assumption, Spec §Assumptions]
- CHK018 - Is the assumption that the REPL's mode-selection prompt "does not change the underlying library contract" (i.e., is purely an input-gathering layer) traceable to a specific requirement, or only asserted informally in contracts/cli-repl-delta.md's closing section? [Dependency, contracts/cli-repl-delta.md]

## Ambiguities & Conflicts

- CHK019 - Is there any ambiguity in FR-001's "not by overloading the existing advisory available-power input" regarding whether a *library* caller (as opposed to the REPL) is also prohibited from any overloaded semantics on `available_power`, given the library reuses that same parameter across all three modes (research.md #3)? [Ambiguity, Spec §FR-001 vs research.md #3]
- CHK020 - Are there unresolved terms distinguishing "rejected with a clear, structured error" (used for all three new error paths) from the base spec's existing "feasibility warning" wording, in a way a new reader could not conflate a rejection with a warning? [Ambiguity, Spec §FR-004/§FR-008]

## Notes

- This checklist targets requirements quality (spec/data-model/contracts
  wording), not implementation verification — it does not duplicate the
  test tasks already defined in tasks.md (T009, T013, T015, T020-T022).
- Items marked [Gap] indicate missing normative text, not necessarily missing
  design intent (design intent may already exist informally in
  contracts/cli-repl-delta.md or data-model.md).
- Recommended next step if addressing these: run `/speckit.clarify` for any
  item requiring a spec.md decision (e.g., CHK001, CHK003, CHK015), or amend
  contracts/data-model.md directly for implementation-level items (e.g.,
  CHK009, CHK017).
