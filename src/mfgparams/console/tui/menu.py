"""The persistent horizontal menu bar (018-tui-splitpane-redesign FR-001),
and the mnemonic-assignment logic the Machining tree also reuses.

Rendering only: this module owns *what the bar's entries are and how they
look*, not the `Application`/`Layout`/key-binding wiring that shows them --
that now lives in `app.py`, since the bar is one row of a single persistent
`Layout` rather than its own full-screen `Application` (017's `run_menu`
built one; that shape no longer fits a bar that stays visible alongside
whatever else is on screen). `_assign_mnemonics` is unchanged from 017
(research.md's consolidated table): picking pairwise-unique accelerator
characters from a label list has nothing to do with how the labels are
laid out.
"""

from __future__ import annotations

from dataclasses import dataclass

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import translate


@dataclass(frozen=True)
class MenuEntry:
    """One selectable item (data-model.md's `MenuBar`/`MenuEntry`).

    ``mnemonic`` is derived by :func:`_assign_mnemonics`, not stored here —
    see its docstring for why (translated labels change which letters are
    free).
    """

    value: str
    label: str


def _assign_mnemonics(entries: list[MenuEntry]) -> list[str | None]:
    """Pick one accelerator character per entry, pairwise-unique within
    this menu (data-model.md's MenuEntry validation rule).

    Prefers each label's first alphabetic character; if that collides with
    an earlier entry's, scans the rest of the label for the first character
    not yet taken. An entry exhausted of free characters gets no mnemonic
    (``None``) rather than raising -- sequential navigation still reaches
    it, per FR-010's "keyboard alone... using both" (mnemonics are an
    accelerator, not the only path).
    """

    taken: set[str] = set()
    mnemonics: list[str | None] = []
    for entry in entries:
        chosen: str | None = None
        for char in entry.label:
            lower = char.lower()
            if lower.isalpha() and lower not in taken:
                chosen = lower
                break
        if chosen is not None:
            taken.add(chosen)
        mnemonics.append(chosen)
    return mnemonics


def default_entries(locale: str) -> list[MenuEntry]:
    """FR-001's exact, closed entry set: Exit, Machining, Configuration,
    About, Help, in that order. Machining/Configuration/About/Help carry
    forward 017's FR-009 item set unchanged; Exit is new (017 had no
    labeled Exit item, only an unlabeled Escape/Ctrl-Q handler -- see
    ``app.py``'s bar-level Escape handling)."""

    return [
        MenuEntry("exit", translate(locale, "tui.menu.exit")),
        MenuEntry("machining", translate(locale, "tui.menu.machining")),
        MenuEntry("configuration", translate(locale, "tui.menu.configuration")),
        MenuEntry("about", translate(locale, "tui.menu.about")),
        MenuEntry("help", translate(locale, "tui.menu.help")),
    ]


def render_menu_bar(
    entries: list[MenuEntry],
    mnemonics: list[str | None],
    selected_index: int,
    *,
    focused: bool,
) -> StyleAndTextTuples:
    """One horizontal row, entries separated by two spaces, the currently
    selected one reverse-video highlighted -- only while ``focused`` (FR-010:
    the bar's own selection should not visually compete for attention once
    the user has moved focus into the body, e.g. an open operation screen's
    fields, per app.py's Escape-based focus model)."""

    fragments: StyleAndTextTuples = []
    for index, (entry, mnemonic) in enumerate(zip(entries, mnemonics)):
        if index > 0:
            fragments.append(("", "  "))
        style = "class:selected" if focused and index == selected_index else ""
        if mnemonic is None:
            fragments.append((style, entry.label))
            continue
        pos = entry.label.lower().index(mnemonic)
        before, marked, after = entry.label[:pos], entry.label[pos : pos + 1], entry.label[pos + 1 :]
        fragments.append((style, before))
        fragments.append((f"{style} class:mnemonic", marked))
        fragments.append((style, after))
    return fragments
