# Quickstart: Metal Drilling Calculations Module

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving the feature works end-to-end, for both the
library API (User Story 2) and the interactive text interface (User Story
1). See [data-model.md](./data-model.md) for entity shapes and
[contracts/](./contracts/) for exact API/error contracts.

## Prerequisites

- Python 3.9+ installed (research.md #1).
- Package installed in a virtual environment: `pip install -e .` (editable
  install from repo root, once `pyproject.toml`/`src/` layout exists per
  Constitution Principle IV).
- Dev/test extras installed for validation: `pip install -e ".[dev]"`
  (provides `pytest`, `pytest-cov`).

## Scenario 1 — Library calculation (User Story 2)

```python
from machine_calc import calculate, UnitSystem

result = calculate(
    diameter=10,
    depth=25,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
)

assert result.error is None
assert result.spindle_speed_rpm is not None
assert result.torque is not None
assert result.power_required is not None
```

**Expected outcome**: `result` contains spindle speed, feed rate, machining
time, torque, and power, all in metric units, with `error is None`.

## Scenario 2 — Invalid input returns structured error, not an exception

```python
result = calculate(diameter=0, depth=25, material="Mild Steel", tool="Carbide")
assert result.error is not None
assert result.error.code == "INVALID_DIAMETER"
assert result.spindle_speed_rpm is None
```

**Expected outcome**: No exception raised; `error.code` is machine-readable
(FR-015).

## Scenario 3 — Unknown power rating still yields a power estimate

```python
result = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
assert result.error is None
assert result.power_required is not None
assert result.feasibility_warning is None
```

## Scenario 4 — Supplied power rating triggers feasibility warning when exceeded

```python
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    available_power=0.1,  # deliberately low, in kW
)
assert result.error is None
assert result.feasibility_warning is not None
```

## Scenario 5 — Interactive text interface (User Story 1)

Run the CLI and follow the prompt sequence in
[contracts/cli-repl.md](./contracts/cli-repl.md):

```bash
python -m machine_calc
```

**Expected outcome**: prompts for unit system, material, tool, diameter,
depth, and optional power rating; displays the same values as Scenario 1 for
identical inputs (FR-016); offers to loop for another calculation (FR-014).

## Scenario 6 — Unsupported material/tool combination is rejected

```python
result = calculate(diameter=10, depth=25, material="Unknown Material", tool="Carbide")
assert result.error is not None
assert result.error.code in ("MISSING_MATERIAL", "UNSUPPORTED_COMBINATION")
```

## Scenario 7 — Configuration file overrides validation bounds

```toml
# machine-calc.toml
max_diameter_mm = 150
max_depth_mm = 600
```

```python
result = calculate(
    diameter=120, depth=25, material="Mild Steel", tool="Carbide",
    config_path="machine-calc.toml",
)
assert result.error is None  # would fail default 100mm bound without override
```

## Running the automated test suite

```bash
pytest --cov=machine_calc --cov-report=term-missing
```

**Expected outcome**: all tests pass; coverage report shows the percentage
that will be published in `README.md` per Constitution Principle VII.

## Building documentation locally

```bash
sphinx-build -b html docs/source docs/build
```

**Expected outcome**: HTML docs build without errors, containing both
end-user and developer sections (Constitution Principle VII); this is the
same build step run and published by CI to GitHub Pages.
