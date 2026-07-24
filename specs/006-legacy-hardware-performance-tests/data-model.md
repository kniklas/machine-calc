# Data Model: Legacy/Low-Power Hardware Performance Simulation Tests

**Feature**: `006-legacy-hardware-performance-tests` | **Date**: 2026-07-23

This feature introduces no persisted storage and no changes to `src/machine_calc`'s domain model.
The "entities" below (from spec.md's Key Entities section) are in-memory Python data structures
used only within `tests/performance/`, existing for the duration of a single suite run.

## Performance Test Case

Represents one measured calculation: which public function it targets, the representative input
used to invoke it, the budgets it is checked against, and its most recent outcome.

**Fields**:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Stable, human-readable identifier (e.g. `"calculate_drilling_metrics"`, `"calculate() (standard mode)"`) used in reports and pytest's parametrized test IDs. |
| `target` | `Callable[..., Any]` | The public calculation function under test (one of `machine_calc.calculate`, `calculate_drilling_metrics`, `calculate_drilling_metrics_at_rpm`, `calculate_power_constrained_metrics`). |
| `call_args` / `call_kwargs` | `tuple`, `dict` | Representative, realistic input values (e.g. a 10mm diameter / 25mm depth mild-steel/carbide drilling case) used to invoke `target`. |
| `time_budget_seconds` | `float` | The enforced wall-clock budget for this case (research.md #4: `1.0`). |
| `memory_budget_bytes` | `int` | The enforced memory ceiling for this case (research.md #4: `128 * 1024 * 1024`). |

**Validation rules**: `call_args`/`call_kwargs` MUST be valid inputs that do not themselves trigger
the target function's own input-validation error path (this suite measures the happy-path cost of
a real calculation, not error handling). Every entry in FR-001's function list (`calculate()`,
`calculate_drilling_metrics()`, `calculate_drilling_metrics_at_rpm()`,
`calculate_power_constrained_metrics()`) MUST have at least one Performance Test Case (SC-002).

**State transitions**: None — each case is re-evaluated fresh on every suite run; no case persists
state across runs (no history/trend storage in this feature's scope).

## Performance Report (Result)

The output produced after invoking a Performance Test Case: measured values, whether each stayed
within budget, whether enforcement was active or degraded, and overage detail on failure.

**Fields**:

| Field | Type | Description |
|---|---|---|
| `case_name` | `str` | The `Performance Test Case.name` this result belongs to. |
| `measured_time_seconds` | `float` | Wall-clock time measured for the single call (research.md #5). |
| `measured_memory_bytes` | `int` | Peak memory (`ru_maxrss`, normalized to bytes per research.md #3) associated with the call. |
| `time_passed` | `bool` | `measured_time_seconds <= time_budget_seconds` (inclusive-pass, research.md #4). |
| `memory_passed` | `bool` | `measured_memory_bytes <= memory_budget_bytes` (inclusive-pass, research.md #4). |
| `cpu_pin_enforced` | `bool` | Whether the single-core pin (FR-002) was actually applied for this run (`True` on Linux where `os.sched_setaffinity` succeeded; `False` in degraded/best-effort mode per FR-009/FR-010). |
| `memory_ceiling_enforced` | `bool` | Whether the memory-ceiling `setrlimit` (FR-003) was actually applied for this run (`False` in degraded/best-effort mode per FR-009/FR-010). |
| `overage_detail` | `str \| None` | Human-readable overage message(s) when `time_passed` and/or `memory_passed` is `False` — states the calculation name, the failed dimension(s) (reported distinctly per spec's Edge Cases / US3 Acceptance Scenario 3), the measured value, the budget, and the amount/percentage exceeded (FR-005). `None` when both checks pass. |

**Validation rules**: `overage_detail` MUST be populated whenever `time_passed` is `False` or
`memory_passed` is `False`, and MUST name the calculation and each failed dimension separately
(never merging a time failure and a memory failure into one ambiguous message) — per FR-005 and
the spec's US3 Acceptance Scenario 3. `cpu_pin_enforced`/`memory_ceiling_enforced` MUST always be
present (never omitted) regardless of pass/fail outcome, so a "pass" recorded without enforcement
is distinguishable from one recorded with it, per FR-010.

**Relationships**: One Performance Report is produced per Performance Test Case per suite run
(1:1 for a given run); pytest's own per-test pass/fail status (asserted from `time_passed` and
`memory_passed`) and captured stdout/assertion message serve as the delivery mechanism for this
report — no separate file/DB artifact is introduced by this feature.

## Suite Run Summary (CI/quality-summary projection)

Derived, run-level aggregate over every Performance Report produced by one suite invocation.
This is *not* a new persisted entity — it is the specific reduction of the per-case Performance
Reports that the CI `performance` job's `$GITHUB_OUTPUT` step (contracts/ci-performance-job-
contract.md) computes and that `quality-summary` (specs/004-pr-quality-check-summary FR-010)
consumes as its single `performance` row. Introduced here because FR-013's Clarifications
(2026-07-23) pin down its exact shape.

**Fields**:

| Field | Type | Description |
|---|---|---|
| `status_label` | `Literal["pass", "fail", "⚠️ degraded", "skipped", "cancelled"]` | The run's outcome label surfaced to `quality-summary`. `⚠️ degraded` is a distinct label — never folded into `pass`/`fail` — computed as `not (cpu_pin_enforced_overall and memory_ceiling_enforced_overall)` (a simple boolean condition over the two run-level enforcement flags below), evaluated independently of whether every case's `time_passed`/`memory_passed` was `True` (FR-013 Clarifications #3/#5; specs/004 FR-010). `skipped`/`cancelled` are set only when the job itself did not execute or was cancelled before producing any per-case measurements. |
| `worst_case_time_seconds` | `float \| None` | `max(report.measured_time_seconds for report in run)` — the single highest measured wall-clock time across every Performance Report in the run. `None` only when no report was produced (skipped/cancelled/fully-degraded-before-measurement). |
| `worst_case_memory_bytes` | `int \| None` | `max(report.measured_memory_bytes for report in run)` — the single highest measured peak memory across every Performance Report in the run. `None` only when no report was produced. |
| `cpu_pin_enforced_overall` | `bool` | `all(report.cpu_pin_enforced for report in run)` — whether the single-core pin was active for *every* case in the run. |
| `memory_ceiling_enforced_overall` | `bool` | `all(report.memory_ceiling_enforced for report in run)` — whether the memory ceiling was active for *every* case in the run. |
| `metric_string` | `str \| None` | The exact text surfaced in the `quality-summary` row's metric column. When `worst_case_time_seconds`/`worst_case_memory_bytes` are not `None` (i.e. at least one real measurement was produced — on pass, fail, *and* degraded-but-measured runs alike, FR-013 Clarifications #4), this is `f"{worst_case_time_seconds:.2f}s / {worst_case_memory_bytes_in_mb}MB (budgets: {time_budget_seconds}s/{memory_budget_bytes_in_mb}MB)"`, e.g. `"0.42s / 58MB (budgets: 1.0s/128MB)"`. When no measurement was produced (`status_label` is `skipped` or `cancelled`, or the job degraded before any case ran), this is the standard `—` "no metric available" placeholder shared with every other check (FR-013 Clarifications #2; specs/004 FR-005) — never a bespoke string and never a stale prior-run value. |

**Validation rules**: `metric_string` MUST show real measured worst-case values whenever
`worst_case_time_seconds`/`worst_case_memory_bytes` are populated, even when `status_label` is
`fail` or `⚠️ degraded` — the `—` placeholder is reserved exclusively for skipped/cancelled/no-
measurement rows and MUST NOT be used to hide a genuine measured failure (contrast with the
`complexity` job's convention of falling back to a placeholder on failure). `status_label` MUST be
computed as `⚠️ degraded` whenever `cpu_pin_enforced_overall` is `False` OR
`memory_ceiling_enforced_overall` is `False`, regardless of the measured pass/fail outcome of any
individual case — a direct boolean check, not a judgment call about whether the missing
enforcement could plausibly have hidden a failure.

**Relationships**: Computed once per CI `performance` job run from that run's full set of
Performance Reports; consumed 1:1 by `quality-summary`'s `performance` row (specs/004-pr-quality-
check-summary FR-010/FR-011). Excluded from `quality-summary`'s overall-status computation
regardless of `status_label`'s value (including `⚠️ degraded` and `fail`), per FR-011.
