# Feature Specification: Legacy/Low-Power Hardware Performance Simulation Tests

**Feature Branch**: `006-legacy-hardware-performance-tests`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Add simple performance tests that simulate the constrained hardware profile described in the constitution (single-core CPU, ~64-128MB memory ceiling, minimal clock speed) and assert each calculation module completes within the 0.5-1.0s budget and stays within the memory budget, run locally (e.g. via pytest) and/or in CI, to give the project an automated way to verify compliance with Constitution Principle V (Resource-Constrained Compatibility), which today is only checked manually/by reviewer judgment during PRs."

## Current State (Baseline)

Constitution Principle V ("Resource-Constrained Compatibility") requires machine-calc to run
within approximately 64-128 MB of RAM on a single-threaded CPU at minimal clock speeds, with
each individual calculation ideally completing within 0.5-1.0 seconds on that legacy/low-power
hardware profile, and requires any feature that cannot reasonably meet these constraints to be
flagged during planning with an explicit trade-off note. The Additional Constraints section
further requires that performance be measured, not assumed, and evaluated against this
legacy-hardware runtime target.

There is currently no automated check for any of this. Compliance with Principle V is verified
only by reviewer judgment during pull request review — there is no test, benchmark, or CI job
that measures execution time or memory usage against the constitution's stated budget.

The package currently exposes one operation module, drilling
(`src/machine_calc/operations/drilling/`), whose public calculation entry points are:

- `machine_calc.calculate()` (re-exported from `operations/drilling/__init__.py`), the top-level
  public API that dispatches to one of three calculation modes.
- `calculate_drilling_metrics()`, `calculate_drilling_metrics_at_rpm()`, and
  `calculate_power_constrained_metrics()` in `operations/drilling/formulas.py`, the underlying
  per-mode formula functions invoked by `calculate()`.

The existing automated test suite (`tests/unit`, `tests/integration`, `tests/contract`,
`tests/static`) is fast, always-on, and gates every pull request via CI (`.github/workflows/ci.yml`,
running on `ubuntu-latest`) with a 90% coverage requirement (`pyproject.toml`). This feature adds
a distinct, separately-run performance test suite; it does not modify the existing suite's
behavior, thresholds, or gating status, and it does not change any calculation logic, public API,
or CLI behavior.

## Clarifications

### Session 2026-07-23

- Q: What exactly should the "achieved key metric" string in the summary-comment row (FR-013)
  contain? → A: A single worst-case value across all performance cases for both time and memory,
  plus their budgets, e.g. `0.42s / 58MB (budgets: 1.0s/128MB)`.
- Q: When the CI performance job is skipped, cancelled, or fully degraded (errors before
  producing any per-case measurements), what should the achieved key metric string show? → A: The
  standard `—` "no metric available" placeholder already defined for other checks (FR-005 of
  specs/004-pr-quality-check-summary), not a bespoke text or a stale prior-run value.
- Q: FR-013 enumerates the performance row's possible results as pass, fail, degraded/best-effort,
  skipped, or cancelled — one more state than every other row. Should the summary comment render
  a distinct "degraded" status label, or fold degraded runs into pass/fail? → A: Render a distinct
  `⚠️ degraded` status label, separate from pass/fail/skipped/cancelled, so a within-budget-but-
  unenforced run is visibly different from a fully-enforced pass.
- Q: When the job produces real measurements but at least one case exceeds its budget (a genuine
  fail, not skip/cancel/degraded), should the metric string show the actual worst-case time/memory
  values, or fall back to the `—` placeholder (as `complexity` does on failure)? → A: Always show
  the real measured worst-case values whenever measurements were actually produced — on pass,
  fail, and enforced-but-failing runs; only skipped/cancelled/no-measurement cases fall back to
  `—`.
- Q: The suite tracks single-core enforcement and memory-ceiling enforcement as two independent
  flags (FR-010). Should the `⚠️ degraded` label trigger whenever *either* mechanism was inactive
  for that run, or only when the inactive mechanism could plausibly have hidden a failure? → A:
  Trigger `⚠️ degraded` whenever either single-core or memory-ceiling enforcement was inactive for
  that run, regardless of the measured pass/fail outcome — a simple boolean AND of the two
  enforcement flags, with no speculative reasoning about what it might have hidden.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer verifies a calculation meets the legacy-hardware time/memory budget before opening a PR (Priority: P1)

