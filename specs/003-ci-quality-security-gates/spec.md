# Feature Specification: Automated CI Quality & Security Gates

**Feature Branch**: `docs/constitution-quality-security-gates`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Implement the automated code complexity/maintainability,
static type-checking, and security scanning gates required by Constitution Principle IX
(v1.4.0): cyclomatic complexity and Maintainability Index thresholds (ruff C90/mccabe,
radon, xenon), static type-checking (mypy), static security analysis (bandit), dependency
vulnerability scanning (pip-audit), and continuous SAST (GitHub CodeQL) — all running in CI
on every pull request and configured as required status checks on the `main` branch, with
branch-protection bypass scoped so it can never skip these gates, only the human-review
requirement."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every Pull Request Shows Objective Quality & Security Results (Priority: P1)

A maintainer opens a pull request and, before deciding whether to merge, sees automated,
objective results for code complexity/maintainability, static type correctness, and
security/dependency risk — not just lint and test pass/fail — so quality regressions and
vulnerabilities are visible at review time rather than discovered later.

**Why this priority**: This is the core value of the feature: making previously invisible
risks (rising complexity, type errors, insecure code patterns, vulnerable dependencies)
visible on every single change, which is the entire rationale behind Constitution
Principle IX.

**Independent Test**: Open a pull request that changes any file under `src/`; confirm the
PR's checks section shows a distinct, clearly labeled result for complexity/maintainability,
type-checking, and security/dependency scanning, independent of the existing lint/test/build
checks.

**Acceptance Scenarios**:

1. **Given** a pull request that introduces a function exceeding the configured complexity
   threshold, **When** CI runs, **Then** the complexity check fails and clearly identifies
   the offending function and file.
2. **Given** a pull request that introduces a new static type error, **When** CI runs,
   **Then** the type-checking check fails and identifies the file/line and the type
   mismatch.
3. **Given** a pull request that introduces a high- or medium-severity security finding,
   **When** CI runs, **Then** the security check fails and identifies the finding, its
   severity, and its location.
4. **Given** a pull request that adds a dependency with a known vulnerability, **When** CI
   runs, **Then** the dependency scan fails and identifies the vulnerable package and
   advisory.
5. **Given** a pull request that meets all thresholds and has no new findings, **When** CI
   runs, **Then** all four checks (complexity, type-checking, security, dependency scan)
   pass and are visible as distinct, successful checks.
6. **Given** a pull request that drops a module's Maintainability Index below the
   configured minimum grade without exceeding any single function's cyclomatic complexity
   threshold, **When** CI runs, **Then** the maintainability check fails independently of
   the cyclomatic-complexity check and identifies the affected module.

---

### User Story 2 - Quality & Security Gates Cannot Be Silently Bypassed (Priority: P1)

A repository owner or administrator MUST NOT be able to merge a pull request that fails any
complexity, maintainability, type-checking, security, or dependency-scanning gate, even
though they may still be able to bypass the separate human-review-approval requirement for
their own pull requests (a pre-existing, distinct governance decision, not part of this
feature).

**Why this priority**: Principle IX explicitly requires this separation; without it, the
gates added in User Story 1 are only advisory and can be routinely bypassed, defeating the
purpose of the amendment. This directly resolves the CRITICAL finding from the constitution
consistency analysis, where disabling `enforce_admins` for `main` currently allows bypassing
every required check indiscriminately.

**Independent Test**: As a repository administrator, attempt to merge a pull request that
fails the complexity, type-checking, security, or dependency-scan check; confirm the merge
is blocked regardless of administrator role. Separately, confirm an administrator can still
merge their own pull request when only the review-approval requirement (not any Principle IX
gate) is unmet.

**Acceptance Scenarios**:

1. **Given** a pull request failing the security scan, **When** a repository administrator
   attempts to merge, **Then** the merge is blocked until the finding is resolved or an
   explicitly documented suppression is added and the check re-run and passed.
2. **Given** a pull request that passes all Principle IX gates but lacks an approving
   review, **When** the repository owner (as the PR author) attempts to merge, **Then**
   the review-approval requirement alone may be bypassed, without affecting enforcement of
   any other required check.

