# Implementation Plan: Legacy/Low-Power Hardware Performance Simulation Tests

**Branch**: `006-legacy-hardware-performance-tests` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-legacy-hardware-performance-tests/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a new, opt-in `tests/performance/` pytest suite that measures wall-clock execution time and
peak memory usage for every currently-existing public calculation entry point
(`machine_calc.calculate()` and the three `operations/drilling/formulas.py` functions), simulating
Constitution Principle V's single-core CPU and 64-128 MB memory ceiling on platforms where that
simulation is supported (Linux, via `taskset`/`sched_setaffinity` for the core pin and
`resource.setrlimit(RLIMIT_AS, ...)` for the memory ceiling), and degrading gracefully to a
best-effort, clearly-labeled mode elsewhere (e.g. macOS/Windows dev machines). The suite is kept
entirely outside the existing default/blocking `pytest` invocation (via a dedicated directory plus
a registered `performance` marker with default auto-skip) so it adds zero overhead or behavior
change to the existing gated test suite, and is wired into CI as a new, separate,
`continue-on-error: true` job that never affects required/blocking status checks. No existing
calculation logic, public API, CLI behavior, or existing test file is modified.

## Technical Context

**Language/Version**: Python 3.9-3.12 (matches `pyproject.toml` `requires-python = ">=3.9"` and the
existing CI test matrix's floor; CI itself runs the single `PYTHON_VERSION: "3.11"`)

**Primary Dependencies**: `pytest` (already a `dev` extra) for the suite runner; Python standard
library only for measurement/enforcement (`time.perf_counter` for wall-clock timing,
`resource.getrusage`/`resource.setrlimit` for memory ceiling + peak-RSS measurement on POSIX,
`os.sched_setaffinity`/`taskset` for the single-core pin on Linux, `platform.system()` for
capability detection). No new third-party dependency is introduced (Principle V: avoid heavy
runtime footprints; any new dependency needs PR justification, so this plan avoids adding one).

**Storage**: N/A (no persisted state; performance results are printed/reported per test run only)

**Testing**: pytest, as a new opt-in suite under `tests/performance/`, isolated from
`tests/unit`, `tests/integration`, `tests/contract`, `tests/static` by directory and by a
registered `performance` pytest marker

**Target Platform**: Per-platform enforcement (asymmetric, not a single "Linux vs. rest" split):
Linux (CI runner `ubuntu-latest`, and Linux developer machines) — full enforcement of both the
single-core pin (`os.sched_setaffinity`) and the memory ceiling (`resource.setrlimit(RLIMIT_AS,
...)`). macOS developer machines — technically has the POSIX `resource` module available, but
verified in practice to commonly fail/degrade the memory ceiling (the interpreter's own address
space typically already exceeds the 128 MB ceiling before the call), so macOS should be treated as
best-effort for both dimensions; the single-core pin is never enforced on macOS
(`sched_setaffinity` is Linux-only). Windows developer machines — best-effort only:
neither mechanism is enforced (`resource` and `sched_setaffinity` are both unavailable); the
suite still runs and measures time/memory, reporting both dimensions as skipped/best-effort per
FR-009/FR-010. See `contracts/performance-suite-contract.md`'s platform-capability table for the
authoritative per-platform matrix.

**Project Type**: Single Python library + CLI project (existing `src/` layout); this feature adds
a test-only addition, no new runtime package.

**Performance Goals**: N/A for the feature itself (the feature *measures* performance; it has no
runtime performance target of its own beyond "the suite itself completes in a reasonable local/CI
time", which is inherently satisfied since it wraps 4 fast calculation calls).

**Constraints**: Per Constitution Principle V and spec FR-003/FR-004: each measured calculation is
checked against a documented single value within the 0.5-1.0s wall-clock budget and a documented
single value within the 64-128 MB memory-ceiling range (this plan documents the exact chosen
values in `research.md`, since the constitution states them as ranges). Per FR-006/SC-004: the
suite MUST add zero execution time or behavior change to the existing default `pytest` invocation.

**Scale/Scope**: 4 public calculation entry points today (`calculate()`,
`calculate_drilling_metrics()`, `calculate_drilling_metrics_at_rpm()`,
`calculate_power_constrained_metrics()|`), each exercised with one or a small number of
representative, realistic inputs; suite is designed (per FR-012) to extend to future
operation modules without a redesign, but wiring in any new not-yet-existing operation is
explicitly out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Assessment |
|---|---|---|
| I. Code Quality | Applies | New test code follows existing lint/format/type conventions (`ruff`, `black`, `mypy` already run against `src/` and `tests/` in CI's `lint`/`typecheck` jobs); no new complexity in `src/`. PASS |
| II. Testing Standards | Applies (as the subject of the feature) | This feature *is* a new test suite; it does not weaken existing coverage requirements — `tests/performance` is excluded from the 90% coverage gate scope by being pure test code (coverage measures `src/machine_calc`, not test files) and by not running under the default `pytest` invocation at all. PASS |
| III. Calculation Robustness & Accuracy | Not touched | No calculation formula is modified; the suite only calls existing public functions with valid inputs. PASS |
| IV. Python Packaging & Versioning | Applies minimally | No new dependency, no public API change, no version bump needed (test-only addition). PASS |
| **V. Resource-Constrained Compatibility** | **Directly implements** | This feature exists specifically to give Principle V an automated check (today manual-only per spec's Current State). Chosen enforcement mechanisms (`sched_setaffinity`, `setrlimit`) are Linux-native per FR-009's acknowledgment; graceful degradation (FR-009/FR-010) is designed in from the start so the suite itself does not violate "MUST degrade gracefully rather than fail outright" when run on unsupported hardware/OS combinations. PASS — no trade-off note required because the feature's design already accounts for the constraint the principle raises (mechanism availability), rather than working around it. |
| VI. Extensibility by Design | Applies | Performance test cases are structured as a small, parametrized table (one entry per public calculation function) so a future operation module can add a case without restructuring the suite (FR-012). PASS |
| VII. Documentation & Publishing | Applies minimally | `quickstart.md` documents the new local command; no Sphinx-published API surface changes since no public API changes. PASS |
| VIII. Internationalization of User-Facing Messages | Not applicable | The performance suite's output is a developer/CI diagnostic report (akin to pytest's own output and CI job logs), not end-user-facing REPL/CLI/error text produced by `src/machine_calc`; Principle VIII scope is "REPL prompts/output, CLI help, and error messages" surfaced by the *application*, not internal test tooling. Treated the same as existing pytest failure output, which is not translated today. PASS (no localization required) |
| IX. Automated Code Quality, Complexity & Security Gates | Applies | New test code is covered by the existing `lint`, `complexity`, `security` (bandit `-r src` only, doesn't scan tests today, unaffected), `typecheck` (`mypy src/machine_calc`, unaffected since no `src/` changes) CI jobs; no new gate needed. PASS |

**Result**: No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-legacy-hardware-performance-tests/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── ci-performance-job-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/machine_calc/                     # UNCHANGED by this feature
├── operations/drilling/
│   ├── __init__.py                   # calculate() - measured, not modified
│   └── formulas.py                   # calculate_drilling_metrics(),
│                                      # calculate_drilling_metrics_at_rpm(),
│                                      # calculate_power_constrained_metrics()
│                                      # - measured, not modified
└── ...                                # everything else - untouched

tests/
├── unit/                             # UNCHANGED - existing, default, gated suite
├── integration/                      # UNCHANGED - existing, default, gated suite
├── contract/                         # UNCHANGED - existing, default, gated suite
├── static/                           # UNCHANGED - existing, default, gated suite
└── performance/                      # NEW - opt-in, non-default, non-gated suite
    ├── __init__.py
    ├── conftest.py                   # registers `performance` marker; auto-skips
    │                                  # collected performance tests unless an
    │                                  # explicit opt-in (env var/marker selection)
    │                                  # is given, so bare `pytest` (tests/, no
    │                                  # args) run by CI's `test` job is unaffected
    ├── budgets.py                    # documented time/memory budget constants
    │                                  # (single chosen values within the
    │                                  # constitution's 0.5-1.0s / 64-128MB ranges)
    ├── harness.py                    # measurement + enforcement helpers:
    │                                  # single-core pin, memory-ceiling rlimit,
    │                                  # peak-RSS sampling, platform capability
    │                                  # detection, pass/fail/degraded reporting
    └── test_calculation_budgets.py   # one parametrized case per public
                                       # calculation function (FR-001, FR-012)

pyproject.toml                        # ADD: `performance` marker registration
                                       # only (tool.pytest.ini_options.markers);
                                       # `testpaths`/`addopts` UNCHANGED so the
                                       # default/blocking command is unaffected

.github/workflows/ci.yml              # ADD: new `performance` job, separate
                                       # from the existing `test` job, marked
                                       # `continue-on-error: true` and excluded
                                       # from `quality-summary`'s `needs:`/
                                       # required-checks list
```

**Structure Decision**: Single-project layout (already in use). The feature adds one new
sibling directory to the existing `tests/` tree (`tests/performance/`), mirroring how
`tests/unit`, `tests/integration`, `tests/contract`, and `tests/static` are already organized as
separately-purposed suites under one `tests/` root — consistent with `pyproject.toml`'s
`testpaths = ["tests"]`. No `src/` changes and no new top-level directory are needed.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations — table intentionally omitted.*