A contributor has changed or added a calculation (e.g. a new drilling formula, or a future
turning/milling operation) and wants to know, before opening a pull request, whether it still
meets Constitution Principle V's 0.5-1.0 second runtime target and the 64-128 MB memory ceiling
on the project's simulated legacy/low-power hardware profile. They run the opt-in performance
test suite locally and get a clear pass/fail result per calculation.

**Why this priority**: This is the core value of the feature — giving contributors and reviewers
an objective, repeatable answer to "does this comply with Principle V?" instead of relying on
guesswork or manual profiling. Without this, the feature delivers nothing.

**Independent Test**: Run the performance test suite locally (e.g. `pytest tests/performance` or
an equivalent opt-in marker/command) against the current codebase's existing drilling
calculations; confirm it produces a per-calculation time and memory result and an overall
pass/fail outcome, without requiring any other part of this feature to exist.

**Acceptance Scenarios**:

1. **Given** the performance test suite is installed and available, **When** a developer runs it
   locally on a supported platform, **Then** it measures wall-clock execution time for each public
   calculation function and reports whether each stayed within the 0.5-1.0 second budget.
2. **Given** the performance test suite is installed and available, **When** a developer runs it
   locally on a supported platform, **Then** it measures peak memory usage for each public
   calculation function and reports whether each stayed within the 64-128 MB budget.
3. **Given** a calculation currently meets both budgets, **When** the suite runs, **Then** it
   reports a pass for that calculation with the measured time and memory values.
4. **Given** the performance suite exists, **When** a developer runs the project's normal/default
   test command (the one CI uses to gate pull requests), **Then** the performance tests do not run
   and do not affect that command's pass/fail outcome or duration.

---

### User Story 2 - Reviewer/CI gets an informational signal without blocking merges (Priority: P2)

A pull request author or reviewer wants visibility into whether a change affects legacy-hardware
performance without the CI pipeline blocking merges on results that may vary by runner hardware or
platform-specific simulation support. The performance suite runs automatically in CI as a
non-blocking, informational job, and its results are visible on the pull request.

**Why this priority**: Automating the check in CI (even non-blocking) closes the gap between "a
developer remembered to run it locally" and "every PR gets checked," which is the difference
between an opt-in tool and genuine, consistent compliance visibility. It is second priority
because User Story 1 (a working local suite) must exist first and is independently useful even if
CI integration is never added.

**Independent Test**: Add or trigger a CI workflow run that includes the performance job on a
sample pull request; confirm the job executes, reports its results (e.g. as job output, an
annotation, or a summary), and that its outcome (pass, fail, or flagged) does not change the
required/blocking status checks needed to merge the pull request.

**Acceptance Scenarios**:

1. **Given** a pull request triggers CI, **When** the informational performance job runs, **Then**
   it executes on the CI runner's platform and produces the same kind of per-calculation
   pass/fail/flag report as the local run.
2. **Given** the informational performance job reports one or more calculations exceeding budget,
   **When** the pull request's merge requirements are evaluated, **Then** the pull request can
   still be merged (the job does not block merge).
3. **Given** the informational performance job cannot simulate the constrained profile on the CI
   runner (e.g. a required mechanism is unavailable), **When** the job runs, **Then** it reports
   this as a degraded/best-effort run rather than silently passing or crashing the workflow.

---

### User Story 3 - Contributor gets an actionable report when a calculation exceeds budget (Priority: P3)

A calculation exceeds the time or memory budget. Instead of a bare assertion failure, the
contributor sees which specific check failed (time or memory), the calculation involved, the
measured value, the budget it was compared against, and by how much it was exceeded — enough
detail to decide whether to optimize the calculation or document the overage as a trade-off in
the pull request description, per Principle V.

**Why this priority**: This directly supports the constitution's requirement to document
expected runtime/rationale for calculations that cannot meet the target. It is lower priority
than Stories 1-2 because a bare failing assertion is still usable (if less convenient) until
this refinement is added.

**Independent Test**: Deliberately run the suite against a calculation whose measured time or
memory exceeds its budget (e.g. via a lowered test-only threshold or a synthetic slow/heavy
calculation) and confirm the failure output names the calculation, the failed dimension
(time/memory), the measured value, the budget, and the overage amount.

