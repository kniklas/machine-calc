# Tasks: Wood Materials Support

**Input**: Design documents from `/specs/007-wood-materials-support/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/wood-materials-registry-contract.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared documentation and reusable test assets for wood-material implementation.

- [X] T001 Create multi-source wood reference evidence table and median-of-sources normalization notes in specs/007-wood-materials-support/research.md
- [X] T002 Create reusable wood materials config fixtures in tests/fixtures/materials/wood-materials-config.toml
- [X] T003 [P] Create invalid-wood-parameter fixture for FR-008 warning scenarios in tests/fixtures/materials/wood-invalid-params.toml
- [X] T030 [P] Create fixed SC-002 benchmark case set (minimum 12 cases, 2 per built-in wood material) in tests/fixtures/materials/wood-benchmark-cases.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement FR-008 warning-and-continue behavior and shared validation plumbing required by all stories.

**⚠️ CRITICAL**: Complete this phase before user-story implementation.

- [X] T004 Refactor material entry conversion to keep invalid entries registered with warning metadata in src/machine_calc/registry.py
- [X] T005 [P] Implement warning logging for invalid/missing material parameters with source path context in src/machine_calc/registry.py
- [X] T006 [P] Extend raw registry parsing support for warning-oriented validation flow in src/machine_calc/registry_config.py
- [X] T007 Add calculation-time guard for unusable materials that returns a safe user-facing error in src/machine_calc/operations/drilling/__init__.py
- [X] T008 [P] Add translatable unusable-material error message key in src/machine_calc/locales/en.py
- [X] T009 Add unit coverage for FR-008 load-time validation warnings and continue behavior in tests/unit/shared/test_registry.py
- [X] T010 Add CLI integration coverage for warning emission + continued startup with invalid materials config in tests/integration/test_cli_materials_config.py
- [X] T031 Add unit-system metadata assertions (metric/imperial field presence and accepted values) for all built-in wood materials in tests/unit/shared/test_registry.py

**Checkpoint**: Registry initialization warns-and-continues, and calculation path safely rejects unusable entries.

---

## Phase 3: User Story 1 - Add hardwood materials to built-in registry (Priority: P1) 🎯 MVP

**Goal**: Provide default hardwood support (Oak, Maple) out of the box.

**Independent Test**: Fresh install/library call lists Oak and Maple; drilling calculations using each return valid numeric results.

- [X] T011 [P] [US1] Add unit tests for Oak and Maple presence with positive canonical parameters in tests/unit/shared/test_registry.py
- [X] T012 [P] [US1] Add drilling calculation reference-result tests for Oak and Maple using benchmark cases and ±10% tolerance in tests/unit/operations/drilling/test_calculate.py
- [X] T013 [US1] Add Oak and Maple built-in material entries in src/machine_calc/data/materials.toml
- [X] T014 [US1] Update bundled material snapshot expectations for hardwood additions in tests/unit/shared/test_registry.py
- [X] T015 [US1] Add packaging parity assertions for hardwood entries in wheel-bundled data in tests/integration/test_packaging_bundled_data.py

**Checkpoint**: Hardwood materials are bundled, selectable, and calculable end-to-end.

---

## Phase 4: User Story 2 - Add soft wood materials to built-in registry (Priority: P1)

**Goal**: Provide default soft wood support (Pine, Spruce, Fir) with values distinct from hardwoods.

**Independent Test**: Fresh install/library call lists Pine, Spruce, and Fir; drilling calculations using soft wood entries produce valid numeric outputs.

- [X] T016 [P] [US2] Add unit tests for Pine, Spruce, and Fir presence and hardwood-distinct parameter expectations in tests/unit/shared/test_registry.py
- [X] T017 [P] [US2] Add drilling calculation reference-result tests for Pine, Spruce, and Fir using benchmark cases and ±10% tolerance in tests/unit/operations/drilling/test_calculate.py
- [X] T018 [US2] Add Pine, Spruce, and Fir built-in material entries in src/machine_calc/data/materials.toml
- [X] T019 [US2] Add CLI integration coverage for selecting soft wood materials in tests/integration/test_cli_flow.py
- [X] T020 [US2] Extend packaged-data parity assertions for soft wood entries in tests/integration/test_packaging_bundled_data.py

**Checkpoint**: Soft wood materials are bundled, selectable, and validated independently of hardwood flow.

---

## Phase 5: User Story 3 - Include engineered wood materials in built-in registry (Priority: P1)

**Goal**: Include MVP engineered woods (Plywood, MDF) as one entry per type.

**Independent Test**: Fresh install/library call lists Plywood and MDF exactly once each; drilling calculations for both return valid results.

- [X] T021 [P] [US3] Add unit tests asserting single-entry engineered wood types (Plywood, MDF) in tests/unit/shared/test_registry.py
- [X] T022 [P] [US3] Add drilling calculation reference-result tests for Plywood and MDF using benchmark cases and ±10% tolerance in tests/unit/operations/drilling/test_calculate.py
- [X] T023 [US3] Add one Plywood entry and one MDF entry (no variants) in src/machine_calc/data/materials.toml
- [X] T024 [US3] Add contract coverage enforcing single generic engineered entries in tests/contract/test_materials_config_schema.py
- [X] T025 [US3] Add CLI/config integration coverage for engineered wood listing and selection in tests/integration/test_cli_materials_config.py
- [X] T032 [US3] Extend packaged-data parity assertions to explicitly include Plywood and MDF entries in tests/integration/test_packaging_bundled_data.py

**Checkpoint**: Engineered wood support is complete for MVP scope with single-entry-per-type enforcement.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize documentation and full feature validation across all stories.

- [X] T026 [P] Document included hardwood/soft wood/engineered wood set and source authority methodology in README.md
- [X] T027 [P] Add wood-materials feature coverage to published docs index in docs/source/index.rst
- [X] T028 Run and document quickstart validation scenarios for wood materials and FR-008 behavior in specs/007-wood-materials-support/quickstart.md
- [X] T029 Execute and record targeted verification commands for this feature in specs/007-wood-materials-support/tasks.md
- [X] T033 Document per-material parameter citations and median-of-sources derivation summary in specs/007-wood-materials-support/quickstart.md

---

## Verification Log (T029)

- `PYTHONPATH=src pytest --no-cov tests/unit/shared/test_registry.py tests/unit/operations/drilling/test_calculate.py tests/integration/test_cli_materials_config.py tests/integration/test_cli_flow.py tests/contract/test_materials_config_schema.py tests/integration/test_packaging_bundled_data.py -q` ✅ (67 passed)
- `PYTHONPATH=src pytest -q` ✅ (239 passed, 8 skipped, coverage 97.91%)
- `ruff check src tests` ✅
- `PYTHONPATH=src python -m build` ✅

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories
- **Phases 3-5 (US1-US3)**: Depend on Phase 2 completion
- **Phase 6 (Polish)**: Depends on completion of selected user stories

### User Story Dependencies

- **US1**: Starts after Foundational; no dependency on US2/US3
- **US2**: Starts after Foundational; no dependency on US1/US3
- **US3**: Starts after Foundational; no dependency on US1/US2

### Within-Story Ordering

- Tests first, then data/implementation, then integration/packaging checks
- Calculation-path checks follow registry/data updates

---

## Parallel Opportunities

- **Setup**: T003 can run in parallel with T001-T002
- **Foundational**: T005, T006, and T008 can run in parallel after T004 starts
- **US1**: T011 and T012 can run in parallel before T013
- **US2**: T016 and T017 can run in parallel before T018
- **US3**: T021 and T022 can run in parallel before T023
- **Polish**: T026 and T027 can run in parallel

---

## Parallel Example: User Story 1

```bash
Task T011: Add unit tests for Oak and Maple in tests/unit/shared/test_registry.py
Task T012: Add drilling calculation tests for Oak and Maple in tests/unit/operations/drilling/test_calculate.py
```

## Parallel Example: User Story 2

```bash
Task T016: Add soft wood registry tests in tests/unit/shared/test_registry.py
Task T017: Add soft wood calculation tests in tests/unit/operations/drilling/test_calculate.py
```

## Parallel Example: User Story 3

```bash
Task T021: Add engineered-wood uniqueness tests in tests/unit/shared/test_registry.py
Task T022: Add engineered-wood calculation tests in tests/unit/operations/drilling/test_calculate.py
```

---

## Implementation Strategy

### MVP First (US1-centric)

1. Complete Setup (Phase 1)
2. Complete Foundational FR-008 work (Phase 2)
3. Deliver US1 hardwoods (Phase 3)
4. Validate and demo US1 independently

### Incremental Delivery

1. Foundation done once (FR-008 + safe calculation guard)
2. Add US1 (hardwoods) and validate
3. Add US2 (soft woods) and validate
4. Add US3 (engineered woods) and validate
5. Final polish docs + quickstart verification

### Team Parallelization

After Phase 2:
- Dev A: US1 tasks
- Dev B: US2 tasks
- Dev C: US3 tasks
- Dev D: Polish docs/verification prep
