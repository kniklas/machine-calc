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
    "cli.result.feed_rate": "Feed rate:         {value} {unit}",
    "cli.result.machining_time": "Machining time:    {value} min",
    "cli.result.torque": "Torque:            {value} {unit}",
    "cli.result.power_required": "Power required:    {value} {unit}",
    "cli.result.warning": "Warning: {message}",
    # --- Validation / structured errors (validation.py, operations.drilling) ---
    "error.invalid_diameter.zero": "Drill diameter must be greater than 0.",
    "error.invalid_diameter.max": "Drill diameter must not exceed {max_diameter_mm:g} mm.",
    "error.invalid_depth.zero": "Hole depth must be greater than 0.",
    "error.invalid_depth.max": "Hole depth must not exceed {max_depth_mm:g} mm.",
    "error.missing_material": "A workpiece material must be selected.",
    "error.missing_tool": "A drilling tool must be selected.",
    "error.unknown_material": "Unknown workpiece material: {material!r}.",
    "error.unknown_tool": "Unknown drilling tool: {tool!r}.",
    "warning.feasibility": (
        "Required power ({required_kw:.2f} kW) exceeds the available "
        "power ({available_kw:.2f} kW)."
    ),
}