**Acceptance Scenarios**:

1. **Given** a calculation's measured execution time exceeds 1.0 seconds, **When** the suite
   reports the result, **Then** the report identifies the calculation, states the measured time,
   the budget, and the amount/percentage by which it was exceeded.
2. **Given** a calculation's measured peak memory exceeds the configured ceiling, **When** the
   suite reports the result, **Then** the report identifies the calculation, states the measured
   memory, the budget, and the amount/percentage by which it was exceeded.
3. **Given** a calculation fails both the time and memory checks, **When** the suite reports the
   result, **Then** both failures are reported distinctly (not merged into one ambiguous message).

---

### Edge Cases

- What happens when the performance suite is run on a platform that does not support pinning the
  process to a single CPU core (e.g. macOS or Windows developer machines) or does not support
  the memory-ceiling enforcement mechanism used? The suite MUST degrade gracefully — running in a
  reduced-guarantee "best-effort" mode (still measuring time/memory and reporting results) or
  skipping the affected check with a clear message — rather than erroring out or silently
  reporting a false pass.
- What happens when a new calculation module/operation (e.g. a future turning or milling
  operation) is added to `src/machine_calc/operations/`? The suite's coverage of "each
  calculation" should be discoverable/extendable to new public calculation functions without
  requiring the whole suite to be redesigned (though wiring in a specific new operation module is
  out of scope for this feature, which covers only the currently-existing drilling operation).
- What happens when a calculation's measured time or memory is exactly at the boundary of its
  budget? The comparison MUST be well-defined (e.g. treat the upper bound as inclusive-pass, or
  document the chosen convention), not ambiguous.
- What happens on a machine or CI runner that is unusually slow or under contention (e.g. shared
  CI runner, background load), causing an otherwise-compliant calculation to intermittently
  exceed budget? Because this is an opt-in/informational suite (not a blocking PR gate), this is
  an accepted limitation rather than something the feature must fully eliminate; the report
  should still clearly show the measured value so a contributor can judge whether it was a
  fluke.
- What happens if the simulated single-core pin and the simulated memory ceiling conflict with
  each other or with the test runner's own overhead (e.g. pytest and its plugins consuming part
  of the 64-128 MB budget)? The suite's measurement approach must isolate, as much as reasonably
  possible, the calculation's own resource usage from the test harness's own overhead, and this
  approach's known limitations should be documented alongside the suite rather than silently
  ignored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide a performance test suite that measures, for each public
  calculation function currently exposed under `src/machine_calc/operations/` (at minimum
  `machine_calc.calculate()` and the per-mode formula functions in
  `operations/drilling/formulas.py`: `calculate_drilling_metrics()`,
  `calculate_drilling_metrics_at_rpm()`, and `calculate_power_constrained_metrics()`), its
  wall-clock execution time and its peak memory usage during that execution.
- **FR-002**: The suite MUST simulate a single-threaded/single-core CPU constraint while running
  these measurements, on platforms where such a constraint can be applied. Exact minimal
  clock-speed emulation is explicitly out of scope and is an accepted approximation of Principle
  V's "minimal clock speeds" language — the suite simulates the single-core aspect of the profile
  and measures actual (not clock-scaled) time on the host machine, not a literal frequency-scaled
  environment.
- **FR-003**: The suite MUST simulate a memory ceiling within the constitution's stated 64-128 MB
  range (the suite MUST document/configure which specific value(s) in that range it uses) and
  MUST determine whether each measured calculation's peak memory usage stays within that ceiling.
- **FR-004**: The suite MUST assert, for each measured calculation, that its wall-clock execution
  time falls within the constitution's stated 0.5-1.0 second budget (the suite MUST
  document/configure which specific value(s) in that range it uses as the enforced threshold).
- **FR-005**: When a calculation exceeds either the time budget or the memory budget, the suite
  MUST produce a report identifying: the calculation that failed, which check(s) failed (time,
  memory, or both), the measured value, the budget it was compared against, and the amount or
  percentage by which the budget was exceeded — not a bare/generic assertion failure.
