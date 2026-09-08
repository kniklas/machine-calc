"""The Drilling parameter-entry screen (FR-002).

Ports `console/cli.py`'s `_run_drilling_session` prompt sequence (research.md
#3) onto `forms.py`'s dialog primitives, calling `mfgparams.calculate`
unchanged. `DrillingSessionState` mirrors `_DrillingSessionState`: one
instance lives for the whole app session (owned by `tui/app.py`), so
revisiting this screen after a calculation offers the previous answers as
defaults, exactly as the REPL's loop did (FR-002, SC-005 parity).
"""

from __future__ import annotations

from dataclasses import dataclass

from mfgparams import (
    CalculationMode,
    UnitSystem,
    calculate,
    list_material_types,
    list_materials,
    list_tools,
)
from mfgparams.config import Configuration
from mfgparams.console.i18n import DEFAULT_LOCALE, translate
from mfgparams.console.tui import forms
from mfgparams.validation import validate_depth_mm, validate_diameter_mm

_DEFAULT_CONFIG = Configuration()


@dataclass
class DrillingSessionState:
    """Editable defaults carried across visits to this screen within one
    app session. Ported unchanged from `console/cli.py`'s
    `_DrillingSessionState`."""

    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    depth: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode: CalculationMode = CalculationMode.STANDARD


def run_drilling_screen(
    state: DrillingSessionState,
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> None:
    """Run one drilling prompt/calculate/display pass, or return early
    ("go back" to the Machining menu) if the user cancels any field."""

    material_types = list_material_types(config_path=materials_config_path)
    tools = list_tools(config_path=materials_config_path)

    unit_system = forms.ask_unit_system(default=state.unit_system, locale=locale)
    if unit_system is None:
        return
    state.unit_system = unit_system
    labels = forms.UNIT_LABELS[state.unit_system]

    mode = forms.ask_mode(default=state.mode, locale=locale)
    if mode is None:
        return
    state.mode = mode
    if state.mode is not state.previous_mode:
        # Mode switch (mirrors cli.py's _run_drilling_session): clear
        # mode-specific values rather than carrying them over.
        state.target_rpm = None
        state.available_power = None
    state.previous_mode = state.mode

    material_type = forms.ask_material_type(
        material_types=material_types, default=state.material_type, locale=locale
    )
    if material_type is None:
        return
    state.material_type = material_type

    materials = list_materials(config_path=materials_config_path, material_type=state.material_type)
    material = forms.ask_material(
        names=materials,
        config_path=materials_config_path,
        default=state.material,
        locale=locale,
        display_locale=display_locale,
    )
    if material is None:
        return
    state.material = material

    tool = forms.ask_drilling_tool(
        names=tools, config_path=materials_config_path, default=state.tool, locale=locale,
        display_locale=display_locale,
    )
    if tool is None:
        return
    state.tool = tool

    diameter = forms.ask_number(
        title=translate(locale, "tui.drilling.title"),
        label=translate(locale, "tui.label.diameter"),
        unit=labels["diameter"],
        default=state.diameter,
        locale=locale,
        validate=lambda mm: validate_diameter_mm(
            _to_mm(mm, state.unit_system), _DEFAULT_CONFIG, DEFAULT_LOCALE
        ),
    )
    if diameter is None:
        return
    state.diameter = diameter

    depth = forms.ask_number(
        title=translate(locale, "tui.drilling.title"),
        label=translate(locale, "tui.label.depth"),
        unit=labels["depth"],
        default=state.depth,
        locale=locale,
        validate=lambda mm: validate_depth_mm(
            _to_mm(mm, state.unit_system), _DEFAULT_CONFIG, DEFAULT_LOCALE
        ),
    )
    if depth is None:
        return
    state.depth = depth

    if not _prompt_power_or_rpm(state, labels, locale):
        return

    result = calculate(
        diameter=state.diameter,
        depth=state.depth,
        material=state.material,
        tool=state.tool,
        unit_system=state.unit_system,
        available_power=state.available_power,
        locale=locale,
        mode=state.mode,
        target_rpm=state.target_rpm,
        materials_config_path=materials_config_path,
    )
    forms.show_result(result, labels, locale)


def _to_mm(value: float, unit_system: UnitSystem) -> float:
    from mfgparams.units import in_to_mm

    return in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value


def _prompt_power_or_rpm(state: DrillingSessionState, labels: dict[str, str], locale: str) -> bool:
    """The mode-dependent power/RPM screen(s); returns False on cancel.

    Extracted from `run_drilling_screen` (Constitution Principle I /
    complexity gate) -- this is the same three-way branch
    `_run_drilling_session` had, just isolated to its own function.
    """

    title = translate(locale, "tui.drilling.title")

    if state.mode is CalculationMode.POWER_CONSTRAINED:
        power = forms.ask_number(
            title=title,
            label=translate(locale, "tui.label.power_required"),
            unit=labels["power"],
            default=state.available_power,
            locale=locale,
        )
        if power is None:
            return False
        state.available_power = power
        return True

    if state.mode is CalculationMode.FIXED_RPM:
        target_rpm = forms.ask_number(
            title=title,
            label=translate(locale, "tui.label.target_rpm"),
            unit="RPM",
            default=state.target_rpm,
            locale=locale,
        )
        if target_rpm is None:
            return False
        state.target_rpm = target_rpm
        state.available_power = forms.ask_optional_number(
            title=title,
            label=translate(locale, "tui.label.power"),
            unit=labels["power"],
            default=state.available_power,
            locale=locale,
        )
        return True

    state.available_power = forms.ask_optional_number(
        title=title,
        label=translate(locale, "tui.label.power"),
        unit=labels["power"],
        default=state.available_power,
        locale=locale,
    )
    return True
