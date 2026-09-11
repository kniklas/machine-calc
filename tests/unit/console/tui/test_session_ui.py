"""Unit tests for SessionUI's tree/open_operation independence
(018-tui-splitpane-redesign, data-model.md, tasks.md T005).

FR-005a's invariant: collapsing/expanding the Machining tree never changes
which operation screen is open, and vice versa. These tests exercise the
data model's own structure -- nothing here couples the two fields -- not
yet the full application (that's tasks.md T018's integration test, once
`app.py`'s actual navigation handlers exist).
"""

from __future__ import annotations

from mfgparams.console.tui.app import (
    FieldId,
    MachiningTree,
    MenuBar,
    OperationScreen,
    SessionUI,
)
from mfgparams.console.tui.menu import MenuEntry
from mfgparams.console.tui.screens.drilling import DrillingSessionState


def _menu_bar() -> MenuBar:
    return MenuBar(entries=(MenuEntry("exit", "Exit"),))


def test_open_operation_defaults_to_none_with_a_fresh_tree():
    ui = SessionUI(menu_bar=_menu_bar())
    assert ui.open_operation is None
    assert ui.tree == MachiningTree()


def test_expanding_the_tree_does_not_touch_an_open_operation():
    ui = SessionUI(menu_bar=_menu_bar())
    screen = OperationScreen(
        operation="drilling",
        session_state=ui.drilling_state,
        selected_field=FieldId.UNIT_SYSTEM,
    )
    ui.open_operation = screen

    ui.tree.toggle_machining()

    assert ui.open_operation is screen
    assert ui.open_operation.selected_field is FieldId.UNIT_SYSTEM


def test_collapsing_the_tree_does_not_close_an_open_operation():
    """The specific regression FR-005a exists to guard against: a tree
    collapse must never be the thing that closes an operation screen. Now
    trivially true (research.md #3) -- the floating window isn't part of
    the tree's own container at all -- but still exercised at the data
    level here."""

    ui = SessionUI(menu_bar=_menu_bar())
    screen = OperationScreen(
        operation="drilling",
        session_state=ui.drilling_state,
        selected_field=FieldId.TOOL,
    )
    ui.tree.toggle_machining()
    ui.open_operation = screen

    ui.tree.toggle_machining()  # collapses the whole tree

    assert ui.tree.expanded is False
    assert ui.open_operation is screen


def test_returning_to_the_menu_does_not_touch_the_tree_state():
    """Acceptance Scenario 5: returning to the main menu leaves the tree
    'not necessarily still expanded to the same leaf' -- i.e. untouched,
    not forcibly collapsed either."""

    ui = SessionUI(menu_bar=_menu_bar())
    ui.tree.toggle_machining()
    ui.open_operation = OperationScreen(
        operation="drilling",
        session_state=ui.drilling_state,
        selected_field=FieldId.DIAMETER,
    )

    ui.open_operation = None  # "return to the main menu"

    assert ui.open_operation is None
    assert ui.tree.expanded is True


def test_drilling_state_and_milling_states_persist_independently_of_open_operation():
    """FR-012's carryover guarantee: the session-lifetime state objects are
    not owned by whichever OperationScreen happens to be open right now."""

    ui = SessionUI(menu_bar=_menu_bar())
    ui.drilling_state.diameter = 12.5
    ui.open_operation = OperationScreen(
        operation="drilling",
        session_state=ui.drilling_state,
        selected_field=FieldId.DEPTH,
    )
    ui.open_operation = None

    assert ui.drilling_state.diameter == 12.5
    assert isinstance(ui.drilling_state, DrillingSessionState)
