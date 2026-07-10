"""Unit tests for the message catalog loader (T018a).

Covers key lookup, ``str.format()`` placeholder substitution (including a
missing-placeholder-value case that MUST NOT raise), missing-key fallback to
English, and missing-locale fallback to English (unset/empty/unrecognized
``MACHINE_CALC_LOCALE``).
"""

from __future__ import annotations

import logging

import pytest

from machine_calc import i18n


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    i18n.clear_catalog_cache()
    yield
    i18n.clear_catalog_cache()


def test_get_locale_defaults_to_english_when_unset(monkeypatch):
    monkeypatch.delenv("MACHINE_CALC_LOCALE", raising=False)
    assert i18n.get_locale() == "en"


def test_get_locale_defaults_to_english_when_empty(monkeypatch):
    monkeypatch.setenv("MACHINE_CALC_LOCALE", "")
    assert i18n.get_locale() == "en"


def test_get_locale_defaults_to_english_when_unrecognized(monkeypatch):
    monkeypatch.setenv("MACHINE_CALC_LOCALE", "xx-not-a-real-locale")
    assert i18n.get_locale() == "en"


def test_get_locale_returns_recognized_bundled_locale(monkeypatch):
    monkeypatch.setenv("MACHINE_CALC_LOCALE", "en")
    assert i18n.get_locale() == "en"


def test_translate_looks_up_known_key():
    assert i18n.translate("en", "error.missing_material") == (
        "A workpiece material must be selected."
    )


def test_translate_substitutes_named_placeholder():
    result = i18n.translate("en", "error.unknown_material", material="Unobtainium")
    assert result == "Unknown workpiece material: 'Unobtainium'."


def test_translate_missing_placeholder_does_not_raise(caplog):
    with caplog.at_level(logging.WARNING):
        result = i18n.translate("en", "error.unknown_material")

    assert isinstance(result, str)
    assert result  # usable, non-blank fallback string
    assert any("error.unknown_material" in record.message for record in caplog.records)


def test_translate_falls_back_to_english_for_unrecognized_locale():
    result = i18n.translate("xx-not-a-real-locale", "error.missing_material")
    assert result == "A workpiece material must be selected."


def test_translate_falls_back_to_english_for_missing_key():
    # No locale ships a key that doesn't exist anywhere; translate() must
    # still return a usable string (the key itself) rather than raise.
    result = i18n.translate("en", "does.not.exist")
    assert result == "does.not.exist"
