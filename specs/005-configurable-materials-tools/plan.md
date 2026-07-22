# Implementation Plan: Configurable Materials & Tools

**Branch**: `main` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-configurable-materials-tools/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Externalize today's hard-coded material registry (`src/machine_calc/registry.py`)
and drilling tool registry (`src/machine_calc/operations/drilling/tools.py`)
into TOML configuration data, bundled as package data so the built-in set
still works with zero configuration (User Story 1). Add a single optional
`--materials-config PATH` CLI flag whose file is merged with the bundled
defaults — same-named entries override, new names are added, per-locale
translations merge per-locale (User Story 2/3) — reusing the TOML-loading
pattern already established by `machine_calc.config.load_configuration`
without touching that separate bounds-configuration mechanism (FR-017). Each
material/tool entry declares whether its reference values are metric or
imperial (defaulting to metric); imperial-declared values are converted to
the canonical-metric representation at load time via new `units.py` helpers,
before reaching the unchanged calculation formulas (User Story 4). No
calculation formula, canonical-metric computation model, or existing
`CalculationResult`/error contract changes.

## Technical Context

**Language/Version**: Python 3.9+ (unchanged from `001-metal-drilling-calc` research.md #1; no change to the supported version floor)

**Primary Dependencies**: None new. Continues to use `tomllib` (3.11+) / `tomli` backport (<3.11, already a declared dependency) for TOML parsing (research.md #1); `importlib.resources` (stdlib since 3.9) for reading bundled package-data TOML files (research.md #2); `argparse` (stdlib) for the new `--materials-config` CLI flag (research.md #3); `functools.lru_cache` (stdlib) for caching the parsed/merged registry per session (research.md #9).

**Storage**: N/A (stateless per-invocation calculations, unchanged); two new package-data files (`src/machine_calc/data/materials.toml`, `src/machine_calc/operations/drilling/data/tools.toml`) plus an optional user-supplied TOML file at a caller/CLI-provided path (research.md #1-#2)

**Testing**: `pytest` + `pytest-cov`, unchanged; new unit tests for `registry_config.py`'s parse/fallback/duplicate-detection/merge logic and unit-conversion helpers, new contract tests for the config schema (`contracts/materials-config-schema.md`), new integration tests for the CLI `--materials-config` flag (missing/malformed/valid-override paths) and a packaging test asserting the bundled TOML files ship inside a built wheel (quickstart.md Scenario 2)

**Target Platform**: Unchanged — cross-platform CLI/library, Debian stable/oldstable as the primary constrained target (Constitution Principle V)

**Project Type**: Single project — Python library with a thin CLI layer (`src/` layout), unchanged

**Performance Goals**: Unchanged 0.5-1.0s per-calculation target (Constitution Principle V); the new TOML-parse-and-merge step is cached per session (`lru_cache`, research.md #9) so it does not add repeated I/O cost to the REPL's per-iteration `list_materials()`/`list_tools()` calls

**Constraints**: No new runtime dependency (Constitution Principle V); bundled defaults MUST be present and lossless when installed from a built wheel/sdist, not only a source checkout (FR-001); a malformed user file MUST be rejected with a translatable error and MUST NOT be partially applied (FR-007); a missing/unreadable user file MUST NOT be an error (FR-005); no change to the existing validation-bounds configuration mechanism or its `config_path` meaning on `calculate()` (FR-017); all new user-facing strings (CLI notices/errors) MUST go through the existing `machine_calc.i18n` catalog mechanism (Constitution Principle VIII)

**Scale/Scope**: Same two entry points (library API + CLI REPL); same drilling operation; effective material/tool sets grow from the fixed built-in ~6 materials/~3 tools to bundled-defaults-plus-unbounded-user-additions; still single-user, single-session usage per invocation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Single-responsibility modules; new `registry_config.py` isolates parse/merge logic from `registry.py`/`tools.py`'s dataclass construction; linting/type-checking unchanged and must still pass | PASS — new module boundary keeps each file focused (research.md #4); public functions (`load_and_merge`, `display_name`, new CLI flag) documented with inputs/outputs/units per existing docstring conventions |
| II. Testing Standards | Unit tests for every calculation-adjacent function incl. boundary/zero/negative/malformed inputs; ≥90% coverage; CI-enforced | PASS — new unit tests planned for `registry_config.py` (parse/fallback/duplicate/merge), extended `units.py` conversions, and `registry.py`/`tools.py` construction from merged entries; new contract tests for the schema; new integration tests for the CLI flag's three paths (absent/missing-file/malformed/valid) |
| III. Calculation Robustness & Accuracy | Tolerance-based float comparisons; validated inputs; cited conversion constants; explicit edge-case handling | PASS — new imperial↔metric conversion constants (ft/min, in/rev reuse, psi↔N/mm²) cited in `units.py` docstrings per research.md #5; malformed/duplicate/invalid entries rejected with structured, specific errors (`RegistryConfigError`) rather than silently applied or crashing (FR-006, FR-007, FR-016); quickstart.md Scenario 5 validates imperial-vs-metric-authored equivalence via `math.isclose` |
| IV. Python Packaging & Versioning | `pyproject.toml` single source of build metadata; explicit dependency declarations; PEP 8/257 | PASS — no new runtime dependency; `pyproject.toml` gains a `[tool.setuptools.package-data]` section (research.md #2) to declare the two new bundled TOML files, which is metadata, not a dependency; new public parameters (`config_path`, `materials_config_path`) follow existing naming/typing conventions |
| V. Resource-Constrained Compatibility | ≤64-128MB RAM, single-threaded; Debian-stable compatible; ~0.5-1.0s per calculation | PASS — no new runtime dependency; `importlib.resources`/`tomllib`/`tomli`/`argparse`/`functools` are all stdlib or already-declared; per-session `lru_cache` (research.md #9) keeps the added TOML-parse step off the per-calculation hot path |
| VI. Extensibility by Design | New calculations/materials/tools addable without rewriting existing logic; shared behavior factored into reusable components; operation-specific vs. shared boundary preserved | PASS — this feature *is* the extensibility improvement the constitution anticipates for materials/tools; shared parse/merge logic lives in one new shared module (`registry_config.py`, research.md #4) reused by both the shared `registry.py` (materials) and the operation-specific `operations/drilling/tools.py` (tools), preserving the existing shared-vs-operation-specific split rather than blurring it |
| VII. Documentation & Publishing | Sphinx docs for end users + developers; README coverage badge | PASS (no regression) — new public functions/parameters get docstrings per Principle I above, which Sphinx already picks up automatically (unchanged doc-build pipeline); no change needed to the doc-publishing automation itself |
| VIII. Internationalization of User-Facing Messages | User-facing strings sourced from message catalog, not hard-coded; English default/fallback; logging always English | PASS — every new CLI-facing string (missing-file notice, malformed-file error, duplicate-entry error, invalid-entry error) is added as a new `en.py` catalog key and routed through `machine_calc.i18n.translate` (research.md #6), never hard-coded inline; translated material/tool *display names* are handled as a separate, explicitly-documented data-driven mechanism (research.md #7) distinct from — but consistent with — the message-catalog English-fallback rule, so no entry is ever shown blank (SC-003) |
| IX. Automated Code Quality, Complexity & Security Gates | Cyclomatic complexity/MI/security/dependency gates unaffected | PASS (no regression) — new logic is factored into small, single-purpose functions in `registry_config.py` (parse / fallback-check / duplicate-check / merge as separate functions) specifically to stay under the existing `max-complexity = 10` mccabe threshold already configured in `pyproject.toml`; no new third-party dependency to scan/audit |

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/005-configurable-materials-tools/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── materials-config-schema.md   # TOML schema/validation contract (bundled + user files)
│   └── library-cli-extensions.md    # Additive deltas to 001's library-api.md / cli-repl.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── machine_calc/
    ├── __init__.py            # Unchanged public re-exports (calculate, list_materials, list_tools, UnitSystem)
    ├── models.py                # Unchanged (CalculationMode, CalculationResult, ErrorInfo, UnitSystem)
    ├── registry.py               # MODIFIED: WorkpieceMaterial gains unit_system/translations fields +
    │                                display_name(); MATERIAL_REGISTRY built from registry_config's merge
    │                                of bundled data/materials.toml + optional user file; list_materials()/
    │                                get_material() gain an optional config_path parameter
    ├── registry_config.py        # NEW: shared, kind-agnostic TOML parse/fallback/duplicate-detection/
    │                                merge logic (research.md #4) + RegistryConfigError; reused by both
    │                                registry.py (materials) and operations/drilling/tools.py (tools)
    ├── units.py                  # MODIFIED: adds ft_min_to_m_min/m_min_to_ft_min and
    │                                psi_to_n_per_mm2/n_per_mm2_to_psi (mm<->in helpers reused as-is
    │                                for feed-per-rev conversion, research.md #5)
    ├── validation.py              # Unchanged
    ├── config.py                  # Unchanged (bounds-only mechanism, FR-017)
    ├── i18n.py                    # Unchanged (loader mechanism); new message keys added to locales/en.py only
    ├── logging_setup.py            # Unchanged
    ├── locales/
    │   └── en.py                    # MODIFIED: adds new notice.materials_config.*/error.materials_config.* keys
    ├── data/
    │   └── materials.toml           # NEW: bundled default materials (package data, research.md #2)
    ├── cli.py                      # MODIFIED: argparse for --materials-config (research.md #3); material/tool
    │                                  prompts display display_name(locale) instead of raw name (research.md #7);
    │                                  catches RegistryConfigError at startup and prints the translated notice/error
    ├── __main__.py                  # Unchanged entry point (delegates to cli.main())
    └── operations/
        ├── __init__.py               # Unchanged
        └── drilling/
            ├── __init__.py            # MODIFIED: calculate() gains optional materials_config_path,
            │                             threaded into get_material()/get_tool() lookups (FR-017: formulas
            │                             themselves unchanged)
            ├── tools.py                 # MODIFIED: DrillingTool gains unit_system/translations fields +
            │                             display_name(); TOOL_REGISTRY built from registry_config's merge
            │                             of bundled data/tools.toml + optional user file; list_tools()/
            │                             get_tool() gain an optional config_path parameter
            ├── data/
            │   └── tools.toml            # NEW: bundled default drilling tools (package data, research.md #2)
            └── formulas.py               # Unchanged (FR-017 — no calculation formula changes)

tests/
├── contract/
│   └── test_materials_config_schema.py   # NEW: validates contracts/materials-config-schema.md rules
├── integration/
│   └── test_cli_materials_config.py      # NEW: CLI --materials-config absent/missing/malformed/valid flows
└── unit/
    ├── operations/
    │   └── drilling/
    │       └── test_tools_registry.py     # NEW (or extends existing): merge/override/unit-conversion for tools
    └── shared/
        ├── test_registry_config.py        # NEW: parse/fallback/duplicate-detection/merge unit tests
        ├── test_registry.py                # EXTENDED: materials merge/override/translation/unit-conversion
        └── test_units.py                   # EXTENDED: new conversion helpers

pyproject.toml               # MODIFIED: adds [tool.setuptools.package-data] for the two new bundled TOML files
```

**Structure Decision**: Single project (unchanged from `001-metal-drilling-calc`
Option 1). This feature adds exactly one new shared module
(`registry_config.py`, alongside the other shared, operation-agnostic
infrastructure — `models.py`, `units.py`, `validation.py`, `config.py`,
`i18n.py`) and one new package-data file per existing registry location
(`machine_calc/data/materials.toml` next to the shared `registry.py`;
`operations/drilling/data/tools.toml` next to the operation-specific
`tools.py`). This mirrors and preserves the exact shared-vs-operation-specific
boundary `001-metal-drilling-calc`'s plan established under Constitution
Principle VI — a future turning/milling operation adds its own
`operations/<op>/data/tools.toml` (or equivalent) and reuses
`registry_config.py` unchanged, without needing to touch this feature's code.
No new top-level directory, project, or architectural layer is introduced.

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
