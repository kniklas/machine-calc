# Implementation Plan: Milling Calculations Module

**Branch**: `009-milling-calculations` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-milling-calculations/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Adds two new machining operations — end milling and face milling — to the
existing `machine_calc` Python library and CLI, each exposed as (1) a
dependency-light callable library function (`calculate_end_milling()`,
`calculate_face_milling()`) and (2) new interactive REPL sub-flows, both
producing identical results for identical inputs (mirroring the existing
drilling contract). The REPL now first asks the user to choose a machining
operation (drilling or milling) before any operation-specific prompts, and
milling further asks the user to choose end milling or face milling. Both
milling sub-operations reuse the existing shared `WorkpieceMaterial`
registry (including its `specific_cutting_force_kc` field), unit system,
configuration, i18n, and structured-error-result infrastructure unchanged,
adding only their own tool registries (`EndMillTool`, `FaceMillTool`) and a
shared internal formula core (see research.md).

## Technical Context

**Language/Version**: Python 3.9+ (unchanged from `001-metal-drilling-calc`; Constitution Principle V / Debian oldstable-stable compatibility)

**Primary Dependencies**: None new. Reuses the existing standard-library-only calculation core, `tomli`/`tomllib` for TOML config/registry parsing (Python <3.11 only), and the existing per-locale message-catalog mechanism. Dev-only: `pytest`, `pytest-cov`, `ruff`, `black`, `mypy`, `radon`, `bandit`, `pip-audit`, `sphinx` (all already declared in `pyproject.toml`).

