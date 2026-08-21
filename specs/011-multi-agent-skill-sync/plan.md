# Implementation Plan: Periodic Multi-Agent Skill Sync Workflow

**Branch**: `011-multi-agent-skill-sync` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/011-multi-agent-skill-sync/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a recurring GitHub Actions workflow (weekly cron + on-demand
`workflow_dispatch`, matching the existing `dependency-scan` job's trigger
pattern) that regenerates every coding-agent integration currently installed
in this repository (`.specify/integration.json`'s `installed_integrations`)
from Spec Kit's upstream template source via `specify integration status`/
`specify integration upgrade`, and opens or updates a single pull request
only when real drift is found — implementing the "automated recurring job"
Constitution Principle XI already anticipates. A small Python helper script
under the existing `scripts/` directory (mirroring the
`scripts/check_maintainability.py` precedent) drives the per-integration
status/upgrade calls, derives the run outcome, and composes the pull request
body; `peter-evans/create-pull-request`, authenticated with a dedicated
repository-secret token (not the default `GITHUB_TOKEN`, which cannot
trigger further `pull_request`-scoped workflow runs), handles the actual
git-branch/PR mechanics so the opened PR still runs this repository's full
required CI suite before it can be reviewed and merged.

## Technical Context

**Language/Version**: Python 3.9+ for the helper script (unchanged
repository baseline); GitHub Actions YAML for the workflow definition itself

**Primary Dependencies**: `specify-cli` (external tool, installed and
pinned via `uv tool install specify-cli --from
"git+https://github.com/github/spec-kit.git@v1.0.0"` — research.md #2, not a
Python package dependency of `machine-calc` itself); the
`peter-evans/create-pull-request` GitHub Action (research.md #3); no new
entries in `pyproject.toml`'s `[project.optional-dependencies]`, since the
helper script needs only the standard library (`json`, `subprocess`) plus
whatever `specify` itself already provides as a CLI

**Storage**: N/A (the workflow reads/writes only repository files already
tracked by `.specify/integration.json` and the per-integration manifests)

**Testing**: `pytest`, for the helper script's pure-logic functions (outcome
derivation per data-model.md's "Sync Run" table, PR body composition per
contracts/sync-workflow-contract.md, and reading the installed-integrations
list) — the surrounding GitHub Actions workflow behavior itself is validated
manually via quickstart.md's scenarios, consistent with how CI workflow
changes are validated elsewhere in this repository (no existing precedent
for unit-testing workflow YAML directly)

**Target Platform**: GitHub Actions (`ubuntu-latest` runner), matching every
existing job in `.github/workflows/ci.yml`

**Project Type**: Addition to the existing single-project repository layout
— no new top-level project; the helper script lives in the existing
`scripts/` directory (research.md #5), not inside the `src/machine_calc`
package

**Performance Goals**: N/A in the Constitution Principle V / SC-style
per-calculation sense (this is CI tooling, not a `machine-calc` calculation
path); the only timing requirement is SC-001's weekly cadence, satisfied by
the cron schedule itself

**Constraints**: MUST NOT auto-merge the pull requests it opens (FR-006);
MUST NOT change the pinned `specify` CLI version as a side effect of a
routine run (FR-012); MUST use a token capable of triggering this
repository's `pull_request`-scoped required checks on the pull requests it
opens (research.md #4) — the default `GITHUB_TOKEN` cannot do this, which is
a hard platform constraint, not a design choice; MUST NOT open a second
sync pull request while one from this workflow is already open (FR-011)

**Scale/Scope**: Two installed integrations today (`copilot`, `claude`);
the helper script and workflow read the installed-integrations list rather
than hard-coding integration names, so a future third integration (e.g.
Cursor) requires zero workflow/script changes (FR-010)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | New helper script MUST be readable/single-responsibility; style tooling should ideally cover it | PASS — this repository's `lint`/`typecheck`/`security` CI jobs are scoped to `ruff check src/ tests/`, `mypy src/machine_calc`, and `bandit -r src -ll` only, which would otherwise leave the new `scripts/sync_agent_integrations.py` unchecked (the same gap the pre-existing `scripts/check_maintainability.py` already sits in). Resolved for this feature's own new code by tasks.md T002, which adds `scripts/sync_agent_integrations.py` to each of those commands by exact file path — deliberately not the whole `scripts/` directory, so `scripts/check_maintainability.py` remains a separate, out-of-scope cleanup rather than being pulled in as a side effect. |
| II. Testing Standards (NON-NEGOTIABLE) | Applies by letter to "calculation logic"; this script has no calculations, but its outcome-derivation/body-composition logic is still testable branching logic | PASS (planned) — unit tests for the helper script's pure functions per the Testing note in Technical Context above, as ordinary good practice and Development Workflow's general review checklist, even though Principle II's NON-NEGOTIABLE calculation-coverage requirement does not itself bind non-calculation CI tooling |
| III. Calculation Robustness & Accuracy | N/A — no floating-point/calculation logic is introduced | N/A |
| IV. Python Packaging & Versioning | N/A — no `machine_calc` public API change; FR-012's "pinned version" refers to the external `specify` CLI tool, not this package's own SemVer | N/A |
| V. Resource-Constrained Compatibility | N/A — runs on a GitHub Actions `ubuntu-latest` runner, not the legacy/low-power hardware profile this principle targets for the `machine-calc` application itself | N/A |
| VI. Extensibility by Design | New integrations MUST be picked up without rewriting the sync workflow | PASS — FR-010; the helper script reads `.specify/integration.json`'s installed-integrations list rather than hard-coding integration names (research.md #5) |
| VII. Documentation & Publishing | N/A for Sphinx/public API docs — this is repository CI tooling, not part of the `machine_calc` library's documented surface | N/A (optionally worth a short mention in `CONTRIBUTING`/README of the automated sync existing, but not required by any FR of this feature) |
| VIII. Internationalization of User-Facing Messages | N/A — the pull-request description this workflow writes is maintainer/reviewer-facing repository tooling output, not `machine-calc` REPL/CLI user-facing text sourced from the message catalog | N/A |
| IX. Automated Code Quality, Complexity & Security Gates | New/changed code MUST stay within configured thresholds where those gates apply | PASS — same remediation as Principle I above (tasks.md T002 adds the new script to `ruff`/`mypy`/`bandit`'s CI-invoked commands); no new dependency is introduced, so `pip-audit`/CodeQL scope is unaffected |
| X. Licensing & Author Rights | N/A — no licensing/metadata change | N/A |
| XI. Multi-Agent Coding-Tool Consistency | This feature IS this principle's anticipated "automated recurring job" (added 2026-08-21, v1.7.0) | PASS — directly implements the principle's SHOULD-level recommendation; keeps the actual regeneration mechanism (`specify integration upgrade`) exactly as the principle requires (no hand-duplicated per-agent files, generated files only touched via this mechanism) |

No violations requiring the Complexity Tracking table. The one gap
`/speckit-analyze` surfaced (Principle I/IX CI-scope coverage for the new
script) is resolved by tasks.md T002, not carried forward as an open note.

## Project Structure

### Documentation (this feature)

```text
specs/011-multi-agent-skill-sync/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   └── sync-workflow-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    └── ci.yml                          # MODIFY: add a new `sync-agent-integrations` job
                                         # (weekly cron + workflow_dispatch, research.md #1/#3/#4),
                                         # OR a new sibling workflow file if kept
                                         # independent of the pull_request-triggered CI suite —
                                         # left as a task-level decision, not a plan-level one,
                                         # since both satisfy every FR identically

scripts/
└── sync_agent_integrations.py          # ADD: reads .specify/integration.json's
                                         # installed_integrations, runs `specify integration
                                         # status --json` then `specify integration upgrade
                                         # <key>` per integration, derives the Sync Run outcome
                                         # (data-model.md), and writes the pull-request body
                                         # (contracts/sync-workflow-contract.md)

tests/
└── scripts/
    └── test_sync_agent_integrations.py # ADD: unit tests for the helper script's pure
                                         # outcome-derivation and PR-body-composition logic
                                         # (Technical Context "Testing"; not part of the
                                         # machine_calc coverage-gated source tree)

# NOT modified by this feature's own code/design (the one expected exception
# is .specify/feature.json, spec-kit's own per-checkout "current feature"
# pointer, updated by /speckit-specify as a matter of course - not part of
# this feature's design surface):
#   src/machine_calc/**                 # This feature touches no application/library code
#   .specify/**                         # Generated/managed by the `specify` CLI itself
#     (per Constitution Principle XI); this feature drives that CLI, it does not
#     hand-edit its output
```

**Structure Decision**: No new top-level project or package. This feature
adds one CI-only Python helper script under the existing `scripts/`
directory (following the `scripts/check_maintainability.py` precedent,
research.md #5) plus one new GitHub Actions job/workflow, and touches
nothing under `src/machine_calc` — consistent with this being repository
tooling rather than a `machine-calc` library/CLI feature.

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
