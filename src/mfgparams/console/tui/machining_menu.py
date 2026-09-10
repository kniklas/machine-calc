"""The collapsible Machining tree (018-tui-splitpane-redesign FR-002/FR-003),
replacing the old full-screen Machining submenu.

Rendering + row-model only, mirroring `menu.py`: `app.py` owns the actual
`Layout`/key-binding wiring and decides what each row's selection *does*
(toggle expansion, or open an operation screen) -- this module only knows
how to lay the tree out and which rows currently exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import translate
from mfgparams.console.tui.app import MachiningTree
from mfgparams.console.tui.menu import MenuEntry, _assign_mnemonics

#: A row's `action` names what selecting it does (app.py dispatches on
#: this): "open_milling" and "open_drilling_tool" open an operation screen
#: (FR-004); "toggle_drilling" only expands/collapses Drilling's own
#: tool-selection shortcut (FR-003's "further expand/collapse to present a
#: choice" -- selecting "Drilling" itself never opens a screen directly,
#: only its shortcut leaf does, per FR-005a's placement resolution).
RowAction = Literal["open_milling", "toggle_drilling", "open_drilling_tool"]


@dataclass(frozen=True)
class TreeRow:
    label_key: str
    action: RowAction
    indent: int


def tree_rows(tree: MachiningTree) -> list[TreeRow]:
    """The tree's currently-visible rows, in display order. Only defined
    while the caller already knows ``tree.expanded`` -- the tree widget
    itself is not shown at all when collapsed (app.py's body-selection
    logic), so there is no "collapsed" row list to represent here."""

    rows = [
        TreeRow("tui.machining_menu.milling", "open_milling", indent=0),
        TreeRow("tui.machining_menu.drilling", "toggle_drilling", indent=0),
    ]
    if tree.drilling_expanded:
        rows.append(TreeRow("tui.machining_menu.drilling_tool", "open_drilling_tool", indent=1))
    return rows


def tree_mnemonics(rows: list[TreeRow], locale: str) -> list[str | None]:
    """One accelerator character per row, pairwise-unique *within the
    tree* (contract §4: "every menu bar entry and tree leaf" gets one) --
    a separate namespace from the bar's own mnemonics, reusing
    `menu._assign_mnemonics` unchanged (research.md) by wrapping each row's
    translated label in a throwaway `MenuEntry`."""

    entries = [MenuEntry(row.action, translate(locale, row.label_key)) for row in rows]
    return _assign_mnemonics(entries)


def render_tree(
    tree: MachiningTree,
    selected_index: int,
    locale: str,
    *,
    focused: bool,
) -> StyleAndTextTuples:
    """The tree's rows, most-recently-selected row reverse-video
    highlighted only while ``focused`` (same convention as
    `menu.render_menu_bar`), each row's mnemonic underlined the same way
    the bar's own entries are."""

    rows = tree_rows(tree)
    mnemonics = tree_mnemonics(rows, locale)
    fragments: StyleAndTextTuples = [("class:pane-title", f"{translate(locale, 'tui.machining_menu.title')}\n")]
    for index, (row, mnemonic) in enumerate(zip(rows, mnemonics)):
        style = "class:selected" if focused and index == selected_index else ""
        indent = "  " * (row.indent + 1)
        label = translate(locale, row.label_key)
        fragments.append((style, f"{indent}"))
        if mnemonic is None:
            fragments.append((style, label))
        else:
            pos = label.lower().index(mnemonic)
            before, marked, after = label[:pos], label[pos : pos + 1], label[pos + 1 :]
            fragments.append((style, before))
            fragments.append((f"{style} class:mnemonic", marked))
            fragments.append((style, after))
        fragments.append((style, "\n"))
    return fragments
