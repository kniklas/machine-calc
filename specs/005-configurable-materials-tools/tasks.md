---

description: "Task list for Configurable Materials & Tools"

---

# Tasks: Configurable Materials & Tools

**Input**: Design documents from `/specs/005-configurable-materials-tools/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/materials-config-schema.md, contracts/library-cli-extensions.md, quickstart.md

**Tests**: Included — the feature spec's plan.md explicitly calls for new unit tests
(`registry_config.py` parse/fallback/duplicate/merge, `units.py` conversions), contract
tests (schema), and integration tests (CLI flag), and the project constitution
(Principle II) mandates unit tests for all calculation-adjacent logic with ≥90% coverage,
plus tolerance-based float comparisons (Principle III) — never `==` on floats.

**Organization**: Tasks are grouped by user story (spec.md P1/P1/P2/P2) to enable
independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Single project (per plan.md "Structure Decision"): `src/machine_calc/`, `tests/` at
repository root — unchanged from `001-metal-drilling-calc`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare package-data plumbing and directories before any registry/tools code changes

- [X] T001 Create `src/machine_calc/data/` and `src/machine_calc/operations/drilling/data/` directories (with `__init__.py` only if needed for packaging; TOML files are non-code package data)
- [X] T002 Add `[tool.setuptools.package-data]` section to `pyproject.toml` declaring `machine_calc/data/*.toml` and `machine_calc/operations/drilling/data/*.toml` so both bundled files ship in wheel/sdist builds (research.md #2)
- [X] T003 [P] Create `tests/contract/`, `tests/integration/`, `tests/unit/shared/`, `tests/unit/operations/drilling/` test file stubs confirmed present (no new dirs needed — verify existing structure per plan.md Project Structure)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core shared infrastructure (bundled data files, message-catalog keys, unit-conversion
helpers, and the kind-agnostic parse/merge module) that every user story's registry/tools/CLI work
depends on. No user story implementation may begin until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Author bundled `src/machine_calc/data/materials.toml` as a lossless re-encoding of today's hard-coded `_MATERIALS` in `src/machine_calc/registry.py` (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium), each entry declaring `unit_system = "metric"` per `contracts/materials-config-schema.md`
- [X] T005 [P] Author bundled `src/machine_calc/operations/drilling/data/tools.toml` as a lossless re-encoding of today's hard-coded tool registry in `src/machine_calc/operations/drilling/tools.py` (HSS, Cobalt, Carbide), each entry declaring `unit_system = "metric"` per `contracts/materials-config-schema.md`
- [X] T006 [P] Add new message-catalog keys to `src/machine_calc/locales/en.py`: `notice.materials_config.not_found`, `error.materials_config.malformed`, `error.materials_config.duplicate_entry`, `error.materials_config.invalid_entry` (Constitution Principle VIII; research.md #6)
- [X] T007 [P] Add `ft_min_to_m_min`/`m_min_to_ft_min` and `psi_to_n_per_mm2`/`n_per_mm2_to_psi` conversion helpers to `src/machine_calc/units.py`, with cited conversion constants in docstrings (research.md #5; Constitution Principle III)
- [X] T008 [P] Unit tests for the four new conversion helpers in `tests/unit/shared/test_units.py`: nominal round-trip values, boundary (zero/near-zero positive), and known reference conversions, all asserted with `math.isclose` (never `==`) per Constitution Principle III
- [X] T009 Create `src/machine_calc/registry_config.py` with `RegistryConfigError` (message_key + kwargs, data-model.md) and the kind-agnostic `RawRegistryEntry`-producing parse function (TOML → list of raw entry dicts with `name`/`fields`/`unit_system`/`translations`), depends on T006
- [X] T010 Implement duplicate-name detection within a single parsed file's entry list in `src/machine_calc/registry_config.py`, raising `RegistryConfigError` with `error.materials_config.duplicate_entry` (FR-016), depends on T009
- [X] T011 Implement the per-name merge algorithm (bundled + optional user entries) in `src/machine_calc/registry_config.py`: wholesale override of `fields`/`unit_system` plus per-locale `translations` merge, append-if-new-name, `None`/missing/unreadable-path → bundled-only + `notice.materials_config.not_found` (data-model.md "Merge Algorithm"; FR-003, FR-004, FR-005, FR-015), depends on T010
- [X] T012 Implement top-level `load_and_merge(bundled_resource, user_path, kind)` entry point in `src/machine_calc/registry_config.py` reading the bundled resource via `importlib.resources.files()`, wrapping parse/duplicate-check/merge, and wrapped with `functools.lru_cache` keyed on `(bundled_resource, user_path)` (research.md #2, #9), depends on T011
- [X] T013 [P] Unit tests for `registry_config.py` in `tests/unit/shared/test_registry_config.py`: valid parse, malformed TOML → `RegistryConfigError` (malformed), missing/unreadable user path → bundled-only + notice key, duplicate name within user file → `RegistryConfigError` (duplicate_entry), override-by-name (scalar fields + unit_system replaced), append-new-name, per-locale translation merge (user wins per-locale, other bundled locales preserved), depends on T012
- [X] T014 [P] Contract test for the configuration schema in `tests/contract/test_materials_config_schema.py`: validates every rule in `contracts/materials-config-schema.md` (required fields, positivity after conversion, `unit_system` value restriction, duplicate-within-file rejection, malformed-file rejection, missing-path notice-not-error), depends on T012

**Checkpoint**: Foundation ready — `registry_config.py`, bundled TOML files, conversion
helpers, and message-catalog keys all exist and are tested; user story implementation
can now begin.

---

## Phase 3: User Story 1 - Built-in materials and tools work out of the box (Priority: P1) 🎯 MVP

**Goal**: Externalize today's hard-coded materials/tools into the bundled TOML files with zero
observable change in behavior, listings, or calculation results when no user config is supplied.

**Independent Test**: Run the CLI/library with no extra configuration; confirm `list_materials()`/
`list_tools()` return exactly the pre-feature built-in names, and a sample calculation (e.g. Mild
Steel + HSS, diameter 10mm, depth 30mm) produces identical numeric results to the current release.

### Tests for User Story 1

- [X] T015 [P] [US1] Extend `tests/unit/shared/test_registry.py` with regression assertions that `list_materials()`/`get_material()` (no `config_path`) return the same six materials with the same reference values as before this feature, using `math.isclose` for numeric comparisons (never `==`)
- [X] T016 [P] [US1] Extend `tests/unit/operations/drilling/test_tools_registry.py` (new file, mirrors `test_registry.py` structure) with regression assertions that `list_tools()`/`get_tool()` (no `config_path`) return the same three tools with the same factors as before this feature
- [X] T017 [P] [US1] Packaging test in `tests/integration/test_packaging_bundled_data.py` asserting a built wheel contains `machine_calc/data/materials.toml` and `machine_calc/operations/drilling/data/tools.toml` (quickstart.md Scenario 2), invoking `python -m build` and inspecting the wheel's namelist

### Implementation for User Story 1

- [X] T018 [US1] Extend `WorkpieceMaterial` dataclass in `src/machine_calc/registry.py` with `unit_system: str = "metric"` and `translations: dict[str, str]` fields plus a `display_name(locale)` method (data-model.md), depends on T009
- [X] T019 [US1] Rebuild `MATERIAL_REGISTRY` construction in `src/machine_calc/registry.py` to call `registry_config.load_and_merge(...)` against `src/machine_calc/data/materials.toml`, convert imperial-declared fields to canonical metric via `units.py` helpers (T007), validate positivity, and construct `WorkpieceMaterial` instances, depends on T004, T007, T012, T018
- [X] T020 [US1] Add optional `config_path: str | None = None` trailing parameter to `list_materials()` and `get_material()` in `src/machine_calc/registry.py`, defaulting to bundled-only behavior identical to today (FR-014), depends on T019
- [X] T021 [US1] [P] Extend `DrillingTool` dataclass in `src/machine_calc/operations/drilling/tools.py` with `unit_system: str = "metric"` and `translations: dict[str, str]` fields plus a `display_name(locale)` method, depends on T009
- [X] T022 [US1] Rebuild `TOOL_REGISTRY` construction in `src/machine_calc/operations/drilling/tools.py` to call `registry_config.load_and_merge(...)` against `src/machine_calc/operations/drilling/data/tools.toml`, validate positivity (no unit conversion — factors are dimensionless per research.md #5), and construct `DrillingTool` instances, depends on T005, T012, T021
- [X] T023 [US1] Add optional `config_path: str | None = None` trailing parameter to `list_tools()` and `get_tool()` in `src/machine_calc/operations/drilling/tools.py`, defaulting to bundled-only behavior identical to today (FR-014), depends on T022
- [X] T024 [US1] Run full existing regression suite (`tests/unit`, `tests/integration`, `tests/contract`) to confirm zero-config behavior is byte-for-byte identical to pre-feature release (SC-002); explicitly include and confirm zero changes/failures in `001-metal-drilling-calc`'s existing `formulas.py` unit tests and `config.py` bounds-config tests, as the dedicated FR-017 (no formula/canonical-model/bounds-config change) verification checkpoint, depends on T020, T023

**Checkpoint**: User Story 1 fully functional and testable independently — bundled TOML
files back the registries with no observable behavior change.

---

## Phase 4: User Story 2 - Add or override materials/tools via a user-supplied file (Priority: P1)

**Goal**: Let a user supply a `--materials-config PATH` file that adds new materials/tools or
overrides built-in ones, without editing the installed package.

**Independent Test**: Supply a user file adding one new material and overriding one built-in
tool's factors; confirm the new material is listed/usable, the overridden tool's factors take
effect in calculation results, and all other built-in entries are unchanged; confirm omitting the
flag reproduces User Story 1 exactly.

### Tests for User Story 2

- [X] T025 [P] [US2] Contract test in `tests/contract/test_library_cli_extensions.py` asserting `calculate()`, `list_materials()`, `list_tools()`, `get_material()`, `get_tool()` gain the new optional parameters described in `contracts/library-cli-extensions.md` without breaking any existing call signature
- [X] T026 [P] [US2] Extend `tests/unit/shared/test_registry.py` with override/append tests: a `tmp_path`-supplied config file overriding a built-in material's values takes effect, a new-named material is appended, and unaffected built-ins are untouched (Acceptance Scenarios 1-3), using `math.isclose` for numeric assertions
- [X] T027 [P] [US2] Extend `tests/unit/operations/drilling/test_tools_registry.py` with equivalent override/append tests for tools
- [X] T028 [P] [US2] Integration test in `tests/integration/test_cli_materials_config.py` covering the CLI `--materials-config` flag's four paths: absent (US1 parity), missing/unreadable path → non-fatal translated notice + REPL proceeds with bundled defaults (quickstart.md Scenario 7), malformed file → translated error + exit without traceback (quickstart.md Scenario 6), valid override/addition file → REPL lists the new/overridden entries (quickstart.md Scenario 3)
- [X] T029 [P] [US2] Integration test in `tests/integration/test_cli_materials_config.py` (or a dedicated file) for the duplicate-name-within-file rejection path (quickstart.md Scenario 6, dup.toml) asserting the translated `error.materials_config.duplicate_entry` message and that neither conflicting entry is applied

### Implementation for User Story 2

- [X] T030 [US2] Add `config_path: str | None = None` threading confirmed end-to-end in `src/machine_calc/registry.py`'s `list_materials()`/`get_material()` (already added in T020) to accept a caller-supplied override path and pass it to `registry_config.load_and_merge()`, depends on T020
- [X] T031 [US2] Add `config_path: str | None = None` threading confirmed end-to-end in `src/machine_calc/operations/drilling/tools.py`'s `list_tools()`/`get_tool()` (already added in T023) to accept a caller-supplied override path, depends on T023
- [X] T032 [US2] Add optional `materials_config_path: str | None = None` keyword parameter to `calculate()` in `src/machine_calc/operations/drilling/__init__.py`, threaded into its internal `get_material()`/`get_tool()` lookups (FR-002, FR-017 — no formula changes), depends on T030, T031
- [X] T033 [US2] Add `argparse`-based `--materials-config PATH` CLI flag to `src/machine_calc/cli.py` (parsed alongside existing arguments; `__main__.py` remains a pure delegation shim to `cli.main()` and needs no changes), resolved once at startup alongside locale resolution (research.md #3), depends on T032
- [X] T034 [US2] Implement CLI startup handling in `src/machine_calc/cli.py`: catch `RegistryConfigError` once at startup, translate via `machine_calc.i18n.translate`, print, and exit without a raw traceback (fatal path); print the translated `notice.materials_config.not_found` once (non-fatal path) and proceed with bundled defaults (contracts/library-cli-extensions.md "Startup sequence"); wire the resolved `--materials-config` path through `run()` so it is forwarded as `config_path`/`materials_config_path` to every call site that lists or uses materials/tools within the REPL loop — `list_materials()`, `list_tools()`, and the `calculate()` invocation — not just parsed and discarded, depends on T033

**Checkpoint**: User Stories 1 AND 2 both work independently — users can add/override
materials and tools via `--materials-config` with correct error/notice handling.

---

## Phase 5: User Story 3 - Material/tool names are translatable (Priority: P2)

**Goal**: Display translated material/tool names in the CLI when available for the active locale,
falling back to the English name otherwise, mirroring the existing i18n fallback rule.

**Independent Test**: Define a material with an English name and one additional-language name;
run the CLI with the locale env var set to that language and confirm the translated name appears;
run again with an unsupported/missing locale and confirm the English name appears.

### Tests for User Story 3

- [X] T035 [P] [US3] Unit tests for `display_name(locale)` on both `WorkpieceMaterial` (`tests/unit/shared/test_registry.py`) and `DrillingTool` (`tests/unit/operations/drilling/test_tools_registry.py`): translation-present case, translation-absent-for-locale fallback case, no-translations-at-all fallback case (Acceptance Scenarios 1-3)
- [X] T036 [P] [US3] Integration test in `tests/integration/test_cli_materials_config.py` (or a new `tests/integration/test_cli_translated_names.py`) reproducing quickstart.md Scenario 4: `MACHINE_CALC_LOCALE=fr` shows the translated name, `MACHINE_CALC_LOCALE=xx` (no bundled catalog) still falls back to English via the data-driven `display_name` lookup independent of the message catalog

### Implementation for User Story 3

- [X] T037 [US3] Confirm/extend `translations` merge behavior in `src/machine_calc/registry_config.py`'s merge step (already implemented in T011) with an explicit per-entry test for the "built-in has French, override adds German, override does not touch French" case (Edge Cases; FR-015), depends on T011
- [X] T038 [US3] Change the material-selection prompt in `src/machine_calc/cli.py` to the "label dict / reverse-lookup dict" pattern already used for `_prompt_mode`: display `material.display_name(locale)`, resolve the user's selection back to the canonical English `name` before calling `calculate()` (research.md #7), depends on T018, T034
- [X] T039 [US3] Change the tool-selection prompt in `src/machine_calc/cli.py` to the same label/reverse-lookup pattern for `DrillingTool.display_name(locale)`, depends on T021, T034

**Checkpoint**: User Stories 1, 2, AND 3 all work independently — translated names are
shown with correct English fallback.

---

## Phase 6: User Story 4 - Each material/tool declares its unit system (Priority: P2)

**Goal**: Let a material/tool entry declare `unit_system = "imperial"` so its reference values are
converted to canonical metric at load time, and expose the declared unit system for display.

**Independent Test**: Define a new material with imperial-declared reference values; confirm a
calculation using it matches (within tolerance) the equivalent metric-authored entry, in both
metric and imperial CLI output modes.

### Tests for User Story 4

- [X] T040 [P] [US4] Unit test in `tests/unit/shared/test_registry.py` asserting an imperial-declared material (`unit_system = "imperial"`, ft/min + in/rev + psi values) converts to the same canonical metric fields (within `math.isclose` tolerance) as an equivalent metric-authored entry (quickstart.md Scenario 5 values: 250 ft/min ≈ 76.2 m/min, 0.008 in/rev ≈ 0.2032 mm/rev, 130000 psi ≈ 896.3 N/mm²)
- [X] T041 [P] [US4] Unit test in `tests/unit/operations/drilling/test_tools_registry.py` asserting a tool entry declaring `unit_system = "imperial"` is accepted, stored, and displayed but performs no numeric conversion on `cutting_speed_factor`/`feed_factor` (documented no-op, research.md #5)
- [X] T042 [P] [US4] Integration test in `tests/integration/test_cli_materials_config.py` reproducing quickstart.md Scenario 5 end-to-end: a calculation using the imperial-declared material matches the metric-authored equivalent in both `metric` and `imperial` CLI unit-system modes

### Implementation for User Story 4

- [X] T043 [US4] Confirm/extend the imperial→metric conversion wiring in `src/machine_calc/registry.py`'s `MATERIAL_REGISTRY` construction (implemented in T019) explicitly applies `ft_min_to_m_min`, `mm_to_in`/`in_to_mm`-equivalent reuse, and `psi_to_n_per_mm2` per-field based on each entry's declared `unit_system` (FR-012), depends on T007, T019
- [X] T044 [US4] Expose `unit_system` on `WorkpieceMaterial`/`DrillingTool` listings so the CLI can display the declared unit system alongside each entry's name (FR-013) — add a `--verbose`-free minimal display hook or extend existing listing output in `src/machine_calc/cli.py`, depends on T018, T021, T043

**Checkpoint**: All four user stories independently functional — imperial-declared
entries convert correctly and their unit system is visible.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Coverage verification, documentation, and end-to-end validation across all stories

- [X] T045 [P] Run `pytest --cov=machine_calc --cov-report=term-missing` and confirm ≥90% line coverage on `registry.py`, `operations/drilling/tools.py`, and the new `registry_config.py` (Constitution Principle II; quickstart.md "Automated coverage")
- [X] T046 [P] Update Sphinx docstrings for all new/changed public functions (`load_and_merge`, `display_name`, `list_materials`/`get_material`/`list_tools`/`get_tool`'s new `config_path` parameter, `calculate`'s new `materials_config_path` parameter) per Constitution Principle VII
- [X] T047 [P] Run mypy, ruff (including complexity check `C90`/`max-complexity = 10`), radon/xenon, bandit, and pip-audit across `src/machine_calc/registry_config.py`, `units.py`, `registry.py`, `operations/drilling/tools.py`, and `cli.py` to confirm the Constitution Principle IX gates pass with no regressions
- [X] T048 Execute all seven quickstart.md scenarios manually end-to-end (built package or editable install) to confirm the CLI's real user-facing behavior matches every documented expectation
- [X] T049 Update `README.md`/user docs (if referencing the fixed built-in material/tool list) to mention the new `--materials-config` flag and the bundled-defaults-plus-user-overrides model

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational completion; builds on the `config_path` parameters added in US1 (T020, T023) — implemented after US1 for a natural build order, but its merge/override logic itself (in `registry_config.py`) was already completed in Phase 2
- **User Story 3 (Phase 5)**: Depends on Foundational completion; builds on `display_name()` (added in US1, T018/T021) and the CLI flag (added in US2, T034)
- **User Story 4 (Phase 6)**: Depends on Foundational completion; builds on the registry construction wiring from US1 (T019) and conversion helpers from Phase 2 (T007)
- **Polish (Phase 7)**: Depends on all four user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — pure re-platforming of existing hard-coded data with no behavior change
- **User Story 2 (P1)**: Reuses US1's `config_path` plumbing (T020, T023) and Phase 2's merge logic (T011); independently testable via the CLI flag once wired
- **User Story 3 (P2)**: Reuses US1's `display_name()` (T018, T021) and US2's CLI flag/startup handling (T033, T034); independently testable via locale env var
- **User Story 4 (P2)**: Reuses Phase 2's conversion helpers (T007) and US1's registry construction (T019); independently testable via an imperial-declared entry, no dependency on US2/US3

### Within Each User Story

- Tests (contract/unit/integration) written before/alongside implementation, per Constitution Principle II
- Dataclass/model extensions before registry-construction rewiring
- Registry-construction rewiring before public-API parameter additions
- Public-API parameter additions before CLI wiring
- Story complete and its checkpoint validated before moving to the next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- T004, T005, T006, T007 (Phase 2) can run in parallel — different files
- T008 (unit conversion tests) can run in parallel with T009-T012 (parse/merge implementation) since they target different files, but T008 should be written first per TDD and will fail until T007 lands
- T013, T014 (Phase 2 tests) can run in parallel with each other once T012 lands
- T015, T016, T017 (US1 tests) can run in parallel
- T018 and T021 (dataclass extensions for materials vs. tools) can run in parallel — different files
- T025, T026, T027, T028, T029 (US2 tests) can run in parallel
- T035, T036 (US3 tests) can run in parallel
- T040, T041, T042 (US4 tests) can run in parallel
- T045, T046, T047 (Polish) can run in parallel

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch bundled-data authoring and message-catalog/units work together:
Task: "Author bundled src/machine_calc/data/materials.toml (lossless re-encoding of _MATERIALS)"
Task: "Author bundled src/machine_calc/operations/drilling/data/tools.toml (lossless re-encoding of tool registry)"
Task: "Add materials-config message-catalog keys to src/machine_calc/locales/en.py"
Task: "Add ft_min_to_m_min/m_min_to_ft_min and psi_to_n_per_mm2/n_per_mm2_to_psi to src/machine_calc/units.py"
```

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Extend tests/unit/shared/test_registry.py with zero-config regression assertions"
Task: "Extend tests/unit/operations/drilling/test_tools_registry.py with zero-config regression assertions"
Task: "Packaging test in tests/integration/test_packaging_bundled_data.py"

# Launch the two dataclass extensions together:
Task: "Extend WorkpieceMaterial in src/machine_calc/registry.py"
Task: "Extend DrillingTool in src/machine_calc/operations/drilling/tools.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories; includes the shared
   `registry_config.py` merge logic, bundled TOML files, and conversion helpers)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Confirm zero-config CLI/library behavior is byte-for-byte
   identical to the pre-feature release (SC-002)
5. Deploy/demo if ready — this alone re-platforms the hard-coded registries with no
   user-visible change, satisfying the non-negotiable backward-compatibility baseline

### Incremental Delivery

1. Complete Setup + Foundational → shared merge/conversion infrastructure ready
2. Add User Story 1 → validate zero-config parity → deploy/demo (MVP!)
3. Add User Story 2 → validate `--materials-config` add/override/notice/error paths → deploy/demo
4. Add User Story 3 → validate translated-name display with English fallback → deploy/demo
5. Add User Story 4 → validate imperial-declared entry conversion → deploy/demo
6. Each story adds value without breaking previous stories (FR-014, FR-017)

### Parallel Team Strategy

With multiple developers, after Setup + Foundational are complete:

- Developer A: User Story 1 (registry/tools re-platforming)
- Developer B: prepares User Story 2's CLI flag scaffolding in parallel (can start once
  US1's `config_path` parameters land, T020/T023)
- Developer C: User Story 4 (unit-system conversion wiring) — independent of US2/US3,
  only needs Phase 2's conversion helpers (T007) and US1's registry construction (T019)
- User Story 3 is best sequenced after US2 lands (needs the CLI flag/startup handling,
  T033/T034) even though its own display logic is independent

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Every calculation-adjacent unit test (conversions, merge logic, registry construction)
  MUST use `math.isclose` (or equivalent explicit tolerance) for float comparisons —
  never `==` — per Constitution Principle III
- Coverage on `registry_config.py`, `registry.py`, and `operations/drilling/tools.py`
  MUST reach ≥90% line coverage per Constitution Principle II; verify with T045 before
  considering the feature complete
- `formulas.py` and the existing bounds-configuration mechanism (`config.py`) are
  explicitly out of scope (FR-017) — no task in this list touches either file's logic
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
