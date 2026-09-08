"""Unit tests for NavigationState push/pop/back semantics (tasks.md T008).

data-model.md's NavigationState entity: `push` remembers where we came from,
`pop` goes back to it (or to MENU if the stack is empty), and MENU itself is
never pushed onto its own stack since there is nothing to go back to from it.
"""

from __future__ import annotations

from mfgparams.console.tui.app import NavigationState, ScreenId


def test_starts_at_menu_with_an_empty_stack():
    state = NavigationState()
    assert state.current_screen is ScreenId.MENU
    assert state.screen_stack == []


def test_push_from_menu_does_not_record_menu_on_the_stack():
    state = NavigationState()
    state.push(ScreenId.MACHINING_MENU)
    assert state.current_screen is ScreenId.MACHINING_MENU
    assert state.screen_stack == []


def test_push_from_a_non_menu_screen_remembers_it():
    state = NavigationState()
    state.push(ScreenId.MACHINING_MENU)
    state.push(ScreenId.MILLING_FORM)
    assert state.current_screen is ScreenId.MILLING_FORM
    assert state.screen_stack == [ScreenId.MACHINING_MENU]


def test_pop_returns_to_the_prior_screen():
    state = NavigationState()
    state.push(ScreenId.MACHINING_MENU)
    state.push(ScreenId.MILLING_FORM)

    result = state.pop()

    assert result is ScreenId.MACHINING_MENU
    assert state.current_screen is ScreenId.MACHINING_MENU
    assert state.screen_stack == []


def test_pop_on_an_empty_stack_returns_to_menu_without_raising():
    state = NavigationState()
    state.push(ScreenId.CONFIGURATION)

    result = state.pop()

    assert result is ScreenId.MENU
    assert state.current_screen is ScreenId.MENU


def test_pop_at_menu_with_nothing_pushed_stays_at_menu():
    state = NavigationState()

    result = state.pop()

    assert result is ScreenId.MENU
    assert state.current_screen is ScreenId.MENU


def test_a_chain_of_pushes_pops_back_in_reverse_order():
    state = NavigationState()
    state.push(ScreenId.MACHINING_MENU)
    state.push(ScreenId.MILLING_FORM)
    # Going "back" from a form to its submenu, then out of the submenu, then
    # (would be) out of the menu -- but MENU is the root, so it stays there.
    assert state.pop() is ScreenId.MACHINING_MENU
    assert state.pop() is ScreenId.MENU
    assert state.pop() is ScreenId.MENU


def test_locale_and_materials_config_path_default_sensibly():
    state = NavigationState()
    assert state.locale == "en"
    assert state.materials_config_path is None
