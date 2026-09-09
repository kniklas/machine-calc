"""Contract test: the screens that invoke a calculation must delegate to
mfgparams's public calculate*() functions and must not reimplement any
drilling/milling formulas (T019).

Retargeted from `console/cli.py` (specs/017-console-text-gui): the REPL
that used to import `calculate()` directly is deleted; the same
responsibility now lives in `console/tui/screens/drilling.py` (drilling)
and `console/tui/screens/milling.py` (end/face milling), which is what
this contract now scans instead.
"""

import ast
from pathlib import Path

_TUI_SCREENS_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "mfgparams" / "console" / "tui" / "screens"
)
DRILLING_PATH = _TUI_SCREENS_DIR / "drilling.py"
MILLING_PATH = _TUI_SCREENS_DIR / "milling.py"

# Formula-bearing operators/functions that would indicate a screen is
# performing its own calculation instead of delegating to calculate*().
DISALLOWED_CALL_NAMES = {"calculate_drilling_metrics", "pi", "sqrt"}


def test_drilling_screen_imports_calculate_from_public_api():
    tree = ast.parse(DRILLING_PATH.read_text())
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)
    assert "calculate" in imported_names, "drilling.py must import calculate() from mfgparams"


def test_milling_screen_imports_calculate_functions_from_public_api():
    tree = ast.parse(MILLING_PATH.read_text())
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)
    assert "calculate_end_milling" in imported_names
    assert "calculate_face_milling" in imported_names


def test_screens_do_not_import_formulas_modules():
    for path in (DRILLING_PATH, MILLING_PATH):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", None) or ""
                for alias in getattr(node, "names", []):
                    full = f"{module}.{alias.name}" if module else alias.name
                    assert "formulas" not in full, f"{path.name} must not import formulas directly"


def test_screens_contain_no_disallowed_calculation_calls():
    for path in (DRILLING_PATH, MILLING_PATH):
        tree = ast.parse(path.read_text())
        called_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
        assert called_names.isdisjoint(DISALLOWED_CALL_NAMES), path.name
