# Phase 0 Research: PR Quality Check Summary Comment

All items below resolve the "how" behind spec.md's functional requirements. No
`NEEDS CLARIFICATION` markers remain in the Technical Context.

## 1. How should the summary be posted/updated as a single PR comment?

**Decision**: Use the third-party GitHub Action `marocchino/sticky-pull-request-comment`,
pinned to `@v3.0.5`, with a stable `header: quality-check-summary` input and no `recreate`/
`append`/`hide` flags.

**Rationale**:
- The action's default behavior (no `recreate`/`append`) is exactly "create a comment if none
  with this `header` exists yet, otherwise edit that same comment's body in place" — which is
  precisely spec.md FR-003/FR-009 (at most one summary comment per PR, converging to the
  latest run's results even across many rapid re-runs, per the Edge Cases section).
- `header` is a hidden marker embedded in the comment body, so it reliably locates "our"
  comment even if maintainers add unrelated PR comments in between, satisfying FR-009's
  "identifiable by the system... via a stable marker" requirement without any custom
  comment-search logic.
- It is a small, single-purpose, widely used action (avoids hand-rolling comment
  create/update/list logic with `actions/github-script`, which would require writing and
  maintaining custom JS/TS against the REST API for the same behavior this action already
  provides out of the box).
- Requires only `permissions: pull-requests: write` on the job, matching the "existing
  CI/GitHub Actions identity and standard pull-request comment permissions" assumption in
  spec.md's Assumptions section (no new bot/service account).

**Alternatives considered**:
- `actions/github-script` with hand-written find-or-create-or-update logic against
  `GET/POST/PATCH /repos/{owner}/{repo}/issues/{number}/comments`. Rejected as unnecessary
  custom code for a well-solved, common CI need; higher maintenance burden for equivalent
  behavior.
- Always creating a new comment on every run. Rejected outright — this is precisely what
  FR-003 and User Story 2 prohibit (comment clutter, no single current-state view).
- `peter-evans/create-or-update-comment`. A viable alternative with similar
  find-by-marker/update semantics, but `sticky-pull-request-comment`'s `header` option and
  `path`-based file input (see #5 below) map slightly more directly onto "build a Markdown
  file, then post it," so it was preferred; either would satisfy the functional requirements.

## 2. How does the summary job read each quality-check job's pass/fail/skipped/cancelled state?

**Decision**: List all eight existing jobs (`lint`, `complexity`, `typecheck`, `security`,
`dependency-scan`, `test`, `build`, `docs`) in the new `quality-summary` job's `needs:`, and
read each one's terminal state from the built-in `needs.<job-id>.result` context, which
GitHub Actions populates with one of `success`, `failure`, `cancelled`, or `skipped`.

**Rationale**:
- This is a native GitHub Actions capability requiring no extra plumbing (no artifacts, no
  custom status file) to learn each dependency job's outcome, and it natively distinguishes
  all four states spec.md's Edge Cases and FR-007 require preserving (in particular
  `skipped`, e.g. a job whose own `if:` condition didn't match, and `cancelled`).
- By default, a job with `needs:` only runs if all needed jobs succeeded. The
  `quality-summary` job instead sets `if: always() && github.event_name == 'pull_request'` so
  it still runs (and can report accurately) even when one or more needed jobs failed or was
  cancelled — otherwise the summary job itself would simply be skipped whenever any check
  failed, defeating User Story 1's Acceptance Scenario 3 (summary must show which check(s)
  failed).
- spec.md's Assumptions section scopes `dependency-scan`, `build`, and `docs` into the
  summary "only if they run as part of the same pull-request-triggered workflow." Reviewing
  the current `.github/workflows/ci.yml`: `lint`, `complexity`, `typecheck`, `security`,
  `test`, `build`, and `docs` all already carry `if: github.event_name != 'schedule'` (so they
  run for `pull_request`), and `dependency-scan` has no `if:` at all (so it always runs,
  including for `pull_request`). All eight therefore run on every pull-request-triggered CI
  run today, so all eight are included in `needs:` and in the summary table.

**Alternatives considered**:
- A separate "collector" job that polls the GitHub Actions API for run/job statuses after the
  fact. Rejected — `needs.<job>.result` is simpler, requires no additional token scope beyond
  what's already used, and is the idiomatic mechanism for this exact use case.
- Treating `dependency-scan`'s weekly-`schedule` run as also needing a PR comment. Rejected —
  FR-006 explicitly excludes scheduled runs from comment posting; the `quality-summary` job's
  `if: github.event_name == 'pull_request'` guard already prevents this regardless of which
  jobs ran.

## 3. How is the test coverage percentage captured for the summary?

**Decision**: Add one step to the existing `test` job, after the `pytest` step, that runs
`coverage report --format=total` (a builtin `coverage.py` invocation; `coverage` is already
installed transitively via the `pytest-cov` dev dependency) and writes its single-line integer
percentage output to `$GITHUB_OUTPUT`, exposed as a job-level `outputs.coverage_pct` value.

**Rationale**:
- `--format=total` is coverage.py's supported way to print exactly one number (no ANSI
  formatting, no per-file breakdown) — trivial to capture with
  `echo "coverage_pct=$(coverage report --format=total)" >> "$GITHUB_OUTPUT"` immediately
  after the existing `pytest --cov=... --cov-report=xml ...` step, since that step already
  leaves the `.coverage` data file in place for `coverage report` to read.
