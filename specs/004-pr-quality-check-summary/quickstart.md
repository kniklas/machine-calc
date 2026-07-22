# Quickstart: Validating the PR Quality Check Summary Comment

This guide validates the feature end-to-end after implementation. It does not duplicate the
full design (see [data-model.md](./data-model.md) and
[contracts/pr-summary-comment-contract.md](./contracts/pr-summary-comment-contract.md)); it
only lists prerequisites, commands, and expected outcomes.

## Prerequisites

- `.github/workflows/ci.yml` updated per plan.md's Project Structure section (new
  `quality-summary` job; `test` job emits `coverage_pct`; `complexity` job emits
  `mi_summary` via the updated `scripts/check_maintainability.py`).
- Repository Settings → Actions → General → Workflow permissions allows
  "Read and write permissions" (or the `quality-summary` job's own
  `permissions: pull-requests: write` block is sufficient — verify per
  `marocchino/sticky-pull-request-comment`'s README troubleshooting notes, research.md #1).
- A branch with a trivial, reviewable change, pushed to a non-fork branch of this repository
  (fork-PR behavior is validated separately below).

## Local pre-checks (fast feedback before pushing)

Run the same commands the `test` and `complexity` jobs run, to confirm the new output-capture
steps behave as expected before relying on a full Actions run:

```bash
pip install -e ".[dev]"

# Mirrors the `test` job's new coverage-percentage step
pytest --cov=machine_calc --cov-report=term-missing --cov-report=xml --cov-fail-under=90
coverage report --format=total
# Expected: a single integer (e.g. "93"), no extra text

# Mirrors the `complexity` job's script, including the new pass-path metric output
python scripts/check_maintainability.py src/
# Expected (passing case): the existing "All modules ... meet the Maintainability Index
# threshold" message; if GITHUB_OUTPUT is unset (as locally), no file-write is attempted.

# Confirm the pass-path metric write also works when GITHUB_OUTPUT is set, as it will be in CI
GITHUB_OUTPUT=$(mktemp) python scripts/check_maintainability.py src/ ; cat "$GITHUB_OUTPUT" 2>/dev/null || true
# Expected: a line like `mi_summary=avg=<NN.N> worst=<A-F>` in the temp file
```

## End-to-end validation: initial run (User Story 1)

1. Open a pull request against this repository from a branch with any trivial change.
2. Wait for the CI workflow to complete all jobs (`lint`, `complexity`, `typecheck`,
   `security`, `dependency-scan`, `test`, `build`, `docs`, `quality-summary`).
3. **Expected**: exactly one new comment appears on the pull request, containing:
   - A row for each of the eight checks with a clear pass/fail (or skipped/cancelled)
     indicator.
   - The test coverage percentage and Maintainability Index summary values alongside their
     respective rows.
   - A single overall status line.
4. This satisfies spec.md User Story 1's Independent Test and SC-002 (status determinable
   within 10 seconds without opening any workflow log).

## End-to-end validation: update in place (User Story 2)

1. On the same pull request from above, push an additional trivial commit (or re-run the
   workflow via the Actions UI/`gh workflow run`/`gh run rerun`).
2. Wait for the workflow to complete again.
3. **Expected**: the pull request still shows exactly one quality-check summary comment (not
   two), and its content/timestamp reflects the latest run.
4. Repeat several times in a row. **Expected**: the comment count on the PR never exceeds one
   (spec.md SC-003), satisfying User Story 2's Independent Test.

## End-to-end validation: metrics visible (User Story 3)

1. On the same pull request, inspect the posted comment's `test` and `complexity` rows.
2. **Expected**: the `test` row shows the numeric coverage percentage; the `complexity` row
   shows the Maintainability Index summary (e.g. average value and/or worst grade letter);
   the `lint`, `typecheck`, `security`, `dependency-scan`, `build`, and `docs` rows show a
   clear pass/fail/skipped/cancelled indicator with an explicit "no metric" placeholder
   (e.g. `—`), not a blank cell or a fabricated value (spec.md SC-004).

## Edge case validation

- **A quality-check job fails**: introduce a deliberate lint violation on a scratch branch,
  open a PR, let CI run. **Expected**: the comment shows `lint` as failed, overall status as
  `FAIL`, and every other check still reported accurately (not omitted or marked failed).
- **A job is skipped**: temporarily adjust an `if:` condition (or observe a job that
  legitimately does not run for the event) to confirm the summary row reads "skipped", not
  "failed" or silently absent.
- **Non-pull_request trigger**: push directly to `main` (or wait for the weekly `schedule`
  run) and confirm no quality-check summary comment is posted or updated on any pull request
  (spec.md SC-005).
- **Fork pull request**: open a pull request from a fork (read-only default `GITHUB_TOKEN`).
  **Expected**: the `quality-summary` job completes without failing the workflow even if the
  comment-posting step itself reports a permissions error in its logs (spec.md FR-008,
  Edge Cases); the underlying quality-check jobs' pass/fail results remain the authoritative
  merge signal regardless of whether the comment was posted.

## Done criteria

All of the above expected outcomes are observed; no `NEEDS CLARIFICATION` markers remain;
proceed to `/speckit.tasks` to generate the implementation task breakdown.
