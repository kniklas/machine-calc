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
version as a side effect of a routine sync run) — an upstream *template*
change is picked up by re-running `integration upgrade`, without needing a
newer `specify` CLI release at all, since the CLI and the templates it
fetches evolve on separate cadences.

**Alternatives considered**:
- `pip install specify-cli`: rejected, package does not exist on PyPI.
- Floating/unpinned install (`@main` or no ref): rejected, directly
  contradicts FR-012 and would make sync-run behavior non-reproducible
  between runs.

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