**Storage**: N/A (stateless per-request calculations); reuses the existing optional TOML configuration file for validation-bound overrides, extended with three new milling-specific bound fields (research.md #8), and two new bundled package-data TOML files for the `EndMillTool`/`FaceMillTool` registries (research.md #3).

**Testing**: `pytest` with `pytest-cov` (unchanged); tolerance-based float comparisons (`math.isclose`) per Constitution Principle III; new unit/contract/integration tests mirror the existing drilling test layout under `tests/unit/operations/milling/`, `tests/contract/`, `tests/integration/`.

**Target Platform**: Cross-platform CLI/library (Linux, incl. Debian stable/oldstable as the primary constrained target); offline-capable, no network dependency (unchanged).

**Project Type**: Single project — Python library with a thin CLI layer (`src/` layout), unchanged.

**Performance Goals**: Each milling calculation completes within 0.5-1.0s on the legacy/low-power hardware profile (Constitution Principle V), identical target to drilling since the formulas are simple closed-form arithmetic (no iteration/optimization). Full REPL flow from launch to end-milling results in at most 14 prompts, at most 12 of which require typing a value (SC-001; contracts/cli-repl-milling.md "Prompt-count budget").

**Constraints**: Runs within ~64-128 MB RAM on a single-threaded, low-clock-speed CPU (Constitution Principle V); no heavy new runtime dependencies; no exceptions raised for expected validation failures (FR-012); application logging remains English-only (Constitution VIII).

**Scale/Scope**: Two new operations (end milling, face milling) added to the existing operation set (drilling); each with its own small bundled tool registry (a handful of tool-material entries, mirroring drilling's `~3` drilling tool types). Reuses the existing ~6-material `WorkpieceMaterial` registry unchanged. Single-user, single-session usage, matching drilling's scale.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Single-responsibility modules; linting/type-checking pass in CI; public entry points documented with inputs/outputs/units | PASS — `operations/milling/{end_milling,face_milling}/{tools,formulas,__init__}.py` mirror drilling's module boundaries exactly; `calculate_end_milling()`/`calculate_face_milling()` docstrings enumerate per-field units under each `UnitSystem` (contracts/library-api-milling.md) |
| II. Testing Standards | Unit tests for every calculation function incl. boundary/zero/negative/reference values; ≥90% coverage; CI-enforced | PASS — pytest suite extended per quickstart.md Scenarios 2-6; existing drilling suite re-run unchanged (Scenario 6) to catch regressions |
| III. Calculation Robustness & Accuracy | Tolerance-based float comparisons; validated inputs; cited formula sources; explicit edge-case handling | PASS — research.md #1 cites the same Sandvik Coromant reference already used for drilling; data-model.md defines validation for every new input (diameter, depth of cut, engagement, feed per tooth, tooth count, length of cut) and the `INVALID_ENGAGEMENT` edge case (FR-009) |
| IV. Python Packaging & Versioning | `pyproject.toml` + `src/` layout; SemVer; explicit dependencies; PEP 8/257 | PASS — no new dependencies; new bundled TOML data files added to `[tool.setuptools.package-data]` (research.md #3); public API additions are additive (new functions, one new optional dataclass field), no breaking change, so a MINOR version bump suffices |
| V. Resource-Constrained Compatibility | ≤64-128MB RAM, single-threaded, low clock speed; Debian-stable compatible; ~0.5-1.0s per calculation | PASS — milling formulas are simple closed-form arithmetic identical in cost profile to drilling's; no new dependencies added; no threading/multiprocessing |
| VI. Extensibility by Design | New calculations addable without rewriting existing logic; architecture anticipates growth beyond drilling (turning, milling, ...) | PASS — this feature is the constitution's own anticipated case: milling added as sibling `operations/milling/` modules without modifying `operations/drilling/` at all; shared cross-cutting infrastructure (`WorkpieceMaterial`, `units.py`, `config.py`, `i18n.py`, `registry_config.py`, `models.py`) is reused, not duplicated (research.md #2, #5, #7, #8). **Conditional on the registry `table_key` allocation**: the shared `registry_config.load_and_merge()` selects entries from a single TOML array-of-tables key, so each milling tool registry MUST use its own key (`end_mill_tools`, `face_mill_tools`) rather than drilling's `tools`; reusing `tools` would inject milling entries into the drilling registry and break the already-shipped drilling flow on the mandatory `feed_factor` field, violating this principle. Normative in data-model.md "Registry `table_key` allocation" and contracts/milling-tools-config-schema.md; enforced by the isolation regression test (tasks.md T011c) |
| VII. Documentation & Publishing | Sphinx docs for end users + developers; auto-published to GitHub Pages; README reports coverage | PASS (planned) — new milling user/developer doc sections added to existing Sphinx sources during implementation; no change to the doc-publishing pipeline itself |
| VIII. Internationalization of User-Facing Messages | REPL/error text sourced from a message catalog; English bundled default/fallback; logging always English | PASS — all new prompts/labels/errors (operation selection, milling sub-operation selection, new field prompts, new error codes) added as new message-catalog keys (`locales/en.py`), following the existing key-based lookup pattern; no hard-coded user-facing strings |
| IX. Automated Code Quality, Complexity & Security Gates | Cyclomatic complexity/MI/security/dependency-vulnerability gates in CI | PASS — new modules follow the same extracted-helper pattern (`_validate_and_prepare`, `_compute_metrics`, `_build_result`-style decomposition; research.md #6) already used in `operations/drilling/__init__.py` to stay within the configured `max-complexity = 10`; no new third-party dependencies to scan |

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/009-milling-calculations/
├── plan.md              # This file (/speckit.plan command output)
├── research.md           # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md         # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   ├── library-api-milling.md
│   ├── cli-repl-milling.md
│   └── milling-tools-config-schema.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── machine_calc/
    ├── __init__.py                     # + calculate_end_milling, calculate_face_milling,
    │                                    #   list_end_mill_tools, list_face_mill_tools re-exports
    ├── models.py                        # + MachiningOperation, MillingSubOperation enums;
    │                                    #   + CalculationResult.material_removal_rate (optional, default None)
    ├── registry.py                      # unchanged (WorkpieceMaterial.specific_cutting_force_kc reused)
    ├── units.py                         # unchanged (mm_to_in/in_to_mm reused for all new mm-based inputs)
    ├── validation.py                    # + validate_depth_of_cut_mm, validate_engagement_mm,
    │                                    #   validate_feed_per_tooth_mm, validate_tooth_count,
    │                                    #   validate_length_of_cut_mm
    ├── config.py                        # + max_mill_diameter_mm, max_depth_of_cut_mm, max_length_of_cut_mm
    ├── i18n.py                          # unchanged (mechanism reused)
    ├── locales/
    │   └── en.py                        # + new operation/milling prompt, label, and error message keys
    ├── cli.py                           # + _prompt_operation, _prompt_milling_sub_operation,
    │                                    #   _run_drilling_session (extracted, unchanged body),
    │                                    #   _run_end_milling_session, _run_face_milling_session
    └── operations/
        ├── __init__.py                  # unchanged (still just documents the dispatch pattern)
        ├── drilling/                     # unchanged
        └── milling/
            ├── __init__.py               # new: package docstring only
            ├── _shared.py                 # new: calculate_milling_metrics() core formula (research.md #2)
            ├── end_milling/
            │   ├── __init__.py             # new: calculate_end_milling() public entry point
            │   ├── tools.py                 # new: EndMillTool registry
            │   ├── formulas.py              # new: EndMillingMetrics wrapper over _shared
            │   └── data/
            │       └── tools.toml            # new: bundled end-mill tool reference data
            └── face_milling/
                ├── __init__.py             # new: calculate_face_milling() public entry point
                ├── tools.py                 # new: FaceMillTool registry
                ├── formulas.py              # new: FaceMillingMetrics wrapper over _shared
                └── data/
                    └── tools.toml            # new: bundled face-mill tool reference data

tests/
├── contract/                # + milling library-api / cli-repl contract tests, identical-results tests
├── integration/              # + CLI operation-selection flow, milling flows, drilling-regression re-run
└── unit/
    ├── operations/
    │   ├── drilling/           # unchanged, re-run for regression (SC-005)
    │   └── milling/
    │       ├── end_milling/     # new: per-formula/tool-registry tests
    │       └── face_milling/    # new: per-formula/tool-registry tests
    └── shared/                 # + tests for new models/validation/config fields

docs/
└── source/                  # + milling end-user and developer/API reference sections (Constitution VII)

pyproject.toml               # + new bundled TOML data files under [tool.setuptools.package-data]
README.md                    # unchanged structurally; coverage figure updates automatically per existing process
```

**Structure Decision**: Single project (Option 1), unchanged from
`001-metal-drilling-calc`. Following Constitution Principle VI, end-milling
and face-milling logic is isolated under two new sibling packages,
`operations/milling/end_milling/` and `operations/milling/face_milling/`,
each with the same internal shape as `operations/drilling/` (its own
`tools.py` registry and `formulas.py`), while a new `operations/milling/
_shared.py` holds the one formula core both sub-operations call (research.md
#2) to avoid duplicating an identical physical model. No existing file under
`operations/drilling/` is modified. Shared, operation-agnostic
infrastructure (`models.py`, `registry.py`, `units.py`, `validation.py`,
`config.py`, `i18n.py`, `registry_config.py`) is extended additively
(new optional fields/functions) rather than duplicated, satisfying
Principle VI's requirement that cross-cutting concerns not be duplicated
per operation. `cli.py` gains a new outer operation-selection loop and two
new milling session functions, while the existing drilling session body is
extracted unchanged into its own function to guarantee zero behavioral
regression (FR-002, SC-005).

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
