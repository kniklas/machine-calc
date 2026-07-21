# Implementation Plan: Automated CI Quality & Security Gates

**Branch**: `docs/constitution-quality-security-gates` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-ci-quality-security-gates/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add the five automated gates Constitution Principle IX (v1.4.0) requires — cyclomatic
complexity/Maintainability Index (`ruff C90`, `xenon`/`radon mi`), static type-checking
(`mypy`), static security analysis (`bandit`), dependency vulnerability scanning
(`pip-audit`), and continuous SAST (`GitHub CodeQL` default setup) — as new CI jobs
alongside the existing (still-unimplemented) lint/test/build/docs workflow from
`001-metal-drilling-calc` (tasks.md T037), and migrate `main`'s branch protection from
classic protection to a GitHub repository ruleset so the repository owner's existing
review-approval bypass no longer also bypasses these new quality/security gates (research.md
#7), closing the CRITICAL findings from the constitution consistency analysis.

## Technical Context

**Language/Version**: Python 3.9+ (unchanged; this feature adds dev-only tooling, no runtime
dependency or language version change)

**Primary Dependencies**: New dev-only tools added to `[project.optional-dependencies].dev`
in `pyproject.toml`: `mypy`, `radon`, `xenon`, `bandit`, `pip-audit` (research.md #1-#5).
GitHub CodeQL is configured at the repository/platform level (Settings → Code security), not
as a project dependency.

**Storage**: N/A — this feature is CI/process configuration only (data-model.md)

**Testing**: No new application test suite; validation is via the quickstart.md gate-by-gate
local runs and by observing real pull request check behavior (spec.md Acceptance Scenarios)

**Target Platform**: GitHub Actions (ubuntu-latest runners), GitHub repository settings
(rulesets, code scanning) — unchanged from the existing/planned CI target

**Project Type**: Single project — CI/tooling configuration layered onto the existing
single Python package; no new application module

**Performance Goals**: N/A (CI runtime should stay reasonable — target each new job under
~2 minutes on this repo's current ~1500 LOC — but this is not a user-facing performance
requirement and not covered by Constitution Principle V, which governs the *application's*
runtime, not CI)

**Constraints**: MUST NOT retroactively block unrelated pull requests for pre-existing
findings (spec.md FR-011); MUST NOT allow any actor to bypass a failing complexity/
type-checking/security/dependency-scan/lint/test/build/docs check (spec.md FR-008); MUST use
version-controlled configuration for all thresholds (spec.md FR-010, `pyproject.toml`)

**Scale/Scope**: Five new CI jobs/gates plus a branch-protection migration (classic →
ruleset); no change to `src/machine_calc`'s runtime behavior, public API, or calculation
logic

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Linting MUST pass in CI (existing); static type-checking (mypy) MUST be configured and pass in CI | PASS — `mypy` added as a new required job (research.md #3); permissive initial config avoids an unrelated rewrite of existing code |
| II. Testing Standards | ≥90% coverage on calculation modules, CI-enforced | PASS (unaffected) — this feature adds no calculation logic; existing `pytest --cov --cov-fail-under=90` job is unchanged |
| III. Calculation Robustness & Accuracy | N/A — no calculation logic touched | PASS (not applicable) |
| IV. Python Packaging & Versioning | New dev dependencies declared explicitly in `pyproject.toml` with version constraints | PASS — `mypy`, `radon`, `xenon`, `bandit`, `pip-audit` added to `dev` extras only, no runtime dependency change |
| V. Resource-Constrained Compatibility | N/A to the application runtime; CI tooling runs on GitHub-hosted runners, not the constrained target hardware | PASS (not applicable) |
| VI. Extensibility by Design | N/A — no operation/module architecture change | PASS (not applicable) |
| VII. Documentation & Publishing | N/A — no new user/developer-facing documentation content beyond this feature's own spec/plan artifacts (README already tracks CI status per Principle VII, unaffected by this feature) | PASS (not applicable) |
| VIII. Internationalization of User-Facing Messages | N/A — no REPL/CLI/error message changes | PASS (not applicable) |
| IX. Automated Code Quality, Complexity & Security Gates | This feature's entire purpose is implementing Principle IX itself | PASS — every FR in spec.md traces directly to a Principle IX bullet; research.md #1-#8 resolve tool/threshold/rollout/bypass-scoping decisions |

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/003-ci-quality-security-gates/
├── plan.md                        # This file (/speckit.plan command output)
├── research.md                    # Phase 0 output (/speckit.plan command)
├── data-model.md                  # Phase 1 output (/speckit.plan command)
├── quickstart.md                  # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── ci-checks-contract.md      # Phase 1 output (/speckit.plan command)
├── checklists/
│   └── requirements.md
└── tasks.md                       # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
pyproject.toml                     # MODIFY: add mypy/radon/xenon/bandit/pip-audit to
                                    #   [project.optional-dependencies].dev; add [tool.mypy],
                                    #   [tool.bandit] sections; add "C90" to
                                    #   [tool.ruff.lint].select with max-complexity config
                                    #   (research.md #1, #3, #4, FR-010)

.github/
└── workflows/
    └── ci.yml                     # CREATE (this feature extends/replaces
                                    #   001-metal-drilling-calc's still-unimplemented T037):
                                    #   lint, complexity (ruff C90 + xenon), typecheck (mypy),
                                    #   security (bandit), dependency-scan (pip-audit, incl.
                                    #   weekly schedule trigger), test, build, docs jobs —
                                    #   see contracts/ci-checks-contract.md for exact job/
                                    #   check names

src/machine_calc/                  # NO functional changes; mypy/bandit may require minor,
                                    #   behavior-preserving fixes (type annotations, narrow
                                    #   `# type: ignore`/`# nosec` suppressions with
                                    #   rationale) surfaced by the Phase 0 "gate rollout"
                                    #   pass (research.md #8) — tracked as tasks, not
                                    #   pre-applied by this plan

(GitHub repository settings, not source-controlled)
├── Code security → Code scanning → CodeQL default setup   # ENABLE (research.md #6)
└── Rules → Rulesets → "main" ruleset                       # CREATE, replacing classic
                                                              #   branch protection on `main`
                                                              #   (research.md #7); required
                                                              #   status checks per
                                                              #   contracts/ci-checks-
                                                              #   contract.md; bypass list
                                                              #   scoped to the repository
                                                              #   owner on the pull-request-
                                                              #   approval rule only
```

**Structure Decision**: No new application module or package. This feature's surface area is
almost entirely `pyproject.toml` tooling configuration, one new/extended GitHub Actions
workflow file, and GitHub repository settings (CodeQL, ruleset) that are not part of the
source tree. `src/machine_calc/` changes, if any, are limited to narrow, behavior-preserving
fixes/suppressions surfaced when the new gates first run against existing code
(research.md #8), not a restructuring — consistent with spec.md's Assumptions ("this feature
governs process/CI configuration; it does not change any existing calculation logic, public
API, or user-facing behavior").

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
