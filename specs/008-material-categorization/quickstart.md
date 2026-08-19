# Quickstart & Validation Guide: Material Categorization System

**Feature**: [spec.md](./spec.md) | **Contract**: [contracts/material-selection.md](./contracts/material-selection.md)

This guide validates the delivered two-step "material type → material"
selection flow. Every command below was actually run against this repo
checkout; outputs are copied verbatim (spindle-speed/torque figures depend
on the diameter/depth/tool you enter).

## Setup

```bash
# From the repository root, with the package installed (editable or not):
python -m machine_calc --help
```

```
usage: machine-calc [-h] [--materials-config PATH]

optional arguments:
  -h, --help            show this help message and exit
  --materials-config PATH
                        Optional path to a TOML file adding/overriding
                        materials and drilling tools (see contracts/materials-
                        config-schema.md).
```

The CLI is invoked as `python -m machine_calc` or the installed
`machine-calc` console script. No separate registry initialization step is
needed — the bundled catalog (`src/machine_calc/data/materials.toml`) is
always available; `--materials-config PATH` adds to or overrides it.

## Scenario 1: Two-step selection with the bundled catalog

Prompt order is: unit system → calculation mode → **material type** →
**material** → drilling tool → diameter → depth → available power.

```bash
printf 'metric\nstandard\nMetal\nAluminum\nHSS\n10\n25\n\nn\n' | python -m machine_calc
```

```
Unit system [metric/imperial] (metric): Calculation mode (standard, power-constrained, fixed-rpm) (standard): Material type (Metal, Wood): Material (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium): Drilling tool (HSS, Cobalt, Carbide): Drill diameter (mm): Hole depth (mm): Available power (kW, blank if unknown): 
Spindle speed:     1909.9 RPM   (recommended)
Feed rate:         477.5 mm/min
Machining time:    0.06 min
Torque:            4.4 N·m
Power required:    0.87 kW

Run another calculation? [y/N]: 
```

Confirms: the `Material type (Metal, Wood):` prompt appears exactly once,
before `Material`; the material list is scoped to whatever type is chosen
(here, the 6 metal materials — `Mild Steel, Stainless Steel, Aluminum, Cast
Iron, Brass, Titanium`).

## Scenario 2: Switching category between calculations drops the stale default

```bash
printf 'metric\nstandard\nMetal\nAluminum\nHSS\n10\n25\n\ny\nmetric\nstandard\nWood\n' \
  | python -m machine_calc
```

The second iteration's material prompt is:

```
Material type (Metal, Wood) (Metal): Material (Oak, Maple, Pine, Spruce, Fir, Plywood, MDF): 
```

Confirms: after switching type to `Wood`, the material list becomes the 7
wood materials and **no default is offered** — `Aluminum` (remembered from
the Metal selection) is not a Wood material, so
`_prompt_material_choice`'s default lookup finds nothing to show.

## Scenario 3: Adding a new category via `--materials-config`, with no catalog label

`machine_calc.locales.en` only has display labels for `metal`/`wood`/
`uncategorized`. A brand-new `material_type` value still gets a readable
(title-cased) label with zero code changes.

```bash
cat > my.toml << 'EOF'
[[materials]]
name = "PVC"
material_type = "plastic"
reference_cutting_speed = 200.0
reference_feed_per_rev = 0.30
specific_cutting_force = 80.0
EOF

printf 'metric\n\nPlastic\nPVC\nCarbide\n10\n25\n\nn\n' \
  | python -m machine_calc --materials-config my.toml
```

```
Unit system [metric/imperial] (metric): Calculation mode (standard, power-constrained, fixed-rpm) (standard): Material type (Metal, Wood, Plastic): Material (PVC): Drilling tool (HSS, Cobalt, Carbide): Drill diameter (mm): Hole depth (mm): Available power (kW, blank if unknown): 
Spindle speed:     15915.5 RPM   (recommended)
Feed rate:         5252.1 mm/min
Machining time:    0.01 min
Torque:            0.7 N·m
Power required:    1.10 kW

Run another calculation? [y/N]: 
```

Confirms: `Material type (Metal, Wood, Plastic):` — `Plastic` is the
title-cased fallback for `material_type = "plastic"` (no
`material_type.plastic` catalog entry exists); `Material (PVC):` shows only
the newly-added material, scoped to its type.

## Scenario 4: Backward compatibility — pre-008 override files keep their category

A `--materials-config` file written before `material_type` existed (e.g. one
that only overrides `Mild Steel`'s cutting parameters) must not silently
move that material to `"uncategorized"`.

```bash
cat > legacy.toml << 'EOF'
[[materials]]
name = "Mild Steel"
reference_cutting_speed = 30.0
reference_feed_per_rev = 0.22
specific_cutting_force = 1850.0
EOF

python -c "
from machine_calc.registry import get_material
m = get_material('Mild Steel', config_path='legacy.toml')
print(m.material_type, m.reference_cutting_speed_m_min)
"
```

```
metal 30.0
```

Confirms the sticky-field merge rule: the overridden cutting speed (30.0)
took effect, while `material_type` stayed `"metal"` (carried over from the
bundled entry) rather than falling back to `"uncategorized"`.

## Scenario 5: Library API (no CLI)

```python
from machine_calc.registry import list_material_types, list_materials

list_material_types()
# ['metal', 'wood']

list_materials(material_type="wood")
# ['Oak', 'Maple', 'Pine', 'Spruce', 'Fir', 'Plywood', 'MDF']

list_materials(material_type="cement")
# []   -- unknown category: empty list, not an error

list_materials()
# ['Mild Steel', 'Stainless Steel', 'Aluminum', 'Cast Iron', 'Brass',
#  'Titanium', 'Oak', 'Maple', 'Pine', 'Spruce', 'Fir', 'Plywood', 'MDF']
#  -- omitting material_type reproduces the exact pre-008 return value
```

## Cleanup

```bash
rm -f my.toml legacy.toml
```

## Out of scope

There is no admin CRUD flow to validate (add/update/delete a material type
at runtime) — User Story 3 was dropped. The only way to add a material or a
category is authoring a `[[materials]]` entry in a TOML file, as shown in
Scenario 3.

## Test Coverage Reference

Automated equivalents of these scenarios live in:

- `tests/unit/shared/test_registry_material_types.py` (35 tests)
- `tests/integration/test_cli_material_types.py` (21 tests)

Run them with:

```bash
pytest tests/unit/shared/test_registry_material_types.py tests/integration/test_cli_material_types.py
```
