# Feature Specification: PR Quality Check Summary Comment

**Feature Branch**: `004-pr-quality-check-summary`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "As part of the CI build process for each pull request, generate a summary of the results of each quality check (e.g., lint, code complexity/maintainability, type checking, security/bandit, test coverage) and post/update this summary as a single comment on the pull request. The comment should be updated in place on re-runs (not duplicated), should clearly show pass/fail status per check, and should include key metrics where available (e.g., test coverage percentage, maintainability index / complexity results). This applies only to pull_request-triggered CI runs, not push-to-main or scheduled runs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See consolidated check results on a pull request (Priority: P1)

As a contributor or reviewer, when CI finishes running on a pull request, I want a single
comment on that pull request that summarizes the pass/fail status of every quality check
(lint, complexity/maintainability, type checking, security, test coverage, and any other
gating check) so I don't have to open each CI job's log individually to understand whether
the PR is safe to review or merge.

**Why this priority**: This is the core value of the feature — without a readable, at-a-glance
summary, the rest of the feature (updating in place, showing metrics) has nothing to attach to.
This alone materially reduces reviewer effort on every PR.

**Independent Test**: Open a pull request against the repository, let CI run to completion, and
verify a comment appears on the PR listing every quality check with a clear pass/fail indicator
for each.

**Acceptance Scenarios**:

1. **Given** a newly opened pull request, **When** all CI quality-check jobs complete, **Then** a
   comment is posted on the pull request listing each check (lint, complexity, typecheck,
   security, test coverage) with a clear pass or fail indicator for each.
2. **Given** a pull request where all checks pass, **When** the summary comment is posted,
   **Then** the comment clearly indicates overall success (e.g., an overall status alongside the
   per-check breakdown).
3. **Given** a pull request where one or more checks fail, **When** the summary comment is
   posted, **Then** the comment clearly identifies which specific check(s) failed, without
   requiring the reader to open workflow logs to know that.

---

### User Story 2 - Comment is updated in place on re-runs (Priority: P2)

As a contributor pushing additional commits or re-running CI on the same pull request, I want
the existing summary comment to be updated with the latest results rather than a new comment
being added each time, so the pull request conversation stays clean and always reflects the
current state of the latest run.

**Why this priority**: Without this, the PR conversation becomes cluttered with a growing list of
stale summary comments, making it hard to find the current status and defeating the purpose of a
single at-a-glance summary.

**Independent Test**: Open a pull request, let CI run and post the summary comment, then push a
new commit (or re-run CI) and verify the same comment is edited in place with updated results
instead of a second comment being created.

**Acceptance Scenarios**:

1. **Given** a pull request that already has a quality-check summary comment from a previous CI
   run, **When** CI completes again for a new commit on the same pull request, **Then** the
   existing comment's content is replaced with the latest results and no additional comment is
   created.
2. **Given** a pull request with multiple prior CI runs, **When** viewing the pull request's
   conversation, **Then** exactly one quality-check summary comment is present, reflecting only
   the most recent run's results.

---

### User Story 3 - Key metrics are visible alongside pass/fail status (Priority: P3)

As a reviewer, I want the summary comment to include key quantitative metrics — such as the test
coverage percentage and the maintainability/complexity results — alongside the pass/fail status,
so I can judge not just whether a check passed but how close it is to its threshold.

**Why this priority**: Pass/fail alone is useful, but reviewers benefit from trend visibility
(e.g., "coverage is 90.4%, just above the 90% gate") to catch regressions or borderline changes
even when a check technically still passes.

**Independent Test**: Open a pull request, let CI run to completion, and verify the summary
comment shows the test coverage percentage and the maintainability/complexity result values, not
just pass/fail labels, for the checks that produce such metrics.

**Acceptance Scenarios**:

1. **Given** a pull request where the test-coverage check has run, **When** the summary comment
   is posted, **Then** it includes the overall test coverage percentage produced by that run.
2. **Given** a pull request where the complexity/maintainability check has run, **When** the
   summary comment is posted, **Then** it includes the maintainability/complexity result
   (e.g., grade or index value) produced by that run.
3. **Given** a check that does not produce a quantitative metric (e.g., lint or type checking
   simply pass or fail), **When** the summary comment is posted, **Then** that check is still
   shown with a clear pass/fail indicator, without a fabricated or misleading metric value.

### Edge Cases

- What happens when one or more quality-check jobs are still running, were skipped, or were
  cancelled when the summary is generated (e.g., a job was skipped due to a prior job failing)?
  The comment MUST represent that job's actual state (e.g., "skipped" or "cancelled") rather than
  silently omitting it or misreporting it as failed or passed.
