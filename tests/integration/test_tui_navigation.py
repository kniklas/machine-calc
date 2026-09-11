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
bindings) rather than arrow-then-Enter. Pressing "m" a second time in a
row does *not* re-toggle Machining from the bar -- the first "m" already
moved focus onto the tree, so a second "m" is read as the tree's own
mnemonic for Milling instead (contract §4's per-level mnemonic
namespaces); getting back to the bar first needs an explicit Escape.

`run_headless`'s `on_batch` fires once *before* each send (capturing the
state settled by every prior batch -- including one initial call before
anything has been sent at all) plus once more after the final batch
settles. So N key_batches yield N+1 snapshots, and `snapshots[i]` is the
state after exactly `i` batches have been applied (`snapshots[0]` is the
pristine startup state).

Rewritten again (revision, tasks.md T043/Phase 8): Drilling's tree-level
tool-selection shortcut is retired (FR-003) -- both Milling and Drilling
are now flat leaves that open their floating window directly on Enter, no
intermediate toggle step. Snapshots drop `tree.drilling_expanded` (the
field no longer exists); `view.body_mode` no longer takes "drilling"/
"milling" values at all (the floating window is independent of it,
research.md #3), so which operation (if any) is open is read from
`ui.open_operation.operation` directly instead.
"""

from __future__ import annotations

from _tui_test_support import run_headless

import mfgparams.console.tui.app as app_mod
from mfgparams.console.i18n import get_locale
from mfgparams.i18n import get_raw_locale


def _drive(key_batches: list[str]) -> list[tuple]:
    """Runs the real app headlessly, returning one snapshot per settled
    batch: ``(body_mode, tree.expanded, open_operation_kind,
    open_operation is not None)`` -- ``open_operation_kind`` is
    ``ui.open_operation.operation`` (``"drilling"``/``"milling"``) or
    ``None``."""

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
            (
                view.body_mode,
                ui.tree.expanded,
                ui.open_operation.operation if ui.open_operation else None,
                ui.open_operation is not None,
            )
        )

    run_headless(target, key_batches, on_batch=on_batch)
    return snapshots


def test_initial_state_shows_nothing_open():
    """Acceptance Scenario 1: the bar is visible on launch, with nothing
    else selected yet -- escape at the root (nothing open) exits."""

    snapshots = _drive(["\x1b"])
    assert snapshots[0] == (None, False, None, False)


def test_selecting_machining_expands_the_tree():
    """Acceptance Scenario 2: the "m" mnemonic jumps to and activates
    Machining directly from the bar."""

    snapshots = _drive(["m", "\x1b", "\x1b"])
    assert snapshots[1] == ("tree", True, None, False)


def test_selecting_drilling_opens_its_floating_window_directly():
    """Acceptance Scenario 3, revised: Drilling is a flat leaf, exactly
    like Milling -- selecting it opens its floating window on Enter, no
    intermediate tree-level toggle."""

    snapshots = _drive(["m", "j", "\r", "\x1b", "\x1b", "\x1b"])
    # m: expand Machining, focus tree (row 0 = Milling); j: move to
    # Drilling (row 1); Enter: opens Drilling directly.
    assert any(s[2] == "drilling" and s[3] is True for s in snapshots)


def test_collapsing_machining_returns_to_its_collapsed_state():
    """Acceptance Scenario 4."""

    snapshots = _drive(["m", "\x1b", "m", "\x1b"])
    # m: expand, focus tree; escape: back to the bar (tree state
    # untouched -- escape alone never collapses); m: re-select Machining
    # from the bar, collapsing; final escape: nothing open -> exit (fast
    # enough that the trailing post-batch snapshot isn't reliably
    # captured, so check right after the collapse instead, at index 3).
    assert snapshots[3] == (None, False, None, False)


def test_selecting_a_leaf_opens_the_corresponding_operation_screen():
    """Independent Test: a leaf selection opens the corresponding
    operation screen, independent of what that screen's panes contain."""

    snapshots = _drive(["m", "\r", "\x1b", "\x1b", "\x1b"])  # Machining, then Milling (row 0)
    assert any(s[2] == "milling" and s[3] is True for s in snapshots)


def test_collapsing_the_tree_never_closes_an_open_operation():
    """FR-005a, quickstart.md Scenario 5 -- the specific regression this
    feature's own `/speckit-clarify` session exists to guard against. Now
    trivially true (research.md #3): the floating window isn't part of the
    tree's own container, so collapsing the tree cannot affect it."""

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
    verified by identity, not just re-checking is_open. Drilling now opens
    with the same default `selected_field` as Milling (`UNIT_SYSTEM`) --
    there is no more tree-shortcut-specific field to land on."""

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
        ["m", "j", "\r", "\x1b", "m", "\x1b", "\x1b"],
        on_batch=on_batch,
    )

    drilling_screens = [s for s in screens_seen if s.operation == "drilling"]
    assert drilling_screens, "Drilling was never opened"
    assert drilling_screens[0].selected_field is FieldId.UNIT_SYSTEM
    # Every snapshot while Drilling was open is the *same* object -- the
    # tree toggle in between did not discard and recreate it.
    assert all(s is drilling_screens[0] for s in drilling_screens)


def test_collapsing_the_tree_does_not_hide_tool_selection_from_the_left_pane():
    """018-tui-splitpane-redesign tasks.md T018/T043 -- contract §2's own
    invariant, checked at the exact granularity it's stated at: FR-005's
    tool-selection field (not just "some screen is open") must still be
    present and reachable in the left pane's row list once the tree is
    collapsed, since FR-005a's whole point is that it was never
    exclusively tree-resident in the first place."""

    from mfgparams.console.tui.app import FieldId
    from mfgparams.console.tui.screens.drilling import rows_for

    locale = get_locale()
    display_locale = get_raw_locale()
    holder: dict = {}

    def target() -> None:
        app, ui, view = app_mod.build_app(None, locale, display_locale)
        holder["ui"] = ui
        holder["view"] = view
        app.run()

    field_id_sets = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None or ui.open_operation.operation != "drilling":
            return
        rows = rows_for(ui.open_operation, None, locale, display_locale)
        field_id_sets.append({row.field_id for row in rows})

    run_headless(
        target,
        [
            "m",  # expand Machining, focus tree
            "j",  # Drilling row
            "\r",  # opens Drilling directly
            "\x1b",  # focus back to bar; Drilling stays open
            "m",  # re-select Machining from the bar: collapses the tree
            "\x1b",  # closes Drilling
            "\x1b",  # nothing open -> exit
        ],
        on_batch=on_batch,
    )

    assert field_id_sets, "Drilling was never open while inspected"
    assert all(
        FieldId.TOOL in ids for ids in field_id_sets
    ), "tool selection dropped out of the left pane's row list while the tree was collapsed"
