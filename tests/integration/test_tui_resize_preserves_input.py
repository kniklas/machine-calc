"""Integration test: a terminal resize mid-form-entry does not discard
already-entered input (tasks.md T013a, FR-008, Edge Cases,
/speckit-analyze finding E2).

**Scope note**: prompt-toolkit's `Application` redraws in place on a resize
(`_on_resize`) without touching widget/buffer state -- this test exercises
that real mechanism directly (calling `_on_resize()` on the actual
`Application` instance `forms.ask_number` constructs, captured via a thin
wrapper around `prompt_toolkit.shortcuts.input_dialog`), rather than
re-testing prompt-toolkit's own internals from scratch. A second test
guards the part that *is* this project's own responsibility: nothing under
`console/tui/` re-checks `terminal_capability` or tears down/reconstructs a
running screen mid-session, which is what would actually be capable of
discarding in-progress input on a resize.
"""

from __future__ import annotations

import ast
import contextvars
import threading
import time
from unittest import mock

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import dialogs as pt_dialogs

from mfgparams.console.tui import forms


def test_resize_mid_entry_does_not_discard_already_typed_text():
    captured_apps = []
    real_input_dialog = pt_dialogs.input_dialog

    def capturing_input_dialog(*args, **kwargs):
        app = real_input_dialog(*args, **kwargs)
        captured_apps.append(app)
        return app

    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            result_holder = {}

            def worker():
                with mock.patch.object(forms, "input_dialog", capturing_input_dialog):
                    result_holder["value"] = forms.ask_number(
                        title="Drilling",
                        label="Drill diameter",
                        unit="mm",
                        default=None,
                        locale="en",
                    )

            ctx = contextvars.copy_context()
            thread = threading.Thread(target=lambda: ctx.run(worker), daemon=True)
            thread.start()

            # Wait for the dialog to exist, then type a partial value.
            deadline = time.time() + 5
            while not captured_apps and time.time() < deadline:
                time.sleep(0.02)
            assert captured_apps, "input_dialog was never constructed"
            pipe_input.send_text("1")
            time.sleep(0.2)

            # Simulate a terminal resize mid-entry.
            captured_apps[0]._on_resize()
            time.sleep(0.2)

            # Finish typing and submit.
            pipe_input.send_text("0\r\r")
            thread.join(timeout=10)

    assert not thread.is_alive()
    assert (
        result_holder.get("value") == 10.0
    ), "the digit typed before the resize was lost -- resize discarded in-progress input"


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