- **FR-006**: The performance test suite MUST be opt-in: it MUST be organized separately from the
  existing default test suite (e.g., a distinct directory and/or pytest marker) such that running
  the project's standard/default test command (the one CI's blocking test job invokes) does not
  execute the performance tests and is not affected by their results or duration.
- **FR-007**: The performance test suite MUST be runnable on demand by a developer via a
  documented local command.
- **FR-008**: The performance test suite MUST also be able to run in CI as a separate,
  informational (non-blocking) job — its outcome (pass, fail, or degraded/best-effort) MUST NOT
  affect whether a pull request is allowed to merge.
- **FR-009**: On platforms or environments where the single-core pin and/or the memory-ceiling
  enforcement mechanism used by the suite is unavailable or unsupported (for example, non-Linux
  developer machines, since these mechanisms are primarily Linux-native), the suite MUST degrade
  gracefully: it MUST either run in a best-effort mode that still measures and reports time and
  memory without the unsupported enforcement, or skip the affected check(s) with a clear message
  explaining why — it MUST NOT error out, crash, or silently report a false pass as though the
  constraint had been enforced.
- **FR-010**: The suite MUST clearly indicate, per run and per platform, whether the single-core
  constraint and the memory ceiling were actually enforced or were run in degraded/best-effort/skipped
  mode, so results can be correctly interpreted (e.g. a "pass" recorded without the memory ceiling
  enforced is a weaker signal than one recorded with it enforced).
- **FR-011**: This feature MUST NOT change any existing calculation formula, public API signature
  or behavior, CLI behavior, or existing test suite's behavior, thresholds, or gating status. It
  adds only new, separate test tooling.
- **FR-012**: The suite's calculation coverage (which public functions are measured) MUST be
  identifiable/extendable so that a future new operation module under
  `src/machine_calc/operations/` can be added to the suite's coverage without redesigning the
  suite, though adding coverage for any specific not-yet-existing operation is out of scope for
  this feature.
- **FR-013**: The CI performance job's outcome and achieved key metric MUST be surfaced as a
  distinct row in the pull-request quality-check summary comment defined by
  specs/004-pr-quality-check-summary, in addition to (not instead of) the job's own visible
  log/step output — consistent with FR-008, this row's result MUST NOT be counted when that
  comment computes its overall pass/fail status. Per Clarifications (2026-07-23), the achieved
  key metric MUST be a single string reporting the worst-case (highest) measured wall-clock time
  and the worst-case (highest) measured peak memory across all of the suite's calculation cases,
  together with the time and memory budgets they were checked against, e.g.
  `0.42s / 58MB (budgets: 1.0s/128MB)` — not a per-case breakdown. When the job is skipped,
  cancelled, or fully degraded before any per-case measurements are produced, the metric MUST show
  the standard `—` "no metric available" placeholder used by other checks (FR-005 of
  specs/004-pr-quality-check-summary) rather than a bespoke string or a stale prior-run value.
  This row's status label MUST render a distinct `⚠️ degraded` state — separate from the
  pass/fail/skipped/cancelled labels used elsewhere in the comment — when the run completed
  without full single-core/memory enforcement (per FR-009/FR-010), so a within-budget-but-
  unenforced result is not visually indistinguishable from a fully-enforced pass. Whenever the
  run actually produces per-case measurements — whether the overall outcome is pass, fail
  (budget exceeded), or degraded — the metric string MUST show the real measured worst-case
  time/memory values; only a skipped, cancelled, or no-measurement run falls back to the `—`
  placeholder. The `⚠️ degraded` label MUST trigger whenever *either* the single-core enforcement
  flag or the memory-ceiling enforcement flag (FR-010) was inactive for that run — a simple
  boolean condition evaluated independently of the measured pass/fail outcome — rather than any
  attempt to infer whether the missing enforcement could plausibly have hidden a failure.

### Key Entities

- **Performance Test Case**: Represents one measured calculation — which public calculation
  function it targets, representative input values used to invoke it, the time budget and
  memory budget it is checked against, and the pass/fail/degraded outcome of its most recent run.
- **Performance Report**: The output produced after a suite run — a per-calculation breakdown of
  measured time, measured memory, whether each stayed within budget, whether enforcement of the
  single-core/memory constraints was active or degraded for that run, and (for any failure) the
  overage detail needed to act on it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can determine, within one local command invocation, whether every
  currently-existing public calculation function complies with Constitution Principle V's stated
  time (0.5-1.0s) and memory (64-128MB) budgets, without needing to write any new test code
  themselves.