- No new dependency: `coverage` ships as `pytest-cov`'s core dependency, already installed via
  `pip install -e ".[dev]"`; no `pyproject.toml` change is required.
- Reuses the existing coverage data/threshold (`--cov-fail-under=90`) rather than introducing
  a second, parallel coverage computation that could drift from the authoritative one.

**Alternatives considered**:
- Parsing the `TOTAL ... NN%` line out of `pytest`'s `--cov-report=term-missing` text output
  with `grep`/`awk`. Rejected — brittle against formatting changes and column-width shifts;
  `coverage report --format=total` is a stable, purpose-built alternative for exactly this.
- Parsing `coverage.xml` (already generated and uploaded to Codecov) with an XML tool.
  Rejected as needlessly indirect when `coverage report --format=total` reads the same
  underlying data file directly and needs no XML parsing step or extra dependency.

## 4. How is the Maintainability Index metric captured for the summary?

**Decision**: Extend `scripts/check_maintainability.py`'s existing passing path (currently:
print a human-readable "All modules ... meet the Maintainability Index threshold" message and
return `0`) to also compute a short metric summary from the same `radon mi -j` JSON it already
parses, and write it to `$GITHUB_OUTPUT` (e.g. `mi_summary=avg=74.3 worst=A`) when that
environment variable is present, leaving the script's CLI/stdout/exit-code contract for local
and non-CI use unchanged.

**Rationale**:
- Directly satisfies "reuse existing scripts (e.g., `scripts/check_maintainability.py`
  output)": no second `radon` invocation, no new script, and no duplicated threshold logic —
  the summary job only needs to read the job's `outputs.mi_summary` value.
- The script already runs `radon mi -n B -x F -j <paths>` and parses its JSON on both the
  failing and passing paths (currently the passing path just receives an empty `findings`
  dict from the `-x F` filter). To compute an average/worst-grade metric even when nothing
  is below the threshold, the change re-runs the unfiltered `radon mi -j <paths>` (no `-x`)
  once, only on the passing path, to get every module's rank/MI value for the summary —
  the failing path already has per-violation data and does not need this.
- Writing to `$GITHUB_OUTPUT` only `if os.environ.get("GITHUB_OUTPUT")` keeps the script safe
  to run locally/in other contexts (no-op there) while still being directly reusable by the
  `complexity` job without extra glue in the workflow YAML.

**Alternatives considered**:
- A second, separate script/step in the `complexity` job that re-implements the `radon mi -j`
  parsing already inside `check_maintainability.py`. Rejected as unnecessary duplication of
  logic that already exists in one place.
- Reporting only pass/fail for the `complexity` check, with no metric. Rejected — this
  directly contradicts spec.md FR-005 and User Story 3, which require the maintainability
  index/grade to be visible, not just a pass/fail label.

## 5. How is the Markdown summary body assembled and handed to the comment-posting action?

**Decision**: Add a shell step in the `quality-summary` job that writes a Markdown table (one
row per quality-check job: name, status icon/label, metric-or-"—") plus an overall status line
to a file (e.g. `summary.md`), then pass that file via the sticky-comment action's `path:`
input.

**Rationale**:
- `marocchino/sticky-pull-request-comment` natively supports `path:` (read the comment body
  from a file) — this avoids fighting YAML multi-line string escaping for a dynamically
  generated table inside the workflow file itself.
- Building the table in a shell step (using `needs.*.result` and `needs.*.outputs.*` values
  interpolated by GitHub Actions' expression syntax before the step runs) keeps all
  status/metric logic in one auditable place, rather than splitting it across the Action's
  own templating.

**Alternatives considered**:
- Inlining the whole Markdown table directly as the action's `message:` input using GitHub
  Actions expressions for every cell. Rejected — becomes unreadable/unmaintainable once
  eight rows plus conditional metric columns are involved; a shell-built file is clearer and
  easier to unit-reason about in code review.

## 6. How is a comment-posting failure prevented from failing the overall run (FR-008)?

**Decision**: Add `continue-on-error: true` to the sticky-comment posting step only (not to
the Markdown-assembly step, which should still fail loudly if the summary itself cannot be
built, since that would indicate a bug in the summary logic rather than a permissions/
environment limitation).

**Rationale**:
- `continue-on-error: true` on a step lets that step fail (e.g. `Resource not accessible by
  integration` on a fork PR where `GITHUB_TOKEN` is read-only) without failing the job or the
  overall workflow run, directly satisfying FR-008 and the fork-PR Edge Case in spec.md.
- Scoping `continue-on-error` to only the posting step (not the whole job) preserves normal
  failure visibility for genuine bugs in the summary-building logic, while still guaranteeing
  that "the summary generation and posting MUST NOT cause the overall CI run to fail" applies
  specifically to the posting mechanism spec.md's Edge Cases describe.
- Because `quality-summary` only ever reads other jobs' `needs.*.result` (already computed by
  the time it runs) and never re-runs or re-gates them, nothing about this job's own success
  or failure can retroactively change any of the eight quality-check jobs' individual
  status-check results used for branch protection/merge decisions.

**Alternatives considered**:
- Wrapping the whole `quality-summary` job in `continue-on-error: true`. Rejected — this would
  also silently swallow failures in the summary-assembly logic itself (e.g. a bug producing a
  malformed table), which is a distinct failure mode from "posting is blocked" and should
  remain visible in CI logs for maintainers to fix.
