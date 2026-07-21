# Checklist: CI Quality & Security Gates — Requirements Quality

**Purpose**: Author self-review before `/speckit.implement` — validate that spec.md,
plan.md, and tasks.md for this feature are complete, unambiguous, internally consistent,
and ready to implement. This checklist tests the requirements themselves, not the eventual
CI implementation.

**Created**: 2026-07-21
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md)
**Depth**: Standard | **Audience**: Author (pre-implementation self-review)

---

## Requirement Completeness

- [x] CHK001 - Are requirements defined for every gate named in Constitution Principle IX (complexity, MI, mypy, bandit, pip-audit, CodeQL), with none left implicit? [Completeness, Spec §FR-001–FR-006]
- [x] CHK002 - Is a requirement defined for how newly-added dev dependencies (mypy, radon, bandit, pip-audit) are declared/version-constrained, not just that they exist? [Completeness, Spec §FR-010] (Note: `xenon` was tried and removed — see research.md #2 Correction note — since it does not enforce Maintainability Index; `radon` alone, via `scripts/check_maintainability.py`, is used instead.)
- [x] CHK003 - Are requirements defined for what happens to a check's status when a pull request touches no source files (e.g., docs-only change)? [Completeness, Spec Edge Cases]
- [x] CHK004 - Are requirements defined for how the weekly scheduled dependency scan's failure is surfaced/actioned, given it runs independent of any pull request? [Gap, Spec §FR-005]
- [x] CHK005 - Is there a requirement covering who/what remediates a CodeQL alert once raised, or is detection alone (FR-006) considered sufficient scope for this feature? [Gap, Spec §FR-006]

## Requirement Clarity

- [x] CHK006 - Is "configured threshold" (FR-001, FR-002) tied to a specific, named source of truth (e.g., "as defined in pyproject.toml") rather than left as an undefined external configuration? [Clarity, Spec §FR-001, FR-002, FR-010]
- [x] CHK007 - Is "high- or medium-severity" (FR-004) defined by reference to a specific tool's severity scale (e.g., bandit's own levels) rather than left as an assumed universal standard? [Clarity, Spec §FR-004]
- [x] CHK008 - Is "documented suppression" (FR-004, FR-009) specific enough to be checked objectively (e.g., "visible in the changed file, with non-empty rationale") rather than left to reviewer judgment alone? [Clarity, Spec §FR-009]
- [x] CHK009 - Is "recurring schedule" (FR-005) quantified with a specific cadence (e.g., weekly) rather than left open-ended? [Clarity, Spec §FR-005]
- [x] CHK010 - Is the distinction between "bypass the review-approval requirement" and "bypass a required check" (FR-008) precise enough that a reader unfamiliar with GitHub's ruleset/branch-protection model could still verify compliance? [Clarity, Spec §FR-008]

## Requirement Consistency

