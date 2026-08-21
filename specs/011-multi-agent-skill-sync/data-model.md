# Phase 1 Data Model: Periodic Multi-Agent Skill Sync Workflow

This feature has no persisted application data store; its "entities" are
structured concepts flowing through a single automated workflow run. They
are documented here as the shapes the Phase 1 contract and the
implementation's helper script (`scripts/sync_agent_integrations.py`,
research.md #5) exchange.

## Integration

One coding-agent integration installed in the repository, as recorded in
`.specify/integration.json`.

| Field | Type | Source | Notes |
|---|---|---|---|
| `key` | string | `.specify/integration.json` → `installed_integrations[]` | e.g. `"copilot"`, `"claude"`; drives FR-010 (new integrations auto-included) |
| `manifest_path` | string | `.specify/integrations/<key>.manifest.json` | per-integration tracked-file list + hashes |
| `status` | one of: `clean`, `modified-blocked`, `upgraded-no-change`, `upgraded-with-changes`, `failed` | derived per run (see Sync Run Outcome below) | drives which part of the PR body / failure report this integration appears in |
| `changed_files` | string[] | `git status --porcelain` scoped to this integration's manifest paths, taken after its `specify integration upgrade <key>` call | empty unless `status == upgraded-with-changes` |
| `blocked_file` | string \| null | `specify integration status --json` → `manifests.<key>.modified_files[0]` | populated only when `status == modified-blocked` (FR-008) |

## Sync Run

A single execution of the workflow (scheduled or manually dispatched).

| Field | Type | Notes |
|---|---|---|
| `trigger` | one of: `schedule`, `workflow_dispatch` | FR-005 |
| `integrations` | `Integration[]` | one entry per installed integration (see above) |
| `outcome` | one of: `no-drift` (FR-004), `pull-request-opened-or-updated` (FR-003/FR-011), `failed` (FR-007/FR-013) | overall run result |
| `specify_cli_version` | string | pinned ref used for this run (research.md #2); recorded for traceability, never changed by the run itself (FR-012) |

**Outcome derivation** (in priority order):
0. Before any `Integration` is even checked: run `check_specify_cli_up_to_date()`
   (research.md #7). If its result is `update-available` (a newer tooling
   release exists) or `inconclusive` (the check itself couldn't reach a
   conclusive answer — network/rate-limit/unexpected failure) → run
   `outcome = failed` immediately, with a message distinguishing the two
   cases (FR-013). Only `up-to-date` lets derivation continue to step 1. No
   integration is checked in either failing case — since `specify
   integration upgrade` regenerates from templates bundled in the
   (possibly-stale) pinned tooling version, checking them would only ever
   produce a false `no-drift` result, and an inconclusive check must not be
   silently treated as equivalent to a confirmed-current one (spec.md
   SC-001).
1. If any `Integration.status == failed` (tooling/network error, not a
   modified-file block) → run `outcome = failed`. No pull request is opened
   or updated (edge case: partial success must not open a *silent* partial
   PR over a genuine tooling failure).
2. Else if any `Integration.status == upgraded-with-changes` → run `outcome
   = pull-request-opened-or-updated`, even when another integration in the
   same run is `modified-blocked`: a blocked integration is a safe,
   expected, disclosed condition (research.md #1), not a silent omission —
   it is named transparently in that same pull request's body instead of
   sinking the whole run (FR-008; contracts/sync-workflow-contract.md "Sync
   Pull Request body contract").
3. Else if any `Integration.status == modified-blocked` (and none
   `upgraded-with-changes`) → run `outcome = failed`, and the failure report
   names the blocked integration(s) and file(s) (FR-008). There is nothing
   to actually put in a pull request in this case, so a visible failed run
   is used instead of an empty, pointless one.
4. Else (`clean` or `upgraded-no-change` for every integration) → run
   `outcome = no-drift`.

## Sync Pull Request

The pull request opened or updated by a run whose `outcome ==
pull-request-opened-or-updated`.

| Field | Type | Notes |
|---|---|---|
| `branch` | string | fixed, stable name (research.md #3), e.g. `chore/sync-agent-integrations` |
| `changed_integrations` | string[] | keys of every `Integration` with `status == upgraded-with-changes`; the PR description enumerates these (FR-003, SC-002) |
| `blocked_integrations` | `{key: string, file: string}[]` | any `modified-blocked` integrations from the same run, surfaced in the description even though they didn't themselves change anything (FR-008); only non-empty when the run's `outcome` is still `pull-request-opened-or-updated` because at least one *other* integration had real changes — if every integration is blocked, the run's `outcome` is `failed` per the derivation above, and no PR is touched |
| `is_update_to_existing` | boolean | true when a prior sync PR was already open on `branch` and this run added a new commit to it rather than opening a new one (FR-011) |
