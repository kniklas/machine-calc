"""Integration test: numeric-field instant-edit and Left/Right nudge
(018-tui-splitpane-redesign FR-016/FR-017, tasks.md T016).

Drives `screens.split_pane`'s edit/nudge functions directly against a real
Drilling screen's rows -- the same functions `app.py`'s key bindings call.
"""

from __future__ import annotations

from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import DrillingSessionState, rows_for


def _screen() -> OperationScreen:
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    split_pane.sync_buffer(rows_for(screen, None, "en", "en"), screen)
    return screen


def _rows(screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(screen, None, "en", "en")


def _goto(screen: OperationScreen, field_id: FieldId) -> None:
    rows = _rows(screen)
    ids = [row.field_id for row in rows]
    screen.selected_field = field_id
    assert field_id in ids
    split_pane.sync_buffer(rows, screen)


def test_typing_a_digit_immediately_edits_with_no_separate_start_editing_action():
    """FR-016."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "1")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter == 1.0

    split_pane.edit_selected(_rows(screen), screen, "5")
    assert state.diameter == 15.0


def test_backspace_edits_the_field_immediately_too():
    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "1")
    split_pane.edit_selected(_rows(screen), screen, "5")
    split_pane.backspace_selected(_rows(screen), screen)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter == 1.0


def test_left_right_nudges_a_numeric_field_by_the_fixed_step():
    """FR-017."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter == split_pane.NUDGE_STEP

    split_pane.nudge_selected(_rows(screen), screen, 1)
    assert state.diameter == 2 * split_pane.NUDGE_STEP

    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert state.diameter == split_pane.NUDGE_STEP


def test_nudging_at_or_below_zero_clears_the_field_rather_than_going_negative():
    """Contract §4's implementation detail."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    split_pane.nudge_selected(_rows(screen), screen, -1)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter is None

    # Nudging down from unset stays unset (never goes negative).
    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert state.diameter is None


def test_left_right_cycles_a_radio_field_rather_than_nudging():
    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "imperial"

    split_pane.nudge_selected(_rows(screen), screen, 1)
    assert state.unit_system.value == "metric"  # wraps


def test_selecting_a_field_syncs_the_buffer_to_its_current_value():
    """Landing on a field shows what's already there, so a user can
    backspace to edit an existing value rather than only ever overwriting
    blindly."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "7")
    _goto(screen, FieldId.DEPTH)
    _goto(screen, FieldId.DIAMETER)
    assert screen.field_buffer == "7"
