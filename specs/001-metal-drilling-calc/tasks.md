# Tasks: Metal Drilling Calculations Module

**Input**: Design documents from `specs/001-metal-drilling-calc/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/library-api.md, contracts/cli-repl.md, quickstart.md

**Tests**: Included as mandatory tasks (not optional) — Constitution Principle II (Testing Standards, NON-NEGOTIABLE) requires unit tests for every calculation function and ≥90% coverage on calculation modules; this is enforced throughout, not treated as an opt-in extra.

**Organization**: Tasks are grouped by user story (US1, US2) to enable independent implementation and testing of each, per spec.md priorities (both P1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Paths follow the single-project `src/machine_calc/` + `tests/` + `docs/` layout defined in plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and tooling, per Constitution Principle IV (packaging) and research.md.

- [X] T001 Create the project skeleton (`src/machine_calc/`, `src/machine_calc/operations/drilling/`, `tests/unit/shared/`, `tests/unit/operations/drilling/`, `tests/contract/`, `tests/integration/`, `docs/source/`) per plan.md Project Structure
- [X] T002 Initialize `pyproject.toml` with PEP 517/518 build backend, `src/` layout package discovery, project metadata, `requires-python = ">=3.9"`, and a conditional `tomli` dependency for Python < 3.11 (Constitution IV; research.md #1, #2, #3)
- [X] T003 [P] Configure `ruff` and `black` (or equivalent) in `pyproject.toml` and add a `lint` script/make target (Constitution I)
- [X] T004 [P] Configure `pytest` and `pytest-cov` in `pyproject.toml`/`pytest.ini` with a coverage-fail-under threshold of 90% for `src/machine_calc/operations` and `src/machine_calc/calculations`-equivalent modules (Constitution II)
- [X] T005 [P] Scaffold the Sphinx project in `docs/source/` (`conf.py` with the `napoleon` extension and `alabaster` theme, `index.rst`) per research.md #7

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared, operation-agnostic infrastructure plus the drilling calculation engine itself — both User Story 1 (CLI) and User Story 2 (library) depend entirely on this phase, since the CLI is a thin layer over the same `calculate()` used directly by library callers (FR-001, FR-002, FR-016).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 [P] Implement `UnitSystem` enum, `CalculationResult`, and `ErrorInfo` dataclasses in `src/machine_calc/models.py` (data-model.md)
- [X] T007 [P] Implement `WorkpieceMaterial` dataclass and the initial material registry (mild steel, stainless steel, aluminum, cast iron, brass, titanium) in `src/machine_calc/registry.py` (FR-004)
- [X] T008 [P] Implement metric↔imperial conversion helpers in `src/machine_calc/units.py` (FR-017; research.md #4)
- [X] T009 [P] Implement `DrillingTool` dataclass and the initial tool registry (HSS, cobalt, carbide) in `src/machine_calc/operations/drilling/tools.py` (FR-005)
- [ ] T009a [P] Implement message catalog loader (`src/machine_calc/i18n.py`) with locale selection, key lookup, and English fallback; implement the default English catalog (`src/machine_calc/locales/en.py`) (FR-019)
- [ ] T009b [P] Configure stdlib `logging` (`src/machine_calc/logging_setup.py`) with hard-coded English log message strings, independent of the i18n catalog (Constitution VIII)
- [ ] T009c [US1] [US2] Retrofit already-implemented hard-coded strings to use the `i18n.py` catalog: replace literal `print()`/`input()` prompt text in `cli.py`, and literal `ErrorInfo(...)` message strings in `validation.py` and `operations/drilling/__init__.py`, with catalog key lookups (English catalog values matching current text); add a `locale` parameter to `calculate()` and thread it through to `ErrorInfo.message` construction (FR-019; depends on T009a, T011, T013, T024)
  - Acceptance: no literal user-facing string remains in `cli.py`'s prompt/output paths or in `ErrorInfo(...)` constructor calls outside `locales/en.py`; `calculate(locale="en")` and CLI output produce identical text for the same catalog.
- [X] T010 Implement `Configuration` loading from an external TOML file with built-in default fallback (`max_diameter_mm=100`, `max_depth_mm=500`) in `src/machine_calc/config.py` (FR-018; research.md #3)
- [X] T011 Implement shared input validation (diameter/depth positivity + configurable bounds, required material/tool presence, returning `ErrorInfo` rather than raising) in `src/machine_calc/validation.py` (FR-009, FR-010)
- [X] T012 Implement drilling formulas (spindle speed, feed rate, machining time in minutes, torque, power) in `src/machine_calc/operations/drilling/formulas.py`, citing the formula sources in code comments (FR-006, FR-007, FR-008, FR-011; research.md #4; Constitution III)
- [X] T013 Implement the drilling `calculate()` orchestration (validate → resolve material/tool combination → compute formulas → apply feasibility check against optional `available_power` → build `CalculationResult`, never raising for expected validation failures) in `src/machine_calc/operations/drilling/__init__.py` (FR-009 through FR-016; depends on T006-T012)
- [X] T014 [P] Unit tests for drilling formulas (nominal inputs, boundary values, known reference results within 5% per SC-002) in `tests/unit/operations/drilling/test_formulas.py` (depends on T012)
- [X] T015 [P] Unit tests for shared validation (zero/negative/non-numeric/out-of-range diameter and depth, missing material/tool) in `tests/unit/shared/test_validation.py` (depends on T011)
- [X] T016 [P] Unit tests for unit conversion helpers (metric↔imperial round-trip, tolerance-based comparisons) in `tests/unit/shared/test_units.py` (depends on T008)
- [X] T017 [P] Unit tests for configuration loading and default-bound fallback in `tests/unit/shared/test_config.py` (depends on T010)
- [X] T018 [P] Unit tests for the material and drilling-tool registries (uniqueness, positive reference values) in `tests/unit/shared/test_registry.py` (depends on T007, T009)
- [ ] T018a [P] Unit tests for the message catalog: key lookup, missing-key fallback to English, missing-locale fallback to English (depends on T009a) in `tests/unit/shared/test_i18n.py`

**Checkpoint**: The drilling `calculate()` engine is fully implemented and unit-tested. User story phases below only add the CLI layer (US1) and library-facing contract guarantees (US2) on top of this foundation.

---

## Phase 3: User Story 1 - Calculate Core Drilling Parameters Interactively (Priority: P1) 🎯 MVP

**Goal**: A step-by-step interactive text REPL (FR-002) that collects unit system, material, tool, diameter, depth, and optional power rating, displays the drilling `CalculationResult`, and loops for further calculations (FR-014), built strictly on top of the Phase 2 `calculate()` engine with no calculation logic of its own.

**Independent Test**: Run `python -m machine_calc`, walk through the prompt sequence in contracts/cli-repl.md, and verify spindle speed, feed rate, machining time, torque, and power are displayed with correct units and labels; verify invalid input and missing selections are re-prompted; verify a supplied power rating below the required power shows a feasibility warning; verify power is still shown when the rating is left blank (quickstart.md Scenario 5).

### Tests for User Story 1 ⚠️

- [X] T019 [P] [US1] Contract test asserting `cli.py` contains no drilling calculation logic and delegates every result to `machine_calc.calculate()` (static/behavioral check) in `tests/contract/test_cli_contract.py`
- [X] T020 [P] [US1] Integration test for the full REPL prompt sequence with valid input, asserting displayed values and unit labels match the library result (FR-013, FR-016) in `tests/integration/test_cli_flow.py`
- [X] T021 [P] [US1] Integration test for REPL validation error handling (invalid diameter/depth, missing material/tool re-prompt) in `tests/integration/test_cli_validation.py`
- [X] T022 [P] [US1] Integration test for the REPL loop: changing one input (e.g., switching drilling tool) and recalculating without restarting (FR-014, spec Acceptance Scenario 4) in `tests/integration/test_cli_loop.py`

### Implementation for User Story 1

- [X] T023 [US1] Implement the public package surface (`calculate`, `list_materials`, `list_tools`, `UnitSystem` re-exported from `operations.drilling`) in `src/machine_calc/__init__.py` (depends on T013)
- [X] T024 [US1] Implement the interactive REPL prompt flow (unit system → material → tool → diameter → depth → optional power → display result → loop) in `src/machine_calc/cli.py` per contracts/cli-repl.md, using message-catalog keys via `i18n.py` for all prompts/labels (no hard-coded user-facing strings) (depends on T023, T009a)
- [X] T025 [US1] Add a runnable entry point: `src/machine_calc/__main__.py` (for `python -m machine_calc`) and a `console_scripts` entry in `pyproject.toml` (depends on T024)
- [X] T026 [US1] Format CLI output with unit labels matching the selected unit system and render `feasibility_warning`/`error.message` clearly (FR-013; depends on T024)

**Checkpoint**: User Story 1 is fully functional and independently testable via the CLI alone.

---

## Phase 4: User Story 2 - Embed Calculations in Another Application (Priority: P1)

**Goal**: Prove and lock the library API's standalone contract (FR-001, FR-015, FR-016) so a calling program can perform a full drilling calculation with no interactive text interface involved, receiving structured results (including torque and power) and structured errors instead of exceptions.

**Independent Test**: Call `machine_calc.calculate(...)` directly from a Python script/test with no CLI invocation, and verify the returned `CalculationResult` matches what the CLI would display for identical inputs, including error and feasibility-warning cases (quickstart.md Scenarios 1-4, 6, 7).

### Tests for User Story 2 ⚠️

- [ ] T027 [P] [US2] Contract test for the `calculate()` success response shape per contracts/library-api.md in `tests/contract/test_library_api_success.py`
- [ ] T027a [P] [US2] Contract test/doc-check asserting `calculate()`'s docstring documents the exact unit for every `CalculationResult` field under both `UnitSystem.METRIC` and `UnitSystem.IMPERIAL` (FR-013 unit-labeling contract; /speckit.analyze finding B1) in `tests/contract/test_library_api_unit_labels.py`
- [ ] T028 [P] [US2] Contract test for every documented error code (`INVALID_DIAMETER`, `INVALID_DEPTH`, `MISSING_MATERIAL`, `MISSING_TOOL`, `UNSUPPORTED_COMBINATION`) asserting no exception is raised in `tests/contract/test_library_api_errors.py`
- [ ] T029 [P] [US2] Contract test for the feasibility-warning behavior (power supplied and exceeded vs. power omitted) in `tests/contract/test_library_api_feasibility.py`
- [ ] T030 [P] [US2] Integration test proving identical `CalculationResult` values from direct `calculate()` calls and from driving the CLI with the same inputs (FR-016) in `tests/integration/test_identical_results.py`
- [ ] T031 [P] [US2] Integration test for a `Configuration` file overriding default diameter/depth bounds (quickstart.md Scenario 7) in `tests/integration/test_config_override.py`

### Implementation for User Story 2

- [ ] T032 [US2] Verify and finalize `list_materials()` / `list_tools()` exposure and docstrings (inputs/outputs/units per Constitution I) in `src/machine_calc/__init__.py` (depends on T023)
- [ ] T033 [US2] Add a `config_path` parameter pass-through from `calculate()` to the `Configuration` loader (FR-018) in `src/machine_calc/operations/drilling/__init__.py` (depends on T013, T010)

**Checkpoint**: Both user stories are independently functional; the FR-016 identical-results guarantee is proven by automated tests.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, CI/CD automation, and final validation spanning both user stories (Constitution Principles V, VII; Additional Constraints).

- [ ] T034 [P] Write `README.md` with install/usage instructions for both the library and CLI, and a test coverage section/badge sourced from `pytest-cov` output (Constitution VII)
- [ ] T035 [P] Write the Sphinx end-user guide (`docs/source/user-guide.rst`): installation, CLI walkthrough, example library snippet
- [ ] T036 [P] Write the Sphinx developer guide (`docs/source/developer-guide.rst`): architecture overview, `operations/` extensibility pattern (Constitution VI), autodoc-generated API reference for `machine_calc`
- [ ] T037 Create the GitHub Actions CI workflow (`.github/workflows/ci.yml`): lint, `pytest --cov` with the 90% threshold, package build check (`python -m build`), and Sphinx docs build on every push/PR (research.md #8; Constitution Additional Constraints)
- [ ] T038 Add the GitHub Pages docs-publish step/job to `.github/workflows/ci.yml` (or a dedicated `docs.yml`), publishing the Sphinx build output on successful builds of `main` (Constitution VII)
- [ ] T039 Create the GitHub Actions release workflow (`.github/workflows/release.yml`): build and publish the package to PyPI on every merge to `main` (Constitution Additional Constraints)
- [ ] T040 Run `pytest --cov=machine_calc --cov-report=term-missing` and confirm ≥90% coverage on calculation modules; address any gaps (Constitution II)
- [ ] T041 Execute all 7 quickstart.md scenarios manually (or via a validation script) and confirm actual behavior matches documented expected outcomes; explicitly time a full end-to-end CLI session (open → select unit system/material/tool → enter diameter/depth → view results) and confirm it completes in under 30 seconds (SC-001)
- [ ] T042 [P] Measure and record calculation execution time against the 0.5-1.0s legacy-hardware target (Constitution V); document the result and methodology in `specs/001-metal-drilling-calc/research.md` (append a "Validation" note) or a new `perf-notes.md`
- [ ] T043 [P] Measure and record peak memory (RSS) usage of a representative CLI session and a representative library `calculate()` call, confirming it fits within the ~64-128 MB target in Constitution Principle V; document the methodology and result alongside T042
- [ ] T043a [P] Static check confirming no literal user-facing strings exist in `cli.py`/error paths outside the message catalog (post-T009c retrofit), and confirming log statements are plain English (Constitution VIII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories (the drilling `calculate()` engine is shared by US1 and US2).
- **User Story 1 (Phase 3)** and **User Story 2 (Phase 4)**: Both depend only on Foundational completion; they touch different files (`cli.py`/`__main__.py` for US1 vs. `__init__.py` exports/tests for US2) and can proceed in parallel.
- **Polish (Phase 5)**: Depends on both user stories being complete (docs and CI reference both the CLI and library; PyPI/Pages publishing needs a working package).

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependency on User Story 2's tasks (it only needs the already-foundational `calculate()`).
- **User Story 2 (P1)**: Can start after Foundational (Phase 2). Independent of User Story 1's CLI files; its identical-results test (T030) reads from both but does not require US1's tasks to be "complete," only for `cli.py` to exist — sequence T030 after T024 if run strictly in parallel teams.

### Within Each User Story

- Tests are written before/alongside implementation and MUST fail before the corresponding implementation task lands (Constitution II).
- Public API surface (T023) before CLI (T024-T026) and before library contract finalization (T032-T033).

### Parallel Opportunities

- T003, T004, T005 (Setup) can run in parallel.
- T006, T007, T008, T009 (Foundational, different files) can run in parallel; T010 and T011 can run in parallel with each other but depend on T006; T012 depends on T007-T009.
- T014-T018 (Foundational tests, different files) can run in parallel once their respective implementation tasks land.
- Once Foundational (Phase 2) is complete, User Story 1 (Phase 3) and User Story 2 (Phase 4) can proceed fully in parallel (different files).
- T019-T022 (US1 tests) can run in parallel with each other; T027-T031 (US2 tests) can run in parallel with each other.
- T034, T035, T036 (Polish docs) can run in parallel; T042 and T043 can run in parallel with documentation tasks and with each other.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent foundational modules together:
Task: "Implement UnitSystem enum, CalculationResult, and ErrorInfo dataclasses in src/machine_calc/models.py"
Task: "Implement WorkpieceMaterial dataclass and material registry in src/machine_calc/registry.py"
Task: "Implement metric<->imperial conversion helpers in src/machine_calc/units.py"
Task: "Implement DrillingTool dataclass and tool registry in src/machine_calc/operations/drilling/tools.py"
```

