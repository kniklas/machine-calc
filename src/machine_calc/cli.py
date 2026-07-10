"""Interactive text interface (REPL) for drilling calculations (FR-002).

Built strictly on top of the public library API (contracts/cli-repl.md) —
contains no calculation logic of its own; every result comes from
``machine_calc.calculate()``.

All prompts, labels, and messages are sourced from the message catalog via
``machine_calc.i18n`` (FR-019a-c) rather than hard-coded literal strings.
The active locale is resolved exactly once at startup from
``MACHINE_CALC_LOCALE`` (:func:`machine_calc.i18n.get_locale`) and held
fixed for the entire REPL loop — it is never re-read mid-session.
"""

from __future__ import annotations

from machine_calc import CalculationMode, UnitSystem, calculate, list_materials, list_tools
from machine_calc.config import Configuration
from machine_calc.i18n import get_locale, translate
from machine_calc.logging_setup import configure_logging
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


def _prompt_unit_system(default: UnitSystem, locale: str) -> UnitSystem:
    default_label = (
        translate(locale, "cli.unit_system.metric")
        if default is UnitSystem.METRIC
        else translate(locale, "cli.unit_system.imperial")
    )
    while True:
        raw = (
            input(translate(locale, "cli.prompt.unit_system", default=default_label))
            .strip()
            .lower()
        )
        if not raw:
            return default
        if raw in ("metric", "m"):
            return UnitSystem.METRIC
        if raw in ("imperial", "i"):
            return UnitSystem.IMPERIAL
        print(translate(locale, "cli.prompt.unit_system.invalid"))


def _prompt_choice(label: str, options: list[str], default: str | None, locale: str) -> str:
    options_display = ", ".join(options)
    suffix = f" ({default})" if default else ""
    while True:
        raw = input(
            translate(
                locale, "cli.prompt.choice", label=label, options=options_display, suffix=suffix
            )
        ).strip()
        if not raw and default:
            return default
        if raw in options:
            return raw
        print(translate(locale, "cli.prompt.choice.invalid", options=options_display))


def _prompt_number(label: str, unit: str, default: float | None, locale: str) -> float:
    if default is not None:
        suffix = translate(locale, "cli.prompt.suffix.with_default", unit=unit, default=default)
    else:
        suffix = translate(locale, "cli.prompt.suffix.no_default", unit=unit)
    while True:
        raw = input(translate(locale, "cli.prompt.number", label=label, suffix=suffix)).strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print(translate(locale, "cli.prompt.number.invalid"))


def _prompt_diameter(
    unit: str, default: float | None, unit_system: UnitSystem, locale: str
) -> float:
    label = translate(locale, "cli.label.diameter")
    while True:
        value = _prompt_number(label, unit, default, locale)
        value_mm = in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value
        error = validate_diameter_mm(value_mm, _DEFAULT_CONFIG, locale)
        if error is None:
            return value
        print(error.message)


def _prompt_depth(unit: str, default: float | None, unit_system: UnitSystem, locale: str) -> float:
    label = translate(locale, "cli.label.depth")
    while True:
        value = _prompt_number(label, unit, default, locale)
        value_mm = in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value
        error = validate_depth_mm(value_mm, _DEFAULT_CONFIG, locale)
        if error is None:
            return value
        print(error.message)


def _prompt_optional_power(unit: str, default: float | None, locale: str) -> float | None:
    default_clause = (
        translate(locale, "cli.prompt.power.default_clause", default=default) if default else ""
    )
    suffix = translate(locale, "cli.prompt.power.suffix", unit=unit, default_clause=default_clause)
    label = translate(locale, "cli.label.power")
    raw = input(translate(locale, "cli.prompt.number", label=label, suffix=suffix)).strip()
    if not raw:
        return default
    if raw.lower() == "skip":
        return None
    try:
        return float(raw)
    except ValueError:
        print(translate(locale, "cli.prompt.power.invalid"))
        return default


_MODE_OPTION_KEYS = {
    CalculationMode.STANDARD: "cli.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "cli.mode.power_constrained",
    CalculationMode.FIXED_RPM: "cli.mode.fixed_rpm",
}


def _prompt_mode(default: CalculationMode, locale: str) -> CalculationMode:
    """Prompt for the calculation mode (FR-001a).

    Re-prompts on an invalid/unrecognized entry, the same as material/tool
    selection (base spec FR-010) — it MUST NOT silently fall back to a
    default mode on an unrecognized entry (spec.md Clarifications
    2026-07-11). A blank entry accepts the current default, exactly like
    the existing material/tool prompts.
    """

    labels_by_mode = {m: translate(locale, key) for m, key in _MODE_OPTION_KEYS.items()}
    modes_by_label = {label: m for m, label in labels_by_mode.items()}
    options = list(labels_by_mode.values())
    label = translate(locale, "cli.label.mode")

    choice = _prompt_choice(label, options, labels_by_mode[default], locale)
    return modes_by_label[choice]


