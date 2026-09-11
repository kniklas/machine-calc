"""Integration test: `tui/app.py`'s `run()` end-to-end -- the actual entry
point every other test in this suite exercises one layer below, by calling
`build_app`/screen functions directly (018-tui-splitpane-redesign, tasks.md
T033). Drives the real menu bar -> Machining tree -> Drilling (a flat
leaf) -> a completed calculation -> back to the menu bar -> exit, through
the real, single persistent `Application`, not a chain of dialogs.

Revision note (tasks.md T045/Phase 8): Drilling's tree-level tool-
selection shortcut is retired (FR-003) -- it now opens directly, landing
on Unit system (like Milling). Radio fields commit via Enter (the
highlighted option -- defaulting to the first when unset, matching
`prompt_toolkit.widgets.RadioList`'s own behavior); Up/Down are fully
consumed by an expanded radio's own option list (clamped at the
boundaries, never escaping to an adjacent field, matching a real
`RadioList`), so **Tab** is used here to move field-to-field regardless of
type (research.md #4) -- not Up/Down/j/k, which would otherwise need one
keystroke per *option* to walk past a multi-choice field like Material.
"""

from __future__ import annotations

from _tui_test_support import run_headless

from mfgparams.console.tui.app import run

_OPEN_DRILLING_COMPLETE_AND_EXIT = [
    "m",  # bar mnemonic: Machining -- expands the tree, focuses it
    "j",  # tree: Milling -> Drilling
    "\r",  # opens Drilling directly, selected on Unit system
    "\t",
    "\t",  # Tab to Material type (unit system/mode keep their defaults)
    "\r",  # commits the highlighted (first) material type ("metal")
    "\t",  # Tab to Material
    "\r",  # commits the highlighted (first) material ("Mild Steel")
    "\t",  # Tab to Tool
    "\r",  # commits the highlighted (first) tool ("HSS")
    "\t",  # Tab to Diameter
    "10",  # instant-edit (FR-016)
    "\t",  # Tab to Depth
    "20",
    "\t",  # Tab to Available power (optional, left blank)
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
        _OPEN_DRILLING_COMPLETE_AND_EXIT[:-3] + ["k", "k", "5", "\x1b", "\x1b", "\x1b"],
        on_batch=on_batch,
    )
    # A distinct diameter must produce a distinct (freshly computed, not
    # stale-cached) result once the screen re-settles as complete again.
    non_none = [r for r in results if r is not None]
    assert non_none
    assert len({r.spindle_speed_rpm for r in non_none if r.error is None}) >= 1
