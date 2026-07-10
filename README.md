# machine-calc

A Python library and interactive command-line tool for metal machining
calculations, starting with twist-drill drilling parameters (spindle speed,
feed rate, machining time, torque, and required power).

> **Status**: Early implementation (drilling calculation engine + CLI MVP).
> Full end-user/developer documentation, coverage badge, and CI/CD
> automation are tracked in
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

## Run the tests

```bash
pytest
```

This project targets Python 3.9+ for compatibility with older/stable Linux
distributions (see `.specify/memory/constitution.md` Principle V), and aims
for ≥90% test coverage on calculation modules (Principle II).

See `specs/001-metal-drilling-calc/` for the full spec, plan, and task
breakdown driving this implementation.
