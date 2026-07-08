<!--
Sync Impact Report
==================
Version change: (template) → 1.0.0
Modified principles: N/A (initial ratification)
Added sections:
  - I. Code Quality
  - II. Testing Standards
  - III. Calculation Robustness & Accuracy
  - IV. Python Packaging & Versioning Standards
  - Additional Constraints (Quality Gates)
  - Development Workflow (Review Process)
  - Governance
Removed sections: none (placeholders replaced)
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (Constitution Check gate references these principles generically; no changes needed)
  ✅ .specify/templates/tasks-template.md (test task guidance already supports test-first ordering; no changes needed)
  ✅ .specify/templates/spec-template.md (no principle-specific mandatory sections introduced; no changes needed)
  ✅ .github/prompts/speckit.constitution.prompt.md (no agent-specific references requiring updates)
Follow-up TODOs:
  - None. Tech stack is Python per this amendment (see Principle IV).
-->

# machine-calc Constitution

## Core Principles

### I. Code Quality
All code merged into this repository MUST be readable, maintainable, and consistent.
- Every module, function, and calculation routine MUST have a single, clear responsibility;
  no god-functions mixing input parsing, calculation, and presentation logic.
- Public functions and calculation entry points MUST be documented with inputs, outputs,
  units of measurement, and valid ranges.
- Linting/formatting tools MUST be configured (e.g., ruff/flake8 + black or an equivalent
  formatter) and MUST pass in CI before merge; style violations are not acceptable
  trade-offs for speed.
- Code reviews MUST verify naming clarity, absence of duplicated logic, and that magic
  numbers/constants tied to physical or mathematical meaning are named and explained.
- Rationale: calculation software is trusted for correctness; unreadable code hides defects
  and makes verification by reviewers or future maintainers effectively impossible.

### II. Testing Standards (NON-NEGOTIABLE)
Automated tests are mandatory for all calculation logic and MUST be written before or
alongside implementation, never deferred to "later".
- Every calculation function MUST have unit tests covering: nominal inputs, boundary values,
  zero/negative/empty inputs, and known reference results (hand-computed or from an
  authoritative source).
- Bug fixes MUST include a regression test that fails before the fix and passes after.
- Integration tests MUST cover any multi-step calculation pipeline (e.g., chained formulas,
  unit conversions) to confirm end-to-end correctness, not just isolated functions.
- Test suites MUST run in CI on every pull request (e.g., via `pytest`); a failing test
  suite blocks merge.
- Target minimum coverage for calculation modules is 90% line coverage; any exclusion MUST
  be justified in the pull request description.
- Rationale: calculation errors are silent and costly; only systematic, repeatable testing
  catches regressions before they reach users making real decisions from the output.

### III. Calculation Robustness & Accuracy
Numerical results MUST be correct, stable, and safe across the full range of realistic inputs.
- Floating-point operations MUST use appropriate precision for the domain; equality checks
  on floating-point results MUST use explicit tolerances (e.g., `math.isclose`), never exact
  `==` comparison.
- All calculation inputs MUST be validated (type, range, unit) before use; invalid input
  MUST produce a clear, actionable error rather than a silently wrong number or a crash.
- Edge cases (division by zero, overflow, negative square roots, empty datasets, unit
  mismatches) MUST be explicitly handled and covered by tests per Principle II.
- Any formula or constant sourced from an external standard/reference MUST cite that source
  in code comments so correctness can be independently verified.
- Rationale: this project exists to produce trustworthy machine/engineering calculations;
  an incorrect result is worse than no result, so correctness and predictable failure modes
  take priority over convenience or premature optimization.

### IV. Python Packaging & Versioning Standards
The project is implemented as a Python module and MUST follow established Python packaging
and versioning conventions, not ad-hoc scripts.
- The package MUST be structured per current packaging standards (`pyproject.toml` as the
  single source of build/project metadata, PEP 517/518-compliant build backend, `src/`
  layout for the importable package) rather than legacy `setup.py`-only distribution.
- Public releases MUST follow Semantic Versioning (MAJOR.MINOR.PATCH) per PEP 440-compatible
  version strings; the version MUST be defined in exactly one place and referenced elsewhere
  (e.g., via the build backend's dynamic version support), never hard-coded in multiple files.
- Dependencies MUST be declared explicitly with sensible version constraints in
  `pyproject.toml`; no undeclared/implicit dependencies on packages imported at runtime.
- Public APIs MUST follow PEP 8 naming and PEP 257 docstring conventions so the module is
  usable as a library, not just an application.
- Breaking changes to the public API MUST bump the MAJOR version and MUST be documented in
  a changelog before release.
- Rationale: treating machine-calc as a properly packaged, versioned Python module (rather
  than a loose collection of scripts) enables reliable installs, reproducible environments,
  and safe upgrades for anyone depending on it.

## Additional Constraints (Quality Gates)

- CI MUST run linting, the full automated test suite, and a package build check on every
  pull request; all three MUST pass before merge.
- Dependencies introducing calculation logic (e.g., math/statistics libraries) MUST be
  vetted for correctness and actively maintained status before adoption.
- Performance MUST be measured, not assumed: any calculation expected to run on large
  datasets or in tight loops MUST have a benchmark or profiling note before optimization.

## Development Workflow (Review Process)

- Every pull request MUST be reviewed by at least one other contributor (or, for solo work,
  self-reviewed against this constitution's checklist) before merge.
- Reviewers MUST explicitly confirm: (1) tests exist and cover edge cases, (2) calculation
  logic is documented with units/sources, (3) no floating-point exact-equality bugs,
  (4) packaging/version metadata is consistent with Principle IV.
- The `/speckit.analyze` and `/speckit.checklist` workflows SHOULD be used before
  `/speckit.implement` on any feature touching calculation logic, to catch spec/plan gaps
  early rather than during code review.

## Governance

This constitution supersedes all other informal practices for this repository. Amendments
require: (1) a documented rationale for the change, (2) a version bump per the policy below,
and (3) propagation of any dependent changes to `.specify/templates/*` and agent guidance
files in the same change.

Versioning policy (semantic versioning applied to governance):
- MAJOR: Backward-incompatible removal or redefinition of a principle.
- MINOR: A new principle or materially expanded guidance is added.
- PATCH: Wording clarifications, typo fixes, non-semantic refinements.

All pull requests and code reviews MUST verify compliance with the principles above.
Any deviation MUST be justified in the pull request description and, if it becomes a
recurring pattern, MUST trigger a proposed constitution amendment rather than repeated
ad-hoc exceptions. Use `.specify/memory/constitution.md` as the authoritative source for
runtime development guidance until a dedicated guidance file is introduced.

**Version**: 1.0.0 | **Ratified**: 2026-07-08 | **Last Amended**: 2026-07-08
