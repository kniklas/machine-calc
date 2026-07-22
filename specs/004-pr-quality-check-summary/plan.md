# Implementation Plan: PR Quality Check Summary Comment

**Branch**: `004-pr-quality-check-summary` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-pr-quality-check-summary/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a new `quality-summary` job to the existing `.github/workflows/ci.yml` that runs after
(`needs:`) the `lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test`,
`build`, and `docs` jobs, gated to `if: always() && github.event_name == 'pull_request'`
(spec.md FR-006). It reads each dependency job's `needs.<job>.result` (`success`/`failure`/
`cancelled`/`skipped`) plus two metric outputs already produced by existing tooling — test
coverage percentage from `coverage report --format=total` in the `test` job, and the
Maintainability Index summary emitted by `scripts/check_maintainability.py` (extended to also
write to `$GITHUB_OUTPUT` on the pass path, not just report violations) in the `complexity`
job — assembles a single Markdown table into a file, and posts/updates it as one PR comment
via `marocchino/sticky-pull-request-comment@v3.0.5` (`header: quality-check-summary`, no
`recreate`, so the same comment is edited in place per spec.md FR-003/FR-009). The posting
step uses `continue-on-error: true` so a comment-posting failure never fails the job or
blocks merge (spec.md FR-008).

## Technical Context

**Language/Version**: Python 3.11 (CI runner version, unchanged) for the one small script
change; YAML for the workflow itself — no application/runtime language change

**Primary Dependencies**: No new Python packages beyond `pyproject.toml`'s existing `dev`
extras (`radon` is already a dependency of `scripts/check_maintainability.py`; `coverage`
is already an indirect dependency via `pytest-cov`). One new third-party GitHub Action:
`marocchino/sticky-pull-request-comment@v3.0.5` (research.md #1)

**Storage**: N/A — no persistent storage; the summary is regenerated from each run's job
results and is not stored between runs (the PR comment itself is the only durable artifact,
owned and updated by the GitHub Action)

**Testing**: No new application/unit test suite. Validation is via quickstart.md: opening a
real (or draft) pull request, observing the rendered comment across an initial run and a
re-run, and inspecting workflow logs for each edge case in spec.md (skipped job, failed job,
fork PR with restricted token permissions)

**Target Platform**: GitHub Actions (`ubuntu-latest` runners), GitHub's pull-request comment
API (via the sticky-comment Action) — same platform as the existing CI workflow

**Project Type**: Single project — this feature only adds/modifies CI/workflow configuration
and one existing helper script; no new application module under `src/`

**Performance Goals**: N/A (not user-facing runtime); the new job should add well under a
minute to overall CI wall-clock time since it does no checkout/build work of its own beyond
reading job outputs and posting one comment

**Constraints**: MUST NOT run for `push`-to-`main` or `schedule` triggers (spec.md FR-006);
MUST NOT create more than one summary comment per pull request across any number of re-runs
(spec.md FR-003, FR-009); MUST NOT fail the overall workflow or alter any quality-check job's
own pass/fail outcome solely because the comment could not be posted (spec.md FR-008,
notably relevant for pull requests from forks where the default `GITHUB_TOKEN` is
read-only); MUST represent every one of the eight existing jobs' actual state (including
`skipped`/`cancelled`), not just pass/fail (spec.md FR-007)