## Parallel Example: User Stories 1 & 2 (after Foundational)

```bash
# Two developers can work simultaneously once Phase 2 is done:
Developer A (US1): T019 → T020 → T021 → T022 → T023 → T024 → T025 → T026
Developer B (US2): T027 → T028 → T029 → T030 → T031 → T032 → T033
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (drilling `calculate()` engine — CRITICAL, blocks both stories).
3. Complete Phase 3: User Story 1 (interactive CLI).
4. **STOP and VALIDATE**: Run quickstart.md Scenario 5 end-to-end; confirm SC-001/SC-003.
5. Demo the CLI as the MVP; the library API (User Story 2) is already usable at this point since Phase 2 exposes `calculate()` directly, but Phase 4's dedicated contract tests formalize that guarantee.

### Incremental Delivery

1. Setup + Foundational → shared calculation engine ready and unit-tested.
2. Add User Story 1 → validate independently → demo the CLI (MVP).
3. Add User Story 2 → validate independently → demo direct library usage (e.g., in a short Python script or notebook).
4. Add Polish (docs, CI/CD, PyPI/Pages publishing) → project is release-ready per Constitution Principle VII and the Additional Constraints CI/CD gate.

### Parallel Team Strategy

With two developers: both complete Setup + Foundational together, then Developer A takes User Story 1 (CLI) while Developer B takes User Story 2 (library contract tests) — both build only on the shared Phase 2 engine and touch disjoint files, so they integrate without conflict.

---

## Notes

- [P] tasks touch different files and have no unmet dependencies within their phase.
- [Story] labels (US1/US2) map tasks to spec.md's user stories for traceability.
- Both user stories are Priority P1 per spec.md; Foundational carries the shared calculation engine so neither story duplicates it (Constitution Principle VI extensibility pattern also relies on this separation for future operations like turning/milling).
- Commit after each task or logical group; verify tests fail before implementing per Constitution Principle II.
- Stop at each checkpoint (end of Phase 2, Phase 3, Phase 4) to validate independently before proceeding.