---

### User Story 3 - Documented Exceptions Instead of Silent Suppressions (Priority: P2)

A contributor who has a legitimate reason to accept a specific finding (e.g., a
false-positive security warning, or a function whose complexity is justified by the
underlying calculation logic) can record an explicit, reviewable exception rather than
disabling the check entirely or silently ignoring the failure.

**Why this priority**: Without a sanctioned exception path, contributors are incentivized to
either weaken checks globally (undermining User Story 1) or route around them entirely.
This is lower priority than establishing the gates themselves (P1) but necessary for the
gates to remain sustainable over time.

**Independent Test**: Introduce a known false-positive finding, add a documented,
tool-native suppression (e.g., an inline `# nosec` / `# noqa` comment with a justification,
or an equivalent per-tool ignore mechanism) referencing the pull request rationale, and
confirm the check passes while the suppression remains visible in the codebase (not hidden
in CI configuration alone).

**Acceptance Scenarios**:

1. **Given** a known false-positive security finding, **When** a contributor adds a
   documented suppression with rationale, **Then** the security check passes and the
   suppression is visible in the changed file, not only in CI configuration.
2. **Given** a pull request with an undocumented suppression (no rationale), **When** it is
   reviewed, **Then** reviewers can identify and reject the undocumented exception before
   merge (per Development Workflow review requirements).

---

### Edge Cases

- What happens when existing code (from `001-metal-drilling-calc` / `002-constrained-calculation-modes`)
  does not meet a newly introduced threshold the first time a gate is enabled? The gate
  MUST NOT retroactively block unrelated pull requests for pre-existing violations; any
  pre-existing findings MUST be catalogued and either remediated or explicitly, visibly
  baselined/suppressed before or as part of enabling that specific gate as a required
  check, so the rollout itself does not silently grandfather undocumented debt.
- How does the system handle a dependency vulnerability with no available upstream fix yet?
  The finding MUST still be surfaced, and merge MUST require an explicit, documented
  risk-acceptance rationale (per FR-009's suppression-record mechanism) rather than blocking
  indefinitely or being silently ignored.
- How does the system handle a pull request that only touches non-code files (e.g.,
  documentation)? Gates that are inapplicable (e.g., no source files changed) MAY report a
  neutral/skipped result rather than a failure, but MUST NOT be silently omitted from the
  PR's checks entirely.
- What happens if the platform's bypass mechanism cannot technically distinguish "skip
  review" from "skip all required checks" for a given repository configuration? This MUST
  be treated as a configuration constraint to resolve during planning (e.g., by adopting a
  bypass mechanism that supports per-check or per-actor scoping), not as a reason to leave
  quality/security gates bypassable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: CI MUST measure cyclomatic complexity for every function in changed source
  code on every pull request and fail the check when a configured threshold is exceeded.
- **FR-002**: CI MUST measure a Maintainability Index (or equivalent maintainability metric)
  per module on every pull request and fail the check when a configured minimum grade/score
  is not met.
- **FR-003**: CI MUST run static type-checking on every pull request and fail the check when
  new or changed code introduces type errors.
- **FR-004**: CI MUST run static security analysis on every pull request and fail the check
  when a high- or medium-severity finding is introduced without a documented suppression.
- **FR-005**: CI MUST run dependency vulnerability scanning on every pull request, and MUST
  also run on a recurring schedule (at least weekly) independent of pull request activity,
  so vulnerabilities disclosed after merge are still detected.
- **FR-006**: The repository MUST have continuous, repository-level static application
  security testing (SAST) enabled, independent of the per-pull-request checks in FR-001
  through FR-005.
- **FR-007**: Every check in FR-001 through FR-005 — as well as the pre-existing lint, test,
  build, and documentation-build checks these gates run alongside — MUST be configured as a
  required status check on the `main` branch, such that a pull request cannot be merged
  while any of them is failing.
- **FR-008**: The mechanism used to allow a repository owner/administrator to bypass the
  human-review-approval requirement MUST NOT also allow bypassing any required status check
  named in FR-007 (the FR-001 through FR-005 gates, or the pre-existing lint/test/build/docs
  checks); if the current branch-protection mechanism cannot express this distinction, an
  alternative mechanism that can MUST be adopted.
- **FR-009**: Any accepted exception to a complexity, maintainability, security, or
  dependency finding MUST be recorded as a visible, tool-native suppression with a written
  rationale in the affected file or configuration, not only as a change to CI behavior.
- **FR-010**: Numeric or categorical thresholds for every check in FR-001 through FR-005
  MUST be defined in version-controlled project configuration (e.g., `pyproject.toml` or
  equivalent tool configuration files), not embedded only in CI workflow definitions or
  left undocumented.
- **FR-011**: Pre-existing findings in code that already existed before a given gate became
  a required check MUST be catalogued and either remediated or explicitly baselined/suppressed
  before that gate blocks unrelated pull requests.

### Key Entities

- **Quality/Security Finding**: A single reported issue (complexity violation,
  maintainability drop, type error, security issue, or vulnerable dependency), with a
  location, severity/threshold context, and status (open, remediated, suppressed).
- **Suppression Record**: A documented, tool-native exception for a specific finding,
  including its rationale, so it remains visible and reviewable in the codebase.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pull requests changing source code display complexity,
  maintainability, type-checking, and security/dependency results before they can be merged.
- **SC-002**: Zero pull requests merge into `main` with an unresolved, undocumented high- or
  medium-severity security or dependency finding.
- **SC-003**: A repository administrator can no longer merge a pull request that fails any
  complexity, maintainability, type-checking, security, or dependency-scanning check,
  regardless of role or override privileges.
- **SC-004**: A contributor can identify, from the pull request's checks alone (without
  contacting the repository owner), exactly which metric or finding failed and why.
