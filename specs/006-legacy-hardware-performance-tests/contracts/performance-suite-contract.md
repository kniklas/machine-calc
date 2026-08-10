# Contract: Performance Test Suite (local invocation)

**Feature**: `006-legacy-hardware-performance-tests`

This is the interface contract for the new opt-in test suite as invoked by a developer or by CI.
There is no HTTP/library API change (FR-011); this document specifies the command-line/behavioral
contract instead, per plan.md's "Define interface contracts... appropriate for the project type".

## Invocation contract

| Aspect | Contract |
|---|---|
| Local opt-in command | `MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov -s` (documented verbatim in quickstart.md) |
| Default/blocking command (`pytest`, or CI's `test` job's exact `pytest --cov=machine_calc --cov-report=term-missing --cov-report=xml --cov-fail-under=90`) | MUST NOT execute any measurement logic in `tests/performance/` and MUST NOT change its own duration, pass/fail outcome, or coverage percentage versus before this feature existed (FR-006, SC-004). |
| Exit code (opt-in run) | Standard pytest semantics: `0` if every Performance Test Case's `time_passed` and `memory_passed` are both `True`; non-zero if any case fails either check. Degraded/best-effort *enforcement* (`cpu_pin_enforced=False` and/or `memory_ceiling_enforced=False`) does NOT by itself cause a non-zero exit — a case run in degraded mode can still "pass" on its measured values, per FR-009 (must not error/crash on unsupported platforms) and FR-010 (must clearly label the weaker signal, not force a failure). **This leniency does NOT extend to an invalid memory *measurement*** (`memory_measurement_valid=False`, i.e. a missing/zero/negative `ru_maxrss` reading): such a case always fails (`memory_passed=False`), forcing a non-zero exit, regardless of enforcement status (issue #23). |
| Per-case report | For every Performance Test Case, output (via pytest's normal per-test result plus an explicit printed/logged line, so it is visible with `-s`/on failure without extra flags) states: case name, measured time, time budget, time pass/fail, measured memory, memory budget, memory pass/fail, enforcement status for both dimensions, and whether the memory measurement itself was valid (FR-005, FR-010, SC-003). |
| Failure message content | On any failed dimension, the assertion message names the calculation, the failed dimension (time and/or memory, reported as distinct failures if both fail), the measured value, the budget, and the overage amount/percentage — never a bare/generic assertion failure (FR-005, SC-003). When the memory failure is due to an invalid measurement rather than exceeding the budget, the message states this explicitly (e.g. "invalid memory measurement") instead of fabricating an overage amount from a missing/zero/negative reading. |
| Extensibility | Adding a case for a new, future public calculation function requires only adding one new entry to the parametrized case table in `tests/performance/test_calculation_budgets.py` (or an equivalent registration point), not modifying `harness.py`'s enforcement/measurement logic (FR-012). |

## Platform-capability contract

| Platform | `cpu_pin_enforced` | `memory_ceiling_enforced` | Behavior |
|---|---|---|---|
| Linux (CI `ubuntu-latest`, Linux dev machines) | `True` (via `os.sched_setaffinity`) | `True` (via `resource.setrlimit(RLIMIT_AS, ...)`) | Fully-enforced run; both constraints simulated per FR-002/FR-003; `resource` is available, so `memory_measurement_valid` is `True` for a healthy run. |
| macOS dev machine | `False` (no `os.sched_setaffinity`) | Best-effort, commonly `False` in practice (`resource.setrlimit(RLIMIT_AS, ...)` is POSIX-supported on macOS, but the 128 MB ceiling typically fails with `ValueError`/`OSError` because the interpreter's own address space already exceeds it before the call) | Best-effort run; still measures and reports time/memory; both *enforcements* typically marked unenforced per FR-009/FR-010 — but `resource.getrusage` IS available on macOS, so `memory_measurement_valid` is still `True` and the case can legitimately `pass` on its measured values despite the unenforced ceiling. |
| Windows dev machine | `False` (no `os.sched_setaffinity`) | `False` (no `resource` module) | Best-effort run for the *enforcement* mechanisms (both clearly marked unenforced per FR-009/FR-010; suite MUST NOT error/crash, FR-009) — but because the `resource` module itself is unavailable on Windows, `measured_memory_bytes` cannot be read at all, so `memory_measurement_valid` is always `False` and every case's memory check always fails (issue #23; this is an intentional exception carved out of FR-009's "must not force a failure" leniency, which applies only to enforcement, not to measurement). |

No platform causes the suite itself to error out, crash, or silently report a false "fully enforced"
pass (FR-009, SC-005). A platform without the memory-*measurement* capability (Windows) is expected
to always report a hard memory-check failure per issue #23, which is distinct from — and MUST NOT
be confused with — the softer "best-effort/degraded enforcement" leniency FR-009 grants for the
single-core pin and memory-ceiling *enforcement* mechanisms.
