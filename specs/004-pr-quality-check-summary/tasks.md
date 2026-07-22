---

description: "Task list for PR Quality Check Summary Comment"
---

# Tasks: PR Quality Check Summary Comment

**Input**: Design documents from `/specs/004-pr-quality-check-summary/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/pr-summary-comment-contract.md, quickstart.md

**Tests**: No automated test-suite tasks are included. Per plan.md's Testing section and
spec.md's Assumptions, this feature is CI/workflow configuration plus one additive change to
a non-calculation helper script; validation is performed via quickstart.md's manual/CI-run
scenarios, not a new pytest suite. Quickstart validation steps are included below as tasks.

**Organization**: Tasks are grouped by user story (from spec.md) to enable independent
delivery and validation of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project (unchanged `src/`/`tests/` layout per plan.md's Structure Decision). This
feature only touches:

- `.github/workflows/ci.yml`
- `scripts/check_maintainability.py`

---

## Phase 1: Setup

**Purpose**: Confirm environment/dependency prerequisites before modifying the workflow

- [X] T001 Confirm no new Python package is required in `pyproject.toml`: verify `coverage`
      is already available transitively via the existing `pytest-cov` dev dependency and
      `radon` is already a direct dependency used by `scripts/check_maintainability.py`
      (research.md #1, #3); the only new dependency this feature introduces is the pinned
      third-party action `marocchino/sticky-pull-request-comment@v3.0.5`, declared directly
      in `.github/workflows/ci.yml`, not in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the `quality-summary` job skeleton (trigger guard, dependency list,
permissions) that every user story's behavior builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add a new `quality-summary` job to `.github/workflows/ci.yml` with
      `needs: [lint, complexity, typecheck, security, dependency-scan, test, build, docs]`,
      `if: always() && github.event_name == 'pull_request'`, `runs-on: ubuntu-latest`, and
      `permissions: pull-requests: write` (no steps yet) (plan.md Project Structure;
      research.md #2; contracts/pr-summary-comment-contract.md Trigger contract)

**Checkpoint**: Job skeleton exists with correct trigger/dependency/permissions — user story
implementation can now begin

---

## Phase 3: User Story 1 - See consolidated check results on a pull request (Priority: P1) 🎯 MVP

**Goal**: A single PR comment lists every quality check's actual pass/fail/skipped/cancelled
status and an overall status, so reviewers don't need to open individual job logs.

**Independent Test**: Open a pull request, let CI run to completion, and verify a comment
appears on the PR listing every quality check with a clear pass/fail (or skipped/cancelled)
indicator, plus an overall status.

### Implementation for User Story 1

- [X] T003 [US1] In the `quality-summary` job in `.github/workflows/ci.yml`, add a shell step
      that writes a Markdown table to `summary.md` with one row per job in
      `lint, complexity, typecheck, security, dependency-scan, test, build, docs` — each row
      showing the check name and a distinct status indicator for each of
      `success`/`failure`/`cancelled`/`skipped` read from `needs.<job>.result` — plus one
      overall status line computed as `FAIL` if any status is `failure`, else a distinct
      cancelled/incomplete indicator if any is `cancelled`, else `PASS`
      (data-model.md Quality Check Result & PR Summary Comment; contracts/pr-summary-comment-contract.md
      Output contract items 1-2; research.md #5)
- [X] T004 [US1] In the `quality-summary` job in `.github/workflows/ci.yml`, add a step using
      `marocchino/sticky-pull-request-comment@v3.0.5` with `header: quality-check-summary`,
      `path: summary.md`, and `continue-on-error: true` on this step only (research.md #1, #6;
      contracts/pr-summary-comment-contract.md Output contract item 3 & Failure-isolation
      contract; spec.md FR-002, FR-008, FR-009) (depends on T003)
- [ ] T005 [US1] Manually validate quickstart.md's "End-to-end validation: initial run (User
      Story 1)" section: open a pull request with a trivial change, let CI finish, and
      confirm exactly one new comment appears containing a row for each of the eight checks
      with a clear status indicator and a single overall status line (depends on T002, T003,
      T004)
      > **PENDING live-PR validation**: implementation-time verification was limited to
      > static/dry-run checks (YAML validity, `actionlint`, and a standalone dry-run of the
      > Markdown-assembly shell logic with representative `success`/`failure`/`cancelled`/
      > `skipped` inputs — see implementation report). Confirming the actual comment renders
      > correctly on a real GitHub pull request still requires opening one.

**Checkpoint**: User Story 1 is fully functional and independently testable/deployable as the
MVP

---

## Phase 4: User Story 2 - Comment is updated in place on re-runs (Priority: P2)

**Goal**: Subsequent CI runs on the same pull request edit the existing summary comment in
place instead of creating a new one, so the PR conversation never accumulates duplicate
summary comments.

**Independent Test**: Open a pull request, let CI post the summary comment, then push a new
commit (or re-run CI) and verify the same comment is edited in place instead of a second one
being created.

### Implementation for User Story 2

- [X] T006 [US2] Review the sticky-pull-request-comment step added in T004 in
      `.github/workflows/ci.yml` and confirm no `recreate`, `append`, or `hide` input is set,
      so the action's default create-or-update-by-`header` behavior (at most one comment per
      `header` per PR) remains in effect (research.md #1; contracts/pr-summary-comment-contract.md
      Idempotency / update contract; spec.md FR-003) (depends on T004)
- [ ] T007 [US2] Manually validate quickstart.md's "End-to-end validation: update in place
      (User Story 2)" section: on the same pull request from T005, push an additional trivial
      commit or re-run the workflow several times in a row, and confirm the PR always shows
      exactly one quality-check summary comment whose content reflects only the latest run
      (spec.md SC-003) (depends on T005, T006)
      > **PENDING live-PR validation**: the sticky-comment action's create-or-update-by-
      > `header` semantics were confirmed by reading its documented behavior (research.md #1)
      > and by reviewing that no `recreate`/`append`/`hide` input is set (T006); actually
      > observing a single comment persist across multiple re-runs still requires a live PR.

**Checkpoint**: User Stories 1 AND 2 both work independently — comment appears and stays
unique across re-runs

---

## Phase 5: User Story 3 - Key metrics are visible alongside pass/fail status (Priority: P3)

**Goal**: The summary comment additionally shows the test coverage percentage and the
Maintainability Index summary alongside the `test` and `complexity` rows' pass/fail status,
with an explicit "no metric" placeholder for checks that don't produce one.

**Independent Test**: Open a pull request, let CI run to completion, and verify the summary
comment shows the test coverage percentage and the maintainability/complexity result values
(not just pass/fail labels) for the checks that produce such metrics, and a placeholder for
those that don't.

### Implementation for User Story 3

- [X] T008 [P] [US3] Add a step to the existing `test` job in `.github/workflows/ci.yml`,
      after the `pytest` step, that runs `coverage report --format=total` and writes
      `coverage_pct=<value>` to `$GITHUB_OUTPUT`; add a job-level `outputs: coverage_pct:` on
      the `test` job referencing that step's output (research.md #3; plan.md Project
      Structure; contracts/pr-summary-comment-contract.md Input contract)
- [X] T009 [P] [US3] Extend `scripts/check_maintainability.py`'s existing passing path (where
      `findings` is empty) to additionally run the unfiltered `radon mi -j <paths>` once,
      compute an average MI value and worst per-module rank from its JSON output, and — only
      when the `GITHUB_OUTPUT` environment variable is set — append a line
      `mi_summary=avg=<NN.N> worst=<A-F>` to the file at that path; leave the existing
      CLI/stdout/exit-code behavior for local/non-CI use unchanged (research.md #4;
      contracts/pr-summary-comment-contract.md Input contract)
- [X] T010 [US3] Add a job-level `outputs: mi_summary:` on the `complexity` job in
      `.github/workflows/ci.yml`, sourced from the `check_maintainability.py` step's captured
      output (requires giving that step an `id:` if it doesn't have one) (research.md #4)
      (depends on T009)
- [X] T011 [US3] Update the Markdown-assembly step added in T003 (in the `quality-summary`
      job in `.github/workflows/ci.yml`) so the `test` row renders
      `needs.test.outputs.coverage_pct` and the `complexity` row renders
      `needs.complexity.outputs.mi_summary`, each falling back to an explicit "no metric"
      placeholder (e.g. `—`) if the output is absent/empty, while all other rows
      (`lint`, `typecheck`, `security`, `dependency-scan`, `build`, `docs`) always render that
      same placeholder (data-model.md Quality Check Result; contracts/pr-summary-comment-contract.md
      Output contract item 1; spec.md FR-005, User Story 3 Acceptance Scenario 3) (depends on
      T003, T008, T010)
- [ ] T012 [US3] Manually validate quickstart.md's "Local pre-checks" and "End-to-end
      validation: metrics visible (User Story 3)" sections: run the local `coverage
      report --format=total` and `check_maintainability.py` (with `GITHUB_OUTPUT` set) checks,
      then open/update a pull request and confirm the `test` and `complexity` rows show their
      metric values while all other rows show the placeholder (depends on T005, T007, T011)
      > **Local pre-checks completed**: `pytest --cov=... --cov-fail-under=90` then
      > `coverage report --format=total` locally produced `97` (a bare integer, as expected);
      > `GITHUB_OUTPUT=$(mktemp) python scripts/check_maintainability.py src/` produced
      > `mi_summary=avg=81.4 worst=A` in the temp file, as expected. **PENDING live-PR
      > validation** of the rendered `test`/`complexity` rows and placeholders on an actual
      > comment, which still requires opening a pull request.

**Checkpoint**: All three user stories are independently functional — pass/fail summary,
in-place updates, and visible metrics

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge-case coverage and quality-gate confirmation across all user stories

- [ ] T013 [P] Manually validate quickstart.md's "Edge case validation" section: a failing
      quality-check job (comment shows `lint` failed, overall `FAIL`, others unaffected), a
      skipped job (row reads "skipped", not "failed" or omitted), a non-`pull_request`
      trigger (push to `main` / scheduled run produces no summary comment on any PR, per
      spec.md SC-005), and a fork-originated pull request (the `quality-summary` job
      completes without failing the workflow even if the posting step reports a permissions
      error) (depends on T002, T004, T011)
      > **PENDING live-PR validation**: verified by static review only — `if:` guard is
      > `always() && github.event_name == 'pull_request'` (non-pull_request triggers produce
      > no comment by construction; confirmed via `actionlint` and PyYAML parse of the
      > condition), the Markdown-assembly logic was dry-run tested locally with a
      > `failure`/`skipped`/`cancelled` combination (see report) producing correct distinct
      > labels and an overall `FAIL`, and `continue-on-error: true` is scoped to only the
      > posting step (fork-PR token-permission behavior cannot be exercised without a real
      > fork PR run).
- [X] T014 [P] Run `ruff check src/ tests/`, `black --check src/ tests/`, `mypy
      src/machine_calc`, and `bandit -r src -ll` locally to confirm the
      `scripts/check_maintainability.py` change in T009 introduces no lint/format/type/security
      regressions (Constitution Principle I) (depends on T009)
- [X] T015 Re-read the Constitution Check table in plan.md after implementation and confirm
      every row's status still holds (no new violations introduced by T002-T011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) only
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2); its tasks review/build on
  the sticky-comment step added in User Story 1 (T004), so in practice runs after Phase 3
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2); T011 builds on the
  Markdown-assembly step added in User Story 1 (T003), so in practice runs after Phase 3
  (T008/T009 have no such dependency and could start earlier if desired)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — delivers the MVP
- **User Story 2 (P2)**: Reviews/validates the comment-posting mechanism User Story 1
  introduces (T004); does not modify unrelated files, remains independently testable via its
  own quickstart scenario
- **User Story 3 (P3)**: Adds metric outputs (T008, T009, T010) that are independent of User
  Story 1/2, then wires them into the assembly step User Story 1 introduces (T011); remains
  independently testable via its own quickstart scenario

### Within Each User Story

- No automated tests are included (see Tests note above); manual quickstart.md validation
  tasks close out each story
- Job/script changes before the assembly-step update that consumes them
- Story complete before moving to next priority

### Parallel Opportunities

- T008 (`test` job coverage output) and T009 (`check_maintainability.py` MI summary) touch
  different files/jobs and can run in parallel
- T013 and T014 (Polish phase) touch independent concerns and can run in parallel

---

## Parallel Example: User Story 3

```bash
# Launch the two independent metric-capture tasks together:
Task: "Add coverage_pct output step to the test job in .github/workflows/ci.yml"
Task: "Extend scripts/check_maintainability.py to emit mi_summary to $GITHUB_OUTPUT"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md's User Story 1 scenario on a real pull request
5. Deploy/demo if ready — this alone satisfies spec.md's core value proposition

### Incremental Delivery

1. Complete Setup + Foundational → job skeleton ready
2. Add User Story 1 → validate independently → Deploy/Demo (MVP!)
3. Add User Story 2 → validate independently (re-run CI, confirm single comment) → Deploy/Demo
4. Add User Story 3 → validate independently (metrics visible) → Deploy/Demo
5. Finish with Phase 6 edge-case and quality-gate validation

### Parallel Team Strategy

With multiple contributors, after Foundational (Phase 2) is merged:

- Contributor A: User Story 1 (T003-T005)
- Contributor B: User Story 3's metric-capture tasks (T008, T009) — independent of T003-T005
- User Story 2 (T006-T007) and User Story 3's assembly wiring (T010-T012) follow once T004
  and T003 respectively have landed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature modifies only `.github/workflows/ci.yml` and
  `scripts/check_maintainability.py` — no new source directories or Python dependencies
- Verify each quickstart.md scenario manually since no automated test suite is added
  (plan.md Testing section)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
