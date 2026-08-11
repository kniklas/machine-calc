# Implementation Plan: Wood Materials Support

**Branch**: `main` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-wood-materials-support/spec.md`

## Summary

Extend the built-in materials registry to include wood materials for MVP use:
hardwoods (oak, maple), soft woods (pine, spruce, fir), and engineered woods
(plywood, MDF). Keep the existing calculation formulas and public API shape,
and implement FR-008 load-time material validation that logs warnings and
continues registry initialization so users can still list/override entries.

## Technical Context

**Language/Version**: Python 3.9+

**Primary Dependencies**: No new runtime dependencies; existing stdlib + current package stack (`tomllib`/`tomli`, `importlib.resources`, `logging`, `pytest`)

**Storage**: N/A (in-memory registry), with bundled package data in `src/machine_calc/data/materials.toml`

**Testing**: `pytest` + `pytest-cov` (existing)

**Target Platform**: Cross-platform CLI/library; Debian stable/older hardware compatibility remains required

**Project Type**: Single Python package (`src/` layout) with CLI entrypoint

**Performance Goals**: Preserve current per-calculation responsiveness target (0.5-1.0s legacy-hardware budget); no new runtime hot-path complexity

**Constraints**:
- Keep canonical metric representation and existing formulas unchanged
- Keep materials configurable via current override mechanism (`--materials-config`)
- Implement FR-008 warning-and-continue behavior for invalid/missing material parameters at load time
- Preserve packaging inclusion of bundled data files in wheel/sdist

**Scale/Scope**:
- Add 7 built-in wood entries (Oak, Maple, Pine, Spruce, Fir, Plywood, MDF)
- No new CLI flags or public top-level API additions
- Limited to shared material registry/data/validation behavior

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Keep registry/data/validation concerns separated and documented | PASS |
| II. Testing Standards | Add/extend unit + integration + packaging tests for wood entries and FR-008 behavior | PASS |
| III. Calculation Robustness & Accuracy | Preserve validated inputs, handle invalid registry parameters predictably with warnings | PASS |
| IV. Packaging & Versioning | Keep pyproject/package-data model intact | PASS |
| V. Resource-Constrained Compatibility | No heavy deps; no significant runtime overhead | PASS |
| VI. Extensibility by Design | Reuse shared registry patterns and configurable data model from spec 005 | PASS |
| VII. Documentation & Publishing | Add feature quickstart + source methodology documentation | PASS |
| VIII. i18n of User-Facing Messages | User-visible strings remain translatable; diagnostic logs remain English | PASS |
| IX. Automated Quality/Security Gates | Existing CI gates remain applicable; no gate bypass | PASS |

No constitutional violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/007-wood-materials-support/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── wood-materials-registry-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── machine_calc/
    ├── data/
    │   └── materials.toml                # add wood + engineered wood built-ins
    ├── registry.py                       # adapt validation path for FR-008 warning-and-continue
    ├── registry_config.py                # preserve/extend parse behavior as needed for warning model
    ├── logging_setup.py                  # reuse existing warning logger behavior
    ├── cli.py                            # ensure warnings are surfaced without aborting initialization
    └── operations/drilling/
        └── __init__.py                   # calculation-time guard behavior for unusable material entries

tests/
├── unit/
│   └── shared/
│       └── test_registry.py              # wood entries + invalid/missing-parameter warning scenarios
├── integration/
│   └── test_cli_materials_config.py      # warning-and-continue CLI behavior
└── contract/
    └── test_materials_config_schema.py   # schema compatibility assertions for new entries
```

**Structure Decision**: Keep the current single-package structure and reuse the
existing configurable-materials architecture from `specs/005-configurable-materials-tools`.
This feature is a bounded extension of shared material data and validation behavior.

## Phase 0: Research Outcomes

Research completed in [research.md](./research.md). No unresolved
`NEEDS CLARIFICATION` items remain.

## Phase 1: Design Outputs

- Data model: [data-model.md](./data-model.md)
- Contract: [contracts/wood-materials-registry-contract.md](./contracts/wood-materials-registry-contract.md)
- Validation guide: [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

Re-evaluated after Phase 1 artifacts: **PASS**.  
No new constitutional violations introduced by the design.

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
