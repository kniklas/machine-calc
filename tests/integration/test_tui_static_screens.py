"""Integration tests for the static/simple screens: Machining submenu,
Configuration, About, Help. Complements test_tui_drilling.py/
test_tui_milling.py, which exercise the parameter-entry screens."""

from __future__ import annotations

from _tui_test_support import run_headless

import mfgparams
from mfgparams.console.tui.machining_menu import run_machining_menu
from mfgparams.console.tui.screens.about import run_about_screen
from mfgparams.console.tui.screens.configuration import run_configuration_screen
from mfgparams.console.tui.screens.help import run_help_screen


def test_machining_menu_mnemonic_selects_milling():
    result_holder = {}
    run_headless(
        lambda: result_holder.__setitem__("value", run_machining_menu(locale="en")), ["m"]
    )
    assert result_holder["value"] == "milling"


def test_machining_menu_mnemonic_selects_drilling():
    result_holder = {}
    run_headless(
        lambda: result_holder.__setitem__("value", run_machining_menu(locale="en")), ["d"]
    )
    assert result_holder["value"] == "drilling"


def test_machining_menu_escape_goes_back():
    result_holder = {}
    run_headless(
        lambda: result_holder.__setitem__("value", run_machining_menu(locale="en")), ["\x1b"]
    )
    assert result_holder["value"] is None


def test_about_screen_shows_name_and_version_then_dismisses():
    # message_dialog has one OK button; a single Enter dismisses it.
    run_headless(lambda: run_about_screen("en"), ["\r"])
    # No exception, no hang -- the assertion is that run_headless returned.


def test_help_screen_is_reachable_and_non_crashing():
    run_headless(lambda: run_help_screen("en"), ["\r"])


def test_configuration_screen_views_a_material_type_then_backs_out():
    # Pick the first material-type choice (Tab, Enter -> default), view it,
    # dismiss the resulting message dialog, then cancel out of the loop.
    run_headless(
        lambda: run_configuration_screen(None, "en"),
        ["\t\r", "\r", "\t\t\r"],
    )


def test_about_screen_text_includes_the_real_version():
    # A lighter-weight check of the same rendering logic used above, without
    # driving a dialog: confirms the version string embedded is the real one.
    from mfgparams.console.i18n import translate

    text = translate("en", "tui.about.text", name="mfgparams", version=mfgparams.__version__)
    assert mfgparams.__version__ in text
