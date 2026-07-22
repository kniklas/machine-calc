# machine-calc

[![CI](https://github.com/kniklas/machine-calc/actions/workflows/ci.yml/badge.svg)](https://github.com/kniklas/machine-calc/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kniklas/machine-calc/branch/main/graph/badge.svg)](https://codecov.io/gh/kniklas/machine-calc)

A Python library and interactive command-line tool for metal machining
calculations, starting with twist-drill drilling parameters (spindle speed,
feed rate, machining time, torque, and required power).

📖 **[Full generated documentation (Sphinx)](https://kniklas.github.io/machine-calc/)** —
published automatically to GitHub Pages on every merge to `main`.

> **Status**: Early implementation (drilling calculation engine + CLI MVP).
> Full end-user/developer documentation and CI/CD automation are tracked in
> [`specs/001-metal-drilling-calc/tasks.md`](specs/001-metal-drilling-calc/tasks.md)
> (Polish phase) and will replace this placeholder README.

## Install (development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Use as a library

```python
from machine_calc import calculate, UnitSystem, CalculationMode

result = calculate(
    diameter=10,
    depth=25,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
)
print(result)
```

### Constrained calculation modes

Two opt-in modes are available alongside the default `STANDARD` mode:

```python
# Power-constrained: reduce spindle speed to fit an available power budget.
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=1.2,  # kW (METRIC) or HP (IMPERIAL)
)

# Fixed-RPM: calculate from a caller-supplied target spindle speed.
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    mode=CalculationMode.FIXED_RPM,
    target_rpm=500,
)
```

See `specs/002-constrained-calculation-modes/quickstart.md` for full
scenarios, including error handling (`INFEASIBLE_POWER_BUDGET`,
`INVALID_TARGET_RPM`, `MODE_CONFLICT`).

## Use the interactive CLI

```bash
python -m machine_calc
```

The REPL prompts for a calculation mode (`standard`, `power-constrained`,
`fixed-rpm`) right after the unit-system prompt; `power-constrained` then
asks for a required available power, and `fixed-rpm` asks for a required
target spindle speed (with an optional advisory available power).

### Configurable materials & tools

The six built-in materials (Mild Steel, Stainless Steel, Aluminum, Cast Iron,
Brass, Titanium) and three built-in tools (HSS, Cobalt, Carbide) are bundled
with the package and used automatically with no configuration required.

To add your own materials/tools, or override a built-in tool's factors,
pass an optional user TOML file via `--materials-config`, either through the
`machine-calc` console script or `python -m machine_calc` (both parse the
same CLI flag):

```bash
machine-calc --materials-config my-machine-calc.toml
# or: python -m machine_calc --materials-config my-machine-calc.toml
```

```toml
# my-machine-calc.toml
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0    # m/min (or ft/min if unit_system = "imperial")
reference_feed_per_rev = 0.18     # mm/rev (or in/rev if imperial)
specific_cutting_force = 750.0    # N/mm^2 (or psi if imperial)

[[tools]]
name = "Carbide"                  # matches a built-in name -> overrides its factors
cutting_speed_factor = 3.0
feed_factor = 1.1
```

- Entries with a new `name` are **added** alongside the built-in defaults;
  entries whose `name` matches a built-in material/tool **override** it.
- `unit_system = "imperial"` (default: `"metric"`) declares that the entry's
  numeric fields are in imperial units; they are converted to metric
  automatically and produce identical results to an equivalent metric entry.
- An optional `[materials.translations]` (or `[tools.translations]`) table
  maps a locale code (e.g. `fr`) to a translated display name, shown when
  `MACHINE_CALC_LOCALE` is set accordingly; unset/unsupported locales and
  entries without a translation fall back to the English `name`.
- A missing/unreadable `--materials-config` file is a non-fatal notice — the
  CLI falls back to the bundled defaults. A malformed TOML file or a
  duplicate material/tool `name` within the file is a fatal, translated
  error and the CLI exits without starting the REPL.

See [`specs/005-configurable-materials-tools/quickstart.md`](specs/005-configurable-materials-tools/quickstart.md)
for full runnable scenarios, and
[`specs/005-configurable-materials-tools/contracts/materials-config-schema.md`](specs/005-configurable-materials-tools/contracts/materials-config-schema.md)
for the exact TOML schema.

## Run the tests

```bash
pytest
```

This project targets Python 3.9+ for compatibility with older/stable Linux
distributions (see `.specify/memory/constitution.md` Principle V), and aims
for ≥90% test coverage on calculation modules (Principle II).

See `specs/001-metal-drilling-calc/` for the full spec, plan, and task
breakdown driving this implementation.

## Quality & Security Gates (CI)

Every pull request runs the following required checks (`.github/workflows/ci.yml`),
per `.specify/memory/constitution.md` Principle IX:

| Check | Tool | Enforces |
|---|---|---|
| `lint` | `ruff` (incl. `C90`/mccabe) | Style, formatting, cyclomatic complexity (FR-001) |
| `complexity` | `scripts/check_maintainability.py` (`radon mi`) | Maintainability Index (FR-002) |
| `typecheck` | `mypy` | Static type errors (FR-003) |
| `security` | `bandit` | High/medium-severity security findings (FR-004) |
| `dependency-scan` | `pip-audit` | Known CVEs in resolved dependencies (FR-005); also runs weekly, independent of PRs |
| `test` | `pytest --cov` | Test failures / coverage below 90% |
| `build` | `python -m build` | Package build failures |
| `docs` | Sphinx | Docs build failures |
| CodeQL (`Analyze (python)`) | GitHub CodeQL default setup | New high-confidence security alerts (FR-006) |

`main` is protected by two GitHub rulesets (not classic branch protection): a
status-checks ruleset with **no bypass for anyone** (a failing required check blocks
every contributor, including the repository owner), and a separate PR-review ruleset
whose "require a pull request" rule has a bypass scoped only to the repository owner.
See `specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md` for the full
contract.

### Documented exceptions instead of silent suppressions

If a finding is a genuine false positive or an accepted, understood risk, suppress it
with the tool's own native mechanism **and a rationale comment**, so the exception is
visible in the code/PR diff rather than hidden in CI config:

- **Complexity** (`ruff`/C901): `# noqa: C901  <why this function's complexity is
  necessary/accepted>`
- **Security** (`bandit`): `# nosec B### <why this specific finding is a false positive
  or accepted risk>` — do not use a bare `# nosec` (it silently suppresses everything on
  that line), and avoid putting the literal word "nosec" in unrelated comment text
  elsewhere on the line, since bandit's suppression regex matches that substring
  anywhere in the trailing comment.
- **Type errors** (`mypy`): `# type: ignore[<error-code>]  <why this specific mypy rule
  doesn't apply here>` — never a bare `# type: ignore` (it hides all future errors on
  that line, not just the one you reviewed).
- **Dependency findings** (`pip-audit`): add a documented ignore entry (e.g. `pyproject.toml`
  `[tool.pip-audit]` `ignore-vulns`, with a comment linking the CVE and the acceptance
  rationale) rather than pinning to an insecure version silently.

**Complexity and security exceptions specifically also require the same rationale to be
restated in the pull request description itself** (Constitution Principle IX) — the
in-code comment alone is not sufficient for these two gates, since they are the ones
most likely to hide a real defect if suppressed casually. See
`.github/pull_request_template.md` for the required section, and reviewers: **reject any
PR that suppresses a complexity or security finding without both** the in-code rationale
comment **and** the PR-description restatement.
