"""Integration test: the Milling operation screen, both sub-operations
(018-tui-splitpane-redesign US2, tasks.md T015).

Same "call the row closures directly" approach as `test_tui_drilling.py` --
see that file's module docstring for why.
"""

from __future__ import annotations

from mfgparams import (
    CalculationMode,
    MillingSubOperation,
    UnitSystem,
    calculate_end_milling,
    calculate_face_milling,
)
from mfgparams.console.tui.app import FieldId, OperationScreen, SessionUI
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.milling import MillingSessionState, calculate_result, rows_for


def _ui() -> SessionUI:
    from mfgparams.console.tui.app import MenuBar

    return SessionUI(menu_bar=MenuBar(entries=()))


def _screen(
    ui: SessionUI, sub_operation: MillingSubOperation = MillingSubOperation.END_MILLING
) -> OperationScreen:
    return OperationScreen(
        operation="milling",
        session_state=ui.milling_states[sub_operation],
        selected_field=FieldId.UNIT_SYSTEM,
    )


def _rows(ui: SessionUI, screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(ui, screen, None, "en", "en")


def _row(rows: list[split_pane.Row], field_id: FieldId) -> split_pane.Row:
    return next(row for row in rows if row.field_id is field_id)


def _fill_end_milling(ui: SessionUI, screen: OperationScreen) -> None:
    _row(_rows(ui, screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(ui, screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(ui, screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(ui, screen), FieldId.DIAMETER).on_edit("10")
    _row(_rows(ui, screen), FieldId.AXIAL_DEPTH_OF_CUT).on_edit("2")
    _row(_rows(ui, screen), FieldId.RADIAL_ENGAGEMENT).on_edit("1")
    _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH).on_edit("0.05")
    _row(_rows(ui, screen), FieldId.NUMBER_OF_TEETH).on_edit("4")
    _row(_rows(ui, screen), FieldId.LENGTH_OF_CUT).on_edit("50")


def test_every_fr005_field_is_visible_simultaneously_without_a_screen_transition():
    """Acceptance Scenario 4 -- the same simultaneous-input pattern applies
    to Milling's own inputs."""

    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    field_ids = {row.field_id for row in _rows(ui, screen)}
    assert field_ids == {
        FieldId.UNIT_SYSTEM,
        FieldId.MODE,
        FieldId.SUB_OPERATION,
        FieldId.MATERIAL_TYPE,
        FieldId.MATERIAL,
        FieldId.TOOL,
        FieldId.DIAMETER,
        FieldId.AXIAL_DEPTH_OF_CUT,
        FieldId.RADIAL_ENGAGEMENT,
        FieldId.FEED_PER_TOOTH,
        FieldId.NUMBER_OF_TEETH,
        FieldId.LENGTH_OF_CUT,
        FieldId.AVAILABLE_POWER,
    }


def test_end_milling_reaches_a_result_matching_the_core_calculation():
    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    assert result.error is None

    expected = calculate_end_milling(
        diameter=10.0,
        axial_depth_of_cut=2.0,
        radial_depth_of_cut=1.0,
        feed_per_tooth=0.05,
        number_of_teeth=4.0,
        length_of_cut=50.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.STANDARD,
        target_rpm=None,
    )
    assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_selecting_face_milling_swaps_to_its_own_independent_session_state():
    """FR-009a: the End-Milling/Face-Milling choice is a left-pane field;
    switching it swaps `OperationScreen.session_state` in place, and each
    sub-operation keeps its own answers independently (FR-002 parity)."""

    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    end_milling_state = screen.session_state

    _row(_rows(ui, screen), FieldId.SUB_OPERATION).on_select(MillingSubOperation.FACE_MILLING.value)
    assert screen.session_state is ui.milling_states[MillingSubOperation.FACE_MILLING]
    assert screen.session_state is not end_milling_state
    # Switching back offers the still-intact End-Milling answers.
    _row(_rows(ui, screen), FieldId.SUB_OPERATION).on_select(MillingSubOperation.END_MILLING.value)
    assert screen.session_state is end_milling_state
    assert screen.session_state.diameter == 10.0


def test_face_milling_reaches_a_result_matching_the_core_calculation():
    ui = _ui()
    screen = _screen(ui, MillingSubOperation.FACE_MILLING)
    _row(_rows(ui, screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(ui, screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(ui, screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(ui, screen), FieldId.DIAMETER).on_edit("50")
    _row(_rows(ui, screen), FieldId.AXIAL_DEPTH_OF_CUT).on_edit("2")
    _row(_rows(ui, screen), FieldId.RADIAL_ENGAGEMENT).on_edit("30")
    _row(_rows(ui, screen), FieldId.FEED_PER_TOOTH).on_edit("0.1")
    _row(_rows(ui, screen), FieldId.NUMBER_OF_TEETH).on_edit("6")
    _row(_rows(ui, screen), FieldId.LENGTH_OF_CUT).on_edit("100")
    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    assert split_pane.is_complete(_rows(ui, screen))

    result = calculate_result(ui, state, None, "en")
    assert result.error is None

    expected = calculate_face_milling(
        diameter=50.0,
        axial_depth_of_cut=2.0,
        width_of_cut=30.0,
        feed_per_tooth=0.1,
        number_of_teeth=6.0,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.STANDARD,
        target_rpm=None,
    )
    assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_revisiting_the_same_sub_operation_offers_prior_answers_as_defaults():
    """SC-005/FR-002 parity."""

    ui = _ui()
    screen = _screen(ui)
    _fill_end_milling(ui, screen)
    first_diameter = ui.milling_states[MillingSubOperation.END_MILLING].diameter

    # A fresh OperationScreen re-opened onto the same, already-populated
    # state (mirrors app.py's `_open_milling` reuse) sees the same values.
    reopened = OperationScreen(
        operation="milling",
        session_state=ui.milling_states[MillingSubOperation.END_MILLING],
        selected_field=FieldId.UNIT_SYSTEM,
    )
    assert reopened.session_state.diameter == first_diameter
