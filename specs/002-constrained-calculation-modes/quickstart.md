# Quickstart: Constrained Drilling Calculation Modes

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/](./contracts/)

Validation scenarios proving the two new modes work end-to-end, on top of
the existing `001-metal-drilling-calc` prerequisites (Python 3.9+ installed,
`pip install -e ".[dev]"`). See [data-model.md](./data-model.md) for the
new/extended entity shapes and [contracts/](./contracts/) for the exact
API/error contract deltas.

## Scenario 1 — Power-constrained mode reduces spindle speed to fit a budget (User Story 1)

```python
from machine_calc import calculate, UnitSystem, CalculationMode

# First, find the standard (unconstrained) required power for these inputs.
standard = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    unit_system=UnitSystem.METRIC,
)
assert standard.error is None
nominal_power = standard.power_required

# Now constrain to a budget below the nominal requirement.
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    unit_system=UnitSystem.METRIC,
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=nominal_power * 0.5,
)

assert result.error is None
assert result.mode is CalculationMode.POWER_CONSTRAINED
assert result.spindle_speed_rpm < standard.spindle_speed_rpm
assert abs(result.power_required - nominal_power * 0.5) < 1e-6
```

**Expected outcome**: `result.spindle_speed_rpm` is reduced proportionally
(research.md #1) so `result.power_required` matches the supplied budget
within floating-point tolerance; feed rate and machining time are
recomputed consistently; torque is unchanged (FR-002).

## Scenario 2 — Power-constrained mode is a no-op when the budget is already sufficient (FR-003)

```python
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    unit_system=UnitSystem.METRIC,
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=nominal_power * 2,
)

assert result.error is None
assert result.spindle_speed_rpm == standard.spindle_speed_rpm
```

**Expected outcome**: Identical numeric results to the standard calculation;
only `result.mode` differs (`POWER_CONSTRAINED` vs. `STANDARD`).

## Scenario 3 — Power-constrained mode rejects an infeasible budget (FR-004)

```python
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    unit_system=UnitSystem.METRIC,
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=0,
)

assert result.error is not None
assert result.error.code == "INFEASIBLE_POWER_BUDGET"
assert result.spindle_speed_rpm is None
```

**Expected outcome**: No exception raised; a structured, distinct error
code; no numeric fields populated.

## Scenario 4 — Fixed-RPM mode derives parameters from a caller-supplied RPM (User Story 2)

```python
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    unit_system=UnitSystem.METRIC,
    mode=CalculationMode.FIXED_RPM,
    target_rpm=1200,
)

assert result.error is None
assert result.mode is CalculationMode.FIXED_RPM
assert result.spindle_speed_rpm == 1200
assert result.feed_rate is not None
assert result.torque is not None
assert result.power_required is not None
```

**Expected outcome**: Feed rate, machining time, torque, and required power
are all derived from `target_rpm=1200`, in the same single call (SC-002).

## Scenario 5 — Fixed-RPM mode rejects a non-positive RPM (FR-007)

```python
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    mode=CalculationMode.FIXED_RPM,
    target_rpm=0,
)

assert result.error is not None
assert result.error.code == "INVALID_TARGET_RPM"
```

## Scenario 6 — The two new modes are mutually exclusive (FR-009)

```python
result = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    mode=CalculationMode.FIXED_RPM,
    target_rpm=1200,
    available_power=0.1,   # would only be a hard constraint in POWER_CONSTRAINED mode...
)
# ...but supplying target_rpm while requesting POWER_CONSTRAINED mode, or
# vice versa, is rejected:
conflicting = calculate(
    diameter=10, depth=25, material="Mild Steel", tool="Carbide",
    mode=CalculationMode.POWER_CONSTRAINED,
    available_power=0.1,
    target_rpm=1200,
)

assert conflicting.error is not None
assert conflicting.error.code == "MODE_CONFLICT"
```

**Expected outcome**: Supplying both a power constraint and a target RPM in
`POWER_CONSTRAINED` mode is rejected with `MODE_CONFLICT`, never silently
prioritizing one input over the other.

## Scenario 7 — Existing standard calculations are unaffected (SC-004, regression check)

```python
result = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
assert result.mode is CalculationMode.STANDARD
# Identical to every 001-metal-drilling-calc quickstart scenario's result.
```

**Expected outcome**: Calls that never pass `mode`/`target_rpm` continue to
behave exactly as documented in
`specs/001-metal-drilling-calc/quickstart.md`, with the sole addition of the
new `mode` field on the result (always `STANDARD` here).

## Scenario 8 — Interactive text interface mode-selection prompt (FR-001a)

Manual/CLI validation (see contracts/cli-repl-delta.md for the full prompt
sequence and example sessions):

1. Run the CLI; at the unit-system prompt, accept the default.
2. At the new "Calculation mode" prompt, select `power-constrained`.
3. Confirm the interface now asks for available power as a **required**
   field (not the base spec's optional advisory prompt), and that the
   result display clearly labels the spindle speed as adjusted.
4. Re-run and select `fixed-rpm`; confirm a required target-RPM prompt
   appears in place of deriving RPM from material/tool, and that the result
   display labels the spindle speed as user-specified.
