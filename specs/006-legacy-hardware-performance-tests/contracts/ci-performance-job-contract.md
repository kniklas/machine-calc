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
  `MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ -m performance -p no:cacheprovider --no-cov`.
- **Non-blocking mechanism**: The job step(s) running the performance suite MUST set
  `continue-on-error: true` (GitHub Actions' documented mechanism for "this step/job may fail
  without failing the workflow or affecting required status checks"), so a failing/flagged
  performance result never marks the job as a blocking failure to the PR's merge-requirement
  evaluation (FR-008, SC-006, Constitution Principle V does not require this to block — only
  Principle IX's *other* named gates are required-status-check gates).
- **Exclusion from existing required-check aggregation**: The `performance` job MUST NOT be added
  to `quality-summary`'s `needs:` list or to any branch-protection required-status-check
  configuration — it is deliberately excluded from both the PR quality-summary comment's checks
  table and from merge-blocking, consistent with FR-008's "does NOT affect whether a pull request
  is allowed to merge."
- **Degraded-run signaling in CI**: Because the runner is always `ubuntu-latest` (Linux), CI runs
  are expected to be in the fully-enforced row of the platform-capability contract; if a future
  runner image ever lacks a mechanism, the job still completes (per FR-009) and its output/log
  reflects the degraded status rather than the job erroring — `continue-on-error: true` already
  guarantees the workflow itself does not fail either way.

## Non-goals for this job

- No new `outputs:` are surfaced to `quality-summary` (unlike `complexity`'s `mi_summary` or
  `test`'s `coverage_pct`) — this job is intentionally kept out of that aggregation entirely, per
  FR-008's "the informational job's results are visible on the pull request" being satisfied by
  the job's own visible log/step output, not by a new summary-comment row.
- No codecov/coverage upload step — the performance suite runs with `--no-cov` (research.md #1)
  since it is not a coverage-relevant run and must not perturb the `test` job's coverage
  reporting pipeline.
