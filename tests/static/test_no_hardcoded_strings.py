"""Static check: no literal user-facing strings outside the message catalog
(T043a; Constitution VIII).

`console/cli.py` no longer holds any interactive prompt logic
(specs/017-console-text-gui deleted the REPL) -- that scan now covers only
`cli.py` itself (its one `print()` call site) and `__main__.py`. The bulk of
this feature's user-facing text lives under `console/tui/`, whose sink is
different: prompt-toolkit dialog constructors (`input_dialog`,
`radiolist_dialog`, `message_dialog`, `yes_no_dialog`, `button_dialog`)
rather than `input()`/`print()`, so a second, dedicated scan below covers
that surface instead of trying to force it through the `input`/`print`
scan the REPL needed.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import mfgparams
from mfgparams import __main__ as entry_point
from mfgparams import logging_setup
from mfgparams.console import cli


def _call_sites(source: str, func_names: set[str]) -> list[ast.Call]:
    tree = ast.parse(source)
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in func_names
    ]


def test_cli_has_no_hardcoded_user_facing_strings():
    source = inspect.getsource(cli)
    calls = _call_sites(source, {"input", "print"})

    assert calls, "expected at least one print() call site in cli.py"

    for call in calls:
        for arg in call.args:
            assert not isinstance(arg, ast.Constant) or not isinstance(arg.value, str), (
                "cli.py must source user-facing text from the message catalog "
                f"(translate()), found a literal string argument at line {call.lineno}"
            )


def test_the_entry_point_has_no_hardcoded_user_facing_strings():
    """`__main__.py` prints too, and Principle VIII does not stop at `cli.py`.

    The FR-011 message and the console's own error status both reach the user
    from here, so a literal added to either `print()` is untranslated output in
    the same sense `cli.py` is scanned for.

    This scan reads *direct* arguments only, which is the shape it can judge
    without guessing: `__main__.py` legitimately holds string literals that are
    not user-facing (message IDs, a marker regex). A literal buried inside a
    nested call is invisible to it -- that hole is covered at runtime by
    `test_the_unnamed_fallback_is_looked_up_rather_than_inlined`, which asserts
    editing the catalog changes the output.
    """

    source = inspect.getsource(entry_point)
    calls = _call_sites(source, {"input", "print"})

    assert calls, "expected at least one print() call site in __main__.py"

    for call in calls:
        for arg in call.args:
            assert not isinstance(arg, ast.Constant) or not isinstance(arg.value, str), (
                "__main__.py must source user-facing text from the message catalog "
                f"(translate()), found a literal string argument at line {call.lineno}"
            )


def test_logging_setup_uses_plain_english_not_the_catalog():
    source = inspect.getsource(logging_setup)
    assert "translate(" not in source
    assert "mfgparams.i18n" not in source and "from mfgparams.i18n" not in source


# --- console/tui/ -- prompt-toolkit dialog sinks (specs/017-console-text-gui) ------

#: Every prompt-toolkit shortcut this feature's screens construct dialogs
#: with. If a screen starts using a different one, add it here rather than
#: silently losing coverage.
_DIALOG_CONSTRUCTORS = {
    "input_dialog",
    "radiolist_dialog",
    "message_dialog",
    "yes_no_dialog",
    "button_dialog",
}

#: Keyword arguments on those constructors that carry user-facing text.
_TEXT_KEYWORDS = {"title", "text", "label", "ok_text", "cancel_text", "yes_text", "no_text"}

_TUI_DIR = Path(mfgparams.__file__).parent / "console" / "tui"


def _tui_source_files() -> list[Path]:
    files = sorted(_TUI_DIR.rglob("*.py"))
    assert files, "no console/tui source files found -- the layout moved and this test did not"
    return files


def _dialog_calls(tree: ast.Module) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _DIALOG_CONSTRUCTORS
    ]


def test_tui_dialog_calls_pass_no_hardcoded_text_keyword_arguments():
    """Every `title=`/`text=`/`label=`/`*_text=` argument to a dialog
    constructor under `console/tui/` must be a `translate(...)` call (or a
    variable/expression built from one), never a literal string -- the
    `console/tui/` equivalent of the REPL-era `input()`/`print()` scan
    above, for prompt-toolkit's dialog shortcuts instead of `input`/`print`.
    """

    checked = 0
    for path in _tui_source_files():
        tree = ast.parse(path.read_text())
        for call in _dialog_calls(tree):
            for kw in call.keywords:
                if kw.arg not in _TEXT_KEYWORDS:
                    continue
                checked += 1
                assert not (
                    isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)
                ), (
                    f"{path.relative_to(_TUI_DIR.parent.parent).as_posix()}:{call.lineno} "
                    f"passes a literal string to {kw.arg!r} -- source it from translate() "
                    "via the message catalog instead"
                )

    assert checked, "expected at least one dialog text-keyword argument under console/tui/"
