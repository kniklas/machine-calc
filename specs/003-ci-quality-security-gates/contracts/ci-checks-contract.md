# Contract: Required CI Status Checks on `main`

This is the interface the CI workflows expose to GitHub branch/ruleset protection and to
contributors reading pull request check results. It is the "public API" of this feature, in
the same sense `contracts/library-api.md` is for `001-metal-drilling-calc`.

## Required status checks

Every check below MUST report a distinct, named GitHub Actions job status (not bundled into
a single opaque "CI" check), so FR-001-FR-006 and SC-004 ("identify exactly which metric or
finding failed") are satisfiable from the PR's checks list alone.

| Check name (job) | Enforces | Trigger | Blocks merge when |
|---|---|---|---|
| `lint` | Existing ruff + black formatting/style, now including FR-001 (`ruff C90` cyclomatic complexity) | push, pull_request | Any lint/format violation or function exceeding the configured complexity threshold |
| `complexity` | FR-002 (`radon mi` via `scripts/check_maintainability.py`, Maintainability Index) — FR-001 (`ruff C90`, cyclomatic complexity) is enforced by the `lint` job below, not duplicated here; note `xenon` was found during implementation to only enforce cyclomatic complexity, not MI, and was dropped (research.md #2) | push, pull_request | Any module exceeds the configured Maintainability Index threshold (research.md #2) |
| `typecheck` | FR-003 (`mypy`) | push, pull_request | Any new/changed type error in `src/machine_calc` |
| `security` | FR-004 (`bandit`) | push, pull_request | Any open high/medium-severity finding without a Suppression Record |
| `dependency-scan` | FR-005 (`pip-audit`) | push, pull_request, schedule (weekly) | Any known CVE in resolved dependencies without a documented risk acceptance |
| `test` | Existing pytest + coverage (unchanged, ≥90%) | push, pull_request | Any test failure or coverage below threshold |
| `build` | Existing package build check (unchanged) | push, pull_request | Build failure |
| `docs` | Existing Sphinx docs build (unchanged) | push, pull_request | Docs build failure |
| CodeQL default setup | FR-006 | push to `main`, pull_request (GitHub-managed, not a custom job) | New high-confidence alert (per GitHub's own gating, not a custom workflow step) |

**Note**: `lint`, `test`, `build`, `docs` already exist as planned (unimplemented) tasks from
`001-metal-drilling-calc` tasks.md (T037); this feature's plan/tasks extend that same
workflow file rather than duplicating it, adding the `complexity`, `typecheck`,
`security`, and `dependency-scan` jobs alongside them.

## Ruleset bypass contract (resolves FR-008)

- The `main` ruleset's "Require a pull request before merging" rule MAY have a bypass entry
  for the repository owner (actor-scoped).
- No other rule in the ruleset (i.e., none of the required status checks above) MAY have a
  bypass entry for any actor. A failing `complexity`, `typecheck`, `security`,
  `dependency-scan`, `lint`, `test`, `build`, or `docs` check blocks merge for every actor,
  including the repository owner.

## Suppression contract (resolves FR-009)

A finding MAY be suppressed only via a tool-native, in-repo mechanism visible in the diff:

- `bandit`: inline `# nosec` comment with a trailing rationale comment on the same or
  preceding line, or a named test-ID skip in `[tool.bandit]` in `pyproject.toml` with a
  comment above it explaining why.
- `ruff` (`C90`)/`mypy`: `# noqa: C901` / `# type: ignore[<code>]` inline, each with a
  trailing rationale comment.
- `pip-audit`: a documented entry in `pyproject.toml` (or an equivalent ignore file) naming
  the CVE ID and the risk-acceptance rationale, per Suppression Record (data-model.md).

A CI-only suppression (e.g., disabling a check in the workflow YAML, or an ignore rule not
visible in the affected file/config) does not satisfy this contract and MUST be rejected in
review (spec.md User Story 3, Acceptance Scenario 2).