def _prompt_required_power(unit: str, default: float | None, locale: str) -> float:
    """Prompt for a required available-power value (power-constrained mode).

    A blank or non-numeric entry re-prompts as a validation failure (FR-002;
    spec.md Clarifications 2026-07-11) — never treated as ``MODE_CONFLICT``
    — unless a default is available (a retained editable default from a
    prior loop iteration in the same mode), in which case blank accepts it.
    """

    label = translate(locale, "cli.label.power_required")
    while True:
        value = _prompt_number(label, unit, default, locale)
        if value > 0:
            return value
        print(translate(locale, "cli.prompt.power_required.invalid"))


def _prompt_target_rpm(default: float | None, locale: str) -> float:
    """Prompt for a required target spindle RPM (fixed-RPM mode).

    A blank or non-numeric entry re-prompts as a validation failure
    (FR-005, FR-007), unless a default is available (a retained editable
    default from a prior loop iteration in the same mode).
    """

    label = translate(locale, "cli.label.target_rpm")
    while True:
        value = _prompt_number(label, "RPM", default, locale)
        if value > 0:
            return value
        print(translate(locale, "cli.prompt.target_rpm.invalid"))


_SPINDLE_SPEED_MODE_LABEL_KEYS = {
    CalculationMode.STANDARD: "cli.result.spindle_speed.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "cli.result.spindle_speed.mode.power_constrained",
    CalculationMode.FIXED_RPM: "cli.result.spindle_speed.mode.fixed_rpm",
}


def _display_result(result, labels: dict[str, str], locale: str) -> None:
    if result.error is not None:
        print(translate(locale, "cli.result.error", message=result.error.message))
        return

    print()
    mode_label = translate(locale, _SPINDLE_SPEED_MODE_LABEL_KEYS[result.mode])
    mode_suffix = translate(locale, "cli.result.spindle_speed.mode_suffix", label=mode_label)
    print(
        translate(locale, "cli.result.spindle_speed", value=f"{result.spindle_speed_rpm:.1f}")
        + mode_suffix
    )
    print(
        translate(
            locale,
            "cli.result.feed_rate",
            value=f"{result.feed_rate:.1f}",
            unit=labels["feed_rate"],
        )
    )
    print(translate(locale, "cli.result.machining_time", value=f"{result.machining_time:.2f}"))
    print(
        translate(locale, "cli.result.torque", value=f"{result.torque:.1f}", unit=labels["torque"])
    )
    print(
        translate(
            locale,
            "cli.result.power_required",
            value=f"{result.power_required:.2f}",
            unit=labels["power"],
        )
    )
    if result.feasibility_warning:
        print(translate(locale, "cli.result.warning", message=result.feasibility_warning))
    print()


def run() -> None:
    """Run the interactive drilling-calculation REPL until the user exits.

    Resolves the active locale exactly once, at the start of the session
    (FR-019c); it is not re-read on subsequent loop iterations even if
    ``MACHINE_CALC_LOCALE`` changes in the environment mid-session.
    """

    locale = get_locale()

    materials = list_materials()
    tools = list_tools()

    unit_system = UnitSystem.METRIC
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    depth: float | None = None
    available_power: float | None = None
    mode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode = mode

    while True:
        unit_system = _prompt_unit_system(unit_system, locale)
        labels = UNIT_LABELS[unit_system]
        mode = _prompt_mode(mode, locale)
        if mode is not previous_mode:
            # Loop re-run mode switch (FR-013, spec.md Clarifications
            # 2026-07-11): clear mode-specific values rather than carrying
            # them over as editable defaults. Shared inputs (unit system,
            # material, tool, diameter, depth) are unaffected.
            target_rpm = None
            available_power = None
        previous_mode = mode
        material = _prompt_choice(
            translate(locale, "cli.label.material"), materials, material, locale
        )
        tool = _prompt_choice(translate(locale, "cli.label.tool"), tools, tool, locale)
        diameter = _prompt_diameter(labels["diameter"], diameter, unit_system, locale)
        depth = _prompt_depth(labels["depth"], depth, unit_system, locale)

        if mode is CalculationMode.POWER_CONSTRAINED:
            available_power = _prompt_required_power(labels["power"], available_power, locale)
        elif mode is CalculationMode.FIXED_RPM:
            target_rpm = _prompt_target_rpm(target_rpm, locale)
            available_power = _prompt_optional_power(labels["power"], available_power, locale)
        else:
            available_power = _prompt_optional_power(labels["power"], available_power, locale)

        result = calculate(
            diameter=diameter,
            depth=depth,
            material=material,
            tool=tool,
            unit_system=unit_system,
            available_power=available_power,
            locale=locale,
            mode=mode,
            target_rpm=target_rpm,
        )
        _display_result(result, labels, locale)

        again = input(translate(locale, "cli.prompt.run_again")).strip().lower()
        if again not in ("y", "yes"):
            break


def main() -> None:
    """Console-script entry point (``machine-calc`` / ``python -m machine_calc``)."""

    configure_logging()
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
