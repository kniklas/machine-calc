# Research: Legacy/Low-Power Hardware Performance Simulation Tests

**Feature**: `006-legacy-hardware-performance-tests` | **Date**: 2026-07-23

All items below resolve open technical questions raised by the Technical Context; the spec has no
outstanding `[NEEDS CLARIFICATION]` markers (checklist already passed per the task input), so this
research focuses on *how*, not *whether*, to build each mechanism.

## 1. Keeping the suite fully opt-in / non-default (FR-006, SC-004)

**Decision**: Put performance tests in `tests/performance/`, register a `performance` pytest
marker in `pyproject.toml` (`[tool.pytest.ini_options] markers = ["performance: ..."]`), and add a
`tests/performance/conftest.py` `pytest_collection_modifyitems` hook that auto-applies
`pytest.mark.skip(reason=...)` to every item under `tests/performance/` unless an explicit
environment variable (`MACHINE_CALC_RUN_PERFORMANCE_TESTS=1`) is set. Leave `pyproject.toml`'s
existing `testpaths = ["tests"]` and `addopts` untouched.

**Rationale**:
- `testpaths = ["tests"]` means a bare `pytest` (what CI's `test` job and any local default run
  invoke) *will* discover `tests/performance/*.py` files by default, since it's a subdirectory of
  `tests/`. An env-var-gated auto-skip (rather than relying on developers remembering `-m` or
  `--deselect` flags) guarantees SC-004 ("zero added overhead or behavior change") even if a
  future contributor runs `pytest` with different flags than today's CI command — skipped tests
  still cost a small, near-zero collection step, not the actual 0.5-1.0s+ measurement runs.
- Using an env var (rather than only a marker) makes the opt-in explicit and greppable, and works
  identically for local developer runs (FR-007) and the future CI job (FR-008) without needing two
  different mechanisms.
- Registering the marker (even though the auto-skip hook is env-var-based, not marker-selection-
  based) still lets `pytest --markers` document intent and lets a developer optionally run
  `pytest tests/performance -m performance` for discovery, and avoids an "unknown marker" warning
  under `--strict-markers`-style configs some IDEs default to.
- Coverage: `--cov-fail-under=90` in `addopts` measures `src/machine_calc` (per
  `[tool.coverage.run] source = ["machine_calc"]`), not test file coverage, so adding
  `tests/performance/*.py` does not change the coverage percentage computed by the existing
  gated `test` job even when that job's `pytest` invocation technically collects (then
  auto-skips) the new files.

**Alternatives considered**:
- *Directory outside `tests/` entirely (e.g. top-level `performance/`)*: rejected — `testpaths`
  would need editing to still let CI/local runs reach it conveniently, and it breaks the
  established convention (`tests/unit`, `tests/integration`, `tests/contract`, `tests/static`) of
  every test suite living under `tests/`.
- *Marker-only opt-out via `addopts = "... -m 'not performance'"`*: rejected — this changes
  `pyproject.toml`'s global `addopts`, which every `pytest` invocation (including IDE
  test-runner integrations that may not intend to filter) would inherit, and a locally-set
  `-m performance` on the command line conflicts with an `-m` already present in `addopts`
  (pytest does not merge two `-m` values). The auto-skip-via-env-var hook avoids touching
  `addopts` at all.
- *`pytest.ini`/`--ignore` at the CLI level only*: rejected — depends on every future invocation
  (local docs, IDE, CI) remembering to pass the flag; the whole point of FR-006 is that the
  *existing* default command's behavior must not depend on new flags being added to it.

## 2. Simulating a single-core CPU constraint (FR-002, FR-009)

**Decision**: On Linux, pin the current process to exactly one CPU core using
`os.sched_setaffinity(0, {core_id})` (stdlib, no `taskset` subprocess needed — Python exposes the
same syscall directly since Python 3.3 on platforms that support it). Restore the prior affinity
mask on teardown. On any platform where `os.sched_setaffinity` is unavailable (macOS, Windows —
`hasattr(os, "sched_setaffinity")` is `False` there), skip the pin and record `cpu_pin_enforced =
False` in that test case's result, per FR-009/FR-010.

