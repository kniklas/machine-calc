# Phase 1 Data Model: PR Quality Check Summary Comment

This feature has no application/domain data model (no database, no persisted Python
objects). The "entities" below are the shapes of data that flow through the CI workflow for
a single run, as introduced by spec.md's Key Entities section. They are documented here as
the workflow's implicit contract between jobs, not as code to be written.

## Quality Check Result

Represents the outcome of one of the eight existing CI jobs, as consumed by the
`quality-summary` job.

| Field | Type | Source | Notes |
|---|---|---|---|
| `name` | string (one of: `lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test`, `build`, `docs`) | Hard-coded in the `quality-summary` job's Markdown-assembly step, one row per job in `needs:` | Fixed set matching spec.md's Assumptions section; not dynamically discovered |
| `status` | enum: `success` \| `failure` \| `cancelled` \| `skipped` | `needs.<name>.result` (GitHub Actions built-in context) | Directly maps to spec.md's Quality Check Result "pass/fail/skipped/cancelled status" attribute (FR-007); no other status values are possible from this context |
| `metric` | optional string | `needs.test.outputs.coverage_pct` (for `test`) or `needs.complexity.outputs.mi_summary` (for `complexity`); absent/`—` for all other checks | Matches spec.md FR-005/User Story 3 Acceptance Scenario 3: checks without a headline metric MUST show a clear pass/fail indicator without a fabricated metric, rendered here as an explicit placeholder (e.g. `—`) rather than blank/omitted |

Validation / invariants (enforced by workflow logic, not a schema):
- `name` set is fixed and exhaustive — every job in `needs:` MUST appear as exactly one row;
  none may be silently omitted (FR-007).
- `status` MUST always be one of the four enum values above; there is no "unknown" state —
  if a job neither ran nor was explicitly skipped/cancelled, GitHub Actions itself would not
  have listed it as a dependency result at all, so this case cannot occur once `needs:` is
  correctly populated.
- `metric` MUST only be populated for `test` and `complexity`; every other check's `metric`
  is always the explicit placeholder, never a guessed or partial value (spec.md User Story 3
  Acceptance Scenario 3).

## PR Summary Comment

Represents the single consolidated comment the `quality-summary` job posts/updates on the
triggering pull request.

| Field | Type | Source | Notes |
|---|---|---|---|
| `pull_request` | implicit (the triggering PR) | `github.event.number` / `github.event.pull_request` context, used implicitly by `marocchino/sticky-pull-request-comment` when run on a `pull_request` event | No explicit PR-number plumbing needed; the action infers it from the event context |
| `overall_status` | enum: `PASS` \| `FAIL` \| `IN PROGRESS/CANCELLED` (derived) | Computed in the Markdown-assembly step from all eight `status` values: `FAIL` if any is `failure`; else a cancelled/incomplete indicator if any is `cancelled`; else `PASS` if all remaining are `success` (any `skipped` is reported per-row per FR-007 but does not by itself flip the overall status to `FAIL`, matching spec.md's Assumptions that `dependency-scan`/`build`/`docs` follow the same reporting rules as the named checks) | Satisfies FR-004's "MUST indicate an overall status for the run as a whole" |
| `results` | list of Quality Check Result (8 entries) | See above | Rendered as the Markdown table's rows |
| `marker` | string constant: `quality-check-summary` | Passed as the sticky-comment action's `header:` input | Satisfies FR-009's "identifiable... via a stable marker"; never shown verbatim to the reader (the action embeds it as an HTML comment) |

Validation / invariants:
- At most one `PR Summary Comment` exists per pull request at any time (FR-003): guaranteed
  by the sticky-comment action's default create-or-update-by-`header` behavior (research.md
  #1), not by any custom lookup code in this feature.
- The comment is only ever created/updated when `github.event_name == 'pull_request'`
  (FR-006); the `quality-summary` job's `if:` condition is the single enforcement point.
- A failure to create/update the comment (e.g. fork PR with a read-only token) MUST NOT
  change `overall_status` as reported to any other system, nor fail the job (FR-008) —
  enforced via `continue-on-error: true` on the posting step only (research.md #6).

## Relationships

```text
CI workflow run (pull_request event)
  ├── lint, complexity, typecheck, security, dependency-scan, test, build, docs jobs
  │     └── each produces exactly one Quality Check Result (status, optional metric)
  └── quality-summary job (needs: all of the above; if: always() && pull_request)
        ├── assembles all 8 Quality Check Results + overall_status → Markdown table (file)
        └── posts/updates exactly one PR Summary Comment (via header marker)
```

No state is persisted between separate workflow runs beyond the PR comment itself, which the
next run's `quality-summary` job locates again by the same `header` marker and overwrites in
place.
