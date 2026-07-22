"""English (``en``) message catalog — the default and fallback locale.

Message IDs are stable and language-independent; do not rename an existing
key when editing its English text (other locale modules and tests key off
these IDs). See ``specs/001-metal-drilling-calc/data-model.md`` (Message
Catalog) for the entity definition this module implements.
"""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    # --- Interactive text interface (cli.py) prompts and labels ---
    "cli.prompt.unit_system": "Unit system [metric/imperial] ({default}): ",
    "cli.prompt.unit_system.invalid": "Please enter 'metric' or 'imperial'.",
    "cli.unit_system.metric": "metric",
    "cli.unit_system.imperial": "imperial",
    "cli.prompt.choice": "{label} ({options}){suffix}: ",
    "cli.prompt.choice.invalid": "Please choose one of: {options}",
    "cli.prompt.number": "{label}{suffix}: ",
    "cli.prompt.number.invalid": "Please enter a numeric value.",
    "cli.prompt.suffix.with_default": " ({unit}, default {default})",
    "cli.prompt.suffix.no_default": " ({unit})",
    "cli.prompt.power.suffix": " ({unit}, blank if unknown{default_clause})",
    "cli.prompt.power.default_clause": ", default {default}",
    "cli.prompt.power.invalid": "Ignoring non-numeric power value.",
    "cli.label.diameter": "Drill diameter",
    "cli.label.depth": "Hole depth",
    "cli.label.power": "Available power",
    "cli.label.material": "Material",
    "cli.label.tool": "Drilling tool",
    "cli.prompt.run_again": "Run another calculation? [y/N]: ",
    "cli.result.error": "\nError: {message}\n",
    "cli.result.spindle_speed": "Spindle speed:     {value} RPM",
    "cli.result.spindle_speed.mode_suffix": "   ({label})",
    "cli.result.spindle_speed.mode.standard": "recommended",
    "cli.result.spindle_speed.mode.power_constrained": "adjusted to fit available power",
    "cli.result.spindle_speed.mode.fixed_rpm": "user-specified",
    "cli.result.feed_rate": "Feed rate:         {value} {unit}",
    "cli.result.machining_time": "Machining time:    {value} min",
    "cli.result.torque": "Torque:            {value} {unit}",
    "cli.result.power_required": "Power required:    {value} {unit}",
    "cli.result.warning": "Warning: {message}",
    # --- Calculation-mode selection prompt (FR-001a) ---
    "cli.label.mode": "Calculation mode",
    "cli.mode.standard": "standard",
    "cli.mode.power_constrained": "power-constrained",
    "cli.mode.fixed_rpm": "fixed-rpm",
    "cli.label.power_required": "Available power",
    "cli.prompt.power_required.invalid": (
        "Please enter a positive numeric value for available power."
    ),
    "cli.label.target_rpm": "Target spindle speed",
    "cli.prompt.target_rpm.invalid": (
        "Please enter a positive numeric value for target spindle speed."
    ),
    # --- Validation / structured errors (validation.py, operations.drilling) ---
    "error.invalid_diameter.zero": "Drill diameter must be greater than 0.",
    "error.invalid_diameter.max": "Drill diameter must not exceed {max_diameter_mm:g} mm.",
    "error.invalid_depth.zero": "Hole depth must be greater than 0.",
    "error.invalid_depth.max": "Hole depth must not exceed {max_depth_mm:g} mm.",
    "error.missing_material": "A workpiece material must be selected.",
    "error.missing_tool": "A drilling tool must be selected.",
    "error.unknown_material": "Unknown workpiece material: {material!r}.",
    "error.unknown_tool": "Unknown drilling tool: {tool!r}.",
    "error.invalid_target_rpm": "Target spindle speed must be a positive, finite number.",
    "error.mode_conflict": (
        "Power-constrained and fixed-RPM inputs cannot be combined in one "
        "request, and power-constrained mode requires an available power "
        "value."
    ),
    "error.infeasible_power_budget": (
        "No spindle speed keeps the required power within the supplied " "available power budget."
    ),
    "warning.feasibility": (
        "Required power ({required_kw:.2f} kW) exceeds the available "
        "power ({available_kw:.2f} kW)."
    ),
    # --- Materials/tools configuration file notices/errors (005) ---
    "notice.materials_config.not_found": (
        "Materials/tools configuration file {path!r} was not found or is not "
        "readable; continuing with the built-in defaults."
    ),
    "error.materials_config.malformed": (
        "Materials/tools configuration file {path!r} could not be parsed as "
        "valid TOML: {details}"
    ),
    "error.materials_config.duplicate_entry": (
        "Materials/tools configuration file {path!r} defines more than one "
        "{kind} named {name!r}."
    ),
    "error.materials_config.invalid_entry": (
        "Materials/tools configuration file {path!r} has an invalid {kind} "
        "entry {name!r}: {details}"
    ),
    "cli.label.unit_system_suffix": "{name} [{unit_system}]",
}
