# Tasks: Periodic Multi-Agent Skill Sync Workflow

**Input**: Design documents from `specs/011-multi-agent-skill-sync/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/sync-workflow-contract.md, quickstart.md

**Tests**: Included — plan.md's Technical Context commits to unit tests for the
helper script's pure functions (outcome derivation, PR body composition) as
ordinary good practice and Development Workflow's general review checklist,
even though Constitution Principle II's NON-NEGOTIABLE calculation-coverage
requirement does not itself bind this non-calculation CI tooling.

**Organization**: Tasks are grouped by user story (US1 = automatic drift
detection & PR, P1; US2 = reviewable/non-auto-merged PR content, P2; US3 =
on-demand trigger, P3) per spec.md priorities, on top of a shared
Foundational phase (all three stories depend on the same core script logic:
reading installed integrations, running `specify integration
status`/`upgrade`, and deriving the Sync Run outcome — data-model.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow plan.md's Project Structure: `scripts/sync_agent_integrations.py`
  (new helper script, outside `src/machine_calc`), `tests/scripts/` (new test
  directory), `.github/workflows/ci.yml` (existing CI workflow, extended
  with a new job)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm existing tooling configuration already covers the new
code paths, and close the one gap it doesn't cover automatically
(`/speckit-analyze` finding C1 — Constitution Principle IX).

- [X] T001 Confirm `pytest`'s `testpaths = ["tests"]` (`pyproject.toml`)
  auto-discovers a new `tests/scripts/` directory with no config change, and
  confirm `scripts/sync_agent_integrations.py` needs no `pyproject.toml`
  change to stay outside `[tool.coverage.run]`'s `source = ["machine_calc"]`
  or `[tool.mypy]`'s `files = ["src/machine_calc"]` default (T002 below adds
  it to CI's lint/typecheck/security *commands* explicitly instead — those
  are separate from `pyproject.toml`'s own scoping defaults)
- [X] T002 [P] Extend `.github/workflows/ci.yml`'s `lint`, `typecheck`, and
  `security` job commands to explicitly include
  `scripts/sync_agent_integrations.py` by exact file path — i.e.
  `ruff check src/ tests/ scripts/sync_agent_integrations.py`,
  `black --check src/ tests/ scripts/sync_agent_integrations.py`,
  `mypy src/machine_calc scripts/sync_agent_integrations.py`, and
  `bandit -r src scripts/sync_agent_integrations.py -ll`. Deliberately name
  the new file rather than the whole `scripts/` directory, so this feature
  does not pull the pre-existing, unrelated `scripts/check_maintainability.py`
  into CI-enforced scope as a side effect (that remains a separate,
  out-of-scope cleanup). This closes Constitution Principle IX's "every pull
  request MUST be automatically measured" gate for the new code this feature
  adds (`/speckit-analyze` finding C1; plan.md Constitution Check Principles
  I/IX)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The core script logic every user story depends on: reading
which integrations are installed, running `specify integration
status`/`upgrade` per integration, and classifying the overall run outcome
per data-model.md's "Sync Run" priority-ordered derivation. **Note (post-PR
#50 Copilot review correction):** the order actually implemented is `failed
> upgraded-with-changes > modified-blocked > no-drift` — a mixed run (one
integration blocked, another genuinely changed) still opens a PR naming
both, rather than the originally-planned "any blocked always fails" order
described in T006 below; see data-model.md and
contracts/sync-workflow-contract.md for the corrected, current contract.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create `scripts/sync_agent_integrations.py` with
  `load_installed_integrations() -> list[str]`, reading
  `.specify/integration.json`'s `installed_integrations` field (FR-010;
  data-model.md "Integration".key) — this is what lets a future integration
  be picked up with zero workflow/script changes
- [X] T004 Add `run_integration_status(key: str) -> dict` to
  `scripts/sync_agent_integrations.py`, wrapping `specify integration
  status --json` and parsing its JSON output to extract that integration's
  `modified_files`/`missing_files` (research.md #1) (depends on T003; same
  file as T003, sequential)
- [X] T005 Add `run_integration_upgrade(key: str) -> IntegrationResult` to
  `scripts/sync_agent_integrations.py`, wrapping `specify integration
  upgrade <key> --script py` (never `--force`, per FR-012's "don't silently
  discard a hand-edit" intent), capturing the exit code/stderr to
  distinguish a modified-file block (research.md #1) from a generic
  tooling/network failure, and running `git status --porcelain` scoped to
  that integration's manifest paths afterward to collect `changed_files`
  (data-model.md "Integration") (depends on T003; same file as T003/T004,
  sequential)
- [X] T006 Implement `derive_run_outcome(integrations: list[IntegrationResult]) -> SyncRunOutcome`
  in `scripts/sync_agent_integrations.py` per data-model.md "Sync Run"'s
  priority-ordered derivation, **as corrected after PR #50's Copilot
  review** (originally planned as any `modified-blocked` → `failed`
  unconditionally, which made the blocked-callout branch of
  `compose_pull_request_body()` unreachable and contradicted FR-008): any
  `failed` → `failed`; else any `upgraded-with-changes` →
  `pull-request-opened-or-updated` (even if another integration in the same
  run is `modified-blocked` — it is named in that PR's body instead of
  sinking the run, research.md #1); else any `modified-blocked` (with
  nothing else changed) → `failed`; else `no-drift` (depends on T004, T005;
  same file, sequential)
- [X] T007 Unit tests for `load_installed_integrations()`,
  `run_integration_status()`, `run_integration_upgrade()` (with
  `subprocess` mocked), and `derive_run_outcome()` in
  `tests/scripts/test_sync_agent_integrations.py`, covering all four
  outcome-derivation cases from data-model.md's priority table including the
  case where a `failed` integration takes priority over a
  `modified-blocked` one in the same run (depends on T003, T004, T005, T006)

**Checkpoint**: The helper script correctly reads installed integrations,
runs status/upgrade, and classifies the overall run outcome — fully
unit-tested. User story phases below add PR-opening, PR-content, and
trigger-wiring behavior on top of this shared core.

---

## Phase 3: User Story 1 - Automatic Drift Detection and Sync Pull Request (Priority: P1) 🎯 MVP

**Goal**: The recurring workflow regenerates every installed integration and
opens exactly one pull request only when real drift is found; a run with no
drift makes no repository changes and opens no pull request (spec.md User
Story 1; FR-001–FR-004, FR-011).

**Independent Test**: Trigger the workflow against a repository state with
known upstream drift; verify a pull request opens bundling the regenerated
files. Trigger it again immediately after (no further drift); verify the
second run makes no changes and opens no pull request (quickstart.md
Scenarios 1–2).

- [X] T008 [US1] Add `write_workflow_output(outcome: SyncRunOutcome) -> None`
  to `scripts/sync_agent_integrations.py`, writing `has_changes=true/false`
  to `$GITHUB_OUTPUT` so the workflow can conditionally invoke the
  PR-creation step (FR-004; contracts/sync-workflow-contract.md "no-drift"
  guarantee) (depends on T006; same file, sequential)
- [X] T009 [US1] Add a `main()` CLI entry point to
  `scripts/sync_agent_integrations.py` that iterates every integration from
  `load_installed_integrations()`, calls `run_integration_status()` then
  `run_integration_upgrade()` for each, calls `derive_run_outcome()` and
  `write_workflow_output()`, and exits non-zero when the outcome is `failed`
  (FR-007; contracts/sync-workflow-contract.md "failed" guarantee) (depends
  on T006, T008; same file, sequential)
- [X] T010 [US1] Add a `sync-agent-integrations` job to the existing
  `.github/workflows/ci.yml` (reusing its already-declared top-level
  `schedule`/`workflow_dispatch` triggers rather than a new sibling
  workflow file), guarded with `if: github.event_name == 'schedule' ||
  github.event_name == 'workflow_dispatch'` (mirroring the `if:
  github.event_name != 'schedule'` guard pattern already used by every
  `pull_request`-only job in this file, inverted for this
  schedule/dispatch-only job); steps install the pinned `specify` CLI
  (`uv tool install specify-cli --from
  "git+https://github.com/github/spec-kit.git@v1.0.0"`, research.md #2)
  and run `python scripts/sync_agent_integrations.py` (depends on T009;
  same file as T002, but T002's edits are to different job blocks —
  sequential to avoid an unnecessary merge, not a real conflict)
- [X] T011 [US1] Add the `peter-evans/create-pull-request` step to the
  `sync-agent-integrations` job from T010, gated on the script's
  `has_changes` output, targeting the fixed branch
  `chore/sync-agent-integrations` (research.md #3; FR-011
  duplicate-pull-request avoidance) and authenticated via a dedicated
  repository-secret token input (e.g. `secrets.SYNC_PR_TOKEN`) rather than
  `secrets.GITHUB_TOKEN`, per research.md #4's documented GitHub Actions
  limitation (default-token PRs never trigger this repo's
  `pull_request`-scoped required checks) (depends on T010; same file as
  T010, sequential)
- [X] T012 [P] [US1] Integration test in
  `tests/scripts/test_sync_agent_integrations.py` exercising `main()`
  end-to-end with `subprocess` mocked, covering both the no-drift case (exit
  0, `has_changes=false`) and the drift-found case (exit 0,
  `has_changes=true`) (depends on T009; different file from T010/T011)

**Checkpoint**: User Story 1 is independently functional and testable — the
script correctly triggers pull-request creation only on real drift, and is
a clean no-op otherwise.

---

## Phase 4: User Story 2 - Reviewable, Non-Auto-Merged Sync Pull Requests (Priority: P2)

**Goal**: A sync pull request's description names every changed integration
(and any integration blocked by a locally-modified file) without the
reviewer needing to open the diff, and the pull request goes through the
repository's normal required review — never auto-merged (spec.md User
Story 2; FR-003, FR-006, FR-008).

**Independent Test**: Open a sync-generated pull request; confirm its
description lists changed integrations; confirm it cannot merge without
review, identically to any other pull request (quickstart.md Scenarios 3,
7).

- [X] T013 [US2] Add `compose_pull_request_body(integrations: list[IntegrationResult]) -> str`
  to `scripts/sync_agent_integrations.py`, producing the body per
  contracts/sync-workflow-contract.md's "Sync Pull Request body contract"
  (changed integrations named first; then, only when at least one other
  integration also changed in the same run, a callout naming any
  `modified-blocked` integration and its specific file — data-model.md
  "Sync Pull Request".blocked_integrations) (depends on T006; same file as
  Phase 2/3 tasks, sequential)
- [X] T014 [US2] Extend `write_workflow_output()` (T008) to also write the
  composed body from `compose_pull_request_body()` to `$GITHUB_OUTPUT`, and
  wire that output into the `peter-evans/create-pull-request` step's
  `body:` input (T011) in `.github/workflows/ci.yml` (depends on T013, T011;
  `.github/workflows/ci.yml` portion is same file as T010/T011, sequential)
- [X] T015 [P] [US2] Unit tests for `compose_pull_request_body()` in
  `tests/scripts/test_sync_agent_integrations.py`: multiple changed
  integrations are all named without needing the diff (SC-002); the
  blocked-integration callout appears only when at least one other
  integration in the same run also changed (depends on T013; different file
  from T014's workflow-YAML portion)
- [X] T016 [US2] Review the `sync-agent-integrations` job (T010–T011) and
  add an inline comment confirming no `permissions:` block or step grants
  merge/auto-approve capability, so the least-privilege default and normal
  required review apply exactly as they do to every other pull request
  (FR-006) — mirrors this file's existing least-privilege comment
  convention at the top of `.github/workflows/ci.yml` (depends on T011;
  same file, sequential)

**Checkpoint**: User Stories 1 and 2 are both independently functional — a
sync pull request only ever opens on real drift (US1) and is self-explanatory
and non-auto-mergeable when it does (US2).

---

## Phase 5: User Story 3 - On-Demand Sync Outside the Schedule (Priority: P3)

**Goal**: The maintainer can trigger an identical sync check via
`workflow_dispatch` without waiting for the weekly schedule (spec.md User
Story 3; FR-005).

**Independent Test**: Manually trigger the workflow; confirm it performs the
identical drift-check and pull-request behavior as a scheduled run
(quickstart.md Scenario 6).

- [X] T017 [US3] Confirm the `sync-agent-integrations` job's `if:` guard
  (T010) treats `schedule` and `workflow_dispatch` identically — no
  additional conditional branches on `github.event_name` anywhere in the
  job that would skip a step only for manual runs — and that
  `workflow_dispatch` requires no input parameters (SC-004) (depends on
  T010; same file, sequential)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation and quality-bar tasks spanning all three user
stories.

- [X] T018 Execute all quickstart.md scenarios and confirm actual behavior
  matches documented expected outcomes (depends on T001–T017). Scenarios 1-3
  (no-drift, drift-found, locally-modified-blocks) validated for real against
  the live `specify` CLI in a disposable git worktree (not this working tree)
  — confirmed correct `has_changes`/`pr_body` output, exit codes, and that a
  blocked integration never invokes `upgrade`. Scenario 5 (new-integration
  pickup) confirmed via no hard-coded integration names in the script.
  Scenarios 6-7 (manual-trigger parity, review still required) confirmed by
  inspection of the job's `if:` guard and lack of elevated `permissions:`
  (same evidence as T017/T016). Scenario 4 (duplicate-PR avoidance) relies on
  `peter-evans/create-pull-request`'s documented branch-reuse behavior
  (research.md #3) and requires a live GitHub Actions run to fully exercise —
  not independently re-tested here beyond that documented behavior.
  **Scenario 2a (added post-PR #50 Copilot review, FR-013)**: validated for
  real — `specify self check` against this repository's actual pinned
  version reported a genuine available update at review time (`1.0.0 →
  v1.0.1`) — plus via
  `test_check_specify_cli_up_to_date_update_available`/
  `test_main_stale_cli_fails_without_checking_integrations` proving `main()`
  fails without ever calling `load_installed_integrations()` in that case.
- [X] T019 [P] Add a short mention of the automated multi-agent sync
  workflow to `README.md` (or a `CONTRIBUTING`-style doc) — optional per
  plan.md's Constitution Check Principle VII note (not required by any FR),
  but low-cost and improves discoverability for future contributors
- [X] T020 Run `pytest` and confirm the new `tests/scripts/` tests pass and
  the existing `--cov=machine_calc --cov-fail-under=90` gate is unaffected
  (depends on T007, T012, T015)
- [X] T021 Add an inline comment on the new `sync-agent-integrations` job in
  `.github/workflows/ci.yml` citing `specs/011-multi-agent-skill-sync`,
  matching this file's existing convention of citing spec numbers next to
  the CI logic they implement (e.g. the `complexity` job's
  `specs/003-ci-quality-security-gates` reference) (depends on T010–T016;
  same file, sequential)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. T002 (CI
  lint/typecheck/security scope extension) can run in parallel with T001
  (a verification-only task with no file edit).
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all
  three user stories (all three depend on the same core script: reading
  installed integrations, running status/upgrade, deriving the run
  outcome).
- **User Story 1 (Phase 3)**, **User Story 2 (Phase 4)**, and **User Story 3
  (Phase 5)**: All depend only on Foundational completion. US2 and US3 each
  touch `scripts/sync_agent_integrations.py` and
  `.github/workflows/ci.yml` lines that US1 also touches (the job/PR-step
  US1 creates in T010–T011), so — as with prior features in this repo where
  a shared file is extended across stories — US1 should be implemented
  first if worked by a single contributor; a second contributor could take
  US2's pure-function tasks (T013, T015) in parallel once Phase 2 lands,
  since those don't depend on T010/T011's workflow YAML.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No
  dependency on User Story 2 or 3.
- **User Story 2 (P2)**: `compose_pull_request_body()` (T013) can start
  after Foundational; wiring it into the workflow (T014) depends on US1's
  T011 (the `create-pull-request` step it extends).
- **User Story 3 (P3)**: Depends on US1's T010 (the job and its `if:`
  guard it verifies).

### Within Each User Story

- Tests are written alongside implementation (Constitution Principle II's
  general spirit, applied here as good practice per plan.md's Testing
  note).
- Foundational script plumbing (T003–T007) before any user-story-specific
  behavior (T008+).
- Same-file tasks (`scripts/sync_agent_integrations.py` across Phases
  2–4; `.github/workflows/ci.yml` across Phases 1, 3–6) are sequential, not
  parallel, even when logically independent — see each task's explicit
  "same file" note above.

### Parallel Opportunities

- T002 (CI scope extension) can run in parallel with T001 in Setup —
  different concerns, T001 makes no file edit.
- T012 (US1 integration test) can run in parallel with T010/T011 (workflow
  YAML) once T009 lands — different files.
- T015 (US2 unit tests) can run in parallel with T014's workflow-YAML
  portion once T013 lands — different files.
- T019 (README mention) can run in parallel with T020/T021 (validation
  gates) in Polish — different files.

---

## Parallel Example: Foundational → User Story 1 handoff

```bash
# Once T009 (main() entry point) lands, these can run together:
Task: "Add sync-agent-integrations job to .github/workflows/ci.yml (T010)"
Task: "Integration test for main() in tests/scripts/test_sync_agent_integrations.py (T012)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (including T002's CI-scope fix)
2. Complete Phase 2: Foundational (CRITICAL — blocks all three stories)
3. Complete Phase 3: User Story 1 (automatic drift detection & PR)
4. **STOP and VALIDATE**: Run quickstart.md Scenarios 1–2 and confirm
   SC-001/SC-003
