---

description: "Task list template for feature implementation"
---

# Tasks: Automated CI Quality & Security Gates

**Input**: Design documents from `/specs/003-ci-quality-security-gates/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ci-checks-contract.md, quickstart.md

**Tests**: This feature is CI/process configuration, not application code with its own automated test suite. Verification is via the quickstart.md scenarios (real pull requests exercising each gate) rather than pytest-style tests; these are captured as explicit validation tasks in each phase below instead of a separate "Tests" subsection.

**Organization**: Tasks are grouped by user story (US1 = gates visible on every PR, P1; US2 = gates cannot be bypassed, P1; US3 = documented exceptions, P2) on top of a shared Foundational phase (the CI workflow skeleton and tool configuration all three user stories build on).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow the existing single-project `pyproject.toml` + `.github/workflows/` + `src/machine_calc/` layout (plan.md Project Structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the new dev-tool dependencies and version-controlled thresholds all gates read from (spec.md FR-010).

- [x] T001 Add `mypy`, `radon`, `bandit`, `pip-audit` to `[project.optional-dependencies].dev` in `pyproject.toml` (research.md #1-#5; `xenon` was added then removed during T020a's real-world validation once it was discovered not to enforce Maintainability Index at all)
- [x] T002 [P] Add `"C90"` to `[tool.ruff.lint].select` and set `[tool.ruff.lint.mccabe] max-complexity = 10` in `pyproject.toml` (research.md #1, FR-001, FR-010)
- [x] T003 [P] Add `[tool.mypy]` section to `pyproject.toml` targeting `src/machine_calc` with `warn_return_any = true`, `ignore_missing_imports = true` (research.md #3, FR-003, FR-010)
- [x] T004 [P] Add `[tool.bandit]` section to `pyproject.toml` (`tests` excluded, medium+ severity) for FR-004/FR-010, ready to hold any future named-skip suppressions with rationale comments (research.md #4, FR-009)
- [x] T005 [P] Document the Maintainability Index threshold in a short comment block near `[tool.ruff]` in `pyproject.toml`, referencing `scripts/check_maintainability.py` (radon `mi` has no native `pyproject.toml` config section or CLI failure-threshold flag; the threshold is versioned in that script per FR-010; research.md #2 — corrected from an original `xenon`-based design, see research.md #2 Correction note)
- [x] T006 `pip install -e ".[dev]"` locally and confirm all four new tools (`mypy`, `radon`, `bandit`, `pip-audit`) are importable/runnable before proceeding to Phase 2

**Checkpoint**: All five gates are runnable locally with version-controlled thresholds; nothing wired into CI yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Run every new gate once against the current `main` tree, remediate or suppress any pre-existing findings (spec.md FR-011, research.md #8), and stand up the shared CI workflow skeleton — all three user stories depend on this being clean before any gate becomes a required check.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T007 Run `ruff check src/ tests/` (with T002's C90 rule) and `python scripts/check_maintainability.py src/` (T005) against current `main`; catalogue any findings in this task's PR description
- [x] T008 Remediate or add a documented `# noqa: C901`-with-rationale suppression (per contracts/ci-checks-contract.md Suppression contract) for every finding from T007, so `src/machine_calc` passes both commands cleanly (depends on T007; FR-011)
- [x] T009 [P] Run `mypy src/machine_calc` (T003) against current `main`; catalogue any findings in this task's PR description
- [x] T010 [P] Remediate or add a documented `# type: ignore[<code>]`-with-rationale suppression for every finding from T009, so `mypy src/machine_calc` passes cleanly (depends on T009; FR-011)
- [x] T011 [P] Run `bandit -r src -ll` (T004) against current `main`; catalogue any findings in this task's PR description
- [x] T012 [P] Remediate or add a documented `# nosec`-with-rationale suppression for every finding from T011, so `bandit -r src -ll` passes cleanly (depends on T011; FR-011)
- [x] T013 [P] Run `pip-audit` against the current resolved dependency set; catalogue any findings (expected: none, given the minimal dependency footprint per Constitution Principle V) in this task's PR description
  - **Finding**: local shared dev environment surfaced advisories for packages
    (`lxml`, `msgpack`, `pypdf2`, `starlette`, etc.) that are NOT declared
    dependencies of `machine-calc` (whose only runtime dependency is
    `tomli>=2.0; python_version < '3.11'`) — these are unrelated packages
    present in this shared local venv, not a real finding for this project.
    The CI job (T015) runs in a fresh, isolated GitHub Actions runner
    installing only `pip install -e ".[dev]"`, so it will not reproduce this
    noise; no remediation/suppression needed for `machine-calc` itself.
