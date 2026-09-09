"""Contract test: menu structure and mnemonic uniqueness
(contracts/console-tui-contract.md §2/§3, data-model.md's MenuEntry rule).

Tasks.md T010.
"""

from __future__ import annotations

from mfgparams.console.i18n import translate
from mfgparams.console.tui.menu import MenuEntry, _assign_mnemonics


def test_top_level_menu_entries_match_the_contract():
    entries = [
        translate("en", "tui.menu.machining"),
        translate("en", "tui.menu.configuration"),
        translate("en", "tui.menu.about"),
        translate("en", "tui.menu.help"),
    ]
    assert entries == ["Machining", "Configuration", "About", "Help"]


def test_machining_submenu_entries_match_the_contract():
    entries = [
        translate("en", "tui.machining_menu.milling"),
        translate("en", "tui.machining_menu.drilling"),
    ]
    assert entries == ["Milling", "Drilling"]


def test_top_level_menu_mnemonics_are_pairwise_unique():
    entries = [
        MenuEntry("machining", "Machining"),
        MenuEntry("configuration", "Configuration"),
        MenuEntry("about", "About"),
        MenuEntry("help", "Help"),
    ]
    mnemonics = _assign_mnemonics(entries)
    non_none = [m for m in mnemonics if m is not None]
    assert len(non_none) == len(set(non_none)), f"mnemonic collision in {mnemonics}"
    assert None not in mnemonics, "every top-level entry should get a mnemonic (M/C/A/H)"


def test_machining_submenu_mnemonics_are_pairwise_unique():
    entries = [MenuEntry("milling", "Milling"), MenuEntry("drilling", "Drilling")]
    mnemonics = _assign_mnemonics(entries)
    assert mnemonics == ["m", "d"]


def test_mnemonic_assignment_falls_back_when_first_letters_collide():
    """Two labels starting with the same letter must not silently collide --
    the assigner should find the next free character in the second one."""

    entries = [MenuEntry("a", "Milling"), MenuEntry("b", "Machining")]
    mnemonics = _assign_mnemonics(entries)
    assert mnemonics[0] == "m"
    assert mnemonics[1] is not None
    assert mnemonics[1] != "m"


def test_a_fully_exhausted_label_gets_no_mnemonic_rather_than_colliding():
    entries = [MenuEntry("a", "Aa"), MenuEntry("b", "Aa")]
    mnemonics = _assign_mnemonics(entries)
    assert mnemonics[0] == "a"
    assert mnemonics[1] is None
