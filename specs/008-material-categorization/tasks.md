# Tasks: Material Categorization System

**Branch**: `008-material-categorization`
**Date**: 2026-08-18
**Input**: Design documents from `/specs/008-material-categorization/`
**Status**: Complete — all in-scope tasks delivered. Revised post-implementation; see [Task list revision](#task-list-revision-2026-08-18).

---

## Functional Requirement Coverage Map

| FR | Requirement | Task IDs | Status |
|----|-------------|----------|--------|
| **FR-001** | Prompt for material type before material | T004, T008, T009, T012, T013 | ✓ Delivered |
| **FR-002** | Offer only materials of the selected type | T005, T009, T013 | ✓ Delivered |
| **FR-003** | Remember selected type as next default | T009, T013 | ✓ Delivered |
| **FR-004** | Add new types without code change | T001, T002, T005, T008, T011, T013 | ✓ Delivered |
| **FR-005** | Assign materials to types via config | T001, T003, T011, T013 | ✓ Delivered |
| **FR-006** | Expose registered type set | T005, T011 | ✓ Delivered |
| **FR-006a** | Type identifiers compared as exact strings | T003, T005, T011 | ✓ Delivered |
| **FR-007** | Material names unique across merged set | (inherited from feature 005; unchanged) | ✓ Pre-existing |
| **FR-008** | Reject material outside the selected type | T009, T013 | ✓ Delivered |
| **FR-009** | *(Reserved — moot; no write API exists)* | — | ⚠ Out of scope |
| **FR-010** | Configurable type display order | T005, T011 | ✓ Delivered |
| **FR-011** | Degrade gracefully on missing/invalid type | T003, T006, T007, T011 | ✓ Delivered |
| **FR-012** | Type labels via message catalog | T008, T010, T013 | ✓ Delivered |

**Coverage**: 12/12 in-scope FRs delivered. FR-009 is out of scope — there is no write API, so
concurrent-edit conflict resolution does not apply.

---

## Implementation Strategy

The feature extends the existing registry rather than adding a subsystem, so it is a short,
mostly sequential list. Ordering is bottom-up — data, then registry, then CLI, then docs — because
each layer's tests exercise the layer below.

- **Phase 1**: Data — categorize the bundled catalog
- **Phase 2**: Registry — type field, validation, listing, filtering, sticky merge
- **Phase 3**: CLI — the two-step prompt (User Stories 1, 2, 4)
- **Phase 4**: Test suite
- **Phase 5**: Documentation and quality gates

---

## Phase 1: Data

- [X] **T001** Add `material_type` to all 13 bundled entries in `src/machine_calc/data/materials.toml`
      (`metal`: Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium; `wood`: Oak,
      Maple, Pine, Spruce, Fir, Plywood, MDF) — *FR-004, FR-005*
- [X] **T002** Document the free-form, extensible semantics of the key in a header comment,
      cross-referencing the 005 config schema contract — *FR-004*

## Phase 2: Registry

- [X] **T003** Add `material_type: str` to the `WorkpieceMaterial` dataclass and a
      `DEFAULT_MATERIAL_TYPE = "uncategorized"` constant in `src/machine_calc/registry.py`
      — *FR-005, FR-006a, FR-011*
- [X] **T004** Add `_parse_material_type()` applying warn-and-continue validation: a non-string or
      empty value records a validation issue and falls back to the default rather than raising
      — *FR-001, FR-011*
- [X] **T005** Add `list_material_types(config_path=None)`, deriving the ordered, deduplicated type
      list from the material set via `dict.fromkeys(...)` so order follows TOML authoring order
      — *FR-002, FR-004, FR-006, FR-006a, FR-010*
- [X] **T006** Add an optional `material_type` filter argument to `list_materials()`, preserving the
      pre-008 signature and behavior when it is omitted — *FR-002, FR-011*
- [X] **T007** Add a generic `sticky_fields: tuple[str, ...]` parameter to `merge_entries()` and the
      `load_and_merge()` call chain in `src/machine_calc/registry_config.py`, keeping that module
      kind-agnostic, and pass `_STICKY_FIELDS = ("material_type",)` from `registry.py`, so a
      pre-008 user override does not decategorize a bundled material — *FR-011*
- [X] **T011** Export `list_material_types` from `src/machine_calc/__init__.py` — *FR-004, FR-005, FR-006, FR-006a, FR-010, FR-011*

## Phase 3: CLI (User Stories 1, 2, 4)

- [X] **T008** Add `_material_type_label()` in `src/machine_calc/cli.py`, resolving `material_type.<id>`
      from the catalog and falling back to a title-cased label for identifiers with no entry
      — *FR-001, FR-004, FR-012*
- [X] **T009** Add `_prompt_material_type_choice()` and make `run()` prompt for type, then call
      `list_materials(material_type=...)` and prompt for a material scoped to that type; a
      remembered material from another type is not offered as a default — *FR-001, FR-002, FR-003, FR-008*
- [X] **T010** Add `cli.label.material_type` and `material_type.{metal,wood,uncategorized}` to
      `src/machine_calc/locales/en.py`, leaving unknown identifiers deliberately absent so they
      reach the title-case fallback — *FR-012*

## Phase 4: Tests

- [X] **T012** Add `tests/unit/shared/test_registry_material_types.py` — 30 tests covering bundled
      categorization, filtering, derived type ordering, pre-008 signature preservation,
      data-driven new categories, sticky-field backward compatibility, and invalid-type
      warn-and-continue — *FR-001, FR-004*
- [X] **T013** Add `tests/integration/test_cli_material_types.py` — 18 tests covering the two-step
      flow, type-scoped material lists, cross-category default rejection, invalid-type reprompt,
      loop-rerun defaults, data-driven category labels including the title-case fallback, and
      uncategorized reachability — *FR-001 – FR-006, FR-008, FR-010, FR-012*
- [X] **T014** Update the ~30 pre-existing CLI integration tests to answer the new prompt
      (`test_cli_flow.py`, `test_cli_edge_cases.py`, `test_cli_fixed_rpm.py`, `test_cli_loop.py`,
      `test_cli_power_constrained.py`, `test_cli_validation.py`, `test_cli_mode_prompt_ux.py`,
      `test_cli_materials_config.py`, `test_identical_results_modes.py`, `test_locale_env.py`,
      `test_main_entrypoint.py`)
- [X] **T015** Remove the dead "clear stale material on type switch" reset after proving its test
      still passed with the logic removed, and rewrite that test to be non-vacuous by feeding a
      blank material answer and asserting the reprompt

## Phase 5: Documentation & Quality Gates

- [X] **T016** Document the two-step flow, the `material_type` key, the title-case label fallback,
      and sticky-merge behavior in `README.md`
- [X] **T017** Document the `material_type` key, its validation rule, and the sticky-merge rule in
      `specs/005-configurable-materials-tools/contracts/materials-config-schema.md`
- [X] **T018** Reference material categorization from `docs/source/index.rst` (Sphinx builds with `-W`)
- [X] **T019** Revise `spec.md`, `plan.md`, and this file to describe the delivered architecture
- [X] **T020** Verify quality gates: `ruff` ✓, `black` ✓, `mypy` ✓, `bandit` ✓, Maintainability Index
      rank A ✓, Sphinx `-W` ✓, pytest 291 passed / 8 skipped at 98.30% coverage ✓ (`registry.py` 100%)

---

## Out of scope

- **User Story 3 — Admin Material Management (CRUD).** Dropped. Adding a material or a material
  type is done by editing `materials.toml` or a `--materials-config` file, which already satisfies
  FR-004 and FR-005. A CRUD API would be a redundant second mechanism for the same outcome. See
  the User Story 3 section of `spec.md`.
- **FR-009 — concurrent-edit conflict resolution.** Moot: there is no write API. Configuration
  files are managed by the user's own editor and version control.

---

## Task list revision 2026-08-18

The original list contained 83 tasks across 7 phases for a `src/machine_calc/materials/` package
with pydantic domain entities, a JSON repository, a `MaterialRegistry` service, admin CRUD, and a
second i18n mechanism. That implementation was built, rejected in review, and deleted in full — it
duplicated the existing registry, added an undeclared heavy dependency, and was never wired into
the CLI, so it delivered no user-visible behavior.

This list records the work actually delivered against the existing registry. The task count fell
from 83 to 20 because the delivered design reuses the TOML loading, merging, caching, validation,
i18n, and prompting machinery that the rejected design would have reimplemented.
