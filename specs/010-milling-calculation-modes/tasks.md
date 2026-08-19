# Tasks: Milling Calculation Modes (Power-Constrained & Fixed-RPM)

**Input**: Design documents from `specs/010-milling-calculation-modes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/library-api-milling-modes-delta.md, contracts/cli-repl-milling-modes-delta.md, quickstart.md

**Tests**: Included as mandatory tasks (not optional) — Constitution Principle II (Testing Standards, NON-NEGOTIABLE) requires unit tests for every calculation function and ≥90% coverage on calculation modules, consistent with `002-constrained-calculation-modes`'s and `009-milling-calculations`'s tasks.md.

**Organization**: Tasks are grouped by user story (US1 = power-constrained mode, P1; US2 = fixed-RPM mode, P2) per spec.md priorities, on top of a shared Foundational phase (both modes reuse drilling's existing `CalculationMode`/validators/error codes unmodified — research.md #4 — and both share the new `_shared.py`/`_calculate.py` at-RPM/dispatch refactor, done once for both end-milling and face-milling — research.md #2/#3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Paths follow the existing single-project `src/machine_calc/` + `tests/` layout (no changes to plan.md's Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new tooling/dependencies are introduced by this feature (plan.md Technical Context); this phase only confirms the existing tooling covers the new code paths.

- [X] T001 Confirm `pytest`, `pytest-cov`, `ruff`, `black`, `mypy` configuration in `pyproject.toml` already covers new/modified modules under `src/machine_calc/operations/milling/` with no config changes needed (no new dependency added per research.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared plumbing that both User Story 1 (power-constrained) and User Story 2 (fixed-RPM) depend on: the at-RPM/power-scaling helpers in `_shared.py`, the mode-dispatch extension of `_calculate.py`'s `calculate_milling()`, and both sub-operations' thin at-RPM wrappers and extended entry-point signatures. `CalculationMode`, `validate_target_rpm()`, `validate_mode_arguments()`, the three error codes, and their message-catalog entries already exist (added by `002-constrained-calculation-modes`) and are reused **unmodified** — no foundational task recreates them (research.md #4).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Refactor `src/machine_calc/operations/milling/_shared.py`: extract `calculate_milling_metrics_at_rpm(diameter_mm, axial_depth_of_cut_mm, radial_engagement_mm, feed_per_tooth_mm, number_of_teeth, length_of_cut_mm, material, spindle_speed_rpm) -> MillingMetrics` from the existing `calculate_milling_metrics()`, which becomes a thin wrapper that derives the nominal RPM from `cutting_speed_factor` and delegates to the new helper (research.md #2; data-model.md)
- [X] T003 [P] Add the closed-form power-scaling helper `calculate_power_constrained_milling_metrics(diameter_mm, axial_depth_of_cut_mm, radial_engagement_mm, feed_per_tooth_mm, number_of_teeth, length_of_cut_mm, material, available_power_kw) -> MillingMetrics` to `src/machine_calc/operations/milling/_shared.py`: compute `n_adjusted = n0 * (available_power_kw / nominal_power_kw)` only when `nominal_power_kw > available_power_kw` using `math.isclose(nominal_power_kw, available_power_kw, rel_tol=1e-9)` to detect the exact-equality boundary (treated as "sufficient" per spec.md FR-003 — never triggers a reduction), else return the nominal metrics unchanged (research.md #1; depends on T002)
- [X] T004 [P] Add `calculate_end_milling_metrics_at_rpm(...)` thin wrapper to `src/machine_calc/operations/milling/end_milling/formulas.py`, adapting `_shared.py`'s new at-RPM core (T002) into `EndMillingMetrics`, mirroring the existing `calculate_end_milling_metrics()` wrapper (FR-014 module-boundary; research.md #3)
- [X] T005 [P] Add `calculate_face_milling_metrics_at_rpm(...)` thin wrapper to `src/machine_calc/operations/milling/face_milling/formulas.py`, adapting `_shared.py`'s new at-RPM core (T002) into `FaceMillingMetrics`, mirroring the existing `calculate_face_milling_metrics()` wrapper (FR-014 module-boundary; research.md #3)
- [X] T006 Extend `calculate_milling()` in `src/machine_calc/operations/milling/_calculate.py` with `mode: CalculationMode = CalculationMode.STANDARD` and `target_rpm: float | None = None` parameters, plus a second injected `compute_at_rpm` callable (alongside the existing `compute` callable) so end-milling and face-milling each pass their own T004/T005 wrapper: run the existing nine-step milling validation first, exactly as today (unchanged order/precedence — a base-spec validation failure is returned before any mode-argument check runs, per `002-constrained-calculation-modes`'s finding U1 precedent), then validate mode/target_rpm/available_power via the existing (unmodified) `validate_mode_arguments()`, then dispatch to the appropriate metrics path (standard: unchanged; power-constrained: T003's helper; fixed-RPM: the injected `compute_at_rpm` directly with `target_rpm`), and set `mode` on every returned `CalculationResult` (success and error) (FR-001 through FR-009, FR-012, FR-014; data-model.md; depends on T002, T003, T004, T005)
- [X] T007 [P] [US1,US2] Extend `calculate_end_milling()` in `src/machine_calc/operations/milling/end_milling/__init__.py` with `mode`/`target_rpm` parameters, passed through to `calculate_milling()` along with the T004 `compute_at_rpm` wrapper (depends on T006)
- [X] T008 [P] [US1,US2] Extend `calculate_face_milling()` in `src/machine_calc/operations/milling/face_milling/__init__.py` with `mode`/`target_rpm` parameters, passed through to `calculate_milling()` along with the T005 `compute_at_rpm` wrapper (depends on T006)
- [X] T009 [P] Unit tests for `calculate_milling_metrics_at_rpm()` and `calculate_power_constrained_milling_metrics()` (nominal-equals-standard case, boundary case where available power exactly equals nominal power — asserting the no-reduction/no-op path per FR-003, using `math.isclose(rel_tol=1e-9)` — reduced-RPM case, zero/negative available power, infeasible-budget case) in `tests/unit/operations/milling/test_shared_at_rpm.py` (depends on T002, T003)
- [X] T010 [P] Unit tests for `calculate_end_milling_metrics_at_rpm()` in `tests/unit/operations/milling/end_milling/test_formulas_at_rpm.py` and `calculate_face_milling_metrics_at_rpm()` in `tests/unit/operations/milling/face_milling/test_formulas_at_rpm.py` (each a thin-wrapper delegation check against T009's core cases) (depends on T004, T005)

**Checkpoint**: `calculate_end_milling()`/`calculate_face_milling()` support `mode`/`target_rpm` end-to-end at the library level, fully unit-tested. User story phases below only add mode-specific CLI prompts and story-focused contract/integration tests.

---

## Phase 3: User Story 1 - Calculate Milling Parameters Within an Available Power Budget (Priority: P1) 🎯 MVP

**Goal**: A machinist supplies a known available power and receives spindle speed/feed rate/torque/material removal rate automatically reduced to the fastest setting that stays within that budget, for both end-milling and face-milling, instead of only an after-the-fact warning (spec.md User Story 1).

**Independent Test**: Call `calculate_end_milling(mode=CalculationMode.POWER_CONSTRAINED, available_power=...)`/`calculate_face_milling(mode=CalculationMode.POWER_CONSTRAINED, available_power=...)` directly (library) and via the CLI's new "power-constrained" mode selection, and verify: (a) required power never exceeds the supplied budget, (b) a budget already sufficient at the nominal RPM returns the unconstrained result unchanged, (c) an infeasible budget (e.g., 0) is rejected with `INFEASIBLE_POWER_BUDGET` and no numeric result (quickstart.md Scenarios 1-3).

### Tests for User Story 1 ⚠️

- [ ] T011 [P] [US1] Contract test for the power-constrained success response shape (adjusted spindle speed, unchanged torque, `power_required` within `math.isclose(rel_tol=1e-9)` of `available_power`, `mode=POWER_CONSTRAINED`) for both `calculate_end_milling()` and `calculate_face_milling()` per contracts/library-api-milling-modes-delta.md in `tests/contract/test_library_api_milling_power_constrained.py`
- [ ] T012 [P] [US1] Contract test for the `INFEASIBLE_POWER_BUDGET` error response (no exception, all numeric fields `None`) for both milling sub-operations in `tests/contract/test_library_api_milling_power_constrained_errors.py`
- [ ] T013 [P] [US1] Integration test proving power-constrained mode is a no-op (identical numeric result to `STANDARD` mode, only `mode` differs) both when the supplied budget comfortably exceeds the nominal requirement and at the exact-equality boundary (FR-003; quickstart.md Scenario 2) for both end-milling and face-milling in `tests/integration/test_milling_power_constrained_noop.py`
- [ ] T014 [P] [US1] Integration test for the CLI's power-constrained mode selection: mode prompt → required available-power prompt (not the base spec's optional prompt) → result display labels the spindle speed as adjusted, for both `_run_end_milling_session()` and `_run_face_milling_session()` (contracts/cli-repl-milling-modes-delta.md) in `tests/integration/test_cli_milling_power_constrained.py`
- [ ] T014a [P] [US1] Integration test for the milling mode-selection prompt's own re-prompt-on-invalid-input behavior, the blank-required-available-power-prompt re-prompt behavior (asserting it is never treated as `MODE_CONFLICT`), and the loop-re-run mode-switch clearing behavior (FR-013; contracts/cli-repl-milling-modes-delta.md) in `tests/integration/test_cli_milling_mode_prompt_ux.py` (depends on T015, T016)

### Implementation for User Story 1

- [ ] T015 [US1] Add the calculation-mode selection prompt (FR-001a) to the shared `_prompt_milling_inputs()` helper in `src/machine_calc/cli.py`, positioned after the unit-system prompt and before material-type/material/tool/geometry, offering `standard`/`power-constrained`/`fixed-rpm` (default `standard`), sourced entirely from the existing `i18n.py` catalog keys (reused unmodified — research.md #4); re-prompt on invalid/empty entry (MUST NOT silently fall back to `standard`); when `standard` is chosen, the remaining milling prompt sequence is byte-for-byte unchanged from `009-milling-calculations`; on a loop re-run (FR-013), if the mode changes from the previous run, clear any previously entered mode-specific value (target RPM, or available-power-as-constraint) for that sub-operation's session state rather than carrying it over as an editable default (depends on T007, T008)
- [ ] T016 [US1] When `power-constrained` mode is selected for either milling sub-operation, replace the existing optional advisory available-power prompt with a required available-power prompt in `src/machine_calc/cli.py`; a blank or non-numeric entry MUST be re-prompted as a validation failure (never treated as `MODE_CONFLICT`), reusing the existing validation message (FR-002; depends on T006, T015)
- [ ] T017 [US1] Update CLI result display in `src/machine_calc/cli.py` to show the mode-appropriate label (e.g., "adjusted to fit available power") next to spindle speed for both milling sessions when `result.mode is CalculationMode.POWER_CONSTRAINED`, reusing the existing catalog key (FR-012; depends on T006, T015)

**Checkpoint**: User Story 1 (power-constrained mode) is fully functional and independently testable via both the library and the CLI, for both end-milling and face-milling.

---

## Phase 4: User Story 2 - Calculate Milling Parameters for a User-Specified Spindle RPM (Priority: P2)

**Goal**: A user supplies a target spindle RPM directly and receives feed rate, machining time, torque, material removal rate, and required power calculated from it in one request, for both end-milling and face-milling (spec.md User Story 2).

**Independent Test**: Call `calculate_end_milling(mode=CalculationMode.FIXED_RPM, target_rpm=...)`/`calculate_face_milling(mode=CalculationMode.FIXED_RPM, target_rpm=...)` directly (library) and via the CLI's new "fixed-rpm" mode selection, and verify: (a) all dependent parameters are derived from the supplied RPM, (b) a non-positive/non-numeric RPM is rejected with `INVALID_TARGET_RPM`, (c) an optional available power that is exceeded at the given RPM produces the existing advisory feasibility warning without altering the RPM (quickstart.md Scenarios 4-5).

### Tests for User Story 2 ⚠️

- [ ] T018 [P] [US2] Contract test for the fixed-RPM success response shape (`spindle_speed_rpm` echoes `target_rpm` exactly, `mode=FIXED_RPM`, all dependent fields populated) for both milling sub-operations per contracts/library-api-milling-modes-delta.md in `tests/contract/test_library_api_milling_fixed_rpm.py`
- [ ] T019 [P] [US2] Contract test for the `INVALID_TARGET_RPM` error response (zero, negative, non-numeric `target_rpm`) for both milling sub-operations in `tests/contract/test_library_api_milling_fixed_rpm_errors.py`
- [ ] T020 [P] [US2] Integration test for fixed-RPM mode combined with an optional `available_power`: exceeded → feasibility warning set and `target_rpm` unchanged; sufficient → no warning (FR-008) for both milling sub-operations in `tests/integration/test_milling_fixed_rpm_feasibility.py`
- [ ] T021 [P] [US2] Integration test for the CLI's fixed-rpm mode selection: mode prompt → required target-RPM prompt → optional advisory available-power prompt → result display labels the spindle speed as user-specified, for both milling sessions (contracts/cli-repl-milling-modes-delta.md) in `tests/integration/test_cli_milling_fixed_rpm.py`
- [ ] T022 [P] [US2] Integration/contract test for mutual exclusivity (FR-009): `POWER_CONSTRAINED` mode with a `target_rpm` supplied, and `FIXED_RPM` mode's `target_rpm` omitted, both rejected with `MODE_CONFLICT`, for both milling sub-operations (quickstart.md Scenario 6) in `tests/contract/test_milling_mode_conflict.py`

### Implementation for User Story 2

- [ ] T023 [US2] When `fixed-rpm` mode is selected for either milling sub-operation, add a required target-RPM prompt (replacing the derived-RPM step) followed by the existing optional advisory available-power prompt in `src/machine_calc/cli.py`, re-prompting on invalid RPM using the existing validation message (FR-005, FR-007, FR-008; depends on T006, T015)
- [ ] T024 [US2] Update CLI result display in `src/machine_calc/cli.py` to show the mode-appropriate label (e.g., "user-specified") next to spindle speed for both milling sessions when `result.mode is CalculationMode.FIXED_RPM`, reusing the existing catalog key (FR-012; depends on T006, T015, T017)
- [ ] T024a [US2] Integration test proving identical `CalculationResult` values from direct `calculate_end_milling(mode=..., ...)`/`calculate_face_milling(mode=..., ...)` calls and from driving the CLI with the same inputs and mode selection, for both new modes and both sub-operations (FR-010 extension) in `tests/integration/test_identical_results_milling_modes.py` (depends on T016, T017, T023, T024)

**Checkpoint**: Both user stories are independently functional for both milling sub-operations; mutual exclusivity (FR-009) and the SC-004 no-regression guarantee are proven by automated tests.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression validation, and quality gates spanning both user stories.

- [ ] T025 [P] Update `calculate_end_milling()`'s and `calculate_face_milling()`'s docstrings (`src/machine_calc/operations/milling/end_milling/__init__.py`, `.../face_milling/__init__.py`) to document `mode`, `target_rpm`, and the three reused error codes (Constitution I; Sphinx autodoc picks this up automatically per research.md — no new doc toolchain)
- [ ] T026 [P] Update the Sphinx developer guide (`docs/source/developer-guide.rst`) and end-user guide (`docs/source/user-guide.rst`) with milling's two new modes and their CLI/library usage, alongside drilling's existing mode documentation (Constitution VII)
- [ ] T027 Regression test: run the full existing `009-milling-calculations` test suite unchanged and confirm 100% pass, proving SC-004 (no behavior change for milling calls that omit `mode`/`target_rpm`)
- [ ] T028 Update `tests/integration/test_cli_prompt_budget.py` to assert per-mode milling prompt counts (research.md #5: 14/12 standard, 14/13 power-constrained, 15/13 fixed-RPM) rather than one fixed count for all milling runs
- [ ] T029 Run `pytest --cov=machine_calc --cov-report=term-missing` and confirm ≥90% coverage is maintained on calculation modules including the new `_shared.py`/`_calculate.py`/`formulas.py` code paths (Constitution II); address any gaps
- [ ] T030 Execute all 8 quickstart.md scenarios (including the manual CLI scenario) and confirm actual behavior matches documented expected outcomes
- [ ] T031 [P] Static check confirming no literal user-facing strings were introduced in `cli.py`'s new milling mode-prompt/output paths outside the message catalog (Constitution VIII; mirrors `002-constrained-calculation-modes` T029)
- [ ] T032 [P] Update `README.md`'s usage section (if it documents CLI/library milling examples) to mention the two new milling modes, keeping the existing test-coverage reporting requirement intact (Constitution VII)
- [ ] T033 Run the full quality-gate suite (`mypy`, `ruff`, `radon`/`xenon` complexity, `bandit`, `pip-audit`) per Constitution Principle IX and confirm no new findings introduced by this feature's changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories (both modes share the `_shared.py` at-RPM/power-scaling helpers, the `_calculate.py` dispatch extension, and both sub-operations' extended entry-point signatures).
- **User Story 1 (Phase 3)** and **User Story 2 (Phase 4)**: Both depend only on Foundational completion. They touch overlapping lines in `cli.py` (the shared mode-selection prompt, T015, is Foundational-adjacent but implemented once in Phase 3 and reused — see note below) but distinct mode-conditional branches, so should be sequenced US1 before US2 if worked by a single contributor; a second contributor could take US2's library-level tasks (T018-T020, T022) in parallel once Phase 2 lands.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependency on User Story 2's tasks.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) for its library-level tests (T018-T020, T022) and contract tests, since `calculate_end_milling()`/`calculate_face_milling()` already support `target_rpm` after Phase 2. Its CLI tasks (T021, T023, T024) depend on T015 (the shared mode-selection prompt), which is implemented as part of US1 (T015) — note this one cross-story file dependency explicitly when sequencing work.

### Within Each User Story

- Tests are written before/alongside implementation and MUST fail before the corresponding implementation task lands (Constitution II).
- Foundational library plumbing (T002-T010) before any CLI prompt work (T015-T017, T023-T024).
- T015 (mode-selection prompt, shared) before T016/T017 (US1 CLI) and before T023/T024 (US2 CLI).

### Parallel Opportunities

- T002, T003 (same file, sequential — T003 depends on T002); T004, T005 (different files, parallel, each depends on T002)
- T007, T008 (different files, parallel, each depends on T006)
- T009, T010 (Foundational tests, parallel with each other once T002-T005 land)
- T011-T014a (US1 tests) can run in parallel with each other; T018-T022 (US2 tests) can run in parallel with each other; US1 and US2 test tasks can run in parallel with each other (different files) once Phase 2 completes.
- T025, T026, T031, T032 (Polish) can run in parallel; T027, T028, T029, T030, T033 are sequential validation gates run after implementation is complete.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent Foundational tasks together (after T002/T003 land):
Task: "Add calculate_end_milling_metrics_at_rpm() thin wrapper in end_milling/formulas.py"
Task: "Add calculate_face_milling_metrics_at_rpm() thin wrapper in face_milling/formulas.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1 (power-constrained mode)
4. **STOP and VALIDATE**: Run quickstart.md Scenarios 1-3 and confirm SC-001/SC-003/SC-004
5. Deploy/demo if ready — power-constrained mode alone already delivers the primary parity gap described in the feature request

### Incremental Delivery

1. Complete Setup + Foundational → shared milling `calculate_*()` extension ready
2. Add User Story 1 (power-constrained) → test independently → deploy/demo (MVP!)
3. Add User Story 2 (fixed-RPM) → test independently → deploy/demo
4. Polish (docs, coverage, quickstart validation, quality gates) → final release

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing (Constitution II)
- Commit after each task or logical group
- Stop at either checkpoint to validate a story independently
- No new runtime dependencies, CI workflows, or top-level modules are introduced by this feature (plan.md); Polish phase reuses the existing CI/CD, Sphinx, and README infrastructure from `009-milling-calculations`/`002-constrained-calculation-modes`
