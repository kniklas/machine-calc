"""Unit test: a `tui.*` key missing from a non-English catalog falls back to
the English catalog entry (tasks.md T029, spec.md User Story 2 Acceptance
Scenario 3)."""

from __future__ import annotations

import mfgparams.console.i18n as console_i18n

_FIXTURE_LOCALE = "xx-fallback-fixture"


def test_missing_tui_key_falls_back_to_english():
    console_i18n._catalog_cache[_FIXTURE_LOCALE] = {"tui.menu.machining": "FIXTURE"}
    try:
        # tui.menu.help is present in English but absent from the fixture.
        rendered = console_i18n.translate(_FIXTURE_LOCALE, "tui.menu.help")
    finally:
        console_i18n._catalog_cache.pop(_FIXTURE_LOCALE, None)

    assert rendered == "Help"


def test_present_tui_key_uses_the_fixture_not_english():
    console_i18n._catalog_cache[_FIXTURE_LOCALE] = {"tui.menu.machining": "FIXTURE"}
    try:
        rendered = console_i18n.translate(_FIXTURE_LOCALE, "tui.menu.machining")
    finally:
        console_i18n._catalog_cache.pop(_FIXTURE_LOCALE, None)

    assert rendered == "FIXTURE"


def test_a_locale_with_no_bundled_or_fixture_catalog_falls_back_entirely():
    rendered = console_i18n.translate("zz-nonexistent-locale", "tui.menu.help")
    assert rendered == "Help"
