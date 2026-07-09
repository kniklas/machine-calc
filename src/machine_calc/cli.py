"""Interactive text interface (REPL) for drilling calculations (FR-002).

Built strictly on top of the public library API (contracts/cli-repl.md) —
contains no calculation logic of its own; every result comes from
``machine_calc.calculate()``.
"""

from __future__ import annotations

from machine_calc import UnitSystem, calculate, list_materials, list_tools
from machine_calc.config import Configuration
from machine_calc.units import in_to_mm
from machine_calc.validation import validate_depth_mm, validate_diameter_mm

_DEFAULT_CONFIG = Configuration()

UNIT_LABELS = {
    UnitSystem.METRIC: {
        "diameter": "mm",
        "depth": "mm",
        "feed_rate": "mm/min",
        "torque": "N\u00b7m",
        "power": "kW",
    },
    UnitSystem.IMPERIAL: {
        "diameter": "in",
        "depth": "in",
        "feed_rate": "in/min",
        "torque": "in-lb",
        "power": "HP",
    },
}


def _prompt_unit_system(default: UnitSystem) -> UnitSystem:
    default_label = "metric" if default is UnitSystem.METRIC else "imperial"
    while True:
        raw = input(f"Unit system [metric/imperial] ({default_label}): ").strip().lower()
        if not raw:
            return default
        if raw in ("metric", "m"):
            return UnitSystem.METRIC
        if raw in ("imperial", "i"):
            return UnitSystem.IMPERIAL
        print("Please enter 'metric' or 'imperial'.")


def _prompt_choice(label: str, options: list[str], default: str | None) -> str:
    options_display = ", ".join(options)
    suffix = f" ({default})" if default else ""
    while True:
        raw = input(f"{label} ({options_display}){suffix}: ").strip()
        if not raw and default:
            return default
        if raw in options:
            return raw
        print(f"Please choose one of: {options_display}")


def _prompt_number(label: str, unit: str, default: float | None) -> float:
    suffix = f" ({unit}, default {default})" if default is not None else f" ({unit})"
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print("Please enter a numeric value.")


def _prompt_diameter(unit: str, default: float | None, unit_system: UnitSystem) -> float:
    while True:
        value = _prompt_number("Drill diameter", unit, default)
        value_mm = in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value
        error = validate_diameter_mm(value_mm, _DEFAULT_CONFIG)
        if error is None:
            return value
        print(error.message)


def _prompt_depth(unit: str, default: float | None, unit_system: UnitSystem) -> float:
    while True:
        value = _prompt_number("Hole depth", unit, default)
        value_mm = in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value
        error = validate_depth_mm(value_mm, _DEFAULT_CONFIG)
        if error is None:
            return value
        print(error.message)


def _prompt_optional_power(unit: str, default: float | None) -> float | None:
    suffix = f" ({unit}, blank if unknown" + (f", default {default}" if default else "") + ")"
    raw = input(f"Available power{suffix}: ").strip()
    if not raw:
        return default
    if raw.lower() == "skip":
        return None
    try:
        return float(raw)
    except ValueError:
        print("Ignoring non-numeric power value.")
        return default


def _display_result(result, labels: dict[str, str]) -> None:
    if result.error is not None:
        print(f"\nError: {result.error.message}\n")
        return

    print()
    print(f"Spindle speed:     {result.spindle_speed_rpm:.1f} RPM")
    print(f"Feed rate:         {result.feed_rate:.1f} {labels['feed_rate']}")
    print(f"Machining time:    {result.machining_time:.2f} min")
    print(f"Torque:            {result.torque:.1f} {labels['torque']}")
    print(f"Power required:    {result.power_required:.2f} {labels['power']}")
    if result.feasibility_warning:
        print(f"Warning: {result.feasibility_warning}")
    print()


def run() -> None:
    """Run the interactive drilling-calculation REPL until the user exits."""

    materials = list_materials()
    tools = list_tools()

    unit_system = UnitSystem.METRIC
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    depth: float | None = None
    available_power: float | None = None

    while True:
        unit_system = _prompt_unit_system(unit_system)
        labels = UNIT_LABELS[unit_system]
        material = _prompt_choice("Material", materials, material)
        tool = _prompt_choice("Drilling tool", tools, tool)
        diameter = _prompt_diameter(labels["diameter"], diameter, unit_system)
        depth = _prompt_depth(labels["depth"], depth, unit_system)
        available_power = _prompt_optional_power(labels["power"], available_power)

        result = calculate(
            diameter=diameter,
            depth=depth,
            material=material,
            tool=tool,
            unit_system=unit_system,
            available_power=available_power,
        )
        _display_result(result, labels)

        again = input("Run another calculation? [y/N]: ").strip().lower()
        if again not in ("y", "yes"):
            break


def main() -> None:
    """Console-script entry point (``machine-calc`` / ``python -m machine_calc``)."""

    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
