# Tasks: Milling Calculations Module

**Input**: Design documents from `/specs/009-milling-calculations/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks ARE included — Constitution Principle II (Testing Standards) is NON-NEGOTIABLE in this repository: every calculation function MUST have unit tests covering nominal, boundary, zero/negative, and known-reference values, and CI enforces ≥90% coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Single project (`src/machine_calc/`, `tests/` at repository root) per plan.md "Structure Decision".

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new package skeleton and register its bundled data files so later phases have somewhere to write to.

- [X] T001 [P] Create the milling package skeleton: `src/machine_calc/operations/milling/__init__.py` (package docstring only, mirroring `operations/__init__.py`'s style), `src/machine_calc/operations/milling/end_milling/__init__.py`, `src/machine_calc/operations/milling/face_milling/__init__.py`, plus empty-but-importable `src/machine_calc/operations/milling/end_milling/data/__init__.py` and `src/machine_calc/operations/milling/face_milling/data/__init__.py` (required for `importlib.resources` package-data access, mirroring `operations/drilling/data/__init__.py`)
- [X] T002 [P] Create the milling test directory skeleton: `tests/unit/operations/milling/end_milling/` and `tests/unit/operations/milling/face_milling/` (with `__init__.py` files if the existing drilling test dirs use them — check `tests/unit/operations/drilling/`)
- [X] T003 Register the two new bundled data files in `pyproject.toml` under `[tool.setuptools.package-data]` by adding `"operations/milling/end_milling/data/*.toml"` and `"operations/milling/face_milling/data/*.toml"` to the existing `machine_calc` entry (depends on T001)

**Checkpoint**: Package skeleton importable; packaging config knows about the new data files.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared, operation-agnostic infrastructure that BOTH milling sub-operations and the CLI operation-selection flow depend on. Every extension here is additive — no existing drilling behavior changes (FR-002, SC-005).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Add `MachiningOperation` (`DRILLING = "drilling"`, `MILLING = "milling"`) and `MillingSubOperation` (`END_MILLING = "end-milling"`, `FACE_MILLING = "face-milling"`) enums to `src/machine_calc/models.py` per data-model.md "New / Changed Shared Entities", with PEP 257 docstrings explaining they drive CLI dispatch only (FR-001, FR-003)
- [X] T005 Add the optional `material_removal_rate: float | None = None` field to `CalculationResult` in `src/machine_calc/models.py`, appended after all existing fields to preserve positional-argument compatibility, documenting its units (cm³/min METRIC / in³/min IMPERIAL) and that drilling results always leave it `None` (research.md #7; depends on T004 — same file)
- [X] T006 [P] Add the three new milling bound fields `max_mill_diameter_mm = 200.0`, `max_depth_of_cut_mm = 50.0`, `max_length_of_cut_mm = 1000.0` to the `Configuration` dataclass in `src/machine_calc/config.py`, and read them in `load_configuration()` from the same TOML file drilling already uses — not a second config file (FR-018, research.md #8, data-model.md "Configuration")
- [X] T007 [P] Add `cm3_min_to_in3_min()` and `in3_min_to_cm3_min()` volumetric conversion helpers to `src/machine_calc/units.py` (needed to report MRR under `UnitSystem.IMPERIAL`; 1 in³ = 16.387064 cm³), with docstrings citing the conversion constant
- [X] T008 Add the new milling validation functions to `src/machine_calc/validation.py`, each returning `ErrorInfo | None` (never raising, per FR-012) and sourcing messages from the catalog: `validate_depth_of_cut_mm()` (→ `INVALID_DEPTH_OF_CUT`), `validate_engagement_mm()` (→ `INVALID_ENGAGEMENT` when engagement > diameter, FR-009), `validate_feed_per_tooth_mm()` (→ `INVALID_FEED_PER_TOOTH`), `validate_tooth_count()` (→ `INVALID_TOOTH_COUNT`; rejects non-whole values such as `4.5` as well as zero/negative, per FR-008), `validate_length_of_cut_mm()` (→ `INVALID_LENGTH_OF_CUT`); all reject zero, negative, non-numeric, NaN and Infinity, and all reject values above their configured upper bound (FR-018), mirroring `validate_target_rpm()`'s existing posture (depends on T006 for the bound fields)
- [X] T009 [P] Add all new user-facing message keys to `src/machine_calc/locales/en.py` (Constitution VIII — no hard-coded strings): operation-selection prompt/labels (`cli.prompt.operation`, `cli.prompt.operation.invalid`, `cli.operation.drilling`, `cli.operation.milling`), milling sub-operation prompt/labels (`cli.prompt.milling_sub_operation`, `cli.milling_sub_operation.end_milling`, `cli.milling_sub_operation.face_milling`), new input prompt labels (axial depth of cut, radial depth of cut, width of cut, feed per tooth, number of teeth, length of cut), the new result line `cli.result.material_removal_rate`, and error messages for the five new error codes from T008
- [X] T010 [P] Implement the shared milling formula core `calculate_milling_metrics()` and its `MillingMetrics` frozen dataclass in `src/machine_calc/operations/milling/_shared.py`, implementing the seven formulas in data-model.md "Formulas" (vc → n → vf → Q → Pc → Mc → tc), with a module docstring citing the Sandvik Coromant "Machining Formulas" source per research.md #1 and Constitution III; all inputs/outputs canonical metric (depends on T001)
- [X] T011 [P] Unit-test the shared formula core in `tests/unit/operations/milling/test_shared_formulas.py`: hand-computed reference values for each of the seven formulas, boundary values, and `math.isclose()` tolerance-based comparisons per Constitution III (depends on T010)
- [X] T011a [P] Accuracy test in `tests/unit/operations/milling/test_shared_formulas_reference.py` validating the shared core against **published** cutting-data examples (not self-computed values): at least three worked examples taken from the Sandvik Coromant "Machining Formulas" reference cited in research.md #1, each asserted with `math.isclose()` at the tolerance SC-002 requires, with the source example's inputs, expected outputs and citation recorded in the test docstring; confirms the reported power is a **net** cutting-power figure (spec.md Assumptions, research.md #1) rather than a motor-power figure (depends on T010; satisfies SC-002)
- [X] T011b [P] Unit-test `validate_tooth_count()` rejects non-whole tooth counts (e.g. `4.5`) with `INVALID_TOOTH_COUNT` while accepting int-valued floats such as `4.0`, in `tests/unit/test_validation_milling.py` (FR-008; depends on T008)
- [X] T011c [P] Regression test proving milling tool registries are isolated from drilling's, in `tests/integration/test_milling_config_isolation.py`: (a) a user config file containing only `[[end_mill_tools]]` leaves `list_tools()` (drilling) identical to the bundled default and lets a drilling calculation succeed; (b) a legacy config containing only `[[materials]]`/`[[tools]]` adds nothing to either milling tool registry; (c) a milling tool entry without `feed_factor` never raises `RegistryConfigError` from the drilling registry (contracts/milling-tools-config-schema.md "Section isolation"; research.md #3; FR-002, FR-015, SC-005)
- [X] T011d [P] Test the configurability of the milling bounds in `tests/unit/test_config_milling_bounds.py`: with no configuration file the documented defaults (`max_mill_diameter_mm = 200.0`, `max_depth_of_cut_mm = 50.0`, `max_length_of_cut_mm = 1000.0`) apply and a value above each is rejected; with a TOML config file raising each bound, the previously rejected value is accepted and a value above the *new* bound is rejected; the same file's existing drilling bounds (`max_diameter_mm`, `max_depth_mm`) are unaffected (FR-018, research.md #8; depends on T006, T008)

**Checkpoint**: Shared models, config, units, validation, message catalog, and the milling formula core are all in place and tested — both milling stories and the CLI selection story can now proceed.

---

## Phase 3: User Story 1 - Select a Machining Operation Before Calculating (Priority: P1) 🎯 MVP

**Goal**: The REPL asks the user to choose a machining operation (drilling or milling) as its very first prompt, routes into the chosen operation's flow, and lets the user re-select the operation on each loop iteration — with drilling's existing behavior completely unchanged.

**Independent Test**: Launch `machine-calc`, verify the first prompt offers drilling and milling before any material/tool prompt; selecting drilling reproduces the existing flow exactly; selecting milling leads to a sub-operation prompt; an unrecognized entry re-prompts; and after a completed calculation the run-again loop returns to the operation prompt.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US1] Integration test for the operation-selection prompt ordering and invalid-entry re-prompt in `tests/integration/test_cli_operation_selection.py`, asserting the operation prompt is emitted before any material/tool prompt and that an unrecognized choice re-prompts with a catalog-sourced message (Acceptance Scenarios 1, 4)
- [X] T013 [P] [US1] Integration test for operation re-selection on the run-again loop in `tests/integration/test_cli_operation_reselection.py`, asserting the user is asked for the operation again (not forced to repeat the previous one) after answering yes to run-again (FR-017, Acceptance Scenario 5)
- [X] T013a [US1] **Before** any `cli.py` refactor, capture a golden baseline of the current drilling REPL session (prompt sequence + rendered result block) by running the pre-feature CLI under scripted input and committing the transcript as `tests/contract/data/drilling_baseline_session.txt`; this fixture is what T014 compares against, since after the refactor there is no other way to prove byte-for-byte parity (blocks T014, T015)
- [X] T014 [P] [US1] Drilling-regression contract test in `tests/contract/test_drilling_unchanged_after_operation_prompt.py`, driving the REPL with a leading `drilling` selection and asserting the subsequent prompt sequence and displayed results are byte-for-byte identical to the T013a baseline transcript (FR-002, SC-005, Acceptance Scenario 2; depends on T013a)

### Implementation for User Story 1

- [X] T015 [US1] Extract the existing drilling REPL loop body from `run()` into a new `_run_drilling_session(...)` function in `src/machine_calc/cli.py`, moving the code verbatim (no behavioral edits) so drilling remains unchanged (FR-002; research.md #6)
- [X] T016 [US1] Add `_prompt_operation(default, locale)` to `src/machine_calc/cli.py`, built on the existing `_prompt_choice()` helper with a `MachiningOperation`-to-translated-label mapping and reverse lookup, mirroring `_prompt_mode()`'s established pattern including its re-prompt-on-invalid-entry behavior (FR-001, Acceptance Scenario 4; depends on T004, T009)
- [X] T017 [US1] Add `_prompt_milling_sub_operation(default, locale)` to `src/machine_calc/cli.py`, structurally identical to T016 but over `MillingSubOperation` (FR-003, Acceptance Scenario 3; depends on T004, T009)
- [X] T018 [US1] Rewrite `run()` in `src/machine_calc/cli.py` as the thin outer loop specified in contracts/cli-repl-milling.md "Startup / loop sequence": prompt for operation → dispatch to `_run_drilling_session()` or (for milling) prompt for sub-operation and dispatch → run-again prompt → loop back to the operation prompt (FR-001, FR-017); keep `run()`'s cyclomatic complexity within `pyproject.toml`'s `max-complexity = 10` (Constitution IX) by delegating all per-operation work to the session functions (depends on T015, T016, T017)
- [X] T019 [US1] Stub `_run_end_milling_session()` and `_run_face_milling_session()` in `src/machine_calc/cli.py` so the milling branch of T018's dispatcher is wired end-to-end and this story is independently runnable; the stubs are fully implemented in US2/US3 (depends on T018)

**Checkpoint**: The REPL's operation-selection step works, drilling is provably unchanged, and the milling branch is wired but not yet productive — User Story 1 is independently testable and demonstrable as the MVP.

---

## Phase 4: User Story 2 - Calculate End Milling Parameters Interactively (Priority: P1)

**Goal**: A user who selects milling → end milling can enter material, end-mill tool, diameter, flute count, axial and radial depth of cut, feed per tooth, and length of cut, and receive spindle speed, feed rate, MRR, machining time, torque, and power — with an optional power-rating feasibility warning.

**Independent Test**: Run the REPL, select milling → end milling, enter a valid material/tool/geometry set, and verify all six outputs match hand-computed reference values; verify invalid inputs (zero/negative/non-numeric, radial depth > diameter) are rejected with clear messages and no result; verify power is still reported when the power rating is omitted.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T020 [P] [US2] Unit tests for the `EndMillTool` registry in `tests/unit/operations/milling/end_milling/test_tools_registry.py`: bundled entries load, user-config override/addition merges via `registry_config`, and a non-positive `cutting_speed_factor` raises `RegistryConfigError`
- [X] T021 [P] [US2] Unit tests for end-milling formulas in `tests/unit/operations/milling/end_milling/test_formulas.py`: nominal hand-computed reference values, boundary values, and `math.isclose()` comparisons (Constitution II, III)
- [X] T022 [P] [US2] Unit/contract tests for `calculate_end_milling()`'s full validation matrix in `tests/unit/operations/milling/end_milling/test_calculate.py`: every error code from data-model.md ("New Error Codes") with all numeric fields asserted `None`, plus the `INVALID_ENGAGEMENT` radial-depth-exceeds-diameter case, and an explicit FR-010 case where the selected material's `specific_cutting_force_kc` is missing or non-positive, asserting `UNUSABLE_MATERIAL` with the material and offending field named in the message (FR-008, FR-009, FR-010, SC-003, Acceptance Scenarios 2, 7)
- [X] T023 [P] [US2] Integration test for the end-milling REPL flow in `tests/integration/test_cli_end_milling.py`: full prompt sequence per contracts/cli-repl-milling.md, result display including the new material-removal-rate line, the feasibility warning when the supplied power rating is exceeded, and power still reported when the rating is omitted (Acceptance Scenarios 1, 5, 6)
- [X] T023a [P] [US2] SC-001 prompt-budget test in `tests/integration/test_cli_prompt_budget.py`, driving a complete end-milling run and asserting the exact number of prompts issued (13) and the number requiring a typed value (12), both within SC-001's stated budget; the exact-count assertion is a deliberate tripwire — the binding requirement is SC-001's ceiling, so a change that legitimately adds a prompt must update this test *and* re-check SC-001 rather than silently drift (SC-001; contracts/cli-repl-milling.md "Prompt-count budget")
- [X] T023b [P] [US2] Imperial round-trip test in `tests/unit/operations/milling/test_imperial_round_trip.py`, asserting that end-milling and face-milling inputs expressed in `UnitSystem.IMPERIAL` produce results equal (within `math.isclose()` tolerance) to the metric-equivalent inputs after conversion back, covering diameter, depths, feed per tooth, length of cut, feed rate, MRR (in³/min ↔ cm³/min), torque (in-lb ↔ N·m) and power (HP ↔ kW) (FR-013; depends on T007)

### Implementation for User Story 2

- [X] T024 [P] [US2] Create the bundled end-mill tool reference data in `src/machine_calc/operations/milling/end_milling/data/tools.toml` with `[[end_mill_tools]]` entries (`name`, `cutting_speed_factor`, `unit_system`) for HSS/Cobalt/Carbide-class end mills, following `operations/drilling/data/tools.toml`'s schema and header-comment style, minus `feed_factor` (research.md #3, #4; contracts/milling-tools-config-schema.md)
- [X] T025 [US2] Implement the `EndMillTool` frozen dataclass plus `list_end_mill_tools()` / `get_end_mill_tool()` in `src/machine_calc/operations/milling/end_milling/tools.py`, built on the existing shared `registry_config.load_and_merge()` and mirroring `operations/drilling/tools.py` (including `display_name()` and `_validate()`), with `cutting_speed_factor` as the only numeric field and `_TABLE_KEY = "end_mill_tools"` — **not** drilling's `"tools"`, which would merge milling entries into the drilling registry and break it on the missing `feed_factor` (data-model.md "Registry `table_key` allocation"; research.md #3; depends on T024)
- [X] T026 [P] [US2] Implement `EndMillingMetrics` and `calculate_end_milling_metrics()` in `src/machine_calc/operations/milling/end_milling/formulas.py` as a thin wrapper delegating to `_shared.calculate_milling_metrics()` with `ae = radial_depth_of_cut_mm`, re-wrapping the shared result in the sub-operation's own named dataclass (research.md #2; depends on T010)
- [X] T027 [US2] Implement the public `calculate_end_milling()` entry point in `src/machine_calc/operations/milling/end_milling/__init__.py` per contracts/library-api-milling.md: imperial→metric input conversion, the nine-step validation order from data-model.md "Validation Order", material resolution/`is_usable` check, metrics computation, optional power feasibility warning, metric→imperial output conversion (including MRR via T007), and a `CalculationResult` return that never raises (FR-005, FR-008, FR-009, FR-011, FR-012); decompose into `_validate_and_prepare`/`_build_result`-style helpers to stay within `max-complexity = 10` (depends on T005, T006, T007, T008, T025, T026)
- [X] T028 [US2] Implement `_run_end_milling_session()` in `src/machine_calc/cli.py` (replacing T019's stub) with the ten-step prompt sequence in contracts/cli-repl-milling.md "End milling session prompts", including `_prompt_end_mill_tool_choice()` mirroring `_prompt_tool_choice()`, and all prompts sourced from the message catalog (FR-004, FR-016; depends on T019, T027)
- [X] T029 [US2] Extend `_display_result()` in `src/machine_calc/cli.py` to print the `cli.result.material_removal_rate` line only when `result.material_removal_rate is not None`, leaving drilling's output byte-for-byte unchanged (contracts/cli-repl-milling.md "Display contract addition"; depends on T005, T009)

**Checkpoint**: End milling is fully functional through both the REPL and the library; User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Calculate Face Milling Parameters Interactively (Priority: P2)

**Goal**: A user who selects milling → face milling can enter material, face-mill tool, cutter diameter, insert count, axial depth of cut, width of cut, feed per tooth, and length of cut, and receive the same six outputs from the face-milling entry point, with its own tool registry, "width of cut" labelling and validation, assuming full/symmetric engagement.

**Independent Test**: Run the REPL, select milling → face milling, enter a valid input set, and verify all six outputs match hand-computed reference values; verify width of cut exceeding the cutter diameter is rejected; verify the feasibility warning fires when the supplied power rating is exceeded.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T030 [P] [US3] Unit tests for the `FaceMillTool` registry in `tests/unit/operations/milling/face_milling/test_tools_registry.py`, mirroring T020
- [X] T031 [P] [US3] Unit tests for face-milling formulas in `tests/unit/operations/milling/face_milling/test_formulas.py`: nominal hand-computed reference values, boundary values, and an explicit assertion that full/symmetric engagement is assumed (no chip-thinning correction applied), per spec.md Assumptions
- [X] T032 [P] [US3] Unit/contract tests for `calculate_face_milling()`'s validation matrix in `tests/unit/operations/milling/face_milling/test_calculate.py`, including the width-of-cut-exceeds-cutter-diameter `INVALID_ENGAGEMENT` case and the same missing/non-positive-`kc` `UNUSABLE_MATERIAL` case as T022 (FR-009, FR-010, SC-003, Acceptance Scenarios 2, 3)
- [X] T033 [P] [US3] Integration test for the face-milling REPL flow in `tests/integration/test_cli_face_milling.py`, asserting the "width of cut" label is used (not "radial depth of cut") and the feasibility warning behavior (Acceptance Scenarios 1, 4)

### Implementation for User Story 3

- [X] T034 [P] [US3] Create the bundled face-mill tool reference data in `src/machine_calc/operations/milling/face_milling/data/tools.toml` with `[[face_mill_tools]]` entries for Carbide/Coated-Carbide-class face mills, following T024's schema and style (research.md #3; contracts/milling-tools-config-schema.md)
- [X] T035 [US3] Implement the `FaceMillTool` frozen dataclass plus `list_face_mill_tools()` / `get_face_mill_tool()` in `src/machine_calc/operations/milling/face_milling/tools.py`, structurally identical to T025 over its own bundled table and with `_TABLE_KEY = "face_mill_tools"` (data-model.md "Registry `table_key` allocation"; depends on T034)
- [X] T036 [P] [US3] Implement `FaceMillingMetrics` and `calculate_face_milling_metrics()` in `src/machine_calc/operations/milling/face_milling/formulas.py` as a thin wrapper delegating to `_shared.calculate_milling_metrics()` with `ae = width_of_cut_mm`, documenting the full/symmetric-engagement assumption in the module docstring (research.md #2; depends on T010)
- [X] T037 [US3] Implement the public `calculate_face_milling()` entry point in `src/machine_calc/operations/milling/face_milling/__init__.py` per contracts/library-api-milling.md, mirroring T027's structure with `width_of_cut` in place of `radial_depth_of_cut` (FR-006, FR-007, FR-009, FR-011, FR-012; depends on T005, T006, T007, T008, T035, T036)
- [X] T038 [US3] Implement `_run_face_milling_session()` in `src/machine_calc/cli.py` (replacing T019's stub) per contracts/cli-repl-milling.md "Face milling session prompts", including `_prompt_face_mill_tool_choice()` and the "width of cut" prompt label (FR-006, FR-016; depends on T019, T029, T037)

**Checkpoint**: All three interactive user stories are independently functional.

---

## Phase 6: User Story 4 - Embed Milling Calculations in Another Application (Priority: P1)

**Goal**: Developers can import and call the milling calculations directly as a library, receiving structured results identical to the REPL's, with structured errors and localized messages, without touching the CLI.

**Independent Test**: Call `calculate_end_milling()` / `calculate_face_milling()` from a standalone Python program with valid and invalid inputs, and verify the structured results match the REPL's output for identical inputs and that invalid inputs yield structured errors rather than exceptions.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T039 [P] [US4] Contract test for the milling public API surface in `tests/contract/test_library_api_milling.py`: `calculate_end_milling`, `calculate_face_milling`, `list_end_mill_tools`, `list_face_mill_tools` are importable from `machine_calc`, have the exact signatures in contracts/library-api-milling.md, and return the documented success/error `CalculationResult` shapes (Acceptance Scenarios 1, 2). Additionally assert the FR-014 module boundary statically: no module under `src/machine_calc/operations/milling/` imports from `operations.drilling`, and no module under `operations/drilling/` imports from `operations.milling` — each operation may depend only on the shared top-level modules (FR-014, Constitution VI)
- [X] T040 [P] [US4] Identical-results contract test in `tests/contract/test_identical_results_milling.py`, driving the REPL and the library with the same inputs for both sub-operations and asserting every numeric field matches exactly (FR-012, Acceptance Scenario 3, SC-004)
- [X] T041 [P] [US4] Contract test for localized milling messages in `tests/contract/test_library_api_milling_locale.py`, asserting the `locale` parameter localizes `ErrorInfo.message` and `feasibility_warning`, with English fallback for missing keys (Acceptance Scenario 5)
- [X] T042 [P] [US4] Contract test asserting drilling's `CalculationResult` still has `material_removal_rate is None` and its existing library contract is unchanged, in `tests/contract/test_drilling_result_backward_compatible.py` (research.md #7, SC-005)

### Implementation for User Story 4

- [X] T043 [US4] Re-export `calculate_end_milling`, `calculate_face_milling`, `list_end_mill_tools`, and `list_face_mill_tools` from `src/machine_calc/__init__.py`, adding them to `__all__` and updating the module docstring's public-surface listing to describe the operations available (contracts/library-api-milling.md "Public surface"; depends on T027, T037)
- [X] T044 [US4] Verify and document the `materials_config_path` pass-through for both milling entry points in their docstrings, matching drilling's documented semantics (missing/unreadable file is not an error; malformed file raises `RegistryConfigError`) (FR-015; depends on T027, T037)

**Checkpoint**: The library API is complete and contractually verified; all four user stories are done.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, quality gates, and end-to-end validation across all stories.

- [X] T045 [P] Add end-user milling documentation to `docs/source/` (how to select an operation in the REPL, the end-milling and face-milling input sets, and how to read the material-removal-rate output), per Constitution Principle VII
- [X] T046 [P] Add developer/API-reference milling documentation to `docs/source/` covering `calculate_end_milling()`, `calculate_face_milling()`, the tool registries, and the `operations/milling/` extension points (Constitution VII, VI)
- [X] T047 [P] Update `README.md` to mention milling support alongside drilling in the feature overview and usage example, and update `pyproject.toml`'s `description` and `keywords` to reflect that milling is now supported
- [X] T048 [P] Add a `MACHINE_CALC_LOCALE`-driven static check extension: verify `tests/static/test_no_hardcoded_strings.py` covers the new `cli.py` milling session functions, extending its scanned surface if it enumerates functions explicitly (Constitution VIII)
- [X] T049 [P] Add legacy-hardware performance budget coverage for the two new milling calculations in `tests/performance/`, following the existing `test_calculation_budgets.py` pattern and the 0.5-1.0s per-calculation target (Constitution Principle V)
- [X] T050 Run the full quality gate locally and fix any findings: `pytest` (≥90% coverage), `ruff check src tests`, `black --check src tests`, `mypy src`, `radon`/`xenon` complexity, `bandit -r src`, `pip-audit` (Constitution I, II, IX)
- [X] T051 Run every scenario in `specs/009-milling-calculations/quickstart.md` end to end (Scenarios 1-6), confirming Scenario 6's drilling regression suite passes unchanged (SC-005)
- [X] T052 Bump the package version to the next MINOR (additive public API, no breaking change per Constitution IV) and record the milling additions in the changelog. While doing so, **consolidate the currently duplicated version definition**: `pyproject.toml` declares `version = "0.2.0"` while `src/machine_calc/__init__.py` declares `__version__ = "0.1.0"`, a pre-existing violation of Constitution IV's single-source-of-truth rule. Pick one source (e.g. keep `__version__` in `__init__.py` and set `[project] dynamic = ["version"]` with a `tool.setuptools.dynamic` lookup, or vice versa), and add a test asserting `machine_calc.__version__ == importlib.metadata.version("machine-calc")` so the two can never diverge again

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (needs the new enums and message keys). T013a MUST be completed before T015 begins, since the drilling baseline transcript can only be captured from the un-refactored `cli.py`
- **User Story 2 (Phase 4)**: Depends on Foundational; its CLI task (T028) also depends on US1's dispatcher (T019)
- **User Story 3 (Phase 5)**: Depends on Foundational; its CLI task (T038) also depends on US1's dispatcher (T019) and US2's `_display_result()` extension (T029)
- **User Story 4 (Phase 6)**: Depends on US2's and US3's public entry points (T027, T037)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent after Foundational — the true MVP; delivers operation selection with drilling proven unchanged
- **User Story 2 (P1)**: Its library half (T024-T027) is fully independent of US1; only its CLI half (T028) needs US1's dispatcher
- **User Story 3 (P2)**: Same shape as US2 — library half independent, CLI half needs US1 and T029
- **User Story 4 (P1)**: Thin re-export/verification layer over US2 and US3; cannot start before both entry points exist

### Within Each User Story

- Tests are written FIRST and MUST fail before implementation (exception: T013a is a baseline-capture task, not a test, and MUST run before the code it baselines is touched)
- Bundled data (`tools.toml`) before its registry module
- Registry and formulas before the `calculate_*()` entry point
- Library entry point before its CLI session function

### Parallel Opportunities

- **Phase 1**: T001 and T002 in parallel (T003 follows T001)
- **Phase 2**: T004, T006, T007, T009 in parallel; T010 in parallel with all of them; T005 follows T004 (same file); T008 follows T006; T011, T011a follow T010; T011b and T011d follow T008; T011c is independent of the formula work and can run alongside T011/T011a
- **Phase 3**: T012 and T013 in parallel (two separate test files); T013a runs FIRST (it must capture the pre-refactor baseline before T015 touches `cli.py`), then T014; implementation T015-T019 is sequential (all in `cli.py`)
- **Phase 4**: T020-T023, T023a, T023b in parallel; T024 and T026 in parallel; T025 follows T024; T027 follows T025/T026; T028-T029 sequential (`cli.py`)
- **Phase 5**: T030-T033 in parallel; T034 and T036 in parallel; T035 follows T034; T037 follows T035/T036
- **Phase 6**: T039-T042 in parallel
- **Phase 7**: T045-T049 in parallel; T050-T052 sequential at the end
- **Cross-story**: Once Foundational completes, US2's and US3's library halves can be developed fully in parallel with US1 by different developers

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together (write first, expect failure):
Task: "Unit tests for the EndMillTool registry in tests/unit/operations/milling/end_milling/test_tools_registry.py"
Task: "Unit tests for end-milling formulas in tests/unit/operations/milling/end_milling/test_formulas.py"
Task: "Validation-matrix tests in tests/unit/operations/milling/end_milling/test_calculate.py"
Task: "Integration test for the end-milling REPL flow in tests/integration/test_cli_end_milling.py"

# Then launch the independent implementation pieces together:
Task: "Create bundled end-mill tool data in src/machine_calc/operations/milling/end_milling/data/tools.toml"
Task: "Implement EndMillingMetrics wrapper in src/machine_calc/operations/milling/end_milling/formulas.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Launch the REPL, confirm the operation prompt appears first and drilling is provably unchanged (run the existing drilling suite)
5. Demo: the REPL now supports multiple operations structurally, even before milling calculates anything

### Incremental Delivery

1. Setup + Foundational → shared milling core ready
2. Add User Story 1 → operation selection works, drilling unregressed → **MVP**
3. Add User Story 2 → end milling calculates end to end → demo
4. Add User Story 3 → face milling calculates end to end → demo
5. Add User Story 4 → library surface published and contractually locked
6. Polish → docs, badges, quality gates, version bump

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then:
   - Developer A: User Story 1 (all of `cli.py`'s restructuring)
   - Developer B: User Story 2's library half (T020-T022, T024-T027)
   - Developer C: User Story 3's library half (T030-T032, T034-T037)
3. Developer A hands off the dispatcher (T019); B and C then add their CLI session functions (T028, T038) sequentially to avoid `cli.py` conflicts
4. Any developer picks up User Story 4 once T027 and T037 land

---

## Notes

- [P] tasks = different files, no dependencies
- All of `cli.py`'s tasks (T015-T019, T028, T029, T038) touch the same file and MUST be serialized, even across stories
- Tests are mandatory here (Constitution II), not optional: verify each test fails before implementing
- Every user-facing string must be a message-catalog key (Constitution VIII); `tests/static/test_no_hardcoded_strings.py` enforces this
- Every formula must cite its source in a docstring/comment (Constitution III)
- No existing file under `src/machine_calc/operations/drilling/` may be modified by any task in this plan (FR-002, SC-005)
- Commit after each task or logical group; stop at any checkpoint to validate a story independently

---

## Phase 8: Convergence

**Purpose**: Close gaps found by `/speckit.converge` between the feature's
artifacts and the implemented code. Appended after Phase 7; existing tasks
above are unchanged.

- [X] T053 Replace the formula-derived expectations in `tests/unit/operations/milling/test_shared_formulas_reference.py` with a genuinely external worked example (the widely-reproduced Groover slab-milling problem: 75mm/10-tooth cutter, vc=37.5 m/min, fz=0.15mm, ap=7.5mm, ae=62.5mm) whose expected spindle speed, feed rate and MRR are computed independently of the module under test from that published problem's inputs; the pre-existing formula-derived checks are kept but now clearly labelled as internal self-consistency checks, not published-output checks. Torque/power remain scoped to self-consistency only — no edition/page-cited `kc`/`Uc` value for this example could be confirmed, and the docstring documents that honestly rather than reintroducing a self-computed "published" claim (SC-002, T011a)
- [X] T054 Added `tests/unit/operations/milling/test_bundled_registry_accuracy.py`: end-to-end accuracy tests driving `calculate_end_milling()` and `calculate_face_milling()` with **bundled** material and tool names ("Mild Steel" + "Carbide"), with expected values computed longhand from the same live registry lookups (`get_material`, `get_end_mill_tool`/`get_face_mill_tool`) the entry points use, catching a wrong `cutting_speed_factor` or bundled `reference_cutting_speed`/`specific_cutting_force` per SC-002
- [X] T055 [P] Added `tests/unit/test_models.py` pinning the public `MachiningOperation` and `MillingSubOperation` enums' member names and string values (`"drilling"`, `"milling"`, `"end-milling"`, `"face-milling"`) against data-model.md "New / Changed Shared Enums", including a guard against extra/renamed members