**Rationale**:
- `os.sched_setaffinity`/`os.sched_getaffinity` are stdlib, added specifically for this use case,
  and avoid shelling out to `taskset` (an extra subprocess + external-binary dependency that is
  itself not guaranteed present on minimal Linux images, and unavailable on macOS entirely).
- Detecting availability via `hasattr(os, "sched_setaffinity")` is a simple, no-subprocess,
  no-exception-driven capability check appropriate for the graceful-degradation requirement.
- Restoring the original affinity mask after each test avoids leaking single-core pinning to
  later tests in the same process/session.

**Alternatives considered**:
- *Shelling out to `taskset -c 0 pytest ...`*: rejected as the primary mechanism — it pins the
  whole pytest process (harder to scope per-calculation and to combine cleanly with per-test
  memory-ceiling enforcement and reporting) and adds a hard dependency on an external binary not
  installed by default on macOS or minimal containers. Documented in `quickstart.md` only as an
  optional, fully-external alternative a developer may already use.
- *`multiprocessing`/subprocess-per-test with CPU affinity set in the child*: rejected as
  unnecessary complexity for this feature's scope (measuring existing fast, non-threaded pure
  calculation functions); `sched_setaffinity(0, ...)` on the current process is sufficient since
  none of the four measured functions spawn their own threads/processes.

## 3. Simulating a memory ceiling (FR-003, FR-009) and measuring peak memory (FR-001)

**Decision**: Use `resource.setrlimit(resource.RLIMIT_AS, (ceiling_bytes, ceiling_bytes))`
(stdlib `resource` module, POSIX-only: Linux and macOS) to cap the process's total address space
for the duration of each measured call, and read peak memory via
`resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` (peak resident set size) before and after each
call, using the delta (or the post-call absolute value, whichever `harness.py` documents) as the
measured figure. On Windows (`resource` module does not exist there), or if `setrlimit` raises
`ValueError`/`OSError` for the chosen limit on a given platform, skip ceiling enforcement and
record `memory_ceiling_enforced = False`, still reporting the measured `ru_maxrss` value per
FR-009/FR-010. **Verified in practice**: on macOS, `setrlimit(RLIMIT_AS, ...)` at the 128 MB
ceiling reliably raises `ValueError`/`OSError` even before the measured call runs, because the
Python interpreter's own address space typically already exceeds 128 MB by the time the test
suite starts. So while `resource` is technically available on macOS, memory-ceiling enforcement
there is in practice commonly degraded (`memory_ceiling_enforced = False`) rather than guaranteed
— it should be treated as best-effort on macOS, not as a reliable second enforced platform.

