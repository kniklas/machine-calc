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
from machine_calc import calculate, UnitSystem

result = calculate(
    diameter=10,
    depth=25,
    material="Mild Steel",
    tool="Carbide",
    unit_system=UnitSystem.METRIC,
)
print(result)
```

## Use the interactive CLI

```bash
python -m machine_calc
```

## Run the tests

```bash
pytest
```

This project targets Python 3.9+ for compatibility with older/stable Linux
distributions (see `.specify/memory/constitution.md` Principle V), and aims
for ≥90% test coverage on calculation modules (Principle II).

See `specs/001-metal-drilling-calc/` for the full spec, plan, and task
breakdown driving this implementation.
