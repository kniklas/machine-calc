# Quickstart: Legacy/Low-Power Hardware Performance Simulation Tests

**Feature**: `006-legacy-hardware-performance-tests`

This guide validates the feature end-to-end once implemented. It does not contain implementation
code — see `data-model.md` and `contracts/` for the structures/behavior to build, and (a future)
`tasks.md` for the implementation breakdown.

## Prerequisites

- Python environment with the project installed in editable/dev mode:
  ```bash
  pip install -e ".[dev]"
  ```
- Linux is required to exercise the *fully-enforced* path (single-core pin + memory ceiling both
  active); macOS/Windows can validate the *degraded/best-effort* path (see
  `contracts/performance-suite-contract.md`'s platform-capability table).

## Scenario 1 — Local opt-in run reports pass/fail per calculation (User Story 1, SC-001, SC-002)

```bash
MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov -v
```

**Expected outcome**:
- All four currently-existing public calculation functions (`calculate()`,
  `calculate_drilling_metrics()`, `calculate_drilling_metrics_at_rpm()`,
  `calculate_power_constrained_metrics()`) each appear as a distinct test case in the output
  (SC-002: 100% coverage of existing public calculation functions).
- Each case's result line/output states its measured wall-clock time vs. the 1.0s budget and
  measured peak memory vs. the 128 MB budget (research.md #4), and whether each passed.
- On a currently-compliant codebase, the run exits `0`.

## Scenario 2 — Default/gated command is unaffected (FR-006, SC-004)

```bash
pytest
```

**Expected outcome**:
- Behaves identically to before this feature existed: same duration (no multi-second performance
  measurements run), same pass/fail outcome, same coverage percentage. `tests/performance/` tests
  are collected but auto-skipped (research.md #1) because `MACHINE_CALC_RUN_PERFORMANCE_TESTS` is
  unset.

## Scenario 3 — Graceful degradation on an unsupported platform (User Story 2 Acceptance Scenario 3, FR-009, SC-005)

On a macOS or Windows developer machine:

```bash
MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov -v
```

**Expected outcome**:
- The run completes (does not error/crash) and still reports measured time/memory per case.
- Output clearly marks `cpu_pin_enforced=False` (macOS and Windows) and, on Windows,
  `memory_ceiling_enforced=False` as well (per the platform-capability contract), so the result is
  legible as a degraded/best-effort signal rather than a silent false pass.

## Scenario 4 — Actionable failure report (User Story 3, SC-003)

To validate the failure-reporting path without waiting for a real regression, temporarily lower
`tests/performance/budgets.py`'s constants to an unreachable value (e.g. `0.0001` seconds) in a
scratch/local-only edit, then re-run Scenario 1's command.

**Expected outcome**:
- The failing case's output/assertion message names the calculation, states which dimension
  failed (time), the measured value, the configured budget, and the amount/percentage by which it
  was exceeded — not a bare `assert` failure.
- Revert the scratch edit afterward; this step is a manual validation aid only and must not be
  committed.

## Scenario 5 — CI informational job never blocks merge (User Story 2, SC-006)

Open (or inspect an existing) pull request after the CI workflow change lands:

**Expected outcome**:
- A `performance` job appears in the PR's checks list, runs on `ubuntu-latest`, and executes
  Scenario 1's command.
- Whatever the job's outcome (pass, fail, or degraded), the PR's required/blocking status checks
  (`lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test`, `build`, `docs`) are
  unaffected, and the PR remains mergeable subject to those checks alone
  (`contracts/ci-performance-job-contract.md`'s `continue-on-error: true` mechanism).
- The `performance` job does not appear as a row in the `quality-summary` PR comment (by design —
  see that contract's Non-goals section).

## Reference

- Budgets and their rationale: `research.md` #4
- Enforcement mechanisms and platform capability matrix:
  `contracts/performance-suite-contract.md`, `research.md` #2-#3
- CI wiring: `contracts/ci-performance-job-contract.md`
- Data structures: `data-model.md`
