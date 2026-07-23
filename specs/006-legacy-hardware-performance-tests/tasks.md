---

description: "Task list for Legacy/Low-Power Hardware Performance Simulation Tests"
---

# Tasks: Legacy/Low-Power Hardware Performance Simulation Tests

**Input**: Design documents from `/specs/006-legacy-hardware-performance-tests/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/performance-suite-contract.md,
contracts/ci-performance-job-contract.md, quickstart.md

**Tests**: No separate contract/integration test tasks are included. The feature's deliverable
*is* an opt-in pytest suite (`tests/performance/`); its own test cases are implementation tasks
below, not tests-of-tests. The feature's spec does not request TDD-style meta-tests for the
harness itself, so none are generated (tests are OPTIONAL per template guidance).

**Organization**: Tasks are grouped by user story (spec.md priorities: US1=P1, US2=P2, US3=P3) so
each story is independently implementable, testable via its own Independent Test criterion, and
deliverable as an incremental slice.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single-project layout already in use (`src/`, `tests/` at repository root; no `src/` changes per
FR-011). All new files live under a new `tests/performance/` sibling directory to the existing
`tests/unit`, `tests/integration`, `tests/contract`, `tests/static` suites, plus one addition to
`pyproject.toml` and one new job in `.github/workflows/ci.yml`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new suite's skeleton and register it with the project's tooling, without
touching any behavior of the existing default/blocking test command.

- [ ] T001 Create the `tests/performance/` package directory with an empty `tests/performance/__init__.py`, per plan.md's Project Structure
- [ ] T002 [P] Register the `performance` marker in `pyproject.toml`'s `[tool.pytest.ini_options]` section (add a `markers = ["performance: opt-in legacy-hardware time/memory budget checks (see tests/performance/)"]` entry) — leave `testpaths` and `addopts` on lines 53-54 unchanged so the default/blocking command is unaffected (FR-006, research.md #1)

**Checkpoint**: `tests/performance/` exists as an (empty) package and is marker-registered; `pytest --markers` lists `performance`; bare `pytest` behavior is still byte-for-byte unchanged (nothing to collect yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared measurement/enforcement/auto-skip infrastructure that every user
story (local run, CI job, actionable report) depends on. No user story is independently testable
until this phase is done, since even US1's Independent Test requires a working harness and
auto-skip hook.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 [P] Define time/memory budget constants in `tests/performance/budgets.py`: `TIME_BUDGET_SECONDS = 1.0` and `MEMORY_BUDGET_BYTES = 128 * 1024 * 1024` (research.md #4's chosen upper-bound values), with a module docstring documenting the inclusive-pass convention (`measured <= budget` passes) per the spec's Edge Cases boundary rule
- [ ] T004 Implement platform-capability detection in `tests/performance/harness.py`: a function that reports whether `os.sched_setaffinity` exists (Linux) and whether the `resource` module and `resource.setrlimit(RLIMIT_AS, ...)` are usable (Linux/macOS), matching the platform-capability table in `contracts/performance-suite-contract.md`
- [ ] T005 Implement single-core CPU pin enforcement in `tests/performance/harness.py`: a context manager/helper that calls `os.sched_setaffinity(0, {core_id})` when available, restores the prior affinity mask on exit, and sets `cpu_pin_enforced=False` without raising when unavailable (FR-002, FR-009) — depends on T004 (same file)
- [ ] T006 Implement memory-ceiling enforcement and peak-memory measurement in `tests/performance/harness.py`: a helper that applies `resource.setrlimit(resource.RLIMIT_AS, (ceiling_bytes, ceiling_bytes))` when available (setting `memory_ceiling_enforced=False` and skipping without raising when unavailable/`ValueError`/`OSError`, per FR-009), plus a function that reads `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` before/after the measured call and normalizes it to bytes (KB→bytes on Linux, already bytes on macOS, per `platform.system()`, per research.md #3) — depends on T004 (same file)
- [ ] T007 Implement wall-clock timing in `tests/performance/harness.py`: a helper that wraps only the target calculation call (not fixture setup) with `time.perf_counter()` and returns elapsed seconds, per research.md #5's isolation approach
- [ ] T008 Define the `PerformanceTestCase` and `PerformanceReport` data structures (e.g. `dataclasses`) in `tests/performance/harness.py` per data-model.md's field tables (`name`, `target`, `call_args`/`call_kwargs`, `time_budget_seconds`, `memory_budget_bytes` for the case; `case_name`, `measured_time_seconds`, `measured_memory_bytes`, `time_passed`, `memory_passed`, `cpu_pin_enforced`, `memory_ceiling_enforced`, `overage_detail` for the report), plus a top-level orchestration function (e.g. `run_case(case) -> PerformanceReport`) that composes T005-T007's helpers — depends on T005, T006, T007
- [ ] T009 Add a module docstring to `tests/performance/harness.py` documenting the suite's known measurement-isolation limitations (ru_maxrss is a whole-process, monotonically-non-decreasing peak; pytest's own baseline footprint is not fully excluded; each case should run in relative isolation where practical) per research.md #5 and the spec's Edge Cases item on harness overhead — depends on T008
- [ ] T010 Implement `tests/performance/conftest.py` with a `pytest_collection_modifyitems` hook that applies `pytest.mark.skip(reason=...)` to every collected item under `tests/performance/` unless the `MACHINE_CALC_RUN_PERFORMANCE_TESTS` environment variable is set to `1` (or a truthy value), so a bare `pytest` run (CI's `test` job, any local default invocation) collects-but-skips these tests at near-zero cost (FR-006, FR-007, SC-004, research.md #1)

**Checkpoint**: `tests/performance/harness.py` and `budgets.py` exist with the full measurement/enforcement/data-structure toolkit; `tests/performance/conftest.py` auto-skips by default. Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Developer verifies a calculation meets the legacy-hardware time/memory budget before opening a PR (Priority: P1) 🎯 MVP

**Goal**: A contributor can run one opt-in local command and get a clear, per-calculation
pass/fail result (time and memory) for every currently-existing public calculation function,
while the project's normal/default `pytest` command remains completely unaffected.

**Independent Test**: Run `MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov -v` against the current codebase's drilling calculations and confirm it produces a per-calculation time/memory result and an overall pass/fail outcome; separately run bare `pytest` and confirm its duration/outcome/coverage is unchanged from before this feature existed.

### Implementation for User Story 1

- [ ] T011 [P] [US1] Define one representative, realistic input set (diameter, depth, material, tool, mode as applicable) for each of the four measured functions in `tests/performance/test_calculation_budgets.py`: `machine_calc.calculate()`, `calculate_drilling_metrics()`, `calculate_drilling_metrics_at_rpm()`, `calculate_power_constrained_metrics()` (all imported from `src/machine_calc/operations/drilling/`), ensuring none trigger the target's own input-validation error path (data-model.md's Performance Test Case validation rule)
- [ ] T012 [US1] Build a parametrized list/table of four `PerformanceTestCase` instances (one per T011 input set) in `tests/performance/test_calculation_budgets.py`, wiring each to `budgets.TIME_BUDGET_SECONDS`/`budgets.MEMORY_BUDGET_BYTES` from T003 (FR-001, SC-002: 100% coverage of the four existing public calculation functions) — depends on T011 and Phase 2's T008
- [ ] T013 [US1] Implement `@pytest.mark.performance` `@pytest.mark.parametrize`-driven test function(s) in `tests/performance/test_calculation_budgets.py` that call `harness.run_case()` (T008) per case, print/log the per-case report line (case name, measured time vs. time budget vs. pass/fail, measured memory vs. memory budget vs. pass/fail, `cpu_pin_enforced`, `memory_ceiling_enforced`) so it is visible with `-v`/`-s`, and assert `time_passed` and `memory_passed` — depends on T012
- [ ] T014 [US1] Validate quickstart.md Scenario 1 locally: run `MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov -v` and confirm all four calculations appear as distinct cases with pass/fail time+memory results and exit code `0`
- [ ] T015 [US1] Validate quickstart.md Scenario 2 locally: run bare `pytest` and confirm identical duration, pass/fail outcome, and coverage percentage to a pre-feature baseline (FR-006, SC-004) — confirms `tests/performance/` is collected but auto-skipped

**Checkpoint**: User Story 1 is fully functional and independently testable — a developer has a working opt-in local performance check, and the default gated suite is provably unaffected.

---

## Phase 4: User Story 2 - Reviewer/CI gets an informational signal without blocking merges (Priority: P2)

**Goal**: The performance suite from User Story 1 runs automatically on every pull request as a
separate, non-blocking, informational CI job, visible on the PR but never affecting mergeability.

**Independent Test**: Trigger a CI workflow run (e.g. via a sample pull request) that includes the new `performance` job; confirm it executes on `ubuntu-latest`, produces the same per-calculation pass/fail/flag report as the local run, and that its outcome does not change the PR's required/blocking status checks.

### Implementation for User Story 2

- [ ] T016 [US2] Add a new `performance` job to `.github/workflows/ci.yml` (after the existing `test` job, before `build`), with `runs-on: ubuntu-latest`, `if: github.event_name != 'schedule'` (matching the other per-change jobs), and steps `actions/checkout@v4` → `actions/setup-python@v5` (`python-version: ${{ env.PYTHON_VERSION }}`) → `pip install -e ".[dev]"` → the opt-in command `MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov`, per `contracts/ci-performance-job-contract.md`'s Job definition contract
- [ ] T017 [US2] Mark the performance-suite step in the new `performance` job (T016) with `continue-on-error: true` so a failing/flagged result never marks the job — or the workflow — as failed, per FR-008/SC-006 and `contracts/ci-performance-job-contract.md`'s Non-blocking mechanism — depends on T016 (same file/job)
- [ ] T018 [US2] Confirm (and, if needed, adjust) that `.github/workflows/ci.yml`'s `quality-summary` job's `needs: [lint, complexity, typecheck, security, dependency-scan, test, build, docs]` list does NOT include `performance`, and that the new job defines no `outputs:` consumed by `quality-summary` — per `contracts/ci-performance-job-contract.md`'s Exclusion/Non-goals sections (FR-008) — depends on T016
- [ ] T019 [US2] Validate quickstart.md Scenario 5 on a real or sample pull request: confirm the `performance` job appears in the PR's checks list, runs, and that the PR's required checks (`lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test`, `build`, `docs`) and mergeability are unaffected by its outcome, and that `performance` does not appear as a row in the `quality-summary` PR comment

**Checkpoint**: User Stories 1 AND 2 both work independently — every PR now gets an automatic, non-blocking performance signal in addition to the local opt-in command.

---

## Phase 5: User Story 3 - Contributor gets an actionable report when a calculation exceeds budget (Priority: P3)

**Goal**: When a calculation fails its time and/or memory budget, the report names the
calculation, the failed dimension(s) (reported distinctly, never merged), the measured value, the
configured budget, and the amount/percentage by which it was exceeded — never a bare assertion
failure.

**Independent Test**: Deliberately run the suite against a calculation whose measured time or memory exceeds its budget (e.g. via a temporarily lowered test-only threshold) and confirm the failure output names the calculation, the failed dimension(s), the measured value, the budget, and the overage amount/percentage, with time and memory failures reported as distinct messages when both occur.

### Implementation for User Story 3

- [ ] T020 [P] [US3] Implement an `overage_detail` message builder in `tests/performance/harness.py` that, given a `PerformanceReport` with `time_passed=False` and/or `memory_passed=False`, composes one distinct, human-readable message per failed dimension — each naming the calculation (`case_name`), the failed dimension (time or memory), the measured value, the configured budget, and the amount/percentage exceeded — and leaves `overage_detail=None` when both checks pass (FR-005, data-model.md's overage_detail validation rule) — depends on Phase 2's T008
- [ ] T021 [US3] Wire T020's message builder into `harness.run_case()` (populating `PerformanceReport.overage_detail`) and into the assertion(s) in `tests/performance/test_calculation_budgets.py` (T013) so a failing case's pytest assertion message is the actionable `overage_detail` text rather than a bare `assert` failure (SC-003) — depends on T020 and Phase 3's T013
- [ ] T022 [US3] Validate quickstart.md Scenario 3 (graceful degradation) on a macOS or Windows machine if available, or by simulating unavailable capabilities: confirm the run completes without erroring/crashing and clearly reports `cpu_pin_enforced=False` (and, on Windows-equivalent conditions, `memory_ceiling_enforced=False`) rather than a silent false pass (FR-009, FR-010, SC-005)
- [ ] T023 [US3] Validate quickstart.md Scenario 4: temporarily lower `tests/performance/budgets.py`'s constants to an unreachable value in a scratch/local-only edit, rerun Scenario 1's command, confirm the failure message names the calculation, states the failed dimension(s) distinctly, the measured value, the budget, and the overage amount/percentage, then revert the scratch edit (this step is a manual validation aid only and MUST NOT be committed)

**Checkpoint**: All three user stories are independently functional — local opt-in checks (US1), non-blocking CI visibility (US2), and actionable overage reporting (US3) all work together and in isolation.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and end-to-end confirmation that span all three user stories, without
changing any story's behavior.

- [ ] T024 [P] Add a brief mention of the opt-in performance suite (its command and a link to `specs/006-legacy-hardware-performance-tests/quickstart.md`) to README.md's existing "Run the tests" section, making clear it is separate from and does not affect the `pytest` command already documented there
- [ ] T025 Run the full `quickstart.md` validation end-to-end (all five scenarios in order) as a final confirmation that FR-001 through FR-012 and SC-001 through SC-006 are all satisfied together

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001's `tests/performance/` directory must exist) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational completion; in practice also depends on User Story 1's `tests/performance/test_calculation_budgets.py` existing so the CI job's command has something meaningful to run, but the CI *wiring itself* (T016-T018) touches only `.github/workflows/ci.yml` and does not require US1's harness internals to be finished
- **User Story 3 (Phase 5)**: Depends on Foundational completion (T008's `PerformanceReport` structure) and on User Story 1's T013 (the assertion call site it enhances)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — the MVP
- **User Story 2 (P2)**: Builds on US1's suite existing (to have something to run in CI) but its own tasks (CI YAML) touch a different file than US1's tasks
- **User Story 3 (P3)**: Enhances US1's reporting (same test file) but is scoped to a separate concern (message content) and can be verified independently per its own Independent Test

### Within Each User Story

- Foundational data structures/helpers before story-specific wiring
- Within Phase 2 (`harness.py`), T004 before T005/T006 (both depend on capability detection); T005/T006/T007 before T008 (data structures compose the helpers); T008 before T009 (docstring documents the finished module)
- Within Phase 3, input definitions (T011) before the case table (T012) before the test function (T013) before manual validation (T014, T015)
- Within Phase 4, job creation (T016) before its `continue-on-error` step (T017) before the exclusion check (T018) before PR validation (T019)
- Within Phase 5, the message builder (T020) before wiring it in (T021) before manual validation (T022, T023)

### Parallel Opportunities

- T002 (pyproject.toml marker) can run in parallel with T001 (directory creation) — different files
- T003 (budgets.py) can run in parallel with T004 (harness.py capability detection) — different files
- T011 (defining the four input sets, all in one new file) is marked [P] as an initial authoring pass but the case table/test function that follow it (T012, T013) are sequential edits to the same file
- T020 (overage message builder in harness.py) can be authored in parallel with unrelated Phase 4 CI tasks (T016-T018) since they touch different files
- T024 (README update) can run in parallel with T025 (end-to-end validation) — different files

---

## Parallel Example: Foundational Phase

```bash
# Launch independent Foundational file-creation tasks together:
Task: "Define time/memory budget constants in tests/performance/budgets.py"
Task: "Implement platform-capability detection in tests/performance/harness.py"
```

## Parallel Example: User Story 2 vs. User Story 3

```bash
# Once Foundational + US1 are done, these can proceed in parallel (different files):
Task: "Add a new performance job to .github/workflows/ci.yml"
Task: "Implement an overage_detail message builder in tests/performance/harness.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md Scenarios 1 and 2 to confirm US1 independently
5. This alone satisfies FR-001 through FR-007, FR-009 through FR-012, and SC-001, SC-002, SC-004, SC-005 (degradation is exercised by Foundational's harness even without US3's polished messages)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate via quickstart.md Scenarios 1-2 → local opt-in suite ships (MVP!)
3. Add User Story 2 → Validate via quickstart.md Scenario 5 → CI visibility ships, still non-blocking
4. Add User Story 3 → Validate via quickstart.md Scenarios 3-4 → actionable overage reporting ships
5. Each story adds value without breaking previous stories or the existing default/blocking suite

### Parallel Team Strategy

With multiple contributors, after Setup + Foundational are complete:

- Contributor A: User Story 1 (`tests/performance/test_calculation_budgets.py`)
- Contributor B: User Story 2 (`.github/workflows/ci.yml`) — can start once US1's test file exists (even before its final overage-message polish), since the CI job just needs a command to invoke
- Contributor C: User Story 3 (`harness.py` overage-message builder) — can start once Foundational's `PerformanceReport` structure exists, and wires into US1's test file once both are ready

---

## Notes

- [P] tasks = different files (or clearly independent additions to the same new module), no dependencies
- [Story] label maps task to specific user story for traceability; Setup/Foundational/Polish tasks intentionally have no [Story] label
- No `src/machine_calc` file is touched by any task (FR-011) — every task above targets `tests/performance/`, `pyproject.toml`, or `.github/workflows/ci.yml`
- Verify after each phase that bare `pytest` (no env var) still passes with unchanged duration/coverage — this is the standing regression check for FR-006/SC-004 throughout implementation, not just at T015
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before proceeding
- Avoid: modifying `tests/unit`, `tests/integration`, `tests/contract`, `tests/static`, or any `src/` file; adding a new third-party dependency; adding the `performance` job to `quality-summary`'s `needs:` list
