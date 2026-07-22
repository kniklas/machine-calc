# Quickstart: Configurable Materials & Tools

**Feature**: [spec.md](./spec.md) | **Schema**: [contracts/materials-config-schema.md](./contracts/materials-config-schema.md)

This is a runnable validation guide, not a design document — it proves the
feature works end-to-end for each user story in `spec.md`. It assumes
`machine-calc` is installed (editable or built) in the current environment.

## Prerequisites

```bash
pip install -e ".[dev]"
```

## Scenario 1 — Built-in materials/tools work with zero configuration (User Story 1)

```bash
# No --materials-config supplied at all.
machine-calc
```

**Expected**: The material and tool prompts list exactly the same six
materials (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium)
and three tools (HSS, Cobalt, Carbide) as before this feature; a calculation
using, e.g., Mild Steel + HSS, diameter 10 mm, depth 30 mm produces the same
numeric results as the pre-feature release.

Automated equivalent:

```bash
pytest tests/unit/shared/test_registry.py tests/unit/operations/drilling -q
```

## Scenario 2 — Package build includes the bundled defaults (User Story 1, Acceptance Scenario 3)

```bash
python -m build
python -c "
import zipfile, glob
wheel = glob.glob('dist/*.whl')[0]
names = zipfile.ZipFile(wheel).namelist()
assert any(n.endswith('data/materials.toml') for n in names), names
assert any(n.endswith('data/tools.toml') for n in names), names
print('bundled defaults present in wheel: OK')
"
```

**Expected**: Both assertions pass — the bundled TOML files are present
inside the built wheel, not only in the source checkout.

## Scenario 3 — Add a new material and override a built-in tool (User Story 2)

Create `my-machine-calc.toml`:

```toml
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0

[[tools]]
name = "Carbide"
cutting_speed_factor = 3.0
feed_factor = 1.1
```

Run:

```bash
machine-calc --materials-config my-machine-calc.toml
```

**Expected**: "Bronze" appears in the material prompt's options alongside the
six built-in materials; selecting it and running a calculation succeeds.
Selecting "Carbide" now applies `cutting_speed_factor = 3.0` (overridden from
the built-in `2.5`) instead of the bundled value. All other built-in
materials/tools (e.g., Mild Steel, HSS) are unaffected. Running again with no
`--materials-config` reproduces Scenario 1 exactly (the override is strictly
additive/optional, FR-005).

## Scenario 4 — Translated material/tool names with English fallback (User Story 3)

Extend `my-machine-calc.toml` with translations:

```toml
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0

[materials.translations]
fr = "Bronze"
de = "Bronze"

[[materials]]
name = "Mild Steel"
reference_cutting_speed = 25.0
reference_feed_per_rev = 0.20
specific_cutting_force = 1900.0

[materials.translations]
fr = "Acier doux"
```

Run in French, then in an unsupported locale:

```bash
MACHINE_CALC_LOCALE=fr machine-calc --materials-config my-machine-calc.toml
# Material prompt shows "Acier doux" for the Mild Steel entry.

MACHINE_CALC_LOCALE=xx machine-calc --materials-config my-machine-calc.toml
# Material prompt falls back to "Mild Steel" (English) — MACHINE_CALC_LOCALE=xx has no
# bundled message catalog, but the name.translations lookup still degrades to English
# independently (spec.md Edge Cases).
```

**Expected**: French run shows the translated name; unsupported-locale run
shows the English name; no blank or broken name is ever shown (SC-003).

## Scenario 5 — Imperial-declared reference values convert correctly (User Story 4)

Add an imperial-declared entry to `my-machine-calc.toml`:

```toml
[[materials]]
name = "Bronze Imperial"
reference_cutting_speed = 250.0   # ft/min
reference_feed_per_rev = 0.008    # in/rev
specific_cutting_force = 130000.0 # psi
unit_system = "imperial"
```

Run a calculation with this material in both metric and imperial output
modes and compare against a metric-authored entry with the equivalent
converted values (e.g., `76.2 m/min`, `0.2032 mm/rev`, `896.3 N/mm²`).

**Expected**: Results for "Bronze Imperial" match (within tolerance,
`math.isclose`) the results for the metric-authored equivalent, in both
`metric` and `imperial` CLI unit-system modes (FR-012, SC-004).

## Scenario 6 — Invalid/malformed configuration is rejected clearly (Edge Cases, SC-005)

```bash
printf '[[materials]\nname = "Broken"\n' > bad.toml   # malformed TOML (missing closing bracket)
machine-calc --materials-config bad.toml
```

**Expected**: A single clear, translated error message identifying that
`bad.toml` could not be parsed; the CLI exits without a raw Python
traceback and without starting the REPL loop (FR-007).

```bash
cat > dup.toml <<'EOF'
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0

[[materials]]
name = "Bronze"
reference_cutting_speed = 50.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
EOF
machine-calc --materials-config dup.toml
```

**Expected**: A clear, translated error identifying the duplicate "Bronze"
entry within `dup.toml`; the CLI exits without applying either entry
(FR-016).

## Scenario 7 — Missing configuration path degrades gracefully (Edge Cases, FR-005)

```bash
machine-calc --materials-config does-not-exist.toml
```

**Expected**: A translated, non-fatal notice that the file was not found;
the REPL still starts and behaves exactly as Scenario 1 (bundled defaults
only).

## Automated coverage

```bash
pytest --cov=machine_calc --cov-report=term-missing
```

**Expected**: Full suite passes; coverage on calculation-adjacent modules
(`registry.py`, `operations/drilling/tools.py`, the new
`registry_config.py`) remains ≥ 90% (Constitution Principle II).