5. Deploy/demo if ready — a working no-review-content, no-manual-trigger
   sync already delivers the core "don't forget to sync agents" value; US2
   and US3 refine reviewability and convenience on top

### Incremental Delivery

1. Complete Setup + Foundational → core script ready, CI gates cover it
2. Add User Story 1 (drift detection & PR) → test independently →
   deploy/demo (MVP!)
3. Add User Story 2 (reviewable PR content, no auto-merge) → test
   independently → deploy/demo
4. Add User Story 3 (on-demand trigger) → test independently → deploy/demo
5. Polish (README mention, coverage validation, quickstart validation) →
   final release

---

## Phase 7: Post-Review Corrections (PR #50 code review)

- [X] T022 Implement `check_specify_cli_up_to_date()` in
  `scripts/sync_agent_integrations.py`, wrapping `specify self check`
  (research.md #7) and returning the newer release tag if one is available;
  call it first in `main()`, failing the run immediately (before checking
  any integration) with the newer version named when one is found (FR-013;
  spec.md SC-001). This closes a genuine architectural gap Copilot's review
  on PR #50 surfaced: `specify integration upgrade`'s templates are bundled
  inside the pinned CLI itself, so without this check, drift detection
  would silently stop working after the pin's one-time initial migration.
  Unit-tested (`test_check_specify_cli_up_to_date_*`,
  `test_main_stale_cli_fails_without_checking_integrations`).
- [X] T023 Fix `run_integration_upgrade()`'s deletion-only-drift blind spot
  (Copilot review, PR #50): capture `_manifest_tracked_paths(key)` **before**
  the upgrade too, not only after, and scope the `git status` check to the
  union of both — a file the upstream *deleted* is absent from the
  post-upgrade manifest alone, so the original post-only scoping silently
  missed it. Added `test_run_integration_upgrade_detects_deletion_only_drift`.
- [X] T024 Pin the `sync-agent-integrations` job's `actions/checkout@v4`
  step to `ref: main` explicitly (Copilot review, PR #50) — an on-demand
  `workflow_dispatch` launched from a non-default branch would otherwise
  checkout that branch, causing `peter-evans/create-pull-request` to default
  its PR base to it instead of `main`.
- [X] T025 Add `scripts/sync_agent_integrations.py` to the `complexity`
  job's `check_maintainability.py` invocation in `.github/workflows/ci.yml`
  (second Copilot review round, PR #50) — the new script was already added
  to `lint`/`typecheck`/`security` (T002) but the separate Maintainability
  Index gate (Constitution Principle IX) was missed.
- [X] T026 Check `git status`'s exit code in `run_integration_upgrade()`
  (second Copilot review round) — a failed `git status` commonly returns
  empty stdout, which was being silently misread as "nothing changed";
  now classified as `STATUS_FAILED`. Added
  `test_run_integration_upgrade_git_status_failure_is_reported`.
- [X] T027 Restructure `check_specify_cli_up_to_date()` to return a
  three-state `CliCheckResult` (`up-to-date`/`update-available`/
  `inconclusive`) instead of `str | None`, and make `main()` fail the run
  on *either* a confirmed-stale pin or an inconclusive check (a non-zero
  exit, or the CLI's own `Could not check latest release`/`Could not
  validate latest release tag` text) — not just the confirmed-stale case
  (second Copilot review round). The original design silently treated a
  network hiccup as "assume up to date," which would break spec.md
  SC-001's notification guarantee exactly as easily as the bug FR-013
  itself was written to close. Updated spec.md FR-013, data-model.md,
  contracts/sync-workflow-contract.md, and research.md #7 to match; added
  `test_check_specify_cli_up_to_date_nonzero_exit_is_inconclusive` and
  `test_main_inconclusive_cli_check_also_fails_without_checking_integrations`.
- [X] T028 Correct contracts/sync-workflow-contract.md's "Triggers" section
  (second Copilot review round): it read as if `push`/`pull_request` never
  start "this workflow" at all, when in the actual shared-`ci.yml`
  implementation they start the workflow file — only this specific job is
  skipped by its own `if:` condition.
- [X] T029 Fix `check_specify_cli_up_to_date()`'s classification logic
  (third Copilot review round): it was a blocklist of two known failure
  strings, silently defaulting to "up to date" for anything else —
  including a third real exit-0 graceful-failure message
  (`Current version could not be determined.`) it missed. Inverted to an
  allowlist: only the literal `Up to date:` success marker counts as
  confirmed-current (research.md #8).
- [X] T030 Distinguish a missing per-integration manifest from an empty one
  in `_manifest_tracked_paths()`/`run_integration_upgrade()` (third
  Copilot review round) — `specify integration upgrade <key>` exits 0 with
  "Nothing to upgrade" and makes zero changes when the manifest is absent
  (an installed-but-never-materialized integration), which was previously
  silently read as "no drift" (research.md #8).
- [X] T031 Add `check_shared_infra_modified()` and surface a locally-
  modified shared `speckit`-tracked file in the pull-request body (third
  Copilot review round; FR-008 extended) — regenerating any integration
  also reconciles shared infrastructure tracked separately from that
  integration's own manifest, which was previously invisible to this
  workflow entirely (research.md #8).
- [X] T032 Add a `concurrency: {group: sync-agent-integrations,
  cancel-in-progress: false}` block to the `sync-agent-integrations` job
  (third Copilot review round) — an overlapping scheduled + manually-
  dispatched run could otherwise race pushing the same fixed branch and
  fail with a stale `--force-with-lease` (research.md #3 addendum).

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- No new runtime dependencies are introduced by this feature (plan.md); the
  only new external tool is `specify-cli`, installed and pinned in CI via
  `uv tool install` (research.md #2), not added to `pyproject.toml`
- T002 remediates `/speckit-analyze` finding C1 (Constitution Principle IX
  gap): `scripts/sync_agent_integrations.py` is explicitly added to CI's
  lint/typecheck/security commands, while the pre-existing, unrelated
  `scripts/check_maintainability.py` deliberately stays out of scope for
  this feature
