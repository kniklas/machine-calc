"""Integration test: numeric-field instant-edit/nudge and RadioList
navigation (018-tui-splitpane-redesign FR-016/FR-017/FR-005, tasks.md
T016, rewritten again for the revision at tasks.md T044/Phase 8).

Drives `screens.split_pane`'s edit/nudge/radio functions directly against a
real Drilling screen's rows -- the same functions `app.py`'s key bindings
call.

Revision note: radio fields no longer cycle their value on Left/Right
(that behavior is retired, research.md #4). They now match
`prompt_toolkit.widgets.RadioList`'s own two-step interaction: Up/Down
(`radio_navigate`) moves a *highlighted* option without committing it --
mirrored in `field_buffer`, reusing the same "not-yet-committed state of
the selected field" role it already plays for numeric fields -- and
Enter/Space (`radio_commit`) commits the highlighted option into
`session_state`. Navigating away without committing leaves the field's
previously-committed value untouched, unlike `NumberRow`'s
commit-on-every-keystroke.
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


def test_left_right_does_not_touch_a_radio_field():
    """research.md #4: Left/Right no longer cycles a radio field's value
    -- that's now Up/Down's job (`radio_navigate`), and only once
    committed (`radio_commit`)."""

    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    split_pane.nudge_selected(_rows(screen), screen, 1)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "metric"  # unchanged -- Left/Right is a no-op here


def test_up_down_highlights_a_radio_option_without_committing_it():
    """`radio_navigate` moves the highlighted option (mirrored in
    `field_buffer`) but does not touch `session_state` until
    `radio_commit`."""

    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    assert screen.field_buffer == "metric"  # starts highlighted on the current value

    split_pane.radio_navigate(_rows(screen), screen, 1)
    assert screen.field_buffer == "imperial"
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "metric"  # still uncommitted


def test_radio_navigate_clamps_at_the_boundary_rather_than_escaping_the_field():
    """Up/Down past the first/last option clamps, matching a real
    `RadioList`'s own behavior -- it never escapes to an adjacent field on
    further Up/Down (that's Tab/Shift-Tab's job instead, research.md #4)."""

    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    # unit_system has exactly two options (metric, imperial); starting on
    # "metric" (index 0), moving backward is already at the boundary.
    split_pane.radio_navigate(_rows(screen), screen, -1)
    assert screen.field_buffer == "metric"  # clamped, unchanged

    split_pane.radio_navigate(_rows(screen), screen, 1)
    assert screen.field_buffer == "imperial"
    split_pane.radio_navigate(_rows(screen), screen, 1)  # past the last option
    assert screen.field_buffer == "imperial"  # clamped, not wrapped back to "metric"


def test_enter_or_space_commits_the_highlighted_radio_option():
    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    split_pane.radio_navigate(_rows(screen), screen, 1)
    split_pane.radio_commit(_rows(screen), screen)

    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "imperial"


def test_navigating_away_without_committing_leaves_the_radio_field_unchanged():
    screen = _screen()
    _goto(screen, FieldId.UNIT_SYSTEM)
    split_pane.radio_navigate(_rows(screen), screen, 1)  # highlight "imperial", don't commit
    _goto(screen, FieldId.MODE)  # move away without pressing Enter/Space

    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system.value == "metric"  # untouched


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