**Rationale**:
- `resource` is stdlib and already POSIX-portable across Linux and macOS (the two Unix-like dev
  platforms this project's contributors are likely to use per the constitution's "Debian
  stable"-class target and general Python packaging conventions), avoiding a new dependency
  (Principle V: avoid heavy runtime footprints).
- `RLIMIT_AS` (virtual address space) is the standard POSIX mechanism for capping a process's
  memory ceiling and will raise `MemoryError`/`OSError` inside the measured call if exceeded,
  which the harness catches and reports as a budget failure rather than letting it crash the
  suite.
- `ru_maxrss` is the conventional cross-Unix "peak memory used so far by this process" figure
  pytest-benchmark-style tools typically approximate with; using the stdlib call avoids adding
  `psutil` or `memory_profiler` as a new dependency.
- On Linux, `ru_maxrss` is reported in **kilobytes**; on macOS/BSD it is reported in **bytes** —
  `harness.py` normalizes this platform difference explicitly (via `platform.system()`) so the
  reported/compared value is always in a single, documented unit (bytes), avoiding a subtle
  10x-off-by-unit bug on macOS dev machines.

**Alternatives considered**:
- *`tracemalloc`*: considered for pure-Python allocation tracking, but rejected as the primary
  metric — it only tracks Python-level object allocations, not total process RSS/address space
  (e.g. C-extension or interpreter overhead), so it would understate real memory pressure
  relative to the constitution's "64-128 MB of RAM" framing, which is about total process
  footprint, not just Python object graphs. Documented as a secondary/optional diagnostic that
  `harness.py` MAY expose but does not use as the pass/fail metric.
- *`psutil.Process().memory_info().rss`*: rejected — adds a new third-party dependency for
  functionality the stdlib `resource` module already provides on the supported platforms.
- *`ulimit -v` shell wrapper around `pytest`*: rejected as the primary mechanism (same rationale
  as `taskset` in item 2 — an external/subprocess-only mechanism is harder to scope per test case
  and to combine with per-test reporting); documented in `quickstart.md` as an optional
  additional/manual verification a developer can layer on top.

## 4. Choosing concrete threshold values within the constitution's stated ranges (FR-003, FR-004)

**Decision**: Enforce a time budget of **1.0 second** (the upper/more permissive bound of the
constitution's 0.5-1.0s range) and a memory ceiling of **128 MB** (the upper/more permissive bound
of the 64-128 MB range), both defined as named constants in `tests/performance/budgets.py`, with
the boundary treated as an **inclusive pass** (`measured <= budget` passes; per spec's Edge Cases
section, the convention must be well-defined, not ambiguous).

**Rationale**:
- The constitution phrases both figures as approximate ranges ("approximately 64-128 MB", "ideally
  ... within 0.5-1.0 seconds"), explicitly leaving the exact enforced value to be
  documented/configured by whichever tool implements the check (constitution Principle V + spec
  FR-003/FR-004 both require the suite to "document/configure which specific value(s)... it
  uses"). Choosing the upper (more permissive) bound of each range avoids false-positive failures
  for calculations that are compliant with the *intent* of the range but would fail against an
  artificially strict lower-bound choice, while still providing a real, enforced ceiling.
- Defining both as named constants in one small module makes the chosen values easy to find,
  reference from the report, and revisit later without hunting through test bodies.

**Alternatives considered**:
- *Lower-bound values (64 MB / 0.5s)*: rejected as the default — more likely to produce noisy
  false failures from harness/interpreter overhead alone (see item 5), which would undermine
  trust in the suite; the suite still *reports* the exact measured value, so a contributor
  wanting the stricter reading can compare manually.
- *Per-calculation-mode-specific budgets*: rejected for this feature's scope — the constitution
  states one range for "each individual calculation" uniformly; introducing per-case budgets
  without a documented reason would add complexity FR-003/FR-004 do not call for.

## 5. Isolating calculation cost from harness/pytest overhead

**Decision**: `harness.py` measures wall-clock time with `time.perf_counter()` immediately
wrapping *only* the call to the target calculation function (not fixture setup, not pytest's own
collection/reporting), and takes the `ru_maxrss` baseline reading immediately before entering that
timed block, comparing it to the reading taken immediately after — documenting in the module
docstring that `ru_maxrss` is a whole-process, monotonically-non-decreasing peak, so it can only
approximate the *incremental* cost of one call amid pytest's own baseline footprint, and that
running each measured test in relative isolation (avoiding accumulating many measurements in one
process where practical) reduces but does not eliminate that shared baseline.

**Rationale**: Directly answers the spec's Edge Cases item about isolating calculation cost from
harness overhead; stdlib-only, minimal-overhead instrumentation keeps the measurement itself from
materially affecting the results it reports.

**Alternatives considered**:
- *Running each performance test in its own subprocess for true isolation*: considered as a
  stronger isolation technique, but rejected as the default given added complexity/runtime cost
  for a suite whose own runtime is not a hard requirement here; noted in `quickstart.md` as a
  documented limitation rather than solved with subprocess-per-case machinery, consistent with
  the spec's edge case wording ("this approach's known limitations should be documented alongside
  the suite rather than silently ignored").