- How does the system handle a pull request opened from a fork with restricted permissions, where
  posting or editing a comment might be blocked by token permissions? The summary generation
  MUST NOT cause the overall CI run to fail solely because the comment could not be posted; the
  underlying quality-check job results remain the source of truth for merge decisions.
- What happens when a job fails so early that it produces no parseable metric output (e.g., the
  environment fails to set up before tests run)? The comment MUST still show that check as failed,
  using a fallback indicator when no metric is available, rather than omitting the check entirely.
- What happens on a pull request that is updated many times in quick succession, causing multiple
  CI runs to be in flight concurrently? The final comment state MUST converge to reflect the most
  recently completed run's results, without leaving the comment in a partially-updated or
  duplicated state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CI process MUST generate a summary of the results of each quality check that
  runs on a pull request, including at minimum: lint, complexity/maintainability, type checking,
  security scanning, and test coverage.
- **FR-002**: The system MUST post the summary as a comment on the pull request that triggered the
  CI run.
- **FR-003**: The system MUST update the existing summary comment in place on subsequent CI runs
  for the same pull request rather than creating a new comment, such that at most one
  quality-check summary comment exists per pull request at any time.
- **FR-004**: The summary comment MUST clearly indicate the pass/fail status of each individual
  quality check, and MUST indicate an overall status for the run as a whole.
- **FR-005**: The summary comment MUST include, for each check capable of producing one, its key
  quantitative metric (e.g., test coverage percentage for the coverage check; maintainability
  index/grade for the complexity check).
- **FR-006**: The summary comment generation and posting MUST run only for CI runs triggered by a
  pull-request event, and MUST NOT run for push-to-main or scheduled CI runs.
- **FR-007**: The summary MUST reflect the actual outcome of every applicable check in the run
  (pass, fail, skipped, or cancelled) without omitting any check that was expected to run.
- **FR-008**: A failure to post or update the summary comment MUST NOT alter the pass/fail outcome
  of the underlying quality-check jobs or block the pull request's CI status on that basis alone.
- **FR-009**: The summary comment MUST be identifiable by the system as belonging to this feature
  (e.g., via a stable marker) so that it can be reliably located and updated across runs,
  distinguishing it from other comments on the pull request.

### Key Entities

- **Quality Check Result**: Represents the outcome of a single CI check (e.g., lint, complexity,
  typecheck, security, test coverage) for one CI run. Key attributes: check name, pass/fail/
  skipped/cancelled status, and an optional key metric value (e.g., percentage, grade, or index).
- **PR Summary Comment**: Represents the single consolidated comment posted on a pull request.
  Key attributes: the pull request it belongs to, the overall status, the list of Quality Check
  Results it summarizes, and the identifying marker used to locate it for updates on subsequent
  runs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pull-request-triggered CI runs that complete their quality-check jobs result
  in exactly one summary comment being present on the pull request.
- **SC-002**: Reviewers can determine the pass/fail status of every quality check for a pull
  request within 10 seconds of opening the pull request, without opening any workflow log.
- **SC-003**: Across 10 consecutive CI re-runs on the same pull request, the number of
  quality-check summary comments on that pull request never exceeds one.
- **SC-004**: For checks that produce a quantitative metric, 100% of summary comments display that
  metric's current value alongside the pass/fail status.
- **SC-005**: Push-to-main and scheduled CI runs never result in a quality-check summary comment
  being posted or updated on any pull request.

## Assumptions

- The existing CI workflow (`.github/workflows/ci.yml`) with jobs `lint`, `complexity`,
  `typecheck`, `security`, `dependency-scan`, `test`, `build`, and `docs` remains the source of
  the check results summarized; this feature aggregates and reports on those jobs' outcomes
  rather than replacing them.
- Of the existing jobs, `lint`, `complexity`, `typecheck`, `security`, and `test` (coverage) are
  the "quality checks" summarized per the feature description; `dependency-scan`, `build`, and
  `docs` are supporting/gating jobs and are included in the summary only if they run as part of
  the same pull-request-triggered workflow, following the same pass/fail/skipped/cancelled
  reporting rules as the named quality checks.
- The comment is posted using the repository's existing CI/GitHub Actions identity and standard
  pull-request comment permissions; no new external service or bot account is introduced.
- "Key metrics where available" means: test coverage percentage from the `test` job, and
  maintainability index/grade from the `complexity` job; other checks (lint, typecheck, security)
  are reported via pass/fail status only, as they do not currently produce a single headline
  metric.
- Only one summary comment is maintained per pull request; historical run results are not
  preserved as separate comments, though standard GitHub audit/history mechanisms (e.g., comment
  edit history) remain available outside this feature's scope.
