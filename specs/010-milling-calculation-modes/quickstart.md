# Quickstart: Milling Calculation Modes

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving power-constrained and fixed-RPM modes work
end-to-end for both milling sub-operations, on top of the existing
`009-milling-calculations` prerequisites (Python 3.9+ installed,
`pip install -e ".[dev]"`). See [data-model.md](./data-model.md) for the
new/extended entity shapes and [contracts/](./contracts/) for the exact
API/error contract deltas.

## Scenario 1 — Power-constrained mode reduces end-milling spindle speed to fit a budget (User Story 1)

```python
from machine_calc import calculate_end_milling, UnitSystem, CalculationMode

geometry = dict(
    diameter=10, axial_depth_of_cut=2, radial_depth_of_cut=5,
    feed_per_tooth=0.05, number_of_teeth=4, length_of_cut=100,
    material="Mild Steel", tool="Carbide", unit_system=UnitSystem.METRIC,
)

standard = calculate_end_milling(**geometry)
assert standard.error is None
nominal_power = standard.power_required

result = calculate_end_milling(
    **geometry,
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=nominal_power * 0.5,
)

assert result.error is None
assert result.mode is CalculationMode.POWER_CONSTRAINED
assert result.spindle_speed_rpm < standard.spindle_speed_rpm
assert abs(result.power_required - nominal_power * 0.5) < 1e-6
# Material removal rate is recomputed consistently with the reduced feed rate.
assert result.material_removal_rate < standard.material_removal_rate
```

**Expected outcome**: `result.spindle_speed_rpm` is reduced proportionally
(research.md #1) so `result.power_required` matches the supplied budget
within floating-point tolerance; feed rate, machining time, and material
removal rate are recomputed consistently; torque is unchanged (FR-002).

## Scenario 2 — Power-constrained mode is a no-op when the budget is already sufficient (FR-003)

```python
result = calculate_end_milling(
    **geometry,
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=nominal_power * 2,
)

assert result.error is None
assert result.spindle_speed_rpm == standard.spindle_speed_rpm
assert result.mode is CalculationMode.POWER_CONSTRAINED
```

**Expected outcome**: the result is numerically identical to the standard
calculation except `mode`, including the exact-equality boundary case
(`available_power == nominal_power`, within `math.isclose()` tolerance).

## Scenario 3 — Power-constrained mode rejects an infeasible budget (FR-004)

```python
result = calculate_end_milling(
    **geometry,
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=0.0,
)

assert result.error is not None
assert result.error.code == "INFEASIBLE_POWER_BUDGET"
assert result.spindle_speed_rpm is None
assert result.material_removal_rate is None
```

**Expected outcome**: a structured error, no numeric fields populated
(SC-003 of `009-milling-calculations`, reused here).

## Scenario 4 — Fixed-RPM mode calculates face-milling parameters from a supplied spindle speed (User Story 2)

```python
from machine_calc import calculate_face_milling

result = calculate_face_milling(
    diameter=63, axial_depth_of_cut=2, width_of_cut=40,
    feed_per_tooth=0.1, number_of_teeth=5, length_of_cut=150,
    material="Mild Steel", tool="Carbide", unit_system=UnitSystem.METRIC,
    mode=CalculationMode.FIXED_RPM,
    target_rpm=1500.0,
)

assert result.error is None
assert result.mode is CalculationMode.FIXED_RPM
assert result.spindle_speed_rpm == 1500.0
assert result.feed_rate is not None and result.torque is not None
assert result.power_required is not None and result.material_removal_rate is not None
```

**Expected outcome**: feed rate, machining time, torque, material removal
rate, and required power are all derived from the supplied `target_rpm`
rather than the material/tool's recommended speed (FR-006).

## Scenario 5 — Fixed-RPM mode rejects an invalid target RPM (FR-007)

```python
for bad_rpm in (0.0, -100.0, float("nan"), float("inf")):
    result = calculate_face_milling(
        diameter=63, axial_depth_of_cut=2, width_of_cut=40,
        feed_per_tooth=0.1, number_of_teeth=5, length_of_cut=150,
        material="Mild Steel", tool="Carbide", unit_system=UnitSystem.METRIC,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=bad_rpm,
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
```

## Scenario 6 — Mode mutual-exclusivity is rejected as `MODE_CONFLICT` (FR-009)

```python
# Power-constrained with a target_rpm also supplied.
conflict1 = calculate_end_milling(
    **geometry, mode=CalculationMode.POWER_CONSTRAINED,
    available_power=1.0, target_rpm=1000.0,
)
assert conflict1.error is not None and conflict1.error.code == "MODE_CONFLICT"

# Power-constrained with no available_power supplied.
conflict2 = calculate_end_milling(**geometry, mode=CalculationMode.POWER_CONSTRAINED)
assert conflict2.error is not None and conflict2.error.code == "MODE_CONFLICT"
```

## Scenario 7 — Standard mode is unaffected (SC-004 regression check)

```python
before = calculate_end_milling(**geometry)  # 009-milling-calculations behavior
after = calculate_end_milling(**geometry, mode=CalculationMode.STANDARD)

assert before.spindle_speed_rpm == after.spindle_speed_rpm
assert before.material_removal_rate == after.material_removal_rate
assert after.mode is CalculationMode.STANDARD
```

## Scenario 8 — Interactive REPL: mode prompt appears for milling, in the same relative position as drilling

```text
$ python -m machine_calc
Select operation: [drilling] milling
Select unit system: [metric] metric
Select calculation mode: [standard] power-constrained
Select material type: ...
...
Enter available power (kW) [required for power-constrained mode]: 0.5
...
```

**Expected outcome**: the mode prompt appears immediately after the
unit-system prompt and before material-type selection (research.md #5); an
invalid entry re-prompts; choosing power-constrained mode makes the
available-power prompt required (blank re-prompts, never a silent
`MODE_CONFLICT`); running the loop again and switching to fixed-RPM mode
clears any previously-entered target RPM/available-power defaults (FR-013).

**Per-mode prompt-count budget** (supersedes `009-milling-calculations`'
SC-001 for the two new modes; research.md #5): standard mode remains 14
prompts / 12 typed values (SC-004, unchanged); power-constrained mode is
14 prompts / 14 typed values (the mode prompt adds one, and the
now-required available-power prompt converts from optional to typed, so
every prompt in this mode requires a typed value); fixed-RPM mode is
15 prompts / 14 typed values (the mode prompt plus the required target-RPM
prompt add two, offset by the optional advisory available-power prompt
remaining a single-Enter default — the only dismissible prompt in this
mode). `tests/integration/test_cli_prompt_budget.py`
asserts these three counts per mode (see tasks.md T028).
