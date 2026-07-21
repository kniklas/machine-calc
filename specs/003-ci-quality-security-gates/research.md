# Phase 0 Research: Automated CI Quality & Security Gates

**Input**: [spec.md](./spec.md), Constitution Principle IX (v1.4.0)

## 1. Cyclomatic complexity threshold & tool

**Decision**: Use `ruff`'s built-in `C90` (mccabe) rule as the primary, fast, already-integrated
complexity gate, with `max-complexity = 10` (industry-standard default; matches mccabe's own
"moderate risk" cutoff). Do not add a separate `radon cc` CI step for the same metric — it
would be redundant with `ruff C90` since both use the same underlying McCabe algorithm.

**Rationale**: `ruff` is already a required dev dependency and CI-integrated linter in this
repo (`pyproject.toml`); adding `C90` to `select` costs nothing extra to run and reports
inline with existing lint output, satisfying FR-001/FR-010 (thresholds versioned in
`pyproject.toml`) with minimal new tooling surface.

**Alternatives considered**: `radon cc` as a standalone step — rejected as redundant with
`ruff C90` for the same metric, adding a second tool/config surface for no additional signal.
`xenon --max-absolute` for cyclomatic complexity — rejected as the sole CC gate because it
reports per-block grades (A-F) rather than a numeric threshold per function, which is less
precise for FR-001's "identify the offending function" requirement; `xenon` is retained
instead for Maintainability Index (see #2).

## 2. Maintainability Index threshold & tool

**Decision**: Use `radon mi` computed and enforced via `xenon --max-absolute B --max-modules A
--max-average A src/`. Grade B (`xenon`'s default recommended floor) is the minimum per-module
grade; module-average and single-worst-case are held to grade A per xenon's stricter
aggregate defaults, which is achievable at the current repo size (~1500 LOC across small,
single-responsibility modules per Constitution Principle I/VI).

**Rationale**: `radon`/`xenon` is the de facto standard, actively maintained pure-Python MI
tool; `xenon` wraps `radon mi` specifically to provide CI-friendly pass/fail exit codes,
satisfying FR-002.

**Alternatives considered**: `wily` (trend-tracking complexity tool) — rejected as it targets
historical trend visualization rather than a simple per-PR pass/fail gate, adding scope beyond
what FR-002 requires.

## 3. Static type-checking tool & scope

**Decision**: `mypy`, run against `src/machine_calc` only (not `tests/`), in a permissive but
non-empty initial configuration (`disallow_untyped_defs = false` initially, `warn_return_any =
true`, `ignore_missing_imports = true` for the optional `tomli` dependency), so it fails on
concrete type errors without requiring an immediate full-strict-mode rewrite of existing code.

**Rationale**: Constitution Principle I requires mypy pass in CI but does not mandate strict
mode; starting permissive avoids a large, unrelated refactor of `001`/`002` code merely to
satisfy this feature (per spec.md FR-011 / Edge Cases: pre-existing code must not be
retroactively blocked). Strictness can be incrementally raised in a future amendment/task.

**Alternatives considered**: `pyright` — comparable capability, but `mypy` is the long-standing
default for `pyproject.toml`-configured Python projects and requires no additional Node.js
runtime in CI, keeping the toolchain simpler.

## 4. Static security analysis tool & severity policy

**Decision**: `bandit -r src -ll` (reports medium and high severity only, per FR-004's
"high- or medium-severity" wording), configured via `[tool.bandit]` in `pyproject.toml` for any
line-level suppressions (`# nosec` with a mandatory trailing justification comment, per
FR-009).

**Rationale**: `bandit` is the standard Python AST-based SAST tool, lightweight, and needs no
external service; `-ll` (medium+) avoids drowning the gate in low-severity/style findings not
required to block merge by FR-004.

**Alternatives considered**: `semgrep` — more powerful/configurable but requires broader rule
curation and an external rule registry; unnecessary for this project's current scope and
adds operational overhead disproportionate to a small single-package library.

## 5. Dependency vulnerability scanning tool & cadence

**Decision**: `pip-audit` run (a) on every pull request against the resolved `dev` + runtime
dependency set, and (b) on a weekly scheduled GitHub Actions run against `main`, per FR-005.

**Rationale**: `pip-audit` is the PyPA-maintained standard tool, queries the Python Packaging
Advisory Database directly, and needs no account/API key, keeping setup friction near zero.

**Alternatives considered**: `safety` — requires a paid API key for full vulnerability DB
access as of recent versions; `pip-audit` remains free and equally authoritative for this
project's scale.

## 6. Continuous SAST (repository-level)

**Decision**: Enable GitHub CodeQL via the "default setup" option (Settings → Code security →
Code scanning), targeting Python, running on push to `main` and on pull requests, per FR-006.

**Rationale**: Default setup requires no workflow YAML to maintain, auto-updates its query
packs, and is free for public repositories — matching this repo's status and minimizing
maintenance burden relative to an "advanced setup" custom CodeQL workflow.

**Alternatives considered**: Advanced setup (custom `codeql.yml`) — offers more control (e.g.,
custom query packs) but adds a workflow file to maintain for no current added benefit; can be
adopted later if custom queries become necessary.

## 7. Branch-protection bypass scoping (resolves FR-008 / analysis finding C1)

**Decision**: Migrate `main`'s protection from classic branch protection to a GitHub
**repository ruleset**, with required status checks for all Principle IX gates (plus existing
lint/test/build/docs checks) and a bypass list scoped to the repository owner for the
**pull request approval rule only**. Rulesets support per-rule, per-actor bypass, unlike
classic branch protection's single repo-wide `enforce_admins` toggle.

**Rationale**: Confirmed via research that GitHub repository rulesets (the successor to
classic branch protection) are available for public repositories on the Free plan, and
support scoping bypass to specific actors and specific rules (not all-or-nothing), directly
satisfying FR-008 and closing analysis finding C1 (the current all-or-nothing
`enforce_admins: false` state).

**Alternatives considered**: Keep classic branch protection and accept the all-or-nothing
bypass risk — rejected, as it directly contradicts Principle IX's explicit bypass-scoping
requirement. Re-enabling `enforce_admins: true` on classic protection — rejected, as it would
re-block the repository owner from merging their own reviewed PRs entirely (the original
problem this repo already hit with PR #3), not just scope the bypass correctly.

## 8. Rollout strategy for pre-existing code (resolves spec.md FR-011 / Edge Cases)

**Decision**: Run all five new checks (complexity, MI, mypy, bandit, pip-audit) once against
the current `main` `src/`/`tests/` tree before marking any of them as a required status check;
catalogue any findings in this feature's `tasks.md`/PR description and either fix them or add
a documented, tool-native suppression, in a "gate rollout" task that runs before the "make
required check" task for each gate.

**Rationale**: Satisfies FR-011 directly: gates activate clean, so they never retroactively
block unrelated future pull requests for undocumented pre-existing debt.

**Alternatives considered**: Enable all gates as required immediately and let pre-existing
findings block the next unrelated PR until fixed — rejected as inconsistent with FR-011 and
likely to cause exactly the kind of "silent grandfathering" or workflow friction the spec's
Edge Cases section calls out.
