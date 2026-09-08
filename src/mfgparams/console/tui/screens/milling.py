"""The Milling parameter-entry screen (FR-002): end milling and face milling.

Ports `console/cli.py`'s `_prompt_milling_sub_operation`/
`_prompt_milling_inputs`/`_run_end_milling_session`/`_run_face_milling_session`
(research.md #3) onto `forms.py`'s dialog primitives. `MillingSessionState`
mirrors `_MillingSessionState`: one instance per sub-operation lives for the
whole app session (owned by `tui/app.py`), so re-selecting the same
sub-operation offers its own previous answers as defaults without the other
sub-operation's answers leaking in (FR-002 parity).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, cast

from mfgparams import (
    CalculationMode,
    MillingSubOperation,
    UnitSystem,
    calculate_end_milling,
    calculate_face_milling,
    list_end_mill_tools,
    list_face_mill_tools,
    list_material_types,
    list_materials,
)
from mfgparams.config import Configuration
from mfgparams.console.i18n import DEFAULT_LOCALE, translate
from mfgparams.console.tui import forms
from mfgparams.processes.machining.milling.end_milling.tools import get_end_mill_tool
from mfgparams.processes.machining.milling.face_milling.tools import get_face_mill_tool
from mfgparams.units import in_to_mm
from mfgparams.validation import (
    validate_depth_of_cut_mm,
    validate_engagement_mm,
    validate_feed_per_tooth_mm,
    validate_length_of_cut_mm,
    validate_mill_diameter_mm,
    validate_tooth_count,
)

_DEFAULT_CONFIG = Configuration()


@dataclass
class MillingSessionState:
    """Ported unchanged from `console/cli.py`'s `_MillingSessionState`."""

    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    axial_depth_of_cut: float | None = None
    radial_engagement: float | None = None
    feed_per_tooth: float | None = None
    number_of_teeth: float | None = None
    length_of_cut: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode: CalculationMode = CalculationMode.STANDARD


def _to_mm(value: float, unit_system: UnitSystem) -> float:
    return in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value


