"""The top-level menu screen, and the generic mnemonic-driven menu widget
`run_menu` that `machining_menu.py` also uses (FR-009, FR-010).

Built as a hand-rolled `Application`, not a `shortcuts` dialog: none of
prompt-toolkit's bundled dialogs support a direct single-key
mnemonic/accelerator per item (contracts/console-tui-contract.md §3), only
sequential (arrow/Tab) navigation.
"""

from __future__ import annotations

from dataclasses import dataclass

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from mfgparams.console.i18n import translate

_STYLE = Style.from_dict(
    {
        "mnemonic": "underline bold",
        "selected": "reverse",
        "hint": "italic",
    }
)


@dataclass(frozen=True)
class MenuEntry:
    """One selectable row (data-model.md's MenuEntry).

    ``mnemonic`` is derived by :func:`run_menu`, not stored here — see its
    docstring for why (translated labels change which letters are free).
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


def _render_entry(entry: MenuEntry, mnemonic: str | None, style: str) -> list[tuple[str, str]]:
    """One menu row's fragments, with its mnemonic character underlined."""

    if mnemonic is None:
        return [(style, f"  {entry.label}"), ("", "\n")]
    pos = entry.label.lower().index(mnemonic)
    before, marked, after = entry.label[:pos], entry.label[pos : pos + 1], entry.label[pos + 1 :]
    return [
        (style, "  "),
        (style, before),
        (f"{style} class:mnemonic", marked),
        (style, after),
        ("", "\n"),
    ]


def _build_key_bindings(
    entries: list[MenuEntry], mnemonics: list[str | None], selected: list[int]
) -> KeyBindings:
    """Arrow/vi navigation, Enter/Escape, and one mnemonic-jump binding per
    entry that has one -- extracted from `run_menu` (complexity gate)."""

    bindings = KeyBindings()

    @bindings.add("up")
    @bindings.add("k")
    def _up(event) -> None:
        selected[0] = (selected[0] - 1) % len(entries)

    @bindings.add("down")
    @bindings.add("j")
    def _down(event) -> None:
        selected[0] = (selected[0] + 1) % len(entries)

    @bindings.add("enter")
    def _enter(event) -> None:
        event.app.exit(result=entries[selected[0]].value)

    @bindings.add("escape")
    @bindings.add("c-q")
    def _cancel(event) -> None:
        event.app.exit(result=None)

    for index, mnemonic in enumerate(mnemonics):
        if mnemonic is None:
            continue

        def _jump(event, target_index: int = index) -> None:
            event.app.exit(result=entries[target_index].value)

        bindings.add(mnemonic)(_jump)

    return bindings


def run_menu(*, title: str, entries: list[MenuEntry], locale: str) -> str | None:
    """Show a full-screen menu of ``entries``; return the selected value, or
    ``None`` if the user backs out (Escape, or Ctrl-Q at the top level).

    Navigation (contracts/console-tui-contract.md §3): Up/Down (or j/k) move
    the highlighted row, Enter selects it, and each row's mnemonic character
    (visibly underlined) jumps to and selects it directly in one keystroke.
    """

    mnemonics = _assign_mnemonics(entries)
    selected = [0]

    def render() -> list[tuple[str, str]]:
        fragments: list[tuple[str, str]] = [("", f"{title}\n\n")]
        for index, (entry, mnemonic) in enumerate(zip(entries, mnemonics)):
            style = "class:selected" if index == selected[0] else ""
            fragments.extend(_render_entry(entry, mnemonic, style))
        fragments.append(("class:hint", f"\n{translate(locale, 'tui.menu.hint')}"))
        return fragments

    control = FormattedTextControl(render, focusable=True)
    root = HSplit([Window(content=control)])
    bindings = _build_key_bindings(entries, mnemonics, selected)

    app: Application[str | None] = Application(
        layout=Layout(root, focused_element=control),
        key_bindings=bindings,
        style=_STYLE,
        full_screen=True,
    )
    return app.run()


def run_top_level_menu(*, locale: str) -> str | None:
    """The top-level menu (FR-009): Machining, Configuration, About, Help.

    Returns one of ``"machining"``, ``"configuration"``, ``"about"``,
    ``"help"``, or ``None`` if the user exits the app (Escape/Ctrl-Q at the
    root, where there is nothing to go "back" to).
    """

    entries = [
        MenuEntry("machining", translate(locale, "tui.menu.machining")),
        MenuEntry("configuration", translate(locale, "tui.menu.configuration")),
        MenuEntry("about", translate(locale, "tui.menu.about")),
        MenuEntry("help", translate(locale, "tui.menu.help")),
    ]
    return run_menu(title=translate(locale, "tui.menu.title"), entries=entries, locale=locale)