- [x] CHK011 - Do FR-007 ("required status check on main") and FR-008 (bypass scoping) agree on which checks are in scope — i.e., does FR-008's "any check in FR-001 through FR-005" consistently exclude the pre-existing lint/test/build/docs checks, or should those also be explicitly covered? [Consistency, Spec §FR-007, FR-008]
- [x] CHK012 - Are the tool choices in spec.md's Assumptions section consistent with the tool choices actually reflected in every Functional Requirement (no requirement silently implying a different/additional tool)? [Consistency, Spec Assumptions vs FR-001–FR-006]
- [x] CHK013 - Does plan.md's Constitution Check table's "PASS (not applicable)" reasoning for Principles III/V/VI/VII/VIII remain consistent with spec.md's stated scope boundary ("does not change any existing calculation logic...")? [Consistency, Plan Constitution Check vs Spec Assumptions]
- [x] CHK014 - Are severity/threshold terms used consistently between spec.md (FR-004's "high- or medium-severity") and the data-model.md Finding entity's `severity` field (which also lists "low"/"info")? [Consistency, Spec §FR-004 vs data-model.md]

## Acceptance Criteria Quality

- [x] CHK015 - Can SC-001 ("100% of pull requests... display... results") be objectively measured without manually sampling every PR (e.g., via a required-check list query), or does it rely on subjective spot-checking? [Measurability, Spec §SC-001]
- [x] CHK016 - Can SC-002 ("zero pull requests merge... with an unresolved, undocumented... finding") be verified after the fact, given that a merged PR's CI state may not be queryable retroactively without an audit log requirement? [Measurability, Spec §SC-002]
- [x] CHK017 - Is SC-003's claim ("administrator can no longer merge...") testable without requiring destructive/real bypass attempts against `main`, per the constraints described in quickstart.md §2–§3? [Measurability, Spec §SC-003, quickstart.md]
- [x] CHK018 - Are the acceptance scenarios under User Story 2 sufficient to prove FR-008 end-to-end (both "review bypass works" and "gate bypass does not work"), or is a scenario missing for the case where both conditions occur on the same pull request? [Coverage, Spec User Story 2]

## Scenario Coverage

- [x] CHK019 - Are requirements defined for the primary flow (a normal, passing pull request) as clearly as for the failure flows, so "everything is fine" is not left implicit? [Coverage, Spec User Story 1]
- [x] CHK020 - Are exception/error flows defined for each of the five gates individually (complexity, MI, type error, security, dependency), or only in aggregate? [Coverage, Spec §FR-001–FR-005, Acceptance Scenarios]
- [x] CHK021 - Is a recovery flow defined for what a contributor does after a gate fails — i.e., does the spec describe the expected next step (fix vs. suppress vs. escalate), or is that left entirely to User Story 3 without linking back to User Story 1's failure scenarios? [Coverage, Spec User Story 1 vs User Story 3]
- [x] CHK022 - Is the non-drilling-calculation-logic scope boundary (spec.md Assumptions) reflected in an explicit "out of scope" statement, or only implied by omission? [Clarity, Spec Assumptions]

## Edge Case Coverage

- [x] CHK023 - Is the pre-existing-code rollout edge case (spec.md Edge Cases, 1st bullet) specific enough to define "done" — e.g., does it specify that ALL pre-existing findings must be catalogued, not just a sample? [Clarity, Spec Edge Cases]
- [x] CHK024 - Is there a defined outcome for a dependency vulnerability with no available fix (spec.md Edge Cases, 2nd bullet) that ties back to a Functional Requirement (FR-009's suppression mechanism), or does it introduce an unreferenced new concept ("risk-acceptance rationale")? [Consistency, Spec Edge Cases vs FR-009]
- [x] CHK025 - Is the platform-bypass-scoping edge case (spec.md Edge Cases, 4th bullet) resolved with a concrete fallback requirement if the assumed ruleset mechanism (research.md #7) turns out to be unavailable for this repository's plan/visibility? [Gap, Spec Edge Cases, Assumptions]

## Non-Functional Requirements

- [x] CHK026 - Are there any requirements or constraints on CI job execution time for the new gates (e.g., an upper bound), or is this left entirely unconstrained? [Gap, Plan Technical Context "Performance Goals"]
- [x] CHK027 - Are requirements defined for what happens if a GitHub-hosted runner or the CodeQL/pip-audit service is unavailable/rate-limited during a pull request check run (transient infrastructure failure vs. a genuine gate failure)? [Gap, Non-Functional]
- [x] CHK028 - Is there a requirement or assumption stating whether these gates apply equally to forked-repository pull requests (where secrets/permissions often differ in GitHub Actions), or is this scope left unaddressed? [Gap, Non-Functional]

## Dependencies & Assumptions

- [x] CHK029 - Is the assumption that "the repository is public... making rulesets available even without a paid plan" validated, or does it remain an unverified assumption at spec-approval time? [Assumption, Spec Assumptions] *(Note: tasks.md T022a already schedules verification during implementation — confirm this checklist item is satisfied by that task's existence, not by the spec alone.)*
- [x] CHK030 - Are all five external tools (ruff C90, radon via `scripts/check_maintainability.py`, mypy, bandit, pip-audit) and the GitHub CodeQL platform feature treated as fixed dependencies whose unavailability/deprecation risk is out of scope, and is that stated explicitly rather than left implicit? [Assumption, Spec Assumptions]
- [x] CHK031 - Does the spec identify its dependency on `001-metal-drilling-calc`'s still-unimplemented CI workflow task (T037) as a prerequisite/co-requisite, or could a reader implement this feature without realizing that base workflow doesn't exist yet? [Dependency, Plan Project Structure, tasks.md T014]

## Ambiguities & Conflicts

- [x] CHK032 - Is there any remaining ambiguity in how "required status check" (FR-007) interacts with GitHub's distinction between a job name and a check name (e.g., matrix jobs producing multiple check contexts per job), given tasks.md T023 lists checks by job name only? [Ambiguity, tasks.md T023]
- [x] CHK033 - Is a requirement/traceability ID scheme consistently applied across spec.md (FR-###/SC-###), data-model.md (unlabeled entities), and contracts/ci-checks-contract.md (unlabeled rows), or would a cross-reference between a contract row and its originating FR benefit from explicit ID tags? [Traceability, contracts/ci-checks-contract.md]

---

## Resolution Notes (Author Self-Review Walkthrough — 2026-07-21)

All 33 items reviewed against spec.md, plan.md, tasks.md, research.md, data-model.md, and
contracts/ci-checks-contract.md. Outcomes:

**Items requiring a spec/tasks fix (now applied):**
- CHK004, CHK005 — added Assumptions bullets scoping scheduled-scan-failure notification and
  CodeQL alert triage to existing GitHub/review defaults, not new tooling.
- CHK007 — added Assumption: severity terms follow each tool's own scale.
- CHK009 — FR-005 now says "at least weekly" explicitly, not just in research.md/tasks.md.
- CHK011 — FR-007/FR-008 now explicitly include the pre-existing lint/test/build/docs checks
  in scope, matching the contract's broader bypass restriction.
- CHK020 — added Acceptance Scenario 6 (Maintainability Index failure, independent of
  cyclomatic complexity) to User Story 1; added task T020a; corrected T020's check mapping
  (cyclomatic complexity is enforced by `lint`, not `complexity`, per the earlier F2 fix) and
  updated quickstart.md §2 to match.
- CHK024 — Edge Cases' dependency-vulnerability-no-fix bullet now explicitly cites FR-009's
  suppression mechanism instead of introducing an unreferenced "risk-acceptance" concept.
- CHK027, CHK028, CHK030, CHK032 — added Assumptions bullets explicitly scoping out transient
  CI infrastructure resilience, forked-repository pull requests, tool/platform deprecation
  risk, and multi-Python-version build matrices as out of scope for this feature.

**Items verified as already satisfied (no change needed):**
- CHK001, CHK002 (covered by Constitution Principle IV, not duplicated here), CHK003, CHK006,
  CHK008 (contract already defines suppression precisely), CHK010, CHK012, CHK013, CHK014,
  CHK015, CHK016 (satisfied by construction via required-check enforcement, not audit log),
  CHK017, CHK018 (combined case is logically subsumed by Scenario 1's unconditional block),
  CHK019, CHK021 (linkage between US1 failures and US3 suppression is implicit via FR-009
  cross-references, judged sufficient at Standard depth), CHK022, CHK023, CHK025 (already
  resolved by tasks.md T022a from the prior `/speckit.analyze` pass), CHK026, CHK029 (same),
  CHK031, CHK033 (explicit cross-reference IDs between data-model.md/contracts and FR-###
  judged unnecessary overhead for a CI-config-only feature at Standard depth).

No item required reopening `/speckit.clarify`. Checklist is now fully resolved (33/33).

