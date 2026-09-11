"""Integration test: a terminal resize mid-form-entry does not discard
already-entered input (018-tui-splitpane-redesign FR-013a, tasks.md T029).

**Scope note**: prompt-toolkit's `Application` redraws in place on a resize
(`_on_resize`) without touching widget/buffer state. 017's version of this
test exercised that mechanism against a short-lived, per-dialog
`Application` (`forms.ask_number`'s own, captured via a wrapper around
`prompt_toolkit.shortcuts.input_dialog`) -- both the dialog and that
wrapper are gone (research.md's consolidated decisions table; `forms.py`
no longer constructs any `Application` at all). This feature's persistent,
long-lived `Application` (`app.py`'s `build_app`) is a materially
different shape (constructed once, not per screen -- this file's own
module docstring note on FR-013a), so this needs re-verifying against
*that* shape specifically, not assumed carried over. A second test guards
the part that *is* this project's own responsibility: nothing under
`console/tui/` re-checks `terminal_capability` or tears down/reconstructs a
running screen mid-session, which is what would actually be capable of
discarding in-progress input on a resize.
"""

from __future__ import annotations

import ast

from _tui_test_support import run_headless

from mfgparams.console.i18n import get_locale
from mfgparams.console.tui import app as app_mod
from mfgparams.console.tui.screens.drilling import DrillingSessionState
from mfgparams.i18n import get_raw_locale

_OPEN_DRILLING_AND_SELECT_DIAMETER = [
    "m",  # bar mnemonic: Machining
    "j",  # tree: Milling -> Drilling
    "\r",  # opens Drilling directly, selected on Unit system (revision:
    # FR-003's tree-level tool-selection shortcut is retired)
    "\t",
    "\t",  # Tab to Material type -- Up/Down/j/k are fully consumed by an
    # expanded radio's own options (research.md #4), so Tab moves
    # field-to-field regardless of type instead.
    "\r",  # commits the highlighted (first) material type
    "\t",
    "\r",  # commits the highlighted (first) material
    "\t",
    "\r",  # commits the highlighted (first) tool
    "\t",  # Tab to Diameter
]


def test_resize_mid_entry_does_not_discard_already_typed_text():
    """Every keystroke is followed by a resize (`on_batch` fires between
    every send) -- a stronger version of "one resize mid-typing", since a
    digit typed under continuous resize pressure is the harder case to get
    wrong, not just a single well-timed one."""

    holder: dict = {}

    def target() -> None:
        application, ui, view = app_mod.build_app(None, get_locale(), get_raw_locale())
        holder["app"] = application
        holder["ui"] = ui
        application.run()

    def on_batch() -> None:
        application = holder.get("app")
        if application is not None:
            application._on_resize()

    run_headless(
        target,
        _OPEN_DRILLING_AND_SELECT_DIAMETER + ["1", "0", "\x1b", "\x1b", "\x1b"],
        on_batch=on_batch,
    )

    ui = holder["ui"]
    assert isinstance(ui.drilling_state, DrillingSessionState)
    assert (
        ui.drilling_state.diameter == 10.0
    ), "a digit typed while a resize kept firing was lost -- resize discarded in-progress input"


def test_no_tui_module_rechecks_terminal_capability_after_startup():
    """The only responsibility this project has for FR-008 is to *not*
    re-run the capability gate (and so not tear down a running screen)
    mid-session -- `terminal_capability.check()` must appear exactly once
    across the whole `console/` tree, in `cli.main()`."""

    import mfgparams

    console_dir = __import__("pathlib").Path(mfgparams.__file__).parent / "console"
    call_sites = []
    for path in console_dir.rglob("*.py"):
        if "locales" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "check"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "terminal_capability"
            ):
                call_sites.append(path)

    assert call_sites == [console_dir / "cli.py"], (
        f"terminal_capability.check() must be called exactly once, from cli.py only; "
        f"found: {call_sites}"
    )
