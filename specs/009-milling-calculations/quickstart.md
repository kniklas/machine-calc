# Quickstart: Milling Calculations Module

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving the feature works end-to-end, for the library
API (User Story 4) and the interactive REPL (User Stories 1, 2, 3). See
[data-model.md](./data-model.md) for entity shapes and
[contracts/](./contracts/) for exact API/error contracts.

## Prerequisites

- Existing `machine-calc` development environment (`pip install -e ".[dev]"`
  from repo root), same as `001-metal-drilling-calc`.
- No new runtime dependencies are introduced by this feature.

## Scenario 1 — Operation selection in the REPL (User Story 1)

```bash
machine-calc
```

**Expected outcome**: the very first prompt asks the user to choose a
machining operation (drilling or milling), before any material/tool
prompts appear. Selecting "drilling" reproduces the existing drilling
flow unchanged. Selecting "milling" then prompts for a milling
sub-operation (end milling or face milling) before any further prompts.

## Scenario 2 — End milling library calculation (User Story 2, 4)

```python
from machine_calc import calculate_end_milling, UnitSystem

result = calculate_end_milling(
    diameter=10,
    axial_depth_of_cut=5,
    radial_depth_of_cut=2,
    feed_per_tooth=0.05,
    number_of_teeth=4,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
)

assert result.error is None
assert result.spindle_speed_rpm is not None
assert result.material_removal_rate is not None
assert result.torque is not None
assert result.power_required is not None
```

**Expected outcome**: `result` contains spindle speed, feed rate, material
removal rate, machining time, torque, and power, all in metric units, with
`error is None`.

## Scenario 3 — Face milling library calculation (User Story 3, 4)

```python
from machine_calc import calculate_face_milling, UnitSystem

result = calculate_face_milling(
    diameter=63,
    axial_depth_of_cut=2,
    width_of_cut=40,
    feed_per_tooth=0.12,
    number_of_teeth=6,
    length_of_cut=150,
    material="Mild Steel",
    tool="Coated Carbide",
    unit_system=UnitSystem.METRIC,
)

assert result.error is None
assert result.material_removal_rate is not None
```

**Expected outcome**: analogous structured result using face-milling
formulas (data-model.md).

## Scenario 4 — Engagement-exceeds-diameter rejection (FR-009)

```python
result = calculate_end_milling(
    diameter=10,
    axial_depth_of_cut=5,
    radial_depth_of_cut=12,  # > diameter
    feed_per_tooth=0.05,
    number_of_teeth=4,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)

assert result.error is not None
assert result.error.code == "INVALID_ENGAGEMENT"
assert result.spindle_speed_rpm is None
```

**Expected outcome**: a clear, structured error; no calculation is
performed (all numeric fields `None`).

## Scenario 5 — Identical results: library vs. REPL (FR-012)

1. Run Scenario 2's library call directly and record the result.
2. Run the REPL (`machine-calc`), select milling -> end milling, and enter
   the same diameter/depth-of-cut/feed-per-tooth/teeth/length-of-cut/
   material/tool values.

**Expected outcome**: the REPL's displayed spindle speed, feed rate,
material removal rate, machining time, torque, and power match the library
call's result exactly, since the REPL performs no calculation of its own
(contracts/cli-repl-milling.md).

## Scenario 6 — Drilling regression check (SC-005)

```bash
pytest tests/unit/operations/drilling tests/contract/test_cli_contract.py tests/integration/test_cli_flow.py
```

**Expected outcome**: the full existing drilling test suite passes
unchanged, confirming the new operation-selection step did not alter
drilling's behavior (FR-002).

## Validation commands

```bash
pytest                       # full suite, includes new milling tests
ruff check src tests         # linting (Constitution I)
mypy src                     # static typing (Constitution I)
```
