# Quickstart: Wood Materials Support

**Feature**: [spec.md](./spec.md) | **Contract**: [contracts/wood-materials-registry-contract.md](./contracts/wood-materials-registry-contract.md)

This guide validates the feature end-to-end once implemented.

## Prerequisites

```bash
pip install -e ".[dev]"
```

## Scenario 1 — Built-in wood materials are available by default

```bash
python -c "from machine_calc import list_materials; print(list_materials())"
```

**Expected**:
- Output includes `Oak`, `Maple`, `Pine`, `Spruce`, `Fir`, `Plywood`, `MDF`
- Existing metal entries still remain

## Scenario 2 — Calculation works with each wood category

Run representative calculations (library or CLI) using:
- Hardwood (`Oak` or `Maple`)
- Soft wood (`Pine` or `Spruce`)
- Engineered wood (`Plywood` or `MDF`)

**Expected**:
- Each run returns numerically valid results
- No formula or unit-conversion regressions vs existing behavior

## Scenario 2b — SC-002 benchmark protocol (fixed reference set)

Use the versioned benchmark fixture:

- `tests/fixtures/materials/wood-benchmark-cases.toml`
- 14 cases total (2 per built-in wood material)
- Shared tolerance rule: ±10% relative tolerance per output metric

Run:

```bash
pytest tests/unit/operations/drilling/test_calculate.py -k wood_reference_results -q
```

**Expected**:
- Every benchmark case passes with `error is None`
- spindle speed, feed rate, torque, power, and machining time all remain within ±10%

## Scenario 3 — Packaging preserves wood data

```bash
python -m build
python -c "
import glob, zipfile
wheel = glob.glob('dist/*.whl')[0]
names = zipfile.ZipFile(wheel).namelist()
assert any(n.endswith('machine_calc/data/materials.toml') for n in names), names
print('materials.toml packaged: OK')
"
```

**Expected**:
- Packaged wheel contains bundled materials data with wood entries

## Scenario 4 — FR-008 warning-and-continue behavior

Create a user config with one invalid wood entry parameter and pass it via
`--materials-config`.

**Expected**:
- Warning is logged for the invalid/missing field
- Registry initialization continues
- Materials list still loads (including entry for override correction path)
- Selecting an invalid entry for calculation fails safely with clear error

## Scenario 5 — Override fixes invalid entry

Provide a corrected override for the previously invalid wood material.

**Expected**:
- Warning disappears for corrected material
- Calculation succeeds for the corrected entry

## Validation test commands

```bash
pytest tests/unit/shared/test_registry.py -q
pytest tests/integration/test_cli_materials_config.py -q
pytest tests/contract/test_materials_config_schema.py -q
pytest tests/integration/test_packaging_bundled_data.py -q
```

**Expected**: All pass with coverage thresholds intact.

## Parameter citation summary (SC-005)

Per-material source triangulation and median-of-sources derivation are documented in
`research.md` section **"Multi-source evidence and median normalization (FR-009, SC-005)"`.

Implemented canonical values:

- Hardwood: Oak, Maple
- Softwood: Pine, Spruce, Fir
- Engineered: Plywood, MDF
