# Phase 0 Research: Metal Drilling Calculations Module

**Feature**: [spec.md](./spec.md) | **Date**: 2026-07-09

This document resolves the technical unknowns needed before Phase 1 design. Each
topic follows the Decision / Rationale / Alternatives Considered format.

## 1. Python version baseline

- **Decision**: Target Python 3.9+ as the minimum supported version.
- **Rationale**: Constitution Principle V requires compatibility with older/stable
  OS releases (e.g., Debian stable and oldstable). Debian 11 ("bullseye",
  oldstable) ships Python 3.9; Debian 12 ("bookworm", stable) ships Python 3.11.
  Targeting 3.9+ keeps the module installable on both without requiring users to
  install a newer interpreter alongside their OS-provided one.
- **Alternatives considered**: Requiring Python 3.11+ (to use stdlib `tomllib`
  directly) was rejected because it would exclude Debian 11 and other
  currently-deployed legacy systems, directly conflicting with Principle V.

## 2. Runtime dependencies

- **Decision**: Zero required third-party runtime dependencies for the core
  library and CLI; use only the Python standard library (`dataclasses`, `enum`,
  `math`, `argparse`/`input()`, `configparser`/`tomllib`). For configuration
  file parsing on Python < 3.11, use the lightweight `tomli` backport
  (pure-Python, no transitive dependencies) as the sole runtime dependency,
  conditional on interpreter version.
- **Rationale**: Constitution Principle V mandates a small memory/CPU footprint
  (64-128 MB RAM, single-threaded, low clock speed target) and explicitly
  requires justifying any dependency with a non-trivial footprint. A
  dependency-free (or near dependency-free) core keeps install size and import
  time minimal and avoids transitive dependency risk on constrained/offline
  systems.
- **Alternatives considered**: `click`/`typer` for the CLI were rejected — they
  add non-trivial import weight and are unnecessary for a simple sequential
  prompt REPL (FR-002). `pydantic` for input validation was rejected as heavy
  for this scale of data validation; plain functions with explicit range
  checks satisfy FR-009/FR-018 without the dependency.

## 3. Configuration file format

- **Decision**: TOML for the external configuration file (FR-018), read via
  stdlib `tomllib` (Python 3.11+) or the `tomli` backport (Python 3.9-3.10).
