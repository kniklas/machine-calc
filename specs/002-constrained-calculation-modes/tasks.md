# Tasks: Constrained Drilling Calculation Modes (Power-Limited & Fixed-RPM)

**Input**: Design documents from `specs/002-constrained-calculation-modes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/library-api-delta.md, contracts/cli-repl-delta.md, quickstart.md

**Tests**: Included as mandatory tasks (not optional) — Constitution Principle II (Testing Standards, NON-NEGOTIABLE) requires unit tests for every calculation function and ≥90% coverage on calculation modules; this is enforced throughout, consistent with `001-metal-drilling-calc`'s tasks.md.

**Organization**: Tasks are grouped by user story (US1 = power-constrained mode, P1; US2 = fixed-RPM mode, P2) per spec.md priorities, on top of a shared Foundational phase (both modes reuse the same `calculate_drilling_metrics_at_rpm()` refactor and `mode`/`target_rpm` parameter plumbing).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Paths follow the existing single-project `src/machine_calc/` + `tests/` layout (no changes to plan.md's Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new tooling/dependencies are introduced by this feature (plan.md Technical Context); this phase only confirms the existing tooling covers the new code paths.

- [X] T001 Confirm `pytest`, `pytest-cov`, `ruff`, `black` configuration in `pyproject.toml` already covers new modules under `src/machine_calc/operations/drilling/` and `src/machine_calc/` with no config changes needed (no new dependency added per research.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared plumbing that both User Story 1 (power-constrained) and User Story 2 (fixed-RPM) depend on: the `CalculationMode` enum, the `calculate_drilling_metrics_at_rpm()` refactor, the extended `calculate()` signature with mode-dispatch/validation, and the new message-catalog keys.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `CalculationMode` enum (`STANDARD`, `POWER_CONSTRAINED`, `FIXED_RPM`) to `src/machine_calc/models.py`; add the new `mode: CalculationMode` field (default `CalculationMode.STANDARD`) to `CalculationResult` (data-model.md)
- [X] T003 [P] Refactor `src/machine_calc/operations/drilling/formulas.py`: extract `calculate_drilling_metrics_at_rpm(diameter_mm, depth_mm, material, tool, spindle_speed_rpm) -> DrillingMetrics` from the existing `calculate_drilling_metrics()`, which becomes a thin wrapper that derives the nominal RPM from cutting speed and delegates to the new helper (research.md #2)
- [X] T004 [P] Add the closed-form power-scaling helper to `src/machine_calc/operations/drilling/formulas.py`: given nominal metrics and an available power budget, compute `n_adjusted = n0 * (available_power_kw / nominal_power_kw)` only when `nominal_power_kw > available_power_kw` using `math.isclose(nominal_power_kw, available_power_kw, rel_tol=1e-9)` to detect the exact-equality boundary (treated as "sufficient", per spec.md FR-003/Clarifications 2026-07-11 — never triggers a reduction), else return the nominal metrics unchanged (research.md #1; depends on T003)
- [X] T005 [P] Implement `validate_target_rpm(target_rpm, locale)` (`math.isfinite()`-based positive/finite check — rejecting zero, negative, non-numeric, `NaN`, and `Infinity` all under the same `INVALID_TARGET_RPM` code per spec.md FR-007/Clarifications 2026-07-11) and `validate_mode_arguments(mode, available_power, target_rpm, locale)` (mutual-exclusivity/required-argument checks producing `MODE_CONFLICT`) in `src/machine_calc/validation.py` (FR-007, FR-009; data-model.md)
- [X] T006 [P] Add new message catalog keys to `src/machine_calc/locales/en.py`: mode-selection prompt + option labels, required-available-power prompt (power-constrained), required-target-RPM prompt (fixed-RPM), adjusted/user-specified spindle-speed display labels, and three separate, distinctly-worded error message keys for `INVALID_TARGET_RPM`/`MODE_CONFLICT`/`INFEASIBLE_POWER_BUDGET` — each MUST let a user identify the specific condition from message text alone (FR-011; spec.md Clarifications 2026-07-11 second checklist follow-up; data-model.md Message Catalog delta)
- [X] T007 Extend `calculate()` in `src/machine_calc/operations/drilling/__init__.py` with `mode: CalculationMode = CalculationMode.STANDARD` and `target_rpm: float | None = None` parameters: run the existing material/tool/diameter/depth validation first, exactly as today (unchanged order/precedence — a base-spec validation failure is returned before any mode-argument check runs), then validate the mode/target_rpm/available_power combination (via T005), then dispatch to the appropriate metrics path (standard: unchanged; power-constrained: T004's helper; fixed-RPM: `calculate_drilling_metrics_at_rpm()` directly with `target_rpm`), and set `mode` on every returned `CalculationResult` (success and error) (FR-001 through FR-009, FR-012; /speckit.analyze finding U1; depends on T002, T003, T004, T005)
- [X] T008 [P] Unit tests for `calculate_drilling_metrics_at_rpm()` and the power-scaling helper (nominal-equals-standard case, boundary case where available power exactly equals nominal power — asserting the no-reduction/no-op path per FR-003, using `math.isclose(rel_tol=1e-9)` — reduced-RPM case, zero/negative available power) in `tests/unit/operations/drilling/test_formulas_at_rpm.py` (depends on T003, T004)
- [X] T009 [P] Unit tests for `validate_target_rpm()` and `validate_mode_arguments()` (zero/negative/non-numeric/`NaN`/`Infinity` target RPM, all asserting `INVALID_TARGET_RPM`; `mode=POWER_CONSTRAINED` with a supplied `target_rpm` asserting `MODE_CONFLICT`; `mode=POWER_CONSTRAINED` without `available_power` asserting `MODE_CONFLICT`; `mode=STANDARD` with a supplied `target_rpm` and/or `available_power` asserting these are silently ignored, NOT `MODE_CONFLICT`, per spec.md FR-009/Clarifications 2026-07-11 second checklist follow-up) in `tests/unit/shared/test_validation_modes.py` (depends on T005)

**Checkpoint**: `calculate()` supports `mode`/`target_rpm` end-to-end at the library level, fully unit-tested. User story phases below only add mode-specific CLI prompts and story-focused contract/integration tests.

---

## Phase 3: User Story 1 - Adjust Calculation to Fit Available Machine Power (Priority: P1) 🎯 MVP

**Goal**: A machinist supplies a known available power and receives spindle speed/feed rate automatically reduced to the fastest setting that stays within that budget, instead of only an after-the-fact warning (spec.md User Story 1).

**Independent Test**: Call `calculate(mode=CalculationMode.POWER_CONSTRAINED, available_power=...)` directly (library) and via the CLI's new "power-constrained" mode selection, and verify: (a) required power never exceeds the supplied budget, (b) a budget already sufficient at the nominal RPM returns the unconstrained result unchanged, (c) an infeasible budget (e.g., 0) is rejected with `INFEASIBLE_POWER_BUDGET` and no numeric result (quickstart.md Scenarios 1-3).

### Tests for User Story 1 ⚠️

- [X] T010 [P] [US1] Contract test for the power-constrained success response shape (adjusted spindle speed, unchanged torque, `power_required` within `math.isclose(rel_tol=1e-9)` of `available_power`, `mode=POWER_CONSTRAINED`) per contracts/library-api-delta.md in `tests/contract/test_library_api_power_constrained.py`
- [X] T011 [P] [US1] Contract test for the `INFEASIBLE_POWER_BUDGET` error response (no exception, all numeric fields `None`) in `tests/contract/test_library_api_power_constrained_errors.py`
- [X] T012 [P] [US1] Integration test proving power-constrained mode is a no-op (identical numeric result to `STANDARD` mode, only `mode` differs) both when the supplied budget comfortably exceeds the nominal requirement and at the exact-equality boundary (`available_power` equal to nominal required power, within `math.isclose(rel_tol=1e-9)` — FR-003, spec.md Clarifications 2026-07-11; quickstart.md Scenario 2) in `tests/integration/test_power_constrained_noop.py`
- [X] T013 [P] [US1] Integration test for the CLI's power-constrained mode selection: mode prompt → required available-power prompt (not the base spec's optional prompt) → result display labels the spindle speed as adjusted (contracts/cli-repl-delta.md) in `tests/integration/test_cli_power_constrained.py`
- [X] T013a [P] [US1] Integration test for the mode-selection prompt's own re-prompt-on-invalid-input behavior, the blank-required-available-power-prompt re-prompt behavior (asserting it is never treated as `MODE_CONFLICT`), and the loop-re-run mode-switch clearing behavior (FR-013; spec.md Clarifications 2026-07-11; contracts/cli-repl-delta.md steps 2, 7, 9) in `tests/integration/test_cli_mode_prompt_ux.py` (depends on T014, T015)

### Implementation for User Story 1

- [X] T014 [US1] Add the calculation-mode selection prompt (FR-001a) to `src/machine_calc/cli.py`, positioned after the unit-system prompt and before material/tool/diameter/depth, offering `standard`/`power-constrained`/`fixed-rpm` (default `standard`), sourced entirely from `i18n.py` catalog keys (T006); re-prompt on invalid/empty entry (the same posture as material/tool selection — MUST NOT silently fall back to `standard`, per spec.md Clarifications 2026-07-11); when `standard` is chosen, the remaining prompt sequence is byte-for-byte unchanged from `001-metal-drilling-calc`; on a loop re-run (FR-014/FR-013), if the mode changes from the previous run, clear any previously entered mode-specific value (target RPM, or available-power-as-constraint) rather than carrying it over as an editable default (depends on T006)
- [X] T015 [US1] When `power-constrained` mode is selected, replace the existing optional advisory available-power prompt with a required available-power prompt in `src/machine_calc/cli.py`; a blank or non-numeric entry MUST be re-prompted as a validation failure (never treated as `MODE_CONFLICT`, per spec.md Clarifications 2026-07-11), using the validation message from T005/T007 (FR-002; depends on T007, T014)
- [X] T016 [US1] Update CLI result display in `src/machine_calc/cli.py` to show the mode-appropriate label (e.g., "adjusted to fit available power") next to spindle speed when `result.mode is CalculationMode.POWER_CONSTRAINED`, using the catalog key from T006 (FR-012; depends on T007, T014)

**Checkpoint**: User Story 1 (power-constrained mode) is fully functional and independently testable via both the library and the CLI.

---

## Phase 4: User Story 2 - Calculate Parameters for a User-Specified Spindle RPM (Priority: P2)

**Goal**: A user supplies a target spindle RPM directly and receives feed rate, machining time, torque, and required power calculated from it in one request (spec.md User Story 2).

**Independent Test**: Call `calculate(mode=CalculationMode.FIXED_RPM, target_rpm=...)` directly (library) and via the CLI's new "fixed-rpm" mode selection, and verify: (a) all dependent parameters are derived from the supplied RPM, (b) a non-positive/non-numeric RPM is rejected with `INVALID_TARGET_RPM`, (c) an optional available power that is exceeded at the given RPM produces the existing advisory `feasibility_warning` without altering the RPM (quickstart.md Scenarios 4-5).

### Tests for User Story 2 ⚠️

- [X] T017 [P] [US2] Contract test for the fixed-RPM success response shape (`spindle_speed_rpm` echoes `target_rpm` exactly, `mode=FIXED_RPM`, all dependent fields populated) per contracts/library-api-delta.md in `tests/contract/test_library_api_fixed_rpm.py`
- [X] T018 [P] [US2] Contract test for the `INVALID_TARGET_RPM` error response (zero, negative, non-numeric `target_rpm`) in `tests/contract/test_library_api_fixed_rpm_errors.py`
- [X] T019 [P] [US2] Integration test for fixed-RPM mode combined with an optional `available_power`: exceeded → `feasibility_warning` set and `target_rpm` unchanged; sufficient → no warning (FR-008) in `tests/integration/test_fixed_rpm_feasibility.py`
- [X] T020 [P] [US2] Integration test for the CLI's fixed-rpm mode selection: mode prompt → required target-RPM prompt → optional advisory available-power prompt → result display labels the spindle speed as user-specified (contracts/cli-repl-delta.md) in `tests/integration/test_cli_fixed_rpm.py`
- [X] T021 [P] [US2] Integration/contract test for mutual exclusivity (FR-009): `POWER_CONSTRAINED` mode with a `target_rpm` supplied, and `FIXED_RPM` mode's `target_rpm` omitted, both rejected with `MODE_CONFLICT` (quickstart.md Scenario 6) in `tests/contract/test_mode_conflict.py`

### Implementation for User Story 2

- [X] T022 [US2] When `fixed-rpm` mode is selected, add a required target-RPM prompt (replacing the derived-RPM step) followed by the existing optional advisory available-power prompt in `src/machine_calc/cli.py`, re-prompting on invalid RPM using the validation message from T005/T007 (FR-005, FR-007, FR-008; depends on T007, T014)
- [X] T023 [US2] Update CLI result display in `src/machine_calc/cli.py` to show the mode-appropriate label (e.g., "user-specified") next to spindle speed when `result.mode is CalculationMode.FIXED_RPM`, using the catalog key from T006 (FR-012; depends on T007, T014, T016)
- [X] T023a [US2] Integration test proving identical `CalculationResult` values from direct `calculate(mode=CalculationMode.POWER_CONSTRAINED, ...)`/`calculate(mode=CalculationMode.FIXED_RPM, ...)` calls and from driving the CLI with the same inputs and mode selection (FR-010/FR-016 extension; /speckit.analyze finding C1) in `tests/integration/test_identical_results_modes.py` (depends on T015, T016, T022, T023)

**Checkpoint**: Both user stories are independently functional; mutual exclusivity (FR-009) and the SC-004 no-regression guarantee are proven by automated tests.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression validation, and quality gates spanning both user stories.

- [X] T024 [P] Update `calculate()`'s docstring in `src/machine_calc/operations/drilling/__init__.py` to document `mode`, `target_rpm`, and the three new error codes (Constitution I; Sphinx autodoc picks this up automatically per research.md — no new doc toolchain)
- [X] T025 [P] Update the Sphinx developer guide (`docs/source/developer-guide.rst`) and end-user guide (`docs/source/user-guide.rst`) with the two new modes and their CLI/library usage (Constitution VII)
- [X] T026 Regression test: run the full existing `001-metal-drilling-calc` test suite unchanged and confirm 100% pass, proving SC-004 (no behavior change for calls that omit `mode`/`target_rpm`)
- [X] T027 Run `pytest --cov=machine_calc --cov-report=term-missing` and confirm ≥90% coverage is maintained on calculation modules including the new formulas.py/validation.py code paths (Constitution II); address any gaps
- [X] T028 Execute all 8 quickstart.md scenarios (including the manual CLI scenario 8) and confirm actual behavior matches documented expected outcomes
- [X] T029 [P] Static check confirming no literal user-facing strings were introduced in `cli.py`'s new prompt/output paths outside the message catalog (Constitution VIII; mirrors `001-metal-drilling-calc` T043a)
- [X] T030 [P] Update `README.md`'s usage section (if it documents CLI/library examples) to mention the two new modes, keeping the existing test-coverage reporting requirement intact (Constitution VII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories (both modes share `calculate_drilling_metrics_at_rpm()`, the `CalculationMode` enum, and the extended `calculate()` signature).
- **User Story 1 (Phase 3)** and **User Story 2 (Phase 4)**: Both depend only on Foundational completion. They touch overlapping lines in `cli.py` (the shared mode-selection prompt, T014, is Foundational-adjacent but implemented once in Phase 3 and reused — see note below) but distinct mode-conditional branches, so should be sequenced US1 before US2 if worked by a single contributor; a second contributor could take US2's library-level tasks (T017-T019, T021) in parallel once Phase 2 lands.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependency on User Story 2's tasks.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) for its library-level tests (T017-T019, T021) and contract tests, since `calculate()` already supports `target_rpm` after Phase 2. Its CLI tasks (T020, T022, T023) depend on T014 (the shared mode-selection prompt), which is implemented as part of US1 (T014) — note this one cross-story file dependency explicitly when sequencing work.

### Within Each User Story

- Tests are written before/alongside implementation and MUST fail before the corresponding implementation task lands (Constitution II).
- Foundational library plumbing (T002-T009) before any CLI prompt work (T014-T016, T022-T023).
- T014 (mode-selection prompt, shared) before T015/T016 (US1 CLI) and before T022/T023 (US2 CLI).

### Parallel Opportunities

- T002, T003, T004, T005, T006 (Foundational, different files) can run in parallel; T004 depends on T003 (same file, sequential); T007 depends on T002-T005.
- T008, T009 (Foundational tests) can run in parallel with each other once T003/T004/T005 land.
- T010-T013 (US1 tests) can run in parallel with each other; T017-T021 (US2 tests) can run in parallel with each other; US1 and US2 test tasks can run in parallel with each other (different files) once Phase 2 completes.
- T024, T025, T029, T030 (Polish) can run in parallel; T026, T027, T028 are sequential validation gates run after implementation is complete.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent Foundational tasks together:
Task: "Add CalculationMode enum to src/machine_calc/models.py"
Task: "Implement validate_target_rpm/validate_mode_arguments in src/machine_calc/validation.py"
Task: "Add new message catalog keys to src/machine_calc/locales/en.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1 (power-constrained mode)
4. **STOP and VALIDATE**: Run quickstart.md Scenarios 1-3 and confirm SC-003/SC-004
5. Deploy/demo if ready — power-constrained mode alone already delivers the primary user need described in the original feature request

### Incremental Delivery

1. Complete Setup + Foundational → shared `calculate()` extension ready
2. Add User Story 1 (power-constrained) → test independently → deploy/demo (MVP!)
3. Add User Story 2 (fixed-RPM) → test independently → deploy/demo
4. Polish (docs, coverage, quickstart validation) → final release

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing (Constitution II)
- Commit after each task or logical group
- Stop at either checkpoint to validate a story independently
- No new runtime dependencies, CI workflows, or top-level modules are introduced by this feature (plan.md); Polish phase reuses the existing CI/CD, Sphinx, and README infrastructure from `001-metal-drilling-calc`
