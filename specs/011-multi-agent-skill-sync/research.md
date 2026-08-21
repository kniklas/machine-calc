# Phase 0 Research: Periodic Multi-Agent Skill Sync Workflow

## 1. How to drift-check installed integrations without hand-rolling detection logic

**Decision**: Use `specify integration status --json` as the read-only,
pre-flight local-integrity check (are any generated files hand-modified since
last install?), and treat "the file tree changed after running `specify
integration upgrade <name>`" (via `git status --porcelain` after each
per-integration upgrade) as the actual signal of upstream drift.

**Rationale**: These are two different, complementary checks, verified
directly against the installed `specify` CLI (v1.0.0, the version this
repository is pinned to per `.specify/integration.json`):

- `specify integration status --json` compares each tracked file's on-disk
  hash against the hash recorded in its integration manifest
  (`.specify/integrations/<name>.manifest.json`) — it detects **local
  hand-edits**, not upstream freshness. Running it against this repository's
  current state returns real findings today (e.g. a `modified_files` entry
  for `.specify/templates/tasks-template.md` under the `speckit` manifest),
  confirming the command works as a genuine pre-flight safety check.
- `specify integration upgrade <name>` regenerates that integration's files
  from whatever template version the installed `specify` CLI currently
  points to. There is no separate "check for upstream updates" command —
  running the upgrade and diffing the working tree afterward **is** the
  drift check.
- Critically, `specify integration upgrade` **blocks entirely** for a given
  integration's regeneration (rather than silently overwriting) when
  `status`'s local-integrity check finds a modified file, unless `--force`
  is passed (confirmed via `specify integration upgrade --help`: "Compares
  manifest hashes to detect locally modified files and blocks the upgrade
  unless --force is used"). This refines spec.md FR-008: the workflow does
  not get a "preserved one file, regenerated the rest" partial result — a
  locally-modified file blocks that integration's *entire* upgrade, which is
  itself a distinct, nameable failure mode the sync run must surface (not a
  generic tooling error, and not silently retried with `--force`, since
  forcing would silently discard the hand-edit Principle XI says should not
  exist in the first place).

**Alternatives considered**:
- Diffing against the upstream git repository directly (e.g. cloning
  `github/spec-kit` and comparing template files by hand). Rejected: this
  reimplements what `specify integration upgrade` already does internally,
  and would drift from whatever resolution logic (presets, extension
  layers) a future `specify` version adds.
- Relying solely on `specify integration status --json`'s output as the
  drift signal. Rejected: it cannot detect "upstream template changed" at
  all — only "the local file no longer matches what was last installed."

## 2. Installing and pinning the `specify` CLI in CI

**Decision**: Install via `uv tool install specify-cli --from
"git+https://github.com/github/spec-kit.git@v1.0.0"` (or the version string
currently recorded in `.specify/integration.json`'s top-level `version`
field), matching this repository's own local dev installation exactly
(verified via `~/.local/share/uv/tools/specify-cli/uv-receipt.toml`).

**Rationale**: `specify-cli` is not published to PyPI (`pip index versions
specify-cli` returns no match); its only installable source is spec-kit's
GitHub repository. Pinning the same `@vX.Y.Z` git ref this repository is
already tracking keeps the workflow reproducible and satisfies spec.md
FR-012 (the sync workflow must not silently change the pinned tooling
version as a side effect of a routine sync run).

**Alternatives considered**:
- `pip install specify-cli`: rejected, package does not exist on PyPI.
- Floating/unpinned install (`@main` or no ref): rejected, directly
  contradicts FR-012 and would make sync-run behavior non-reproducible
  between runs.

**Addendum (post-PR #50 Copilot review — corrects an earlier factual
error)**: this decision's original rationale claimed "an upstream template
change is picked up by re-running `integration upgrade`... since the CLI
and the templates it fetches evolve on separate cadences." That is **false**
and has been removed above. Verified directly against the installed
package: `specify_cli/_assets.py`'s `_locate_core_pack()` docstring states
the `core_pack` (containing `templates/`) is bundled into the wheel *at
build time* — "core_pack is a sibling directory of this file" — not fetched
from a live source at `integration upgrade` time. `specify integration
upgrade` therefore always regenerates from whatever templates shipped with
the *currently installed CLI version*; with that version pinned (as this
decision requires per FR-012), re-running it can only ever surface drift
**once** — the one-time migration from whatever previously generated the
committed files to the pinned version's own output — never ongoing drift
from a newer spec-kit release. Confirmed empirically too: `specify self
check` against this repository's actual pinned v1.0.0 reported a real
available update (`v1.0.0 → v1.0.1`) that `integration upgrade` alone would
never have surfaced. This is what spec.md FR-013 and
`check_specify_cli_up_to_date()` (using `specify self check`, which *is* a
genuine live check against GitHub's Releases API — see that function's
docstring) exist to close: the sync run now fails visibly, naming the newer
release, instead of silently and indefinitely reporting "no drift" once the
one-time migration is done.

## 3. Avoiding duplicate open sync pull requests (FR-011)

**Decision**: Push the regenerated files to a single, stable branch name
(e.g. `chore/sync-agent-integrations`) on every run, and open/update the
pull request for that branch via the `peter-evans/create-pull-request`
GitHub Action.

**Rationale**: `peter-evans/create-pull-request` is a widely-used, actively
maintained action whose core behavior already implements exactly what
FR-011 requires: given a fixed branch name, it commits only if there is a
diff, and if a pull request from that branch is already open it updates that
same pull request instead of opening a second one — no custom
"search-for-an-existing-open-PR" logic needs to be written or tested by this
project.

**Alternatives considered**:
- Hand-rolled `gh pr list --head <branch>` check before `gh pr create`.
  Rejected: reimplements a well-tested action's exact purpose, adding
  surface area with no benefit.
- A fresh, timestamped branch per run (e.g. `sync/2026-08-21-...`). Rejected:
  directly produces the duplicate-open-PR problem FR-011 forbids.

**Addendum (third Copilot review round on PR #50)**: the fixed branch alone
doesn't fully prevent a *race* between two runs pushing it concurrently
(`create-pull-request@v6` pushes with `--force-with-lease`, so an
overlapping scheduled + manually-dispatched run could fail with a stale
lease). Closed by adding a `concurrency: {group:
sync-agent-integrations, cancel-in-progress: false}` block to the job in
`.github/workflows/ci.yml`, so a second run queues behind the first rather
than racing it — a native GitHub Actions mechanism, not custom logic.

## 4. Authenticating the workflow so its pull requests actually run required CI checks

**Decision**: Use a dedicated repository secret holding a fine-grained
personal access token (or GitHub App installation token) — not the default
`secrets.GITHUB_TOKEN` — as the `token:` input to
`peter-evans/create-pull-request`.

**Rationale**: This is a well-documented GitHub Actions platform limitation
(not a project-specific choice): pull requests opened using the default
`GITHUB_TOKEN` do not trigger other `on: pull_request`-triggered workflow
runs, to prevent unbounded recursive workflow chains. This repository's
entire quality-gate suite (`lint`, `typecheck`, `security`,
`dependency-scan`, `test`, `build`, `docs`, `performance`,
`quality-summary`) is defined with `on: pull_request` in
`.github/workflows/ci.yml`. If the sync PR were opened with the default
token, none of those checks would run on it, so a reviewer approving it
would be approving an un-vetted change — silently violating spec.md FR-006
("go through the repository's existing required pull-request review process
... identically to any other change") and Constitution Principle IX (CI
gates as required status checks). A dedicated PAT/bot token sidesteps this
platform restriction, exactly as `peter-evans/create-pull-request`'s own
documentation recommends for this scenario.

**Alternatives considered**:
- Default `GITHUB_TOKEN` with elevated `permissions: contents: write,
  pull-requests: write` at the job level. Rejected: elevated permissions do
  not change the no-further-workflow-triggering restriction; the sync PR
  would still open with zero CI checks attached.
- A `workflow_run`-triggered follow-up job to run checks separately after
  the sync PR opens. Rejected: needlessly reinvents the existing
  `pull_request`-triggered CI suite as a second, parallel-maintained
  mechanism for one workflow's PRs only.

## 5. Implementation surface: where the sync logic lives

**Decision**: A single Python helper script under the existing top-level
`scripts/` directory (alongside the established `scripts/check_maintainability.py`
precedent), invoked from a new GitHub Actions workflow (or a new job in the
existing `.github/workflows/ci.yml`, per the Phase 1 design). The script
iterates `.specify/integration.json`'s `installed_integrations` list, runs
`specify integration status --json` then `specify integration upgrade
<name>` per integration, and composes the pull-request body summarizing
which integrations changed (FR-003) and which were blocked by a
locally-modified file (FR-008).

**Rationale**: `scripts/` is already the established location in this
repository for CI-support Python code that is not part of the installable
`machine_calc` package — `scripts/check_maintainability.py` is excluded from
`[tool.setuptools.packages.find]`, `[tool.coverage.run]`'s `source`, and
`[tool.mypy]`'s `files`, and is not covered by the `lint`/`typecheck`
jobs' `src/ tests/`-scoped commands in `.github/workflows/ci.yml`. Following
this exact precedent means Constitution Principle IX's calculation-code
quality gates (radon/xenon, bandit, mypy scoped to `src/machine_calc`) are
correctly not stretched to cover CI tooling scripts, consistent with how the
repository already treats `scripts/check_maintainability.py`. Reading the
integration list from `.specify/integration.json` (rather than hard-coding
`["copilot", "claude"]` in the script or workflow) is what satisfies FR-010
(a newly installed integration is picked up automatically).

**Alternatives considered**:
- Inline shell (`run:` steps only, no Python helper). Rejected: composing a
  structured, per-integration PR body and parsing `specify integration
  status --json` is materially easier and more testable in Python than in
  workflow-embedded shell/`jq`.
- Placing the script under `.specify/scripts/` (alongside Spec Kit's own
  managed scripts). Rejected: that directory is itself a
  `specify`-integration-managed, generated location (tracked by the
  `speckit` manifest) — putting project-authored logic there would violate
  the same generated-vs-hand-authored separation Constitution Principle XI
  establishes for agent instruction files.

**Addendum (post-`/speckit-analyze`)**: living in `scripts/` does not, by
itself, exempt this feature's script from Constitution Principle IX's CI
gates — that would just inherit `scripts/check_maintainability.py`'s
pre-existing, undesirable gap. tasks.md T002 closes that gap for this
feature's own new file by adding it to the CI `lint`/`typecheck`/`security`
commands explicitly (by file path, not by widening scope to all of
`scripts/`), so this decision is about *where the code lives*, not about
*whether it's quality-gated*.

## 6. Failure notification

**Decision**: Rely on GitHub Actions' built-in behavior of emailing the
actor who last edited a scheduled workflow's cron schedule when a scheduled
run fails; no custom notification (issue creation, chat webhook, etc.) is
built by this feature.

**Rationale**: Already documented as an Assumption in spec.md; confirmed
here as the research decision — this is standard, zero-additional-code
GitHub Actions platform behavior, and building custom notification logic
for a solo-maintainer repository's low-frequency (weekly) maintenance
workflow is unjustified additional surface area (Constitution Principle VI:
avoid unneeded complexity).

**Alternatives considered**:
- A dedicated GitHub Issue opened/updated on failure. Rejected as
  out-of-scope for this feature's MVP; could be added later without
  changing this feature's other decisions if the maintainer finds the email
  notification insufficient.

## 7. Detecting a stale pinned tooling version (FR-013, added post-PR #50 review)

**Decision**: Run `specify self check` (a read-only command that queries
GitHub's Releases API — `GITHUB_API_LATEST =
"https://api.github.com/repos/github/spec-kit/releases/latest"` in the
installed package's `_version.py`) at the start of every sync run, before
touching any integration, and classify its result into exactly three
states (`check_specify_cli_up_to_date()`'s `CliCheckResult`): if its output
matches `Update available: X → Y`, the run fails immediately with `Y`
named in the error; if the command exits non-zero, or reports `Could not
check latest release: ...`/`Could not validate latest release tag...` (the
CLI's own documented graceful-failure text on exit 0), the run *also* fails
— with a distinct "could not verify" message — rather than silently
proceeding; only an explicit `Up to date: X` lets the run proceed to the
normal per-integration drift check. No integration is checked in either
failing case.

**Rationale**: This decision #2's original rationale for CLI pinning turned
out to rest on a false premise (decision #2's addendum) — templates are
bundled inside the pinned CLI, so re-running `integration upgrade` with an
unchanged pin can never detect a newer spec-kit release. `specify self
check` is the one command in this CLI that actually performs a live check
against upstream (everything else this script calls -
`integration status`/`integration upgrade` - operates entirely on local
state and the bundled package). Failing the run (rather than silently
proceeding to a false "no drift") is what makes spec.md SC-001's "never
more than a week out of date without the maintainer being notified"
promise actually true, without requiring the workflow to violate FR-012 by
bumping its own pin.

**Alternatives considered** (the three options presented to and decided by
the maintainer):
- **Auto-bump and regenerate**: have the workflow itself update the pinned
  version (in `.github/workflows/ci.yml` and `.specify/integration.json`)
  and regenerate files from the new release, bundling the version bump into
  the sync pull request. Rejected: requires rewriting FR-012 from "never
  changes the pin" to "the pin's own change must be a reviewable part of
  the PR," and lets an unattended weekly job unilaterally pull in a new,
  unreviewed external tool release before a human has chosen to.
- **Leave the gap undocumented/unaddressed**: keep the original design,
  where drift detection only ever fires once (right after a human
  separately bumps the pin some other way). Rejected: leaves spec.md
  SC-001's core promise silently unmet indefinitely, with nothing to
  prompt the maintainer to notice or act.

**Addendum (second Copilot review round on PR #50)**: this decision's first
version treated a network/inconclusive `specify self check` result as
"proceed normally, assume up to date" rather than failing the run. That
was itself a second instance of the exact SC-001 gap this decision exists
to close — an unreachable Releases API would then produce a silent,
unnotified false "no drift" result, no different in effect from the
original bundled-templates problem. Corrected as reflected in the Decision
above: any non-`Up to date` result — confirmed-stale *or* inconclusive —
now fails the run, distinguished only by message text.

## 8. Third Copilot review round on PR #50: remaining robustness gaps

Three further gaps, verified directly against the installed `specify-cli`'s
source before fixing (not just the review's own description of them):

- **`check_specify_cli_up_to_date()`'s classification logic was itself a
  blocklist of two known failure strings**, falling through to "up to
  date" for anything else — missing a third exit-0 graceful-failure
  message (`Current version could not be determined.`, from
  `_version.py`'s `self_check`, when local version metadata is
  unavailable). Fixed by inverting to an allowlist: only the literal
  `Up to date:` success marker (confirmed in source:
  `console.print(f"[green]Up to date:[/green] {installed}")`) counts as
  confirmed-current; everything else — including any future CLI message
  not anticipated here — defaults to `CLI_CHECK_INCONCLUSIVE`.
- **A missing per-integration manifest was silently treated as "zero
  tracked files"**, indistinguishable from a manifest that genuinely
  tracks nothing. Verified in source
  (`specify_cli/integrations/_migrate_commands.py`,
  `integration_upgrade`): when the manifest file doesn't exist,
  `specify integration upgrade <key>` prints `No manifest found for
  integration '<key>'. Nothing to upgrade.` and exits **0** without
  creating one — an installed-but-never-materialized integration (`key`
  listed in `.specify/integration.json` without ever running `specify
  integration install <key>`). `_manifest_tracked_paths()` now returns
  `None` (not `[]`) for a missing manifest, and `run_integration_upgrade()`
  fails the integration if it is *still* missing after the upgrade call.
- **Regenerating any integration also reconciles shared Spec Kit
  infrastructure tracked by a separate `speckit` manifest, not just the
  files listed in that integration's own manifest.** Verified in source:
  `integration_upgrade` calls `_install_shared_infra_or_exit(...)`
  unconditionally (every call, not only for the "default" integration as
  initially assumed from the review comment's wording) — but its default
  (non-`--force`) overwrite policy is "only add missing files; existing
  ones are skipped" (`_install_shared_infra`'s own docstring), so a
  locally-modified shared file is never actually at risk of being
  clobbered by a routine sync run. `check_shared_infra_modified()` (reusing
  `run_integration_status()` against the `speckit` key, since `specify
  integration status --json` already reports it alongside every installed
  integration) surfaces this as an informational PR-body note per FR-008's
  "surface that fact" duty — not a blocking condition, since nothing is
  actually at risk of being overwritten.
