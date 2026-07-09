# Implementation Plan: Metal Drilling Calculations Module

**Branch**: `main` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-metal-drilling-calc/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

A Python calculation engine for twist-drill machining parameters (spindle
speed, feed rate, machining time, torque, power) exposed as (1) a
dependency-light callable library and (2) a step-by-step interactive text
REPL built on that same library, both producing identical results for
identical inputs. The module supports metric and imperial units selectable
per request/session, validates inputs against configurable bounds, rejects
unsupported material/tool combinations with structured errors, and never
raises exceptions for expected validation failures — always returning a
structured result object instead (see research.md and contracts/).

## Technical Context

**Language/Version**: Python 3.9+ (research.md #1 — Debian oldstable/stable compatibility per Constitution Principle V)

**Primary Dependencies**: None required at runtime beyond the standard library; `tomli` (pure-Python TOML parser) only on Python < 3.11 for configuration file support (research.md #2, #3). Dev-only: `pytest`, `pytest-cov`, `ruff`, `black` (or equivalent), `sphinx`.

**Storage**: N/A (stateless per-request calculations); optional local TOML configuration file for validation-bound overrides (FR-018)

**Testing**: `pytest` with `pytest-cov` for coverage reporting; tolerance-based float comparisons (`math.isclose`) per Constitution Principle III

**Target Platform**: Cross-platform CLI/library (Linux, incl. Debian stable/oldstable as the primary constrained target; macOS/Windows supported incidentally); offline-capable, no network dependency

**Project Type**: Single project — Python library with a thin CLI layer (src/ layout)

**Performance Goals**: Each calculation completes within 0.5-1.0s on the legacy/low-power hardware profile in Constitution Principle V; full interactive flow (open CLI → get results) under 30s (SC-001)

**Constraints**: Runs within ~64-128 MB RAM on a single-threaded, low-clock-speed CPU (Constitution Principle V); no heavy third-party runtime dependencies (research.md #2); Debian-stable/oldstable OS compatibility; no exceptions raised for expected validation failures (FR-015)

**Scale/Scope**: Two user-facing entry points (library API + CLI REPL) for this feature's drilling operation; initial reference dataset of ~6 workpiece materials × ~3 drilling tool types (spec Assumptions); single-user, single-session usage. Per Constitution Principle VI (amended 2026-07-09), the architecture MUST anticipate future metal machining operations beyond drilling (e.g., turning, milling) without requiring rework of shared infrastructure — this shapes the per-operation module boundary in Project Structure below, even though only drilling is in scope for this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Single-responsibility modules (models / calculations / cli / config); linting (ruff/black) required in CI; public entry points documented with inputs/outputs/units | PASS — planned structure separates concerns (see Project Structure); `calculate()` docstring MUST enumerate per-field units under each `UnitSystem` (contracts/library-api.md, resolving /speckit.analyze finding B1) |
| II. Testing Standards | Unit tests for every calculation function incl. boundary/zero/negative/reference values; ≥90% coverage on calculation modules; CI-enforced | PASS — pytest + pytest-cov planned; contract/integration/unit test layout below |
| III. Calculation Robustness & Accuracy | Tolerance-based float comparisons; validated inputs; cited formula sources; explicit edge-case handling | PASS — research.md #4 cites formula sources; data-model.md defines validation and `ErrorInfo` |
| IV. Python Packaging & Versioning | `pyproject.toml` + `src/` layout; SemVer/PEP 440; explicit dependency declarations; PEP 8/257 | PASS — planned structure uses `src/machine_calc/`; no undeclared dependencies (research.md #2) |
| V. Resource-Constrained Compatibility | ≤64-128MB RAM, single-threaded, low clock speed; Debian-stable compatible; ~0.5-1.0s per calculation | PASS — zero/near-zero runtime dependencies (research.md #2), simple arithmetic-only calculations, no threading/multiprocessing used; RAM footprint and calculation timing both explicitly measured and recorded (tasks.md T042, T043, resolving /speckit.analyze finding E1) |
| VI. Extensibility by Design | New calculations/materials/tools addable without rewriting existing logic; architecture MUST anticipate future non-drilling machining operations (turning, milling, etc.) per the 2026-07-09 amendment | PASS — data-model.md registry pattern for `WorkpieceMaterial`/`DrillingTool`; calculation logic behind a stable `calculate()` interface (contracts/library-api.md); Project Structure below isolates drilling-specific formulas in an `operations/drilling` module distinct from shared infrastructure (registries, units, config, error reporting) so future operations can be added as sibling modules |
| VII. Documentation & Publishing | Sphinx docs for end users + developers; auto-published to GitHub Pages; README reports coverage | PASS (planned, not yet implemented) — research.md #7 selects Sphinx+alabaster; CI/CD automation captured in research.md #8 for `/speckit.tasks` to schedule |

No violations requiring the Complexity Tracking table.

*Post-clarification re-validation (2026-07-09, after the "machining time unit"
clarification): no gate status changes. `data-model.md`'s `machining_time`
field and all contract/quickstart examples already used minutes; the
clarification made this explicit in `spec.md` (FR-008) without requiring any
structural changes to this plan.*

## Project Structure

### Documentation (this feature)

```text
specs/001-metal-drilling-calc/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md         # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   ├── library-api.md
│   └── cli-repl.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── machine_calc/
    ├── __init__.py         # Public API surface: calculate(), list_materials(), list_tools(), UnitSystem
    ├── models.py            # Shared entities: UnitSystem, CalculationResult, ErrorInfo (operation-agnostic)
    ├── registry.py           # Shared WorkpieceMaterial registry (extensible across operations, Principle VI)
    ├── units.py              # Shared metric<->imperial conversion helpers
    ├── validation.py         # Shared input validation + Configuration bound checks (FR-009, FR-018)
    ├── config.py             # Shared TOML configuration file loading (research.md #3)
    ├── cli.py                # Interactive REPL (FR-002), built only on the public API (contracts/cli-repl.md)
    └── operations/
        ├── __init__.py        # Operation registry/dispatch (future: turning, milling register alongside drilling)
        └── drilling/
            ├── __init__.py     # This feature's public entry point: calculate() for drilling
            ├── tools.py         # DrillingTool registry (operation-specific reference data)
            └── formulas.py      # Spindle speed / feed rate / machining time / torque / power formulas (research.md #4)

tests/
├── contract/                # Verifies library-api.md / cli-repl.md contracts (structured results, error codes, identical-results)
├── integration/              # End-to-end: CLI flow, config-file override flow, multi-tool comparison flow
└── unit/
    ├── operations/
    │   └── drilling/           # Per-formula tests for the drilling operation
    └── shared/                 # Tests for models, registry, units, validation, config

docs/
└── source/                  # Sphinx sources: end-user guide + developer/API reference (Constitution Principle VII)

pyproject.toml               # Build/project metadata, src/ layout, dependencies (Constitution Principle IV)
README.md                    # Includes test coverage badge/section (Constitution Principle VII)
```

**Structure Decision**: Single project (Option 1 from the template) — this is
a Python library with a thin CLI layer, not a web/mobile app, so the
frontend/backend or API/mobile options are not applicable. The `src/`
layout satisfies Principle IV. Following the 2026-07-09 constitution
amendment to Principle VI, drilling-specific logic (cutting/feed/torque/
power formulas and the `DrillingTool` registry) is isolated under
`operations/drilling/`, separate from shared, operation-agnostic
infrastructure (`models.py`, `registry.py` for materials, `units.py`,
`validation.py`, `config.py`, `cli.py`). A future turning or milling
operation can therefore be added as a new sibling module under
`operations/`, implementing the same kind of `calculate()`-style interface
and reusing the shared infrastructure unchanged — satisfying Principle VI
without reworking this feature's code. Only `operations/drilling/` and its
direct integration points (public `__init__.py`, `cli.py`, tests) are in
scope for this feature; the `operations/` package structure is established
now so it does not need to be retrofitted later.

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