- [x] T014 Create `.github/workflows/ci.yml` with `lint`, `test`, `build`, `docs` (build-only, not publish) jobs per `001-metal-drilling-calc` tasks.md T037 (still unimplemented) — this feature's `complexity`/`typecheck`/`security`/`dependency-scan` jobs (Phase 3-5 below) are added into this same file, not a separate one (plan.md Project Structure; depends on T006); the GitHub Pages publish step (`001-metal-drilling-calc` tasks.md T038) is a distinct job out of scope for this feature and is not affected by these changes
- [x] T015 Add a `dependency-scan` job to `.github/workflows/ci.yml` running `pip-audit`, triggered on `pull_request` AND on a weekly `schedule` cron (contracts/ci-checks-contract.md; research.md #5, FR-005; depends on T013, T014)

**Checkpoint**: `src/machine_calc` passes every new gate cleanly at the CLI level; the base CI workflow file exists with `lint`/`test`/`build`/`docs`/`dependency-scan` jobs. User story phases below add the remaining required-check jobs and the branch-protection/bypass changes.

---

## Phase 3: User Story 1 - Every Pull Request Shows Objective Quality & Security Results (Priority: P1) 🎯 MVP

**Goal**: Every pull request that changes source code displays distinct, clearly labeled complexity, maintainability, type-checking, and security/dependency results (spec.md User Story 1).

**Independent Test**: Open a pull request changing a file under `src/`; confirm the checks section shows `complexity`, `typecheck`, and `security` as distinct, named checks independent of `lint`/`test`/`build`/`docs` (contracts/ci-checks-contract.md).

### Implementation for User Story 1

- [x] T016 [P] [US1] Add a `complexity` job to `.github/workflows/ci.yml` running only `python scripts/check_maintainability.py src/` (T005) for Maintainability Index (FR-002); the C90 cyclomatic-complexity rule (FR-001, T002) is already enforced by the existing `lint` job's `ruff check` invocation and MUST NOT be re-run here to avoid gating the same rule twice, on `push`/`pull_request` (contracts/ci-checks-contract.md; depends on T008, T014). **Implementation correction**: originally implemented with `xenon --max-absolute B --max-modules A --max-average A src/`; discovered during T020a's real scratch-PR validation that `xenon` only enforces cyclomatic complexity (via `radon.complexity`), never Maintainability Index, so it silently never gated FR-002 and duplicated the `lint` job's C90 check instead. Replaced with `scripts/check_maintainability.py` (a thin `radon mi` threshold wrapper); `xenon` removed from `pyproject.toml` dev extras entirely.
- [x] T017 [P] [US1] Add a `typecheck` job to `.github/workflows/ci.yml` running `mypy src/machine_calc`, on `push`/`pull_request` (contracts/ci-checks-contract.md; depends on T010, T014)
- [x] T018 [P] [US1] Add a `security` job to `.github/workflows/ci.yml` running `bandit -r src -ll`, on `push`/`pull_request` (contracts/ci-checks-contract.md; depends on T012, T014)
- [x] T019 [US1] Enable GitHub CodeQL "default setup" for Python via repository Settings → Code security → Code scanning (research.md #6, FR-006) — not a workflow file change, a repository setting
- [ ] T020 [US1] Open a scratch pull request per quickstart.md §2 introducing a deliberately over-threshold-complexity function; confirm the `lint` check (ruff C90) fails and clearly identifies the offending function/file (validates FR-001, spec.md Acceptance Scenario 1; depends on T002, T014)
- [x] T020a [US1] Open a scratch pull request introducing a module whose Maintainability Index drops below the configured minimum grade without exceeding the cyclomatic-complexity threshold; confirm the `complexity` check fails independently of `lint`, clearly identifying the affected module (validates FR-002, spec.md Acceptance Scenario 6; depends on T016). **Finding**: the original `xenon`-based `complexity` job never actually failed on this scenario (xenon doesn't measure MI) — a first local-only run is exactly what caught that bug. Re-validated for real against GitHub Actions on scratch PR #6 (`scratch/validate-mi-gate` against the corrected `ci.yml`): `complexity` failed with `MI=18.91 rank=B` while `lint` (C90) stayed green, confirming the two checks are now genuinely independent; PR closed and branch deleted after confirmation.
- [x] T021 [US1] Repeat quickstart.md-style validation for `typecheck` (introduce a type error) and `security` (introduce a known-bad pattern, e.g. `eval()`), confirming each failure clearly identifies file/line and cause (validates FR-003/FR-004, spec.md Acceptance Scenarios 2-3; depends on T017, T018); revert all scratch changes afterward. **Validated** via scratch PR #7 (`scratch/validate-typecheck-security`, closed + branch deleted): `typecheck` correctly failed on a deliberate `int`/`str` type mismatch. First `security` attempt used `eval()` (bandit B307, **Low** severity) and correctly did NOT fail — this matches FR-004's "high- or medium-severity" scope, not a bug. Switched the probe to `subprocess.call(cmd, shell=True)` (B602, **High** severity) which correctly failed `security`. **Side finding**: bandit's `# nosec` suppression matches the literal substring `nosec` anywhere in a trailing comment (even mid-word, e.g. `nosec-free`), which silently suppressed the first probe's finding — worth flagging in T027/T028's suppression-mechanism documentation so reviewers/authors avoid accidental false-suppressions in real PRs.

**Checkpoint**: User Story 1 is fully functional and independently verifiable — every pull request now surfaces complexity, maintainability, type-checking, and security results as distinct checks.

---

## Phase 4: User Story 2 - Quality & Security Gates Cannot Be Silently Bypassed (Priority: P1)

**Goal**: No actor, including the repository owner/administrator, can merge a pull request that fails any complexity, maintainability, type-checking, security, or dependency-scanning gate — while the pre-existing review-approval bypass for the repository owner continues to work for that requirement alone (spec.md User Story 2; resolves analysis finding C1).

**Independent Test**: As the repository owner, attempt to merge a PR failing `security`; confirm it is blocked. Separately, confirm a PR passing all gates but lacking review can still be merged by the owner via the scoped bypass (quickstart.md §2-§3).

### Implementation for User Story 2

- [x] T022 [US2] Re-enable `enforce_admins` on the existing classic branch protection for `main` as an interim safety measure before the ruleset migration lands, closing the immediate exposure window from PR #3's override (depends on nothing; can run anytime, ideally first). Confirmed via `gh api repos/.../branches/main/protection`: `enforce_admins.enabled: true`.
- [x] T022a [US2] Verify GitHub repository rulesets on this repository's actual plan/visibility (public, free plan) genuinely support per-rule bypass scoping (i.e., a bypass entry on "require pull request" that does NOT apply to required status checks), per research.md #7's assumption — create a disposable test ruleset on a throwaway branch if needed to confirm before committing to T023 (spec.md Edge Cases, bypass-scoping-unavailable case; FR-008; depends on T022). **Finding (research.md #7 corrected)**: GitHub's `bypass_actors` field lives on the ruleset object, not per-rule — a single ruleset's bypass exempts an actor from *all* its rules together, not one rule selectively. True per-rule-group scoping is achieved by splitting rules across **two separate rulesets** targeting the same branch (rulesets combine additively). Empirically validated with a disposable throwaway branch + two scratch rulesets + a real PR (#8, closed) using the Statuses API to flip a `lint` context: merge was correctly blocked while the status was failing (despite the owner's review-only bypass), and succeeded without review once the status passed. All test rulesets/branches/PR deleted after confirmation. T023/T024 below are updated to use this two-ruleset split.
- [ ] T023 [US2] Create a GitHub repository ruleset (**"status checks" ruleset**, no bypass actors) targeting `main` with required status checks for `lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test`, `build`, `docs`, **and `CodeQL`/`Analyze (python)` per T035's finding** (contracts/ci-checks-contract.md; research.md #7; depends on T014, T015, T016, T017, T018, T022a); note that classic branch protection (with `enforce_admins` re-enabled per T022) and this new ruleset MAY coexist during migration — GitHub applies whichever rule is stricter, so `main` remains fully protected throughout T023-T025 with no gap
- [ ] T024 [US2] Create a **separate "PR review" ruleset** targeting `main` containing only the "Require a pull request before merging" rule, with a bypass actor scoped to the repository owner (`bypass_mode: pull_request`); per T022a's finding, this MUST be a distinct ruleset from T023's status-checks ruleset (not a bypass entry within it), since GitHub's bypass scoping applies per-ruleset, not per-rule — leave T023's ruleset with no bypass actors for any actor (contracts/ci-checks-contract.md Ruleset bypass contract; FR-008; depends on T023)
- [ ] T025 [US2] Disable/remove the classic branch protection rule on `main` immediately after T024 is confirmed active (no intervening merges), avoiding any prolonged window where both protections apply and avoiding duplicate/conflicting protection configs (research.md #7; depends on T023, T024)
- [ ] T026 [US2] Validate per quickstart.md §2-§3: a failing required check blocks merge for the repository owner; a PR passing all required checks but lacking review can still be merged by the owner via the bypass (spec.md Acceptance Scenarios 1-2; depends on T025)

**Checkpoint**: Both P1 user stories are complete — gates are visible (US1) and unconditionally enforced except for the scoped review-approval bypass (US2). This resolves the CRITICAL findings from the constitution consistency analysis.

---

## Phase 5: User Story 3 - Documented Exceptions Instead of Silent Suppressions (Priority: P2)

**Goal**: A contributor with a legitimate reason to accept a specific finding can record a visible, tool-native suppression with rationale, rather than disabling a check or routing around it (spec.md User Story 3).

**Independent Test**: Introduce a known bandit false positive, add a documented `# nosec` suppression with rationale, confirm the `security` check passes and the suppression is visible in the diff (quickstart.md §4).

### Implementation for User Story 3

- [ ] T027 [P] [US3] Document the suppression mechanisms (inline `# nosec`, `# noqa: C901`, `# type: ignore[<code>]`, `pip-audit` ignore entries — all requiring a trailing rationale comment) in a new "Quality & Security Gates" section of `README.md` or `docs/source/developer-guide.rst`, referencing contracts/ci-checks-contract.md (FR-009; Constitution Principle VII)
- [ ] T028 [US3] Add a reviewer checklist note to the repository (e.g., a PR template snippet or an addition to the Development Workflow section already in `.specify/memory/constitution.md`) reminding reviewers to reject undocumented suppressions per spec.md User Story 3 Acceptance Scenario 2 (depends on T027)
- [ ] T029 [US3] Validate per quickstart.md §4: introduce a deliberate bandit false positive with a documented `# nosec` + rationale, confirm `security` passes and the suppression is visible in the PR diff, then revert the scratch change (depends on T018, T027)

**Checkpoint**: All three user stories are independently functional; the exception path is documented and demonstrated end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, constitution/PR alignment, and full-suite validation spanning all user stories.

- [ ] T030 [P] Update `README.md`'s CI/status description (if present) to mention the new required checks, keeping the existing test-coverage reporting requirement intact (Constitution Principle VII)
- [ ] T031 [P] Update `specs/001-metal-drilling-calc/tasks.md` T037 to reference this feature's `ci.yml` as the source of truth instead of describing a separate, narrower lint/test/build/docs-only workflow, avoiding duplicate/conflicting task definitions across features
- [ ] T032 Execute all 5 quickstart.md scenarios end-to-end in order and confirm actual behavior matches documented expected outcomes (spec.md SC-001 through SC-005)
- [ ] T033 Re-run `pip-audit` and confirm the weekly `schedule` trigger (T015) has fired at least once successfully after merge, independent of pull request activity (FR-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (all three stories need a clean, gate-passing `main` and the base `ci.yml` skeleton to build on).
- **User Story 1 (Phase 3)**: Depends only on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on Foundational completion AND on User Story 1's jobs existing (T023 lists `complexity`/`typecheck`/`security` as required checks, which US1 creates) — sequence US1 before US2.
- **User Story 3 (Phase 5)**: Depends on Foundational completion AND on US1's `security` job (T018) existing for its validation task (T029) — can be planned in parallel with US2 by a second contributor, but its validation step (T029) needs T018 done.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependency on User Story 2 or 3.
- **User Story 2 (P1)**: Can start after Foundational, but its required-check list (T023) depends on US1's job definitions (T016-T018) existing first.
- **User Story 3 (P2)**: Can start after Foundational for documentation tasks (T027, T028); its validation task (T029) depends on US1's `security` job (T018).

### Within Each Phase

- Catalogue-then-remediate pairs in Phase 2 (T007/T008, T009/T010, T011/T012) run sequentially per tool but the three tools' pairs can run in parallel with each other.
- CI workflow job additions (T016-T018) can be authored in parallel (different job blocks in the same file, but logically independent) — apply as sequential edits to avoid merge conflicts within the same PR, though no cross-job data dependency exists.
- Branch-protection/ruleset tasks (T022-T025, including the T022a verification step) are strictly sequential (each depends on the previous ruleset/protection state).

### Parallel Opportunities

- T002, T003, T004, T005 (Setup, different `pyproject.toml` sections) are logically independent but touch the same file — treat as sequential edits within one contributor's work, parallelizable only across contributors coordinating on non-overlapping sections.
- T009/T010, T011/T012, T013 (Foundational, different tools/files) can run in parallel with each other and with T007/T008.
- T016, T017, T018 (US1, distinct job blocks) can be developed in parallel by different contributors before merging into one `ci.yml` PR.
- T027 (US3 documentation) can run in parallel with US2's Phase 4 tasks once Foundational completes.

---

## Parallel Example: Foundational Phase Gate Rollout

```bash
# Launch independent gate-rollout checks together:
Task: "Run mypy src/machine_calc against main and catalogue findings"
Task: "Run bandit -r src -ll against main and catalogue findings"
Task: "Run pip-audit against current dependency set and catalogue findings"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — clean gate rollout, base `ci.yml`)
3. Complete Phase 3: User Story 1 (visible complexity/typecheck/security/CodeQL results)
4. **STOP and VALIDATE**: Run quickstart.md §1-§2 script and confirm SC-001, SC-004
5. Deploy/demo if ready — visible gates alone already deliver significant value even before bypass-scoping (US2) lands

### Incremental Delivery

1. Complete Setup + Foundational → gates runnable locally, clean on `main`
2. Add User Story 1 (visible checks) → validate independently → deploy/demo (MVP!)
3. Add User Story 2 (unbypassable enforcement) → validate independently → deploy/demo — closes the CRITICAL constitution-consistency findings
4. Add User Story 3 (documented exceptions) → validate independently → deploy/demo
5. Polish (docs, T037 cross-reference, full quickstart validation) → feature complete

---

## Notes

- [P] tasks = different files or independent repository settings, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature has no application-level automated tests (data-model.md: CI/process
  configuration only); verification is via quickstart.md scenarios executed against real
  pull requests, captured as explicit tasks per phase above
- Commit after each task or logical group
- Stop at either P1 checkpoint (end of Phase 3 or Phase 4) to validate independently
- T022 (re-enabling `enforce_admins` on classic protection) is a fast, low-risk interim fix
  and SHOULD be done first/early regardless of overall task sequencing, since it directly
  closes the CRITICAL exposure window identified in the constitution consistency analysis

---

## Phase 7: Convergence

- [ ] T034 CRITICAL: Add a PR template / reviewer-checklist requirement that any accepted complexity (FR-001) or security (FR-004) exception be explicitly restated with its written rationale in the pull request description itself — not only as the in-file `# noqa: C901`/`# nosec` suppression comment already required by FR-009/T027/T028 — per Constitution Principle IX (both the complexity and security bullets explicitly require the rationale "in the pull request description") (contradicts)
- [ ] T035 Add the CodeQL default-setup check to the `main` ruleset's required-status-check list configured in T023 (alongside `lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test`, `build`, `docs`), and add a corresponding CodeQL validation scenario to `quickstart.md`, per `contracts/ci-checks-contract.md`'s required-checks table (which already lists CodeQL as a required row) and Constitution Principle IX's "new high-confidence alerts MUST be triaged before... merge" requirement (partial)
