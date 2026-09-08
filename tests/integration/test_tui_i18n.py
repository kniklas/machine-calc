"""Integration test: the text GUI renders in the configured locale, with
correct fallback to English for a missing key (tasks.md T028, spec.md User
Story 2, quickstart.md Scenario 3).

Registers a fixture locale directly in the console's catalog cache --
`mfgparams.console.i18n`'s own docstring documents this as supported test
usage (a plain dict, not `functools.lru_cache`, "so tests can register/clear
fixture catalogs deterministically") -- since only English ships today.
"""

from __future__ import annotations

import mfgparams.console.i18n as console_i18n
from mfgparams.console.tui.forms import render_error as forms_render_error
from mfgparams.console.tui.menu import run_top_level_menu

from _tui_test_support import run_headless

_FIXTURE_LOCALE = "xx-tui-fixture"


def _register_fixture_catalog(overrides: dict[str, str]) -> None:
    console_i18n._catalog_cache[_FIXTURE_LOCALE] = overrides


def _clear_fixture_catalog() -> None:
    console_i18n._catalog_cache.pop(_FIXTURE_LOCALE, None)


def test_top_level_menu_renders_in_a_registered_locale():
    # Deliberately distinct first letters (not a shared prefix) so each
    # entry's derived mnemonic is unambiguous and predictable for the
    # assertion below.
    _register_fixture_catalog(
        {
            "tui.menu.title": "Ubytek",
            "tui.menu.machining": "Zeta",
            "tui.menu.configuration": "Wombat",
            "tui.menu.about": "Yonder",
            "tui.menu.help": "Xenon",
            "tui.menu.hint": "Kliknij",
        }
    )
    try:
        result_holder = {}

        def target():
            result_holder["value"] = run_top_level_menu(locale=_FIXTURE_LOCALE)

        run_headless(target, ["z"])
        # "z" is the mnemonic derived from "Zeta" -- confirms the fixture
        # catalog's translated label (not the English default "Machining",
        # whose mnemonic would be "m") is what got rendered and matched.
        assert result_holder["value"] == "machining"
    finally:
        _clear_fixture_catalog()


def test_validation_error_renders_via_the_catalog_not_a_hardcoded_english_string():
    """User Story 2 Acceptance Scenario 2: a deliberately-triggered
    validation error must render through the catalog mechanism, not a
    hardcoded English string -- checked here at the `forms.render_error`
    level (the same function every screen's validation-error path uses),
    against a fixture locale that supplies a translated error template."""

    from mfgparams.models import ErrorInfo

    _register_fixture_catalog({"error.invalid_diameter.zero": "FIXTURE: {label} musi byc dodatni"})
    try:
        error = ErrorInfo(
            code="INVALID_DIAMETER",
            message="Drill diameter must be greater than 0.",
            message_key="error.invalid_diameter.zero",
            kwargs=(("label", "Drill diameter"),),
        )
        rendered = forms_render_error(error, _FIXTURE_LOCALE)
    finally:
        _clear_fixture_catalog()

    assert rendered == "FIXTURE: Drill diameter musi byc dodatni"


def test_missing_key_falls_back_to_english_rather_than_showing_a_blank_or_broken_string():
    # A catalog that has *some* keys but is missing tui.menu.help entirely.
    _register_fixture_catalog(
        {
            "tui.menu.title": "FIXTURE-TITLE",
            "tui.menu.machining": "FIXTURE-MACHINING",
            "tui.menu.configuration": "FIXTURE-CONFIG",
            "tui.menu.about": "FIXTURE-ABOUT",
            "tui.menu.hint": "FIXTURE-HINT",
            # tui.menu.help intentionally absent.
        }
    )
    try:
        rendered = console_i18n.translate(_FIXTURE_LOCALE, "tui.menu.help")
    finally:
        _clear_fixture_catalog()

    assert rendered == "Help", "missing key must fall back to the English catalog entry"
    assert rendered != "tui.menu.help", "must not leak the raw key as a broken string"
