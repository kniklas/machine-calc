# Implementation Plan: Material Categorization System

**Branch**: `008-material-categorization` | **Date**: 2026-08-18 | **Spec**: [specs/008-material-categorization/spec.md](spec.md)

**Input**: Feature specification from `/specs/008-material-categorization/spec.md` with 5 clarifications resolved

**Status**: Implemented. This plan was revised after implementation — see [Plan revision](#plan-revision-2026-08-18).

## Summary

Group the existing workpiece materials into material types (`metal`, `wood`) and make the
interactive CLI ask for the type before the specific material, so the material prompt stays
short as the catalog grows. New types (cement, plastic, …) must be addable with no code change.

The feature is delivered by **extending the existing registry**, not by adding a new subsystem:
a single optional `material_type` key on each `[[materials]]` TOML entry, a filter and a
type-listing function on the registry, and one extra CLI prompt.

## Technical Context

**Language/Version**: Python >= 3.9 (`requires-python` in `pyproject.toml`; ruff/black `target-version = py39`)

**Primary Dependencies**: none added. The only runtime dependency remains `tomli`, and only on
Python < 3.11. No pydantic, no ORM, no third-party validation library.

**Storage**: TOML, loaded via `importlib.resources` — the convention already used for materials
and drilling tools. Bundled catalog: `src/machine_calc/data/materials.toml`. User overrides and
additions: an optional file passed via `--materials-config`. No database, no JSON registry, no
write path.

**Testing**: `pytest`. Unit tests under `tests/unit/shared/`, CLI tests under `tests/integration/`.
Coverage gate `--cov-fail-under=90`.

**Target Platform**: cross-platform CLI + library.

**Project Type**: extension of the existing `machine_calc` library.

**Performance Goals**: material types are derived from the already-loaded material registry, so
the feature adds no I/O and no measurable startup cost. The registry snapshot is memoized with
`functools.cache`, as before.

**Constraints**:
- Resource-constrained hardware (Principle V): no new dependency, no new data file, no extra load.
- Extensibility (Principle VI): a new type must require zero code change.
- Backward compatibility: user config files written before this feature must keep working.

**Scale/Scope**: 13 bundled materials across 2 types; a handful of user-added materials and types
is the realistic upper bound for a single-user CLI.

## Constitution Check

### Gate status

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **I. Code Quality** | Readable, single-responsibility modules; documented public functions; lint/type gates | ✅ Pass | `ruff`, `black`, `mypy` clean; Maintainability Index rank A. `registry_config.py` stays kind-agnostic via a generic `sticky_fields` parameter rather than a materials-specific hack. |
| **II. Testing Standards** | Unit tests for all logic, ≥90% coverage, CI | ✅ Pass | 48 new tests (30 registry, 18 CLI); suite at 291 passed / 8 skipped, 98.30% total coverage, `registry.py` at 100%. |
| **III. Calculation Robustness** | Input validation, clear errors, edge cases | ✅ Pass | Invalid/missing `material_type` follows the module's established warn-and-continue policy: a validation issue is recorded, the material stays usable, and it falls back to `uncategorized`. Invalid prompt input is re-prompted with valid options. |
| **IV. Python Packaging** | `pyproject.toml`, PEP 257 docstrings, PEP 8 naming | ✅ Pass | No packaging change needed — `material_type` rides inside the already-shipped `data/*.toml`. New public functions carry PEP 257 docstrings. |
| **V. Resource Constraints** | <128 MB RAM, legacy hardware, single-threaded | ✅ Pass | Zero new dependencies and zero new files; types are derived in-memory from the existing registry. |
| **VI. Extensibility by Design** | Modular, stable interfaces, no special-casing | ✅ Pass | `material_type` is a free-form string, **not** an enum, so `metal` and `wood` receive no special handling and a new type needs no code. Type labels fall back to title-case, so even the prompt text needs no code for a new type. |
| **VII. Documentation & Publishing** | README, Sphinx docs | ✅ Pass | README documents the two-step flow and the `material_type` key; `docs/source/index.rst` links this feature; the 005 config schema contract documents the key and the sticky-merge rule. |
| **VIII. i18n of User-Facing Strings** | User text translatable; logs in English | ✅ Pass | `cli.label.material_type` and `material_type.*` live in `src/machine_calc/locales/en.py`. Validation warnings remain English log output. |

**✅ GATE PASSED** — no constitutional blockers.

## Project Structure

### Documentation (this feature)

```text
specs/008-material-categorization/
├── spec.md              # Feature specification (revised post-implementation)
├── plan.md              # This file
├── research.md          # Design decisions and rationale
├── data-model.md        # Entity/field definitions and validation
├── quickstart.md        # Runnable validation scenarios
├── contracts/
│   └── material-selection.md   # Public API surface
├── checklists/
│   └── requirements.md
└── tasks.md             # Implementation tasks
```

### Source code (repository root)

No new package is created. The feature touches five existing files:

```text
src/machine_calc/
├── data/materials.toml     # + material_type on all 13 bundled entries
├── registry_config.py      # + generic `sticky_fields` merge parameter (kind-agnostic)
├── registry.py             # + material_type field, DEFAULT_MATERIAL_TYPE, _STICKY_FIELDS,
│                           #   _parse_material_type(), list_material_types(),
│                           #   material_type filter on list_materials()
├── cli.py                  # + _material_type_label(), _prompt_material_type_choice(),
│                           #   two-step prompt in run()
├── locales/en.py           # + cli.label.material_type, material_type.{metal,wood,uncategorized}
└── __init__.py             # + list_material_types export

tests/
├── unit/shared/test_registry_material_types.py    # 30 tests (new)
├── integration/test_cli_material_types.py         # 18 tests (new)
└── integration/test_cli_*.py                      # ~30 existing tests updated for the new prompt
```

## Design decisions

1. **`material_type` is a free-form string, not an enum.** Declaring an unused value in TOML
   registers a new category immediately. An enum would have made "add a type" a code change,
   directly contradicting FR-004.
2. **Types are derived, not stored.** `list_material_types()` builds the list from the material
   set with `dict.fromkeys(...)`, which both deduplicates and preserves first-appearance order.
   This gives FR-010's configurable order for free (author order in TOML) and makes an empty
   type structurally impossible.
3. **`DEFAULT_MATERIAL_TYPE = "uncategorized"`** for entries omitting the key, so pre-008
   configuration files still load.
4. **Sticky-field merge.** A user entry that overrides a bundled material but omits
   `material_type` inherits the bundled value. Without this, any pre-008 override of e.g.
   "Mild Steel" would silently move it to *Uncategorized* — a real regression. Implemented as a
   generic `sticky_fields: tuple[str, ...]` parameter so `registry_config.py`, which is shared
   with drilling tools, stays kind-agnostic; `registry.py` supplies `("material_type",)`.
5. **Warn-and-continue validation** for an invalid type, matching how the module already treats
   invalid numerics, instead of raising and making one bad entry fatal.
6. **Title-case label fallback.** `machine_calc.i18n.translate()` returns the key verbatim when
   missing, which is used to detect an absent catalog entry and render `composite-fibre` as
   `Composite Fibre` — keeping "new type, no code change" true for the prompt text too.
7. **No explicit reset on type switch.** `_prompt_material_choice` already resolves a default
   against the option list it is handed, so a remembered material from another type is simply not
   offered. An explicit reset was written, proven dead (its test passed with the logic removed),
   and deleted.

## Plan revision 2026-08-18

The original plan specified a new `src/machine_calc/materials/` package with domain/service/
repository layers, pydantic models, a JSON-file repository, a `MaterialRegistry` service, an
admin CRUD API, a second i18n mechanism, and Python 3.11+.

That design was built and then rejected during review because it violated the constitution and
misread the project: it duplicated the existing material registry (Principle VI), introduced an
undeclared `pydantic` dependency that is heavy for the hardware targets (Principles IV and V),
added a second i18n mechanism alongside `machine_calc.i18n` (Principle VIII), used JSON against
the project's TOML convention, invented materials that are not in the catalog, targeted the wrong
Python version, and — decisively — was never wired into the CLI or `calculate()`, so it produced
no user-visible behavior at all.

It was deleted in full and replaced with the design above. User Story 3 (admin CRUD) was dropped
in the process: editing a TOML file already adds materials and types, so a write API would be a
redundant second mechanism. See the User Story 3 section of `spec.md` for the rationale.

## References

- **Feature Specification**: [spec.md](spec.md)
- **Config file schema**: [specs/005-configurable-materials-tools/contracts/materials-config-schema.md](../005-configurable-materials-tools/contracts/materials-config-schema.md)
- **Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md)
