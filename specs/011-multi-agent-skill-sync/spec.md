# Feature Specification: Periodic Multi-Agent Skill Sync Workflow

**Feature Branch**: `011-multi-agent-skill-sync`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "periodic multi-agent skill sync workflow as a follow-up to recent constitution changes"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Drift Detection and Sync Pull Request (Priority: P1)

As the repository maintainer, I want a recurring automated check that regenerates
each installed coding-agent integration's instruction/skill files (Copilot's
`.github/agents/`+`.github/prompts/`, Claude Code's `.claude/skills/`, and any
future integration) from Spec Kit's upstream template source, and opens a pull
request only when those files have actually drifted from what upstream now
produces — so I don't have to remember to manually run `specify integration
upgrade` for every installed agent (Constitution Principle XI).

**Why this priority**: This is the entire point of the feature — without it,
keeping agents in sync remains a manual, easily-forgotten chore, which is
exactly the drift Principle XI and issue #46 were written to prevent.

**Independent Test**: Trigger the workflow (on its schedule or manually) against
a repository state where upstream templates have changed since the last sync;
verify a pull request is opened bundling the regenerated files. Trigger it again
immediately after merging that pull request (no further upstream drift) and
verify the second run makes no repository changes and opens no pull request.

**Acceptance Scenarios**:

1. **Given** an installed integration's upstream template has changed since the
   last sync, **When** the workflow runs, **Then** it opens a pull request
   containing the regenerated files for that integration.
2. **Given** no installed integration's upstream template has changed since the
   last sync, **When** the workflow runs, **Then** it makes no repository
   changes and opens no pull request.
3. **Given** multiple installed integrations have each drifted independently,
   **When** the workflow runs, **Then** a single pull request is opened
   containing the regenerated files for all of them, not one pull request per
   integration.

---

### User Story 2 - Reviewable, Non-Auto-Merged Sync Pull Requests (Priority: P2)

As a reviewer, I want a sync-generated pull request to clearly state which
coding-agent integration(s) changed and go through the same required review
process as any other change, so I can review what upstream regenerated before
it reaches `main`, rather than an automated process silently rewriting agent
instructions.

**Why this priority**: Directly supports User Story 1 by making the automation
trustworthy — an automated PR that nobody reviews, or that misidentifies what
changed, defeats the purpose of surfacing drift in the first place.

**Independent Test**: Open a sync-generated pull request and confirm its
description lists each changed integration by name; confirm the pull request
is subject to the repository's normal required-review branch protection (it
cannot merge on its own).

**Acceptance Scenarios**:

1. **Given** a sync run has opened a pull request, **When** a reviewer opens
   it, **Then** the description lists which integration(s) changed without
   the reviewer needing to inspect the diff first.
2. **Given** a sync pull request is open, **When** no reviewer has approved
   it, **Then** it cannot be merged, identically to any other pull request
   against `main`.
3. **Given** a sync pull request reports that a locally-modified generated
   file was preserved instead of overwritten (diff-aware handling), **When**
   a reviewer opens the pull request, **Then** the description calls out
   that preserved-file case explicitly, since a generated file diverging
   from upstream is itself a signal worth reviewing (Constitution Principle
   XI: generated files must not be hand-edited).

---

### User Story 3 - On-Demand Sync Outside the Schedule (Priority: P3)

As the maintainer, I want to trigger a sync check on demand, so I can confirm
agent instructions are current right after installing a new integration or
right before a release, without waiting for the next scheduled run.

**Why this priority**: A convenience/control capability on top of the
core automated behavior in User Story 1; valuable but not required for the
feature to deliver its primary benefit.

**Independent Test**: Manually trigger the workflow outside its schedule and
confirm it performs the same drift check and pull-request behavior as a
scheduled run.

**Acceptance Scenarios**:

1. **Given** the maintainer manually triggers the workflow, **When** it runs,
   **Then** it performs the identical drift-check and pull-request behavior
   as a scheduled run.

---

### Edge Cases

- What happens when the sync check succeeds for one installed integration but
  fails for another in the same run? The run MUST be treated as failed overall
  and MUST NOT open a partial pull request containing only the successful
  integration's changes — a silently-omitted failing integration would hide a
  real regression.
- What happens when a previous sync pull request is still open and unmerged
  when the next scheduled run finds further drift? The workflow MUST NOT open a
  second, duplicate sync pull request while one is already open; it updates the
  existing open sync pull request instead.
- What happens when the upstream template source is unreachable, or has changed
  in a way the currently-pinned `specify` tooling cannot process? The run MUST
  fail visibly (a failed workflow run the maintainer can see), never silently
  skip the affected integration or apply a partial/broken result.
- What happens when a new coding-agent integration (e.g., a future Cursor
  integration) is installed after this workflow already exists? The next run
  MUST pick it up automatically from the repository's installed-integrations
  record, without requiring any change to the workflow's own configuration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide an automated, recurring workflow that
  regenerates every currently-installed coding-agent integration's
  instruction/skill files from Spec Kit's upstream template source (the same
  mechanism as manually running `specify integration upgrade` for each
  installed integration).
- **FR-002**: The workflow MUST detect whether any installed integration's
  regenerated files differ from what is currently committed in the
  repository.
- **FR-003**: When one or more integrations' files have changed, the workflow
  MUST open a single pull request containing all changed files, with a
  description that lists which integration(s) changed.
- **FR-004**: When no installed integration's files have changed, the
  workflow MUST complete without opening a pull request or otherwise
  modifying the repository.
- **FR-005**: The workflow MUST run on a recurring schedule and MUST also be
  triggerable on demand, without waiting for the next scheduled run (User
  Story 3).
- **FR-006**: The workflow MUST NOT auto-merge the pull requests it opens;
  they MUST go through the repository's existing required pull-request
  review process identically to any other change (Constitution Principle IX;
  Development Workflow).
- **FR-007**: If regenerating any installed integration's files fails (e.g.,
  the upstream source is unreachable, or a tooling error occurs), the
  workflow MUST fail visibly rather than silently skip that integration or
  open a pull request with a partial result.
- **FR-008**: If the regeneration step reports that a locally-modified
  generated file was preserved rather than overwritten (diff-aware update
  handling), the pull request description MUST surface that fact so the
  maintainer can review why a generated file diverged from its
  expected regenerate-only status (Constitution Principle XI).
- **FR-009**: The workflow's own configuration (schedule, trigger conditions)
  MUST live in version-controlled workflow configuration, not in an
  undocumented external scheduler.
- **FR-010**: Adding a new coding-agent integration to the repository MUST be
  picked up automatically by this workflow's next run — from the
  repository's existing installed-integrations record — without requiring a
  change to the workflow's own configuration (Constitution Principle XI).
- **FR-011**: The workflow MUST NOT open a second, duplicate sync pull
  request while a previous sync pull request it opened is still open; further
  drift detected in that state MUST update the existing open pull request.
- **FR-012**: The workflow MUST NOT modify the pinned version of the
  underlying Spec Kit tooling used to perform the sync; upgrading that
  tooling's own version remains a separate, explicit maintainer action
  outside this workflow's scope.

### Key Entities

- **Sync Run**: A single execution of the periodic (or manually-triggered)
  workflow. Produces either "no drift found" (no repository change) or
  exactly one pull request (opened or updated).
- **Integration**: One coding-agent integration installed in the repository
  (e.g., Copilot, Claude Code), whose generated instruction/skill files are
  regenerated and checked for drift by a sync run.
- **Sync Pull Request**: The pull request a sync run opens (or updates) when
  drift is detected; bundles all changed integrations' regenerated files with
  a description enumerating each one and any preserved-local-file cases.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An installed coding-agent integration's instruction files are
  never more than one week out of date relative to Spec Kit's upstream
  template source without an open pull request notifying the maintainer of
  the drift.
- **SC-002**: 100% of sync pull requests identify, in their description alone
  (without the reviewer opening the diff), which coding-agent integration(s)
  changed.
- **SC-003**: A sync run that finds no drift results in zero repository
  changes and zero pull requests — no review noise from a no-op run.
- **SC-004**: A maintainer can obtain an out-of-cycle sync result (pull
  request opened, updated, or "no changes") without waiting for the next
  scheduled run.
- **SC-005**: Adding a new coding-agent integration requires zero changes to
  the sync workflow's own configuration for that integration to be included
  in the next run.

## Assumptions

- A single combined pull request per sync run (covering every drifted
  integration) is used rather than one pull request per integration, since
  all installed integrations are regenerated from the same upstream
  mechanism in the same run and are already governed together under
  Constitution Principle XI.
- Weekly is used as the recurring schedule cadence, matching the existing
  `dependency-scan` workflow's established weekly cron convention (`0 6 * * 1`)
  already used in this repository (`.github/workflows/ci.yml`) for other
  non-per-PR recurring maintenance checks.
- Sync pull requests always require the repository's existing required
  review-approval before merge, consistent with Constitution Principle IX,
  which limits any administrator bypass to the review-approval gate alone and
  never to other automated gates — this workflow introduces no exception to
  that.
- Upgrading the pinned Spec Kit CLI/tooling version itself is out of scope for
  this workflow (FR-012); it remains a separate, explicit, manually-triggered
  maintenance action, so that this workflow's own behavior cannot silently
  change as a side effect of an unrelated tooling upgrade.
- This feature only adds a new recurring workflow and its supporting
  automation; it does not change the manual `specify integration
  install`/`specify integration upgrade` commands themselves, nor the
  Constitution Principle XI rules those commands are already required to
  satisfy.
