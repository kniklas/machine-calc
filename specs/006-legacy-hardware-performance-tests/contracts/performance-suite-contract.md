# Contract: Performance Test Suite (local invocation)

**Feature**: `006-legacy-hardware-performance-tests`

This is the interface contract for the new opt-in test suite as invoked by a developer or by CI.
There is no HTTP/library API change (FR-011); this document specifies the command-line/behavioral
contract instead, per plan.md's "Define interface contracts... appropriate for the project type".

## Invocation contract

| Aspect | Contract |
|---|---|
| Local opt-in command | `MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov` (documented verbatim in quickstart.md) |
| Default/blocking command (`pytest`, or CI's `test` job's exact `pytest --cov=machine_calc --cov-report=term-missing --cov-report=xml --cov-fail-under=90`) | MUST NOT execute any measurement logic in `tests/performance/` and MUST NOT change its own duration, pass/fail outcome, or coverage percentage versus before this feature existed (FR-006, SC-004). |
| Exit code (opt-in run) | Standard pytest semantics: `0` if every Performance Test Case's `time_passed` and `memory_passed` are both `True`; non-zero if any case fails either check. Degraded/best-effort enforcement (`cpu_pin_enforced=False` and/or `memory_ceiling_enforced=False`) does NOT by itself cause a non-zero exit — a case run in degraded mode can still "pass" on its measured values, per FR-009 (must not error/crash on unsupported platforms) and FR-010 (must clearly label the weaker signal, not force a failure). |
| Per-case report | For every Performance Test Case, output (via pytest's normal per-test result plus an explicit printed/logged line, so it is visible with `-s`/on failure without extra flags) states: case name, measured time, time budget, time pass/fail, measured memory, memory budget, memory pass/fail, and enforcement status for both dimensions (FR-005, FR-010, SC-003). |
| Failure message content | On any failed dimension, the assertion message names the calculation, the failed dimension (time and/or memory, reported as distinct failures if both fail), the measured value, the budget, and the overage amount/percentage — never a bare/generic assertion failure (FR-005, SC-003). |
| Extensibility | Adding a case for a new, future public calculation function requires only adding one new entry to the parametrized case table in `tests/performance/test_calculation_budgets.py` (or an equivalent registration point), not modifying `harness.py`'s enforcement/measurement logic (FR-012). |

## Platform-capability contract

| Platform | `cpu_pin_enforced` | `memory_ceiling_enforced` | Behavior |
|---|---|---|---|
| Linux (CI `ubuntu-latest`, Linux dev machines) | `True` (via `os.sched_setaffinity`) | `True` (via `resource.setrlimit(RLIMIT_AS, ...)`) | Fully-enforced run; both constraints simulated per FR-002/FR-003. |
| macOS dev machine | `False` (no `os.sched_setaffinity`) | Best-effort, commonly `False` in practice (`resource.setrlimit(RLIMIT_AS, ...)` is POSIX-supported on macOS, but the 128 MB ceiling typically fails with `ValueError`/`OSError` because the interpreter's own address space already exceeds it before the call) | Best-effort run; still measures and reports time/memory; both enforcements typically marked unenforced per FR-009/FR-010. |
| Windows dev machine | `False` (no `os.sched_setaffinity`) | `False` (no `resource` module) | Best-effort run; still measures and reports time/memory; both enforcements clearly marked unenforced per FR-009/FR-010; suite MUST NOT error/crash (FR-009). |

No platform causes the suite itself to fail to run or to silently report a false "fully enforced"
pass (FR-009, SC-005).