**Scale/Scope**: One new CI job, one new step added to the existing `test` job (coverage
percentage capture), a small additive change to `scripts/check_maintainability.py` (emit
metric output on the passing path in addition to its existing failure-reporting behavior),
and one new job-level `permissions: pull-requests: write` grant; no change to any
quality-check job's own pass/fail logic or thresholds

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Linting/formatting and static type-checking MUST pass in CI | PASS — the one script change (`scripts/check_maintainability.py`) stays within existing `ruff`/`black`/`mypy` configuration; no new module, no relaxation of any existing check |
| II. Testing Standards | Automated tests mandatory for calculation logic; ≥90% coverage | N/A — this feature touches CI workflow configuration and one non-calculation helper script, not `src/machine_calc` calculation logic; the existing `--cov-fail-under=90` gate on `test` is unchanged and unaffected |
| III. Calculation Robustness & Accuracy | Numerical correctness/edge-case handling for calculations | N/A — no calculation logic is added or modified |
| IV. Python Packaging & Versioning | Dependencies declared explicitly with version constraints | PASS — no new Python package is added to `pyproject.toml`; the only new dependency is a pinned third-party GitHub Action (`marocchino/sticky-pull-request-comment@v3.0.5`), declared by pinned tag directly in `.github/workflows/ci.yml` (research.md #1) |
| V. Resource-Constrained Compatibility | Application MUST run within legacy/low-power constraints | N/A — this feature is CI-only and runs on GitHub-hosted runners, never on the constrained target hardware the application itself must support |
| VI. Extensibility by Design | New calculations/operations added via extension, not modification of shared code | N/A — no operation/calculation architecture is touched |
| VII. Documentation & Publishing | Docs generation/publishing, README badges | N/A — this feature adds a PR-comment summary, not end-user or developer documentation; it does not touch Sphinx docs, the docs job's own pass/fail behavior, or README badges |
| VIII. Internationalization of User-Facing Messages | User-facing REPL/CLI/error strings MUST be translatable | N/A — the PR summary comment is CI tooling output aimed at contributors/reviewers reading GitHub, not application REPL/CLI/error output within this constitution principle's scope; no new user-facing application strings are introduced |
| IX. Automated Code Quality, Complexity & Security Gates | Complexity/MI/security/dependency gates MUST run in CI and be required status checks | PASS — this feature does not change any gate's enforcement, threshold, or required-status-check configuration; it strictly adds a read-only reporting layer on top of the existing gates' results (research.md #2), and explicitly must not become a way to bypass or mask a failing gate (FR-008 only covers the *comment*, never the underlying job's own status) |

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/004-pr-quality-check-summary/
├── plan.md                          # This file (/speckit.plan command output)
├── research.md                      # Phase 0 output (/speckit.plan command)
├── data-model.md                    # Phase 1 output (/speckit.plan command)
├── quickstart.md                    # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── pr-summary-comment-contract.md  # Phase 1 output (/speckit.plan command)
├── checklists/
└── tasks.md                         # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    └── ci.yml                # MODIFY:
                               #   - `test` job: add a step that runs
                               #     `coverage report --format=total` after pytest and
                               #     writes the percentage to a step/job `outputs:` value
                               #     (research.md #3)
                               #   - `complexity` job: no invocation change (still runs
                               #     `python scripts/check_maintainability.py src/`); the
                               #     script itself now also writes a metric string to
                               #     `$GITHUB_OUTPUT` when available, surfaced as a job
                               #     `outputs:` value (research.md #4)
                               #   - new `quality-summary` job:
                               #     needs: [lint, complexity, typecheck, security,
                               #             dependency-scan, test, build, docs]
                               #     if: always() && github.event_name == 'pull_request'
                               #     permissions: pull-requests: write
                               #     steps: checkout (for a reusable script, if needed),
                               #     build the Markdown summary from `needs.*.result` and
                               #     the two metric outputs into a file, then post/update
                               #     via marocchino/sticky-pull-request-comment@v3.0.5
                               #     with `header: quality-check-summary` and
                               #     `continue-on-error: true` on that step (FR-008)

scripts/
└── check_maintainability.py  # MODIFY: on the passing path (previously only printed a
                               #   human-readable "All modules ... meet threshold" message
                               #   and returned 0), also compute and emit a short metric
                               #   summary (e.g. worst per-module rank and average MI value
                               #   across `radon mi -j`'s findings) to `$GITHUB_OUTPUT` when
                               #   that environment variable is set, so the `complexity`
                               #   job can expose it as a job output without a second
                               #   `radon` invocation (research.md #4); CLI/stdout/exit-code
                               #   behavior for local/non-CI use is unchanged

tests/
└── (unchanged — no new application test suite; this feature has no calculation logic)
```

**Structure Decision**: Single project (unchanged from the existing `src/`/`tests/` layout).
This feature is CI/workflow configuration plus one small, additive change to an existing
helper script; no new source directories, packages, or Python dependencies are introduced.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table intentionally omitted.