- **SC-002**: 100% of the public calculation functions existing under
  `src/machine_calc/operations/` at the time this feature ships are covered by a performance test
  case.
- **SC-003**: When a calculation fails a budget check, a contributor can identify, from the report
  alone (without reading suite source code), which calculation and which dimension (time or
  memory) failed, and by how much — in other words, no calculation failure is reported as an
  unexplained/generic error.
- **SC-004**: Running the project's normal/default test command (the one that currently gates
  pull requests) takes the same amount of time and produces the same pass/fail outcome after this
  feature is added as it did before — i.e., zero added overhead or behavior change to the existing
  gated suite.
- **SC-005**: On a developer machine where the simulated single-core/memory-ceiling enforcement is
  unsupported, the suite still completes a run and reports results (in degraded/best-effort mode)
  rather than failing to run at all.
- **SC-006**: A pull request whose CI run includes the informational performance job, and in which
  that job reports one or more calculations exceeding budget, can still be merged (subject to all
  other existing required checks passing) — the informational job never blocks a merge.

## Assumptions

- "Each individual calculation" (per Principle V) is interpreted, for this feature, as each
  currently-existing public calculation entry point under `src/machine_calc/operations/`: the
  top-level `machine_calc.calculate()` dispatcher and the underlying per-mode formula functions
  in `operations/drilling/formulas.py`. Internal/private helper functions (e.g. validation or
  unit-conversion helpers) are not separately measured as "calculations" for this feature.
- The suite selects one or more concrete representative input value sets (diameter, depth,
  material, tool, mode, etc.) per calculation for measurement; it is not expected to exhaustively
  measure every possible input combination.
- The suite enforces one specific memory ceiling value chosen from within the constitution's
  64-128 MB range (rather than testing at every value in that range), and one specific time
  budget value chosen from within the 0.5-1.0 second range; the exact values are an
  implementation decision for the planning phase, not fixed by this specification.
- "Simulating a single-threaded CPU constraint" is accepted to mean constraining the test
  process/thread to run on a single CPU core (e.g. via OS-level affinity or an equivalent
  mechanism), not emulating a specific historical CPU model or literal reduced clock frequency;
  actual measured wall-clock time reflects the host machine's real speed, which may be faster
  than genuinely old/low-power hardware — this is a known, accepted approximation, not a defect.
- CPU-core pinning (single-core simulation) is assumed to be reliably available only on Linux
  (including the `ubuntu-latest` GitHub Actions runner already used by CI per
  `.github/workflows/ci.yml`), via OS-level CPU affinity, and is assumed to be unavailable on
  macOS and Windows developer machines. Memory-ceiling enforcement via the POSIX `resource`
  module (`resource.setrlimit(RLIMIT_AS, ...)`) is technically available on both Linux and macOS
  and unavailable only on Windows, but in practice it is verified to reliably succeed on Linux
  while commonly failing/degrading on macOS (the interpreter's own address space typically already
  exceeds the 128 MB ceiling before the call, raising `ValueError`/`OSError`), so macOS
  memory-ceiling enforcement should be treated as best-effort rather than guaranteed. This
  asymmetric
  degradation (full enforcement on Linux, partial enforcement on macOS, best-effort measurement
  only on Windows) is why graceful degradation (FR-009) is required rather than treated as an
  edge case that can be ignored.
- The performance suite is understood to be inherently sensitive to host machine load and
  hardware, so its results — especially in local, non-CI runs — are advisory/diagnostic rather
  than a strict pass/fail gate on the developer's own machine; the existing default/gated test
  suite (`tests/unit`, `tests/integration`, `tests/contract`, `tests/static`, run via the project's
  existing pytest configuration in `pyproject.toml`) remains the only pull-request-blocking test
  suite, unaffected by this feature.
- No new runtime dependency is assumed to be required to ship this feature beyond what is already
  available in the project's existing `dev` optional-dependency group (`pyproject.toml`) or the
  Python standard library; if the planning phase determines a new dependency (e.g. a
  memory-profiling library) is warranted, that is a planning-time decision, not fixed here.