- **SC-005**: All pre-existing complexity/maintainability/security/dependency findings in
  code merged before this feature are catalogued, with each either remediated or explicitly
  documented as an accepted exception, before the corresponding gate becomes a required
  check.

## Assumptions

- The specific tools named in Constitution Principle IX (ruff C90/mccabe, radon, xenon,
  mypy, bandit, pip-audit, GitHub CodeQL) are the tools to implement this feature with;
  no alternative tool evaluation is in scope.
- Exact numeric thresholds (max cyclomatic complexity, minimum Maintainability Index grade)
  are not fixed by this specification and are deferred to `/speckit.plan`, consistent with
  the constitution's amendment notes.
- The repository is public, which is expected to make GitHub's newer repository-ruleset
  bypass controls (supporting scoped, per-actor bypass) available even without a paid plan;
  if unavailable, FR-008 requires finding an equivalent mechanism during planning rather than
  accepting an all-or-nothing bypass.
- "Changed source code" for FR-001/FR-002 means files under `src/`; test, documentation, and
  configuration-only changes are not subject to complexity/maintainability thresholds.
- Severity terms in FR-004 ("high- or medium-severity") follow the reporting tool's own
  severity scale (e.g., bandit's HIGH/MEDIUM/LOW levels) rather than a separate universal
  standard defined by this feature.
- Triage and remediation of a raised GitHub CodeQL alert (FR-006) follows the repository's
  existing pull request review process (Constitution's Development Workflow section); this
  feature's scope is limited to enabling continuous detection, not building a separate
  alert-triage tool or process.
- A failing scheduled dependency-scan run (FR-005) relies on GitHub Actions' default
  failed-workflow notification behavior; no additional alerting or ticketing integration is
  in scope for this feature.
- The five tools/platform features named above (research.md) are treated as available and
  maintained for the duration of this feature's rollout; their own long-term deprecation or
  unavailability risk is out of scope for this specification.
- External/forked-repository pull requests are out of scope; all required checks are
  assumed to run against branches within this repository. Handling restricted secrets/
  permissions for fork-originated pull requests, if external contributions begin, is a
  follow-up concern not addressed here.
- CI for these gates runs against a single Python version per job (no build matrix across
  Python 3.9-3.12); if a version matrix is introduced later, each required status check
  name would need to be re-specified per matrix leg, which is out of scope for this feature.
- This feature governs process/CI configuration; it does not change any existing
  calculation logic, public API, or user-facing behavior of `machine-calc` itself.
