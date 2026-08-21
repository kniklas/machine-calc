# Quickstart: Periodic Multi-Agent Skill Sync Workflow

Validation scenarios for the sync workflow described in
[spec.md](./spec.md), [data-model.md](./data-model.md), and
[contracts/sync-workflow-contract.md](./contracts/sync-workflow-contract.md).

## Prerequisites

- `specify` CLI installed locally at the version pinned for this repository
  (research.md #2): `uv tool install specify-cli --from
  "git+https://github.com/github/spec-kit.git@v1.0.0"`.
- A clean working tree on a throwaway branch (these scenarios modify
  generated files).
- `gh` CLI authenticated, for the pull-request scenarios.

## Scenario 1 — No drift: run produces no changes (FR-004, SC-003)

1. On a branch already up to date with `main`, run the same steps the
   workflow runs locally: `specify integration status --json`, then
   `specify integration upgrade <key> --script py` for each key in
   `.specify/integration.json`'s `installed_integrations`.
2. **Expected**: `git status --porcelain` is empty after every integration's
   upgrade. No commit, no pull request.

## Scenario 2 — Upstream drift: run produces a single pull request (FR-001–FR-003, SC-001, SC-002)

1. Simulate upstream drift by editing one line of a generated file under
   `.claude/skills/speckit-converge/SKILL.md` (or any tracked file) to
   differ from what `specify integration status --json` recorded, then
   revert the manifest hash check by re-running the integration's install
   step, OR — more directly — pin to an older `specify` CLI version, run the
   sync steps, then re-pin to the current version and re-run: the second run
   should regenerate the newer content.
2. Run the sync steps from Scenario 1.
3. **Expected**: `git status --porcelain` shows changed files for the
   drifted integration. The composed pull-request description names that
   integration per the body contract (contracts/sync-workflow-contract.md
   §"Sync Pull Request body contract" item 1).

## Scenario 3 — Locally-modified file blocks that integration (FR-007, FR-008)

1. Hand-edit any file tracked by an integration's manifest (e.g. append a
   comment to `.claude/skills/speckit-plan/SKILL.md`).
2. Run `specify integration status --json`.
3. **Expected**: the JSON output's `manifests.<key>.modified_files` lists the
   edited file, and `findings` includes a `managed-files-modified` entry for
   that integration.
4. Run `specify integration upgrade <key> --script py` (no `--force`) for
   that same integration.
5. **Expected**: the command blocks/fails rather than silently overwriting
   or silently skipping the file; per the Sync Run outcome derivation
   (data-model.md), this run's overall outcome is `failed`, and the failure
   message names the specific integration and file (FR-008) — distinct from
   a generic tooling-error failure.

## Scenario 4 — Duplicate-PR avoidance (FR-011)

1. After Scenario 2 opens a pull request on the fixed sync branch (research.md
   #3), do **not** merge or close it.
2. Introduce further drift (repeat Scenario 2's simulation for a different
   file) and re-run the sync steps.
3. **Expected**: the same pull request is updated with a new commit; no
   second pull request is opened. (`gh pr list --head
   chore/sync-agent-integrations` shows exactly one open pull request before
   and after.)

## Scenario 5 — New integration is picked up automatically (FR-010)

1. Add a hypothetical new integration key to `.specify/integration.json`'s
   `installed_integrations` list (e.g. install a real new integration via
   `specify integration install <name>`, or, for a dry validation, confirm
   the sync script reads this list rather than a hard-coded set — inspect
   `scripts/sync_agent_integrations.py` for any hard-coded integration name
   and confirm there is none).
2. **Expected**: the next sync run includes the new integration without any
   change to the workflow YAML or the helper script.

## Scenario 6 — Manual trigger matches scheduled behavior (FR-005, User Story 3)

1. `gh workflow run ci.yml` (the `sync-agent-integrations` job lives inside
   the existing `.github/workflows/ci.yml`, not a separate workflow file —
   plan.md Project Structure)
2. **Expected**: the triggered run performs the identical drift-check and
   pull-request behavior described in Scenarios 1–4 above; there is no
   behavioral difference from a `schedule`-triggered run other than the
   trigger type recorded on the run (data-model.md "Sync Run" →
   `trigger`).

## Scenario 7 — Sync pull requests still require review (FR-006)

1. Locate an open (or newly opened, per Scenario 2) sync pull request.
2. **Expected**: it cannot be merged without the repository's normal
   required review-approval, identically to any other pull request against
   `main` — no auto-merge behavior is present anywhere in the workflow
   definition.
