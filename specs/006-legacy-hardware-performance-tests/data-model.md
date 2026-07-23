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
