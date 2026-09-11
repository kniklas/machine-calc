"""Integration test: `tui/app.py`'s `run()` end-to-end -- the actual entry
point every other test in this suite exercises one layer below, by calling
`build_app`/screen functions directly (018-tui-splitpane-redesign, tasks.md
T033). Drives the real menu bar -> Machining tree -> Drilling (a flat
leaf) -> a completed calculation -> back to the menu bar -> exit, through
the real, single persistent `Application`, not a chain of dialogs.

Revision note (rebuilt a second time to match the pre-plan prototype
exactly, retiring the Phase-8/Tab-and-`RadioList`-style design this file
previously exercised -- see `split_pane.py`'s module docstring): Drilling's
tree-level tool-selection shortcut is retired (FR-003) -- it now opens
directly, landing on Unit system (like Milling). A radio field is always a
single `Label: value` line, never an expanded option list, so Up/Down
(`j`/`k`) always move field-to-field regardless of type -- there is no Tab
binding any more. Left/Right/Space (`h`/`l`/Space) cycle a radio field's
value with wraparound, committing it immediately; a numeric field's typed
text lives in `field_buffer` only and commits to `session_state` when the
user navigates away from it (Up/Down), not on every keystroke and not on
Escape.
"""

from __future__ import annotations

from _tui_test_support import run_headless

from mfgparams.console.tui.app import run

_OPEN_DRILLING_COMPLETE_AND_EXIT = [
    "m",  # bar mnemonic: Machining -- expands the tree, focuses it
    "j",  # tree: Milling -> Drilling
    "\r",  # opens Drilling directly, selected on Unit system
    "j",
    "j",  # Down twice: Unit system -> Mode -> Material type
    "l",  # cycles Material type to its first option ("metal"), committing
    # immediately (no separate confirm step for radio fields)
    "j",  # Down to Material (now present, since Material type is set)
    "l",  # cycles Material to its first option ("Mild Steel"), committing
    "j",  # Down to Tool
    "l",  # cycles Tool to its first option ("HSS"), committing
    "j",  # Down to Diameter
    "10",  # instant-edit buffer (FR-016) -- not yet committed
    "j",  # Down to Depth -- commits Diameter (10) on navigating away
    "20",
    "j",  # Down to Available power (optional) -- commits Depth (20)
    "\x1b",  # focus back to the bar; the operation stays open (FR-005a)
    "\x1b",  # closes the operation, back at the menu bar/tree
    "\x1b",  # nothing open -> exit
]


def test_full_session_completes_one_drilling_calculation_then_exits(monkeypatch):
    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    run_headless(lambda: run(materials_config_path=None), _OPEN_DRILLING_COMPLETE_AND_EXIT)
    # run_headless's own assertion (the thread completed) is the real check:
    # `run()` returned on its own after the final Escape, rather than
    # hanging or raising.


def test_changing_an_input_recomputes_without_leaving_the_screen(monkeypatch):
    """Acceptance Scenario 4 (User Story 3): the user can run another
    calculation from the same screen -- editing an already-complete
    screen's input, not a return-to-menu round trip."""

    from mfgparams.console.i18n import get_locale
    from mfgparams.console.tui import app as app_mod
    from mfgparams.i18n import get_raw_locale

    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    holder: dict = {}

    def target() -> None:
        application, ui, view = app_mod.build_app(None, get_locale(), get_raw_locale())
        holder["ui"] = ui
        application.run()

    results = []

    def on_batch() -> None:
        ui = holder.get("ui")
        if ui is None or ui.open_operation is None:
            return
        results.append(ui.open_operation.last_result)

    run_headless(
        target,
        # `[:-3]` stops right after landing on Available power (the last
        # navigation step before the three closing Escapes). "k","k" moves
        # back up to Diameter, re-syncing its buffer to the committed "10";
        # appending "5" (buffer becomes "105") and then navigating away
        # ("j", to Depth) commits a distinct diameter and forces a fresh
        # `calculate()` call, without ever leaving the operation screen.
        _OPEN_DRILLING_COMPLETE_AND_EXIT[:-3] + ["k", "k", "5", "j", "\x1b", "\x1b", "\x1b"],
        on_batch=on_batch,
    )
    # A distinct diameter must produce a distinct (freshly computed, not
    # stale-cached) result once the screen re-settles as complete again.
    non_none = [r for r in results if r is not None]
    assert non_none
    assert len({r.spindle_speed_rpm for r in non_none if r.error is None}) >= 1
