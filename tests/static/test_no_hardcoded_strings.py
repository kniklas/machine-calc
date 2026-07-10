"""Static check: no literal user-facing strings outside the message catalog
(T043a; Constitution VIII).

Parses ``cli.py`` and confirms every ``input(...)``/``print(...)`` call
site passes either no argument, a variable, or a call to
``machine_calc.i18n.translate(...)`` — never a hard-coded string literal —
so future edits cannot silently reintroduce untranslated text. Also
confirms ``logging_setup.py`` (the one place Constitution VIII requires
plain English) uses ordinary string literals, not catalog lookups.
"""

from __future__ import annotations

import ast
import inspect

from machine_calc import cli, logging_setup


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

    assert calls, "expected at least one input()/print() call site in cli.py"

    for call in calls:
        for arg in call.args:
            assert not isinstance(arg, ast.Constant) or not isinstance(arg.value, str), (
                "cli.py must source user-facing text from the message catalog "
                f"(translate()), found a literal string argument at line {call.lineno}"
            )


def test_logging_setup_uses_plain_english_not_the_catalog():
    source = inspect.getsource(logging_setup)
    assert "translate(" not in source
    assert "machine_calc.i18n" not in source and "from machine_calc.i18n" not in source
