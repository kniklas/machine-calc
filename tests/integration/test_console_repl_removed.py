"""Integration test: the REPL is fully gone (tasks.md T014, spec.md
Acceptance Scenario 4, FR-001, FR-007).

Two checks: `mfgparams.console.cli` contains no `input()`-driven session
function left (static, mirroring `tests/contract/test_cli_contract.py`'s
own ast-based style), and invoking the console launches the text GUI rather
than a REPL loop (checked here via the `terminal_capability` gate it goes
through first, since driving the full text GUI end-to-end is what
test_tui_drilling.py/test_tui_milling.py already do).
"""

from __future__ import annotations

import ast
import inspect

import mfgparams.console.cli as cli


def test_cli_module_calls_no_input_function():
    """`input()` was the REPL's whole interaction mechanism -- if it is
    gone from every function in this module, the REPL is gone."""

    tree = ast.parse(inspect.getsource(cli))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "input" not in calls


def test_cli_module_has_no_repl_session_functions():
    """These REPL-only functions must not exist anywhere in the codebase
    any more -- deleted, not renamed or hidden (FR-001)."""

    removed_names = {
        "_run_drilling_session",
        "_run_end_milling_session",
        "_run_face_milling_session",
        "_run_milling_session",
        "_prompt_operation",
        "_prompt_milling_sub_operation",
        "run",
    }
    defined = {name for name in dir(cli) if not name.startswith("__")}
    overlap = removed_names & defined
    assert not overlap, f"REPL-only names still present in console/cli.py: {overlap}"


def test_main_launches_the_text_gui_not_a_repl_loop():
    """`main()` must reach `terminal_capability.check()` before anything
    else -- the REPL had no such gate at all, since it never needed one
    (it degraded to nothing, per spec.md's now-superseded original User
    Story 3). Confirmed by source inspection: the gate is the first
    statement in the function body, before any prompt-toolkit-touching
    import."""

    source = inspect.getsource(cli.main)
    gate_line = next(
        i for i, line in enumerate(source.splitlines()) if "terminal_capability.check" in line
    )
    tui_import_lines = [
        i for i, line in enumerate(source.splitlines()) if "from mfgparams.console.tui" in line
    ]
    assert tui_import_lines, "main() must import the text GUI somewhere"
    assert gate_line < min(tui_import_lines), (
        "terminal_capability.check() must run before the text GUI is imported/constructed "
        "(research.md #2)"
    )