- **Rationale**: TOML is human-editable, supports comments (unlike JSON), and
  is already the project's packaging format (`pyproject.toml`), keeping
  tooling and mental model consistent. Reading is available without a heavy
  dependency (see #2).
- **Alternatives considered**: JSON was rejected (no comments, less friendly
  for a config file end users hand-edit). YAML was rejected because it
  requires the external `PyYAML` dependency, conflicting with the minimal
  footprint goal in Principle V.

## 4. Drilling calculation formulas

- **Decision**: Use standard twist-drill machining formulas as published in
  widely-referenced industry sources (e.g., Sandvik Coromant's "Machining
  Formulas" reference and Machinery's Handbook), specifically:
  - Spindle speed: `n = (vc × 1000) / (π × D)` (metric: vc in m/min, D in mm, n
    in RPM); imperial equivalent uses vc in ft/min and D in inches with the
    appropriate constant.
  - Feed rate: `vf = n × fn` (fn = feed per revolution from the material/tool
    reference data).
  - Machining time: `tc = (depth + point-engagement allowance) / vf`, with the
    point-engagement allowance approximated from drill diameter and point
    angle (standard practice: ~0.3 × D for a 118° point).
  - Torque: `Mc = (Kc × D² × fn) / 4000` (Nm; Kc = specific cutting force for
    the material in N/mm², D in mm, fn in mm/rev).
  - Power: `Pc = (Mc × n) / 9550` (kW; standard torque-to-power conversion).
  - Imperial results are derived via unit conversion of the same underlying
    metric calculation (FR-017) rather than a parallel formula set, to avoid
    duplicated/divergent logic.
- **Rationale**: These are the standard, publicly documented formulas used
  across machining references; using them satisfies SC-002 (results within 5%
  of published reference values) and Constitution Principle III's requirement
  to cite external formula sources in code comments.
- **Alternatives considered**: Deriving custom empirical curve-fits was
  rejected — it would require proprietary test data and could not be
  independently verified against a citable source, violating Principle III.

## 5. Data/entity representation

- **Decision**: Represent Workpiece Material and Drilling Tool reference data
  as plain `dataclasses` held in an in-memory registry (dict keyed by name),
  with the registry structured so new entries can be added without touching
  calculation logic.
- **Rationale**: Satisfies Constitution Principle VI (extensibility by
  design) — adding a material or tool is a data addition, not a code change —
  while keeping the runtime footprint minimal (no ORM/database, per Principle
  V).
- **Alternatives considered**: Loading material/tool data from an external
  file (e.g., CSV/TOML) at runtime was considered for extensibility, but
  deferred: an in-memory registry is sufficient for the initial fixed list
  (per spec Assumptions) while still allowing future migration to file-based
  data without changing the public API shape.

## 6. Testing & coverage tooling

- **Decision**: `pytest` for the test suite, `pytest-cov` for coverage
  measurement/reporting, with tolerance-based float assertions
  (`math.isclose`) throughout per Constitution Principle III.
- **Rationale**: Already the project's established testing convention
  (Constitution Principle II); `pytest-cov` integrates directly with CI to
  produce the coverage percentage referenced in Principle VII's README
  requirement.
- **Alternatives considered**: `unittest` alone was rejected in favor of
  `pytest` for more ergonomic parametrized tests across the material × tool ×
  unit-system combinations this feature requires.

## 7. Documentation tooling

- **Decision**: Sphinx with the `napoleon` extension (Google/NumPy-style
  docstring support) and the built-in `alabaster` theme (no extra
  dependency), generating separate end-user and developer documentation
  trees from the same docstrings/handwritten `.rst` pages.
- **Rationale**: Satisfies Constitution Principle VII (Sphinx-generated docs
  for both audiences); `alabaster` avoids adding a themed-dependency footprint
  inconsistent with Principle V.
- **Alternatives considered**: `sphinx-rtd-theme`/`furo` were considered for
  a more modern look but rejected as an unnecessary added dependency for a
  documentation-only build step (not part of the runtime footprint, but kept
  minimal for consistency and CI build speed).

## 8. CI/CD automation

- **Decision**: GitHub Actions workflows: (a) a CI workflow running lint,
  tests with coverage, package build check, and Sphinx docs build on every
  push/PR; (b) a docs-publish job (part of or triggered by the same
  workflow) that publishes the built Sphinx output to GitHub Pages on
  successful builds of `main`; (c) a release workflow that builds and
  publishes the package to PyPI on every merge to `main`.
- **Rationale**: Directly implements Constitution Principle VII and the
  Additional Constraints CI/CD gate.
- **Alternatives considered**: Manual/local doc builds and manual PyPI
  releases were rejected as they conflict with the constitution's explicit
  automation requirements.

## 9. Internationalization (i18n) mechanism

- **Decision**: User-facing messages (REPL prompts/labels, library
  `ErrorInfo`/warning text) are sourced from a message catalog implemented as
  one pure-Python module per locale (`src/machine_calc/locales/en.py`,
  exposing a `dict[str, str]` of message ID → string), loaded via
  `src/machine_calc/i18n.py`. Dynamic values are substituted with
  `str.format()`-style named placeholders (e.g. `{material}`) at lookup time.
  The CLI selects its locale solely from the `MACHINE_CALC_LOCALE`
  environment variable at startup (no OS/system locale auto-detection, no
  new interactive prompt); the library's `calculate()` accepts an optional
  `locale` parameter. Both fall back to the bundled English catalog for any
  missing locale or message key. Only the English catalog ships with this
  feature (spec.md Clarifications, 2026-07-10).
- **Rationale**: A plain Python dict module avoids adding a JSON/YAML parser
  or a `gettext` toolchain dependency, keeping the runtime footprint minimal
  per Constitution Principle V, while fully satisfying Constitution Principle
  VIII (translatable user-facing messages, English-only logging, English
  default/fallback). An environment variable requires no new REPL prompt
  step, keeping FR-002's prompt sequence unchanged.
- **Alternatives considered**: `gettext` `.po`/`.mo` catalogs were rejected —
  they add build-time tooling (`msgfmt`) and a runtime dependency footprint
  disproportionate to a project targeting minimal resource usage. JSON/YAML
  catalog files were rejected for the same minimal-dependency reason (JSON
  lacks comments for translator context; YAML needs `PyYAML`). OS locale
  auto-detection (`LANG`/`LC_ALL`) was rejected to keep locale selection
  deterministic and testable, independent of inconsistent environment setup
  on legacy/constrained target systems (Principle V).

## Outcome

All NEEDS CLARIFICATION items from the Technical Context are resolved above.
No open unknowns remain blocking Phase 1 design.
