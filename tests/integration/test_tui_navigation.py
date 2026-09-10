"""Integration test: headless navigation shell -- menu bar + Machining tree
(018-tui-splitpane-redesign, spec.md User Story 1, tasks.md T009).

017's `test_tui_app_run.py` drove `NavigationState` push/pop directly, which
no longer exists in that shape (data-model.md's `SessionUI` replaces it);
this drives the real, single persistent `Application` (`app.build_app`)
headlessly instead, using `_tui_test_support.run_headless`'s `on_batch` hook
(research.md #2) to inspect `SessionUI`/`_ViewState` between keystrokes.

Note: the bar's *first* entry is Exit (contract's fixed order), so a bare
Enter at startup exits immediately -- every scenario below reaches
Machining via its mnemonic jump key ("m", `app.py`'s per-character bar
bindings) rather than arrow-then-Enter.

`run_headless`'s `on_batch` fires once *before* each send (capturing the
state settled by every prior batch -- including one initial call before
anything has been sent at all) plus once more after the final batch
settles. So N key_batches yield N+1 snapshots, and `snapshots[i]` is the
state after exactly `i` batches have been applied (`snapshots[0]` is the
pristine startup state).
"""

from __future__ import annotations

from _tui_test_support import run_headless

import mfgparams.console.tui.app as app_mod
from mfgparams.console.i18n import get_locale
from mfgparams.i18n import get_raw_locale


def _drive(key_batches: list[str]) -> list[tuple]:
    """Runs the real app headlessly, returning one snapshot per settled
    batch: ``(body_mode, tree.expanded, tree.drilling_expanded,
    open_operation is not None)``."""

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["ui"] = ui
        holder["view"] = view
        app.run()

    snapshots: list[tuple] = []

    def on_batch() -> None:
        ui = holder.get("ui")
        view = holder.get("view")
        if ui is None:
            return
        snapshots.append(
            (view.body_mode, ui.tree.expanded, ui.tree.drilling_expanded, ui.open_operation is not None)
        )

    run_headless(target, key_batches, on_batch=on_batch)
    return snapshots


def test_initial_state_shows_nothing_open():
    """Acceptance Scenario 1: the bar is visible on launch, with nothing
    else selected yet -- escape at the root (nothing open) exits."""

    snapshots = _drive(["\x1b"])
    assert snapshots[0] == (None, False, False, False)


def test_selecting_machining_expands_the_tree():
    """Acceptance Scenario 2: the "m" mnemonic jumps to and activates
    Machining directly from the bar."""

    snapshots = _drive(["m", "\x1b", "\x1b"])
    assert snapshots[1] == ("tree", True, False, False)


def test_selecting_drilling_expands_its_tool_shortcut():
    """Acceptance Scenario 3."""

    snapshots = _drive(["m", "j", "\r", "\x1b", "\x1b"])
    # m: expand Machining, focus tree (row 0 = Milling); j: move to
    # Drilling (row 1); Enter: toggle its shortcut expansion.
    assert snapshots[3][2] is True


def test_collapsing_machining_returns_to_its_collapsed_state():
    """Acceptance Scenario 4: re-collapsing loses the Drilling sub-
    expansion too (data-model.md's validation rule)."""

    snapshots = _drive(["m", "j", "\r", "\x1b", "m", "\x1b"])
    # m, j, Enter: expand Machining and Drilling's shortcut; escape: focus
    # back to bar; m again: re-select Machining from the bar, collapsing;
    # final escape: nothing open -> exit.
    assert snapshots[5] == (None, False, False, False)


def test_selecting_a_leaf_opens_the_corresponding_operation_screen():
    """Independent Test: a leaf selection opens the corresponding
    operation screen, independent of what that screen's panes contain."""

    snapshots = _drive(["m", "\r", "\x1b", "\x1b", "\x1b"])  # Machining, then Milling (row 0)
    assert any(s[0] == "milling" and s[3] is True for s in snapshots)


def test_drilling_tool_shortcut_opens_drilling_not_just_expands():
    snapshots = _drive(["m", "j", "\r", "j", "\r", "\x1b", "\x1b", "\x1b"])
    # m, j, Enter: expand Drilling's shortcut; j: move onto the now-visible
    # Tool row; Enter: opens Drilling (not just another toggle).
    assert any(s[0] == "drilling" and s[3] is True for s in snapshots)


def test_collapsing_the_tree_never_closes_an_open_operation():
    """FR-005a, quickstart.md Scenario 5 -- the specific regression this
    feature's own /speckit-clarify session exists to guard against."""

    snapshots = _drive(
        [
            "m",  # expand Machining, focus tree
            "\r",  # open Milling (row 0)
            "\x1b",  # focus back to bar; operation and tree state untouched
            "m",  # re-select Machining from the bar: collapses the tree
            "\x1b",  # on bar, operation still open -> this escape closes it
            "\x1b",  # on bar, nothing open -> exit
        ]
    )
    after_collapse = snapshots[4]
    assert after_collapse[1] is False  # tree collapsed
    assert after_collapse[3] is True  # operation still open


def test_reopening_drilling_preserves_its_state_across_a_tree_collapse():
    """The concrete, data-level version of the same guarantee: not just
    "still open", but the *same* OperationScreen (FR-012 carryover) --
    verified by identity and `selected_field`, not just re-checking
    is_open."""

    from mfgparams.console.tui.app import FieldId

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["ui"] = ui
        holder["view"] = view
        app.run()

    screens_seen = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None:
            return
        screens_seen.append(ui.open_operation)

    run_headless(
        target,
        ["m", "j", "\r", "j", "\r", "\x1b", "m", "\x1b", "\x1b"],
        on_batch=on_batch,
    )

    drilling_screens = [s for s in screens_seen if s.operation == "drilling"]
    assert drilling_screens, "Drilling was never opened"
    assert drilling_screens[0].selected_field is FieldId.TOOL
    # Every snapshot while Drilling was open is the *same* object -- the
    # tree toggle in between did not discard and recreate it.
    assert all(s is drilling_screens[0] for s in drilling_screens)
