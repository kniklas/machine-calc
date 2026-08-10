---
name: code-review
description: Repo-specific context for GitHub Copilot code review on machine-calc pull requests. Applies constitution-derived checks around calculation correctness, resource-constrained hardware limits, packaging conventions, and lint/type/test gates whenever reviewing changes in this repository.
---

# Code Review Skill (machine-calc)

Use this skill whenever reviewing a pull request in this repository. It
gives Copilot code review repo-specific context beyond generic best
practices: this project's constitution
(`.specify/memory/constitution.md`), CI gates, and conventions in
`.github/instructions/python.instructions.md`.

## 1. Priorities, in order

1. **Calculation correctness** — this is a metal-machining calculation
   library; a wrong number is worse than a crash or a missing feature.
2. **Resource-constrained compatibility** — the tool must run on old,
   low-power hardware (single core, ~64-128 MB RAM).
3. **Test coverage and regression safety.**
4. **Extensibility** — new operations/units must not require rewriting
   shared infrastructure.
5. Style/lint/type issues (already enforced by CI; flag only if CI would
   miss them, e.g. logic hidden inside a string or comment).

## 2. Calculation correctness (Constitution Principles I & III)

Flag any of the following in changed calculation code
(`src/machine_calc/**`, especially `operations/*/formulas.py`):

- Floating-point equality checks using `==` instead of `math.isclose` (or
  an explicit tolerance).
- Missing input validation (type/range/unit) before a value is used in a
  formula — invalid input must raise a clear, actionable error, never
  silently produce a wrong number.
- Unhandled edge cases: division by zero, negative square roots, zero/empty
  inputs, unit mismatches.
- A formula or constant taken from an external standard/reference without a
  code comment citing that source.
- A public calculation function without a docstring documenting inputs,
  outputs, units of measurement, and valid ranges.
- Magic numbers with physical/mathematical meaning that aren't named or
  explained.

## 3. Resource-constrained compatibility (Constitution Principle V)

This project must run within ~64-128 MB RAM on a single-threaded, low-clock
CPU, and each calculation should ideally complete within 0.5-1.0 seconds on
that hardware profile (enforced by the opt-in suite under
`tests/performance/`, budgets in `tests/performance/budgets.py`).

- New dependencies with a non-trivial runtime memory footprint (e.g. a
  numerical/data-science stack) MUST be justified in the PR description —
  flag if it's a heavy dependency (e.g. `numpy`, `pandas`, `scipy`) added
  without justification, when the standard library or a lighter dependency
  would do.
- New calculation logic that clearly can't meet the time/memory budget MUST
  document the expected runtime/rationale in the PR description.
- Any change to `tests/performance/harness.py`'s measurement/validation
  logic (child-process isolation, `ru_maxrss` handling, budget comparisons)
  is high-risk: a `0`/`None`/negative memory reading MUST always be treated
  as an invalid measurement and fail the case — never silently reported as
  a passing "0 bytes used" result. Flag any change that could reintroduce
  that class of bug (see issue #23's original symptom: `0.00s / 0MB` yet
  `pass=True`).

## 4. Testing standards (Constitution Principle II, non-negotiable)

- Every new/changed calculation function needs unit tests covering nominal
  inputs, boundary values, zero/negative/empty inputs, and a known
  reference result.
- Bug fixes MUST include a regression test that would fail before the fix.
- Multi-step calculation pipelines (chained formulas, unit conversions)
  need integration-level coverage, not just isolated unit tests.
- Target coverage is 90% (`pyproject.toml`'s `--cov-fail-under=90`); flag
  PRs that drop coverage without justification.
- New test files under `tests/performance/` are auto-skipped by default
  (see `tests/performance/conftest.py`) — any test meant to run in the
  default/blocking suite belongs under `tests/unit/`, `tests/integration/`,
  or `tests/contract/` instead, not `tests/performance/`.

## 5. Extensibility (Constitution Principle VI)

- Operation-specific logic (e.g. drilling's spindle speed/feed/torque/power
  formulas) must live behind a per-operation module/interface
  (`operations/<name>/`), not be hard-coded into shared infrastructure
  (CLI, config loading, unit conversion, material/tool registries).
- Shared cross-cutting concerns (validation, unit conversion, error
  reporting) belong in shared components, not duplicated per operation.

## 6. Packaging & versioning (Constitution Principle IV)

- `pyproject.toml` is the single source of build/project metadata (no
  `setup.py`-only distribution); dependencies must be declared there.
- Public API changes must follow PEP 8 naming / PEP 257 docstrings.
- Breaking changes to the public API require a MAJOR version bump and a
  changelog entry.

## 7. Style conventions (`.github/instructions/python.instructions.md`)

- `black` formatting, `ruff`/`flake8` linting, `snake_case`/`PascalCase`/
  `UPPER_SNAKE_CASE` naming, grouped+alphabetized imports, f-strings over
  `%`/`.format()`.
- No bare `except:`, no mutable default arguments, no wildcard imports, no
  silent exception swallowing (`except Exception: pass`).
- Prefer `dataclasses` over manual `__init__` boilerplate for simple data
  containers.

## 8. Cross-referencing issues

If the PR description references a GitHub issue (e.g. `Fixes #23`),
confirm the diff actually satisfies that issue's stated acceptance
criteria/suggested fix — not just a partial or superficial mitigation.