def _prompt_tool(
    sub_operation: MillingSubOperation,
    state: MillingSessionState,
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> tuple[str | None, str]:
    """The end-mill/face-mill tool screen, plus which engagement label this
    sub-operation uses. Extracted from `run_milling_screen` (complexity
    gate); the two sub-operations differ only in which registry/label they
    use, not in the prompting logic itself."""

    resolve: Callable[[str, str | None], object | None]
    if sub_operation is MillingSubOperation.END_MILLING:
        tool_names = list_end_mill_tools(config_path=materials_config_path)
        resolve, label_key = get_end_mill_tool, "tui.label.end_mill_tool"
        engagement_label_key = "cli.label.radial_depth_of_cut"
    else:
        tool_names = list_face_mill_tools(config_path=materials_config_path)
        resolve, label_key = get_face_mill_tool, "tui.label.face_mill_tool"
        engagement_label_key = "cli.label.width_of_cut"

    tool = forms.ask_tool(
        names=tool_names,
        resolve=resolve,
        label_key=label_key,
        config_path=materials_config_path,
        default=state.tool,
        locale=locale,
        display_locale=display_locale,
    )
    return tool, engagement_label_key


def run_milling_screen(
    states: dict[MillingSubOperation, MillingSessionState],
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> None:
    """Ask which sub-operation, then run its prompt/calculate/display pass."""

    sub_options = {
        MillingSubOperation.END_MILLING.value: translate(
            locale, "tui.milling_sub_operation.end_milling"
        ),
        MillingSubOperation.FACE_MILLING.value: translate(
            locale, "tui.milling_sub_operation.face_milling"
        ),
    }
    choice = forms.ask_choice(
        title=translate(locale, "tui.milling.title"),
        label=translate(locale, "tui.label.milling_sub_operation"),
        options=sub_options,
        default=MillingSubOperation.END_MILLING.value,
        locale=locale,
    )
    if choice is None:
        return
    sub_operation = MillingSubOperation(choice)
    state = states[sub_operation]

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
        state.target_rpm = None
        state.available_power = None
    state.previous_mode = state.mode

    material_types = list_material_types(config_path=materials_config_path)
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

    tool, engagement_label_key = _prompt_tool(
        sub_operation, state, materials_config_path, locale, display_locale
    )
    if tool is None:
        return
    state.tool = tool

    if not _prompt_geometry(state, engagement_label_key, labels, locale):
        return

    if not _prompt_power_or_rpm(state, labels, locale):
        return

    result = _calculate(sub_operation, state, materials_config_path, locale)
    forms.show_result(result, labels, locale)


def _prompt_power_or_rpm(state: MillingSessionState, labels: dict[str, str], locale: str) -> bool:
    """The mode-dependent power/RPM screen(s); returns False on cancel.

    Extracted from `run_milling_screen` (Constitution Principle I /
    complexity gate) -- mirrors drilling.py's identically-shaped helper.
    """

    title = translate(locale, "tui.milling.title")

    if state.mode is CalculationMode.POWER_CONSTRAINED:
        power = _prompt_required_power(labels, state, locale)
        if power is None:
            return False
        state.available_power = power
        return True

    if state.mode is CalculationMode.FIXED_RPM:
        target_rpm = _prompt_target_rpm(state, locale)
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


def _calculate(
    sub_operation: MillingSubOperation,
    state: MillingSessionState,
    materials_config_path: str | None,
    locale: str,
):
    """Dispatch to `calculate_end_milling`/`calculate_face_milling` with the
    resolved inputs. Extracted from `run_milling_screen` (complexity gate)."""

    inputs = _resolved(state)
    if sub_operation is MillingSubOperation.END_MILLING:
        return calculate_end_milling(
            diameter=inputs.diameter,
            axial_depth_of_cut=inputs.axial_depth_of_cut,
            radial_depth_of_cut=inputs.radial_engagement,
            feed_per_tooth=inputs.feed_per_tooth,
            number_of_teeth=inputs.number_of_teeth,
            length_of_cut=inputs.length_of_cut,
            material=inputs.material,
            tool=inputs.tool,
            unit_system=state.unit_system,
            available_power=state.available_power,
            locale=locale,
            mode=state.mode,
            target_rpm=state.target_rpm,
            materials_config_path=materials_config_path,
        )
    return calculate_face_milling(
        diameter=inputs.diameter,
        axial_depth_of_cut=inputs.axial_depth_of_cut,
        width_of_cut=inputs.radial_engagement,
        feed_per_tooth=inputs.feed_per_tooth,
        number_of_teeth=inputs.number_of_teeth,
        length_of_cut=inputs.length_of_cut,
        material=inputs.material,
        tool=inputs.tool,
        unit_system=state.unit_system,
        available_power=state.available_power,
        locale=locale,
        mode=state.mode,
        target_rpm=state.target_rpm,
        materials_config_path=materials_config_path,
    )


def _prompt_geometry(
    state: MillingSessionState, engagement_label_key: str, labels: dict[str, str], locale: str
) -> bool:
    """Prompt the six milling geometry inputs; returns False on cancel."""

    unit_system = state.unit_system
    title = translate(locale, "tui.milling.title")

    diameter = forms.ask_number(
        title=title,
        label=translate(locale, "tui.label.mill_diameter"),
        unit=labels["diameter"],
        default=state.diameter,
        locale=locale,
        validate=lambda mm: validate_mill_diameter_mm(
            _to_mm(mm, unit_system), _DEFAULT_CONFIG, DEFAULT_LOCALE
        ),
    )
    if diameter is None:
        return False
    state.diameter = diameter

    axial = forms.ask_number(
        title=title,
        label=translate(locale, "cli.label.axial_depth_of_cut"),
        unit=labels["depth"],
        default=state.axial_depth_of_cut,
        locale=locale,
        validate=lambda mm: validate_depth_of_cut_mm(
            _to_mm(mm, unit_system), _DEFAULT_CONFIG, DEFAULT_LOCALE, "cli.label.axial_depth_of_cut"
        ),
    )
    if axial is None:
        return False
    state.axial_depth_of_cut = axial

    diameter_mm = _to_mm(state.diameter, unit_system)
    engagement = forms.ask_number(
        title=title,
        label=translate(locale, engagement_label_key),
        unit=labels["depth"],
        default=state.radial_engagement,
        locale=locale,
        validate=lambda mm: (
            validate_depth_of_cut_mm(
                _to_mm(mm, unit_system), _DEFAULT_CONFIG, DEFAULT_LOCALE, engagement_label_key
            )
            or validate_engagement_mm(
                _to_mm(mm, unit_system), diameter_mm, DEFAULT_LOCALE, engagement_label_key
            )
        ),
    )
    if engagement is None:
        return False
    state.radial_engagement = engagement

    feed = forms.ask_number(
        title=title,
        label=translate(locale, "tui.label.feed_per_tooth"),
        unit=labels["feed_per_tooth"],
        default=state.feed_per_tooth,
        locale=locale,
        validate=lambda mm: validate_feed_per_tooth_mm(_to_mm(mm, unit_system), DEFAULT_LOCALE),
    )
    if feed is None:
        return False
    state.feed_per_tooth = feed

    teeth = forms.ask_number(
        title=title,
        label=translate(locale, "tui.label.number_of_teeth"),
        unit=translate(locale, "tui.unit.teeth"),
        default=state.number_of_teeth,
        locale=locale,
        # Tooth count is a pure count, never unit-converted.
        validate=lambda value: validate_tooth_count(value, DEFAULT_LOCALE),
    )
    if teeth is None:
        return False
    state.number_of_teeth = teeth

    length = forms.ask_number(
        title=title,
        label=translate(locale, "tui.label.length_of_cut"),
        unit=labels["depth"],
        default=state.length_of_cut,
        locale=locale,
        validate=lambda mm: validate_length_of_cut_mm(
            _to_mm(mm, unit_system), _DEFAULT_CONFIG, DEFAULT_LOCALE
        ),
    )
    if length is None:
        return False
    state.length_of_cut = length
    return True


def _prompt_required_power(
    labels: dict[str, str], state: MillingSessionState, locale: str
) -> float | None:
    while True:
        value = forms.ask_number(
            title=translate(locale, "tui.milling.title"),
            label=translate(locale, "tui.label.power_required"),
            unit=labels["power"],
            default=state.available_power,
            locale=locale,
        )
        if value is None:
            return None
        if math.isfinite(value) and value > 0:
            return value


def _prompt_target_rpm(state: MillingSessionState, locale: str) -> float | None:
    while True:
        value = forms.ask_number(
            title=translate(locale, "tui.milling.title"),
            label=translate(locale, "tui.label.target_rpm"),
            unit="RPM",
            default=state.target_rpm,
            locale=locale,
        )
        if value is None:
            return None
        if math.isfinite(value) and value > 0:
            return value


@dataclass(frozen=True)
class _ResolvedMillingInputs:
    """A fully-answered milling input set, ready to pass to the library.
    Ported from `console/cli.py`'s identically-named class (research.md #3)."""

    material: str
    tool: str
    diameter: float
    axial_depth_of_cut: float
    radial_engagement: float
    feed_per_tooth: float
    number_of_teeth: float
    length_of_cut: float


def _resolved(state: MillingSessionState) -> _ResolvedMillingInputs:
    """Fully-answered geometry/material/tool, per `_MillingSessionState.resolved`."""

    return _ResolvedMillingInputs(
        material=cast(str, state.material),
        tool=cast(str, state.tool),
        diameter=cast(float, state.diameter),
        axial_depth_of_cut=cast(float, state.axial_depth_of_cut),
        radial_engagement=cast(float, state.radial_engagement),
        feed_per_tooth=cast(float, state.feed_per_tooth),
        number_of_teeth=cast(float, state.number_of_teeth),
        length_of_cut=cast(float, state.length_of_cut),
    )
