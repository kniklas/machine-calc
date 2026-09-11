"""Integration test: numeric-field buffered edit/nudge and radio-field
cycle-and-commit navigation (018-tui-splitpane-redesign FR-016/FR-017/
FR-005, tasks.md T016, rewritten a second time to match the pre-plan
prototype exactly -- see `split_pane.py`'s module docstring for why).

Drives `screens.split_pane`'s edit/nudge/move functions directly against a
real Drilling screen's rows -- the same functions `app.py`'s key bindings
call.

Governing behaviors (matching the prototype's own code, not the
Phase-8/`RadioList`-style two-step interaction this file previously
tested):

- A radio field is a single `Label: value` line. Left/Right/Space cycle its
  value with wraparound and commit it *immediately* via `on_select` -- no
  separate highlight/confirm step, no more `radio_navigate`/`radio_commit`.
- Up/Down (`move_selection`) always moves between fields, unconditionally.
- A numeric field's typed/nudged text lives in `field_buffer` only.
  `session_state` is untouched until the user navigates away from the
  field (`move_selection`, which calls `_commit_current` first).
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
    """Jumps directly to a field with nothing pending -- used only for
    initial setup in these tests, not to simulate a mid-edit Up/Down (that
    commit path is `move_selection`, exercised explicitly below)."""

    rows = _rows(screen)
    ids = [row.field_id for row in rows]
    screen.selected_field = field_id
    assert field_id in ids
    split_pane.sync_buffer(rows, screen)


def test_typing_a_digit_edits_the_buffer_without_committing_until_navigating_away():
    """FR-016."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "1")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert screen.field_buffer == "1"
    assert state.diameter is None  # not yet committed

    split_pane.edit_selected(_rows(screen), screen, "5")
    assert screen.field_buffer == "15"
    assert state.diameter is None  # still not committed

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    assert state.diameter == 15.0


def test_backspace_edits_the_buffer_too():
    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "1")
    split_pane.edit_selected(_rows(screen), screen, "5")
    split_pane.backspace_selected(_rows(screen), screen)
    assert screen.field_buffer == "1"

    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter is None  # still uncommitted

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    assert state.diameter == 1.0


def test_left_right_nudges_a_numeric_fields_buffer_without_committing_until_navigating_away():
    """FR-017."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    assert screen.field_buffer == "1"
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter is None  # still uncommitted

    split_pane.nudge_selected(_rows(screen), screen, 1)
    assert screen.field_buffer == "2"

    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert screen.field_buffer == "1"

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    assert state.diameter == split_pane.NUDGE_STEP


def test_nudging_at_or_below_zero_clears_the_buffer_rather_than_going_negative():
    """Contract §4's implementation detail."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert screen.field_buffer == ""

    # Nudging down from unset stays unset (never goes negative).
    split_pane.nudge_selected(_rows(screen), screen, -1)
    assert screen.field_buffer == ""

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter is None


def test_left_right_cycles_a_radio_field_and_commits_it_immediately():
    """Matches the prototype's `cycle_field`: no buffering, no separate
    confirm step -- Left/Right/Space on a radio field commits right away."""

    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    split_pane.nudge_selected(_rows(screen), screen, 1)

    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "imperial"


def test_radio_cycle_wraps_at_the_boundary_rather_than_clamping():
    """`unit_system` has exactly two options; cycling past either end wraps
    around rather than clamping (matching the prototype's modulo
    arithmetic, unlike a `RadioList`'s own clamped navigation)."""

    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "metric"

    split_pane.nudge_selected(_rows(screen), screen, -1)  # wraps backward past the start
    assert state.unit_system.value == "imperial"

    split_pane.nudge_selected(_rows(screen), screen, 1)  # wraps forward back to the start
    assert state.unit_system.value == "metric"


def test_up_down_always_moves_between_fields_regardless_of_row_type():
    """Up/Down (`move_selection`) is unconditional -- no per-field-type
    dispatch, unlike the retired Tab/Shift-Tab-vs-Up/Down split."""

    screen = _screen()
    rows = _rows(screen)
    ids = [row.field_id for row in rows]
    assert screen.selected_field is FieldId.UNIT_SYSTEM

    split_pane.move_selection(rows, screen, 1, "en")
    assert screen.selected_field == ids[1]

    split_pane.move_selection(_rows(screen), screen, -1, "en")
    assert screen.selected_field is FieldId.UNIT_SYSTEM


def test_move_selection_commits_the_pending_numeric_edit_before_moving_away():
    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "7")

    split_pane.move_selection(_rows(screen), screen, 1, "en")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.diameter == 7.0


def test_selecting_a_field_syncs_the_buffer_to_its_committed_value():
    """Landing on a field shows what's already committed, so a user can
    backspace to edit an existing value rather than only ever overwriting
    blindly."""

    screen = _screen()
    _goto(screen, FieldId.DIAMETER)
    split_pane.edit_selected(_rows(screen), screen, "7")
    split_pane.move_selection(_rows(screen), screen, 1, "en")  # commits 7.0, moves to DEPTH
    split_pane.move_selection(_rows(screen), screen, -1, "en")  # moves back to DIAMETER
    assert screen.field_buffer == "7"
