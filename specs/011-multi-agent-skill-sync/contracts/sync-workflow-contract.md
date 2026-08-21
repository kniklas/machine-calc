# Contract: Periodic Multi-Agent Skill Sync Workflow

This feature's only external interface is the GitHub Actions workflow
itself (there is no library/CLI/API surface): what triggers it, what it is
guaranteed to do (and not do) on each trigger, and the shape of the pull
request it produces. Downstream consumers are the repository's maintainer
and reviewers, and the repository's own required-review branch policy.

## Triggers

| Trigger | Behavior |
|---|---|
| `schedule` (weekly cron, `0 6 * * 1` — research/spec Assumptions) | Runs the full sync check (FR-001–FR-005) |
| `workflow_dispatch` | Runs the identical sync check on demand (FR-005, User Story 3); no input parameters required |

No other trigger (`push`, `pull_request`, etc.) starts this workflow — it is
independent of ordinary code-change activity, mirroring the existing
`dependency-scan` job's `schedule`/`workflow_dispatch`-only trigger pattern
in `.github/workflows/ci.yml`.

## Guarantees per run (see data-model.md "Sync Run" for the outcome derivation)

- **`no-drift`**: zero repository changes, zero pull requests opened or
  updated, workflow run reports success (FR-004, SC-003).
- **`pull-request-opened-or-updated`**: exactly one pull request, on the
  fixed branch (research.md #3), either newly opened or updated with a new
  commit if one was already open (FR-003, FR-011); workflow run reports
  success.
- **`failed`**: the workflow run itself fails (non-zero exit / red status
  check) — visible in the Actions tab and (for `schedule` runs) via GitHub's
  built-in failure-notification email (research.md #6); no pull request is
  opened or updated for this run (FR-007). A genuine tooling/network error
  always produces this outcome, regardless of any other integration's
  result. An integration blocked by a locally-modified file (FR-008)
  produces this same outcome only when *no other* integration in the run
  had real changes to PR (data-model.md "Sync Run" outcome derivation); when
  at least one other integration did, the run is
  `pull-request-opened-or-updated` instead, and the blocked integration is
  named in that pull request's body rather than sinking the run.

## Sync Pull Request body contract

The pull request description a `pull-request-opened-or-updated` run
produces or updates MUST contain, in this order:

1. A line naming each changed integration (`changed_integrations`,
   data-model.md), so a reviewer can identify scope from the description
   alone without opening the diff (FR-003, SC-002).
2. If any integration in the same run was blocked by a locally-modified file
   (`blocked_integrations`, data-model.md) — which is possible only when at
   least one other integration still had real changes, since an all-blocked
   run is itself a `failed` run (see Guarantees above) — a clearly labeled
   line naming that integration and the specific file, so a reviewer
   understands why that integration's regenerated files were **not** part of
   this pull request (FR-008).
3. No other structural requirement; free-form additional detail (e.g. the
   `specify` CLI version used) is permitted but not contractually required
   by this feature.

## Non-goals (explicitly out of contract scope)

- Auto-merging the pull request (FR-006) — always requires the repository's
  normal required review.
- Upgrading the pinned `specify` CLI/tooling version (FR-012) — a separate,
  manual maintainer action.
- Any interface for consuming sync results other than the pull request
  itself and the workflow run's own pass/fail status (no additional API,
  file, or notification channel is part of this contract — research.md #6).
