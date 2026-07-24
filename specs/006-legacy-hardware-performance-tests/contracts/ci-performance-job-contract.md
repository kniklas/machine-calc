# Contract: CI Informational Performance Job

**Feature**: `006-legacy-hardware-performance-tests`

Specifies how the new CI job integrates into `.github/workflows/ci.yml` without becoming a
blocking/required check (FR-008, SC-006), and without modifying any existing job.

## Job definition contract

- **New job name**: `performance` (distinct from the existing `test` job; does not replace or
  rename it).
- **Trigger**: Same `on:` events already defined for other non-schedule jobs (`push` to `main`,
  `pull_request`); guarded with `if: github.event_name != 'schedule'` like the existing
  `lint`/`complexity`/`typecheck`/`security`/`test`/`build`/`docs` jobs, since this is a per-change
  informational signal, not a scheduled scan.
- **Runner**: `ubuntu-latest`, matching every other job (so `cpu_pin_enforced`/
  `memory_ceiling_enforced` are both `True` for CI runs — the fully-enforced platform-capability
  row from `performance-suite-contract.md`).
- **Steps**: `actions/checkout@v4`, `actions/setup-python@v5` (same `PYTHON_VERSION` env var as
  every other job), `pip install -e ".[dev]"`, then the documented opt-in invocation:
  `MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov -s`.
- **Non-blocking mechanism**: The job step(s) running the performance suite MUST set
  `continue-on-error: true` (GitHub Actions' documented mechanism for "this step/job may fail
  without failing the workflow or affecting required status checks"), so a failing/flagged
  performance result never marks the job as a blocking failure to the PR's merge-requirement
  evaluation (FR-008, SC-006, Constitution Principle V does not require this to block — only
  Principle IX's *other* named gates are required-status-check gates).
- **Exclusion from merge-blocking, inclusion in the summary comment**: The `performance` job
  MUST NOT be added to any branch-protection required-status-check configuration, and its result
  MUST NOT affect merge eligibility (FR-008, SC-006). However, per FR-013, its result and
  achieved key metric MUST be surfaced as a distinct row in the `quality-summary` job's PR comment
  (specs/004-pr-quality-check-summary) — the job MUST be added to `quality-summary`'s `needs:` list
  and MUST expose two outputs (mirroring `complexity`'s `mi_summary` and `test`'s `coverage_pct`
  pattern): a `status_label` and a `metric` string, both computed from the run's Suite Run Summary
  (data-model.md). This row MUST be excluded from `quality-summary`'s overall-status computation
  (FR-011 of specs/004-pr-quality-check-summary), the same way a `skipped` check is excluded, even
  though it is now included in `needs:` and in the visible table.
- **Achieved-metric string format (FR-013 Clarifications, 2026-07-23)**: The `metric` output MUST
  be a single string reporting the worst-case (highest) measured wall-clock time and the
  worst-case (highest) measured peak memory across *all* of the run's Performance Reports,
  together with the time and memory budgets they were checked against — never a per-case
  breakdown. Format: `f"{worst_time:.2f}s / {worst_memory_mb}MB (budgets: {time_budget}s/
  {memory_budget_mb}MB)"`, e.g. `0.42s / 58MB (budgets: 1.0s/128MB)`. This value MUST be shown
  whenever the run actually produced per-case measurements — on a clean pass, on a genuine budget
  failure, and on a degraded-but-measured run alike (FR-013 Clarifications #4) — real measured
  values are never hidden behind a placeholder to mask a failure, unlike the `complexity` job's
  convention of falling back to a placeholder on failure.
- **Placeholder fallback (FR-013 Clarifications, 2026-07-23)**: The `metric` output MUST fall back
  to the standard `—` "no metric available" placeholder already used by other checks (FR-005 of
  specs/004-pr-quality-check-summary) only when the job was skipped, was cancelled, or degraded
  before producing any per-case measurement at all — never a bespoke string, and never a stale
  prior-run value.
- **Distinct `⚠️ degraded` status label (FR-013 Clarifications, 2026-07-23)**: The `status_label`
  output MUST be able to take the value `⚠️ degraded`, distinct from `pass`/`fail`/`skipped`/
  `cancelled`, so a within-budget-but-unenforced run is visibly different from a fully-enforced
  pass in the summary comment. `⚠️ degraded` MUST still be excluded from `quality-summary`'s
  overall-status computation (FR-011 of specs/004-pr-quality-check-summary), the same as `skipped`.
- **`⚠️ degraded` trigger condition (FR-013 Clarifications, 2026-07-23)**: `status_label` MUST be
  `⚠️ degraded` whenever *either* the run-level single-core enforcement flag
  (`cpu_pin_enforced_overall`) *or* the run-level memory-ceiling enforcement flag
  (`memory_ceiling_enforced_overall`) — data-model.md's Suite Run Summary — was `False` for that
  run, regardless of the measured pass/fail outcome of any individual case. This is a simple
  boolean condition (`not (cpu_pin_enforced_overall and memory_ceiling_enforced_overall)`)
  evaluated independently of whether the measurements themselves were within budget — there is no
  speculative reasoning about whether the missing enforcement could plausibly have hidden a
  failure.
- **Degraded-run signaling in CI**: Because the runner is always `ubuntu-latest` (Linux), CI runs
  are expected to be in the fully-enforced row of the platform-capability contract; if a future
  runner image ever lacks a mechanism, the job still completes (per FR-009) and its output/log
  reflects the `⚠️ degraded` status per the trigger condition above, rather than the job erroring
  — `continue-on-error: true` already guarantees the workflow itself does not fail either way.

## Non-goals for this job

- No codecov/coverage upload step — the performance suite runs with `--no-cov` (research.md #1)
  since it is not a coverage-relevant run and must not perturb the `test` job's coverage
  reporting pipeline.
- This job does not become a required/blocking status check, and its `continue-on-error: true`
  step-level result (rather than the job's `needs.performance.result`, which `continue-on-error`
  causes GitHub Actions to always report as `success`) MUST be the actual signal consumed for the
  metric/outcome surfaced to `quality-summary` — a dedicated step output (not the job's own
  `result`) is required so a genuinely failing/degraded run isn't misreported as passing in the
  summary comment.
