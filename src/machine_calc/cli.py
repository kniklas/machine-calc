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

import argparse

from machine_calc import CalculationMode, UnitSystem, calculate, list_materials, list_tools
from machine_calc.config import Configuration
from machine_calc.i18n import get_locale, get_raw_locale, translate
from machine_calc.logging_setup import configure_logging
from machine_calc.operations.drilling.tools import DrillingTool, get_tool
from machine_calc.registry import WorkpieceMaterial, get_material
from machine_calc.registry_config import RegistryConfigError, load_and_merge
from machine_calc.units import in_to_mm
from machine_calc.validation import validate_depth_mm, validate_diameter_mm

_DEFAULT_CONFIG = Configuration()

# Bundled package/resource identifiers, reused (not duplicated) here purely
# to detect a "missing/unreadable materials-config path" startup notice
# ahead of the REPL loop (contracts/library-cli-extensions.md "Startup
# sequence"); the actual parse/merge/validate logic lives in
# ``registry.py``/``operations/drilling/tools.py``/``registry_config.py``.
_MATERIALS_BUNDLED_PACKAGE = "machine_calc.data"
_MATERIALS_BUNDLED_RESOURCE = "materials.toml"
_MATERIALS_TABLE_KEY = "materials"

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


def _display_label(
    entry: WorkpieceMaterial | DrillingTool, display_locale: str, message_locale: str
) -> str:
    """Build a material/tool prompt option label (User Story 3, 4).

    Displays the translated name (falling back to English, research.md #7),
    resolved from ``display_locale`` — the *raw* ``MACHINE_CALC_LOCALE``
    value (:func:`machine_calc.i18n.get_raw_locale`), independent of
    whether a bundled message catalog exists for it (quickstart.md Scenario
    4: a data-driven translation is shown even when the message-catalog
    locale falls back to English). Only when the entry declares a
    non-default (``"imperial"``) unit system is a unit-system suffix
    appended (FR-013), translated via ``message_locale`` (the
    catalog-resolved active locale) — this keeps the bundled, all-metric
    defaults' prompt labels byte-for-byte identical to
    pre-``005-configurable-materials-tools`` behavior (FR-014, SC-002).
    """

    name = entry.display_name(display_locale)
    if entry.unit_system == "metric":
        return name
    return translate(
        message_locale, "cli.label.unit_system_suffix", name=name, unit_system=entry.unit_system
    )


def _prompt_material_choice(
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str:
    """Prompt for a material, displaying translated name + unit system.

    Resolves the user's selection back to the canonical English ``name``
    before returning it (research.md #7), the same "label dict /
    reverse-lookup dict" pattern already used by :func:`_prompt_mode`.
    """

    materials = {name: get_material(name, config_path) for name in names}
    labels_by_name = {
        name: _display_label(material, display_locale, locale)
        for name, material in materials.items()
        if material is not None
    }
    names_by_label = {label: name for name, label in labels_by_name.items()}
    options = list(labels_by_name.values())
    default_label = labels_by_name.get(default) if default else None
    choice_label = _prompt_choice(
        translate(locale, "cli.label.material"), options, default_label, locale
    )
    return names_by_label[choice_label]


def _prompt_tool_choice(
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str:
    """Prompt for a drilling tool, displaying translated name + unit system.

    Mirrors :func:`_prompt_material_choice` for :class:`DrillingTool`.
    """

    tools = {name: get_tool(name, config_path) for name in names}
    labels_by_name = {
        name: _display_label(tool, display_locale, locale)
        for name, tool in tools.items()
        if tool is not None
    }
    names_by_label = {label: name for name, label in labels_by_name.items()}
    options = list(labels_by_name.values())
    default_label = labels_by_name.get(default) if default else None
    choice_label = _prompt_choice(
        translate(locale, "cli.label.tool"), options, default_label, locale
    )
    return names_by_label[choice_label]


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


def _resolve_materials_config(materials_config_path: str | None, locale: str) -> None:
    """Validate ``materials_config_path`` once at CLI startup and print any notice.

    Raises :class:`SystemExit` (after printing a translated error, no raw
    traceback) if the file exists but is malformed or invalid
    (``RegistryConfigError``, FR-007). If the path is missing/unreadable,
    prints the translated non-fatal notice and returns normally, so the
    REPL proceeds with bundled defaults only (FR-005). Does nothing if
    ``materials_config_path`` is ``None`` (contracts/library-cli-extensions.md
    "Startup sequence").
    """

    if materials_config_path is None:
        return

    try:
        # Triggers the full parse/duplicate/validate/convert path for both
        # materials and tools, exactly as the REPL loop will use them.
        list_materials(config_path=materials_config_path)
        list_tools(config_path=materials_config_path)
    except RegistryConfigError as exc:
        print(translate(locale, exc.message_key, **exc.kwargs))
        raise SystemExit(1) from exc

    result = load_and_merge(
        _MATERIALS_BUNDLED_PACKAGE,
        _MATERIALS_BUNDLED_RESOURCE,
        materials_config_path,
        _MATERIALS_TABLE_KEY,
    )
    if result.notice_key:
        print(translate(locale, result.notice_key, **dict(result.notice_kwargs)))


def run(materials_config_path: str | None = None) -> None:
    """Run the interactive drilling-calculation REPL until the user exits.

    Resolves the active locale exactly once, at the start of the session
    (FR-019c); it is not re-read on subsequent loop iterations even if
    ``MACHINE_CALC_LOCALE`` changes in the environment mid-session.

    Args:
        materials_config_path: Optional path (resolved once at startup from
            the ``--materials-config`` CLI flag) to a user-supplied
            materials/tools configuration file. Forwarded, unchanged for
            the whole session, to every ``list_materials()``/
            ``list_tools()``/``calculate()`` call in the REPL loop
            (research.md #3).
    """

    locale = get_locale()
    display_locale = get_raw_locale()

    _resolve_materials_config(materials_config_path, locale)

    materials = list_materials(config_path=materials_config_path)
    tools = list_tools(config_path=materials_config_path)

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
        material = _prompt_material_choice(
            materials, materials_config_path, material, locale, display_locale
        )
        tool = _prompt_tool_choice(tools, materials_config_path, tool, locale, display_locale)
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
            materials_config_path=materials_config_path,
        )
        _display_result(result, labels, locale)

        again = input(translate(locale, "cli.prompt.run_again")).strip().lower()
        if again not in ("y", "yes"):
            break


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments (currently just ``--materials-config``, FR-002)."""

    parser = argparse.ArgumentParser(prog="machine-calc")
    parser.add_argument(
        "--materials-config",
        dest="materials_config",
        default=None,
        metavar="PATH",
        help=(
            "Optional path to a TOML file adding/overriding materials and "
            "drilling tools (see contracts/materials-config-schema.md)."
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    """Console-script entry point (``machine-calc`` / ``python -m machine_calc``)."""

    configure_logging()
    args = _parse_args()
    try:
        run(materials_config_path=args.materials_config)
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
