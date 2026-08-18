"""Integration tests: two-step material selection in the CLI.

Covers the user-facing half of specs/008-material-categorization — the user
picks a material *type* first, then a material within it (008 US1, US2) —
plus category switching, data-driven category labels, and stale-selection
handling (008 FR-001, FR-002, FR-004, FR-010, FR-011).
"""

from __future__ import annotations

import builtins

import pytest

from machine_calc import i18n
from machine_calc.cli import run


def _feed(monkeypatch, answers):
    """Feed ``answers`` to ``input()``, echoing each prompt so it is captured."""

    iterator = iter(answers)

    def _input(prompt=""):
        print(prompt, end="")
        return next(iterator)

    monkeypatch.setattr(builtins, "input", _input)


def _write_config(tmp_path, body: str) -> str:
    path = tmp_path / "user-materials.toml"
    path.write_text(body, encoding="utf-8")
    return str(path)


class TestTypeThenMaterialFlow:
    """US1 + US2: the type prompt precedes and scopes the material prompt."""

    def test_type_prompt_precedes_material_prompt(self, monkeypatch, capsys):
        _feed(monkeypatch, ["metric", "", "Metal", "Mild Steel", "Carbide", "10", "25", "", "n"])

        run()

        out = capsys.readouterr().out
        assert "Material type (Metal, Wood)" in out
        assert out.index("Material type") < out.index("Material (")
        assert "Spindle speed:" in out

    def test_material_prompt_lists_only_the_chosen_category(self, monkeypatch, capsys):
        _feed(monkeypatch, ["metric", "", "Wood", "Oak", "Carbide", "10", "25", "", "n"])

        run()

        out = capsys.readouterr().out
        assert "Material (Oak, Maple, Pine, Spruce, Fir, Plywood, MDF)" in out
        assert "Mild Steel" not in out

    def test_selecting_metal_excludes_wood_materials(self, monkeypatch, capsys):
        _feed(monkeypatch, ["metric", "", "Metal", "Titanium", "Carbide", "10", "25", "", "n"])

        run()

        out = capsys.readouterr().out
        assert "Material (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium)" in out
        assert "Oak" not in out

    def test_material_from_another_category_is_rejected_and_reprompted(self, monkeypatch, capsys):
        """Choosing "Wood" must not accept a metal (008 FR-002)."""

        _feed(
            monkeypatch,
            ["metric", "", "Wood", "Mild Steel", "Oak", "Carbide", "10", "25", "", "n"],
        )

        run()

        out = capsys.readouterr().out
        assert "Please choose one of" in out
        assert "Spindle speed:" in out

    def test_invalid_type_is_reprompted(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            ["metric", "", "Ceramic", "Metal", "Mild Steel", "Carbide", "10", "25", "", "n"],
        )

        run()

        out = capsys.readouterr().out
        assert "Please choose one of: Metal, Wood" in out
        assert "Spindle speed:" in out


class TestCategorySwitchingOnLoopRerun:
    """Re-running the REPL loop remembers, or correctly clears, the selection."""

    def test_unchanged_type_reuses_previous_material_default(self, monkeypatch, capsys):
        _feed(
            monkeypatch,
            [
                "metric",
                "",
                "Metal",
                "Mild Steel",
                "HSS",
                "10",
                "25",
                "",
                "y",
                # Second pass: blank type reuses "Metal", blank material reuses
                # "Mild Steel"; only the tool changes.
                "metric",
                "",
                "",
                "",
                "Carbide",
                "",
                "",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        assert out.count("Spindle speed:") == 2

    def test_switching_type_does_not_offer_a_cross_category_default(self, monkeypatch, capsys):
        """After switching to Wood, the metal default must not be reusable (008 FR-011).

        The second pass answers the material prompt with a blank line. If the
        remembered "Mild Steel" were still offered as this category's default,
        the blank would silently select it; instead the prompt must reject the
        blank and reprompt until a wood is named.
        """

        _feed(
            monkeypatch,
            [
                "metric",
                "",
                "Metal",
                "Mild Steel",
                "Carbide",
                "10",
                "25",
                "",
                "y",
                "metric",
                "",
                "Wood",
                "",  # blank must NOT resolve to the remembered "Mild Steel"
                "Oak",  # an explicit in-category choice is required
                "",
                "",
                "",
                "",
                "n",
            ],
        )

        run()

        out = capsys.readouterr().out
        second_pass = out[out.index("Run another calculation?") :]
        assert "Please choose one of" in second_pass
        assert "(Mild Steel)" not in second_pass
        assert out.count("Spindle speed:") == 2


class TestDataDrivenCategories:
    """A category added by configuration alone is fully usable (008 FR-004)."""

    def test_new_category_appears_and_is_selectable(self, monkeypatch, capsys, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Portland Cement"
material_type = "cement"
reference_cutting_speed = 30.0
reference_feed_per_rev = 0.15
specific_cutting_force = 1400.0
""",
        )
        _feed(
            monkeypatch,
            ["metric", "", "Cement", "Portland Cement", "Carbide", "10", "25", "", "n"],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        # "cement" has no catalog entry; the label falls back to title case.
        assert "Material type (Metal, Wood, Cement)" in out
        assert "Material (Portland Cement)" in out
        assert "Spindle speed:" in out

    def test_multi_word_category_id_is_title_cased(self, monkeypatch, capsys, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "CFRP"
material_type = "composite-fibre"
reference_cutting_speed = 60.0
reference_feed_per_rev = 0.10
specific_cutting_force = 900.0
""",
        )
        _feed(
            monkeypatch,
            ["metric", "", "Composite Fibre", "CFRP", "Carbide", "10", "25", "", "n"],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        assert "Composite Fibre" in out
        assert "Spindle speed:" in out

    def test_uncategorized_materials_are_still_selectable(self, monkeypatch, capsys, tmp_path):
        """A pre-008 config file's new material remains reachable (008 FR-011)."""

        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )
        _feed(
            monkeypatch,
            ["metric", "", "Uncategorized", "Bronze", "Carbide", "10", "25", "", "n"],
        )

        run(materials_config_path=config_path)

        out = capsys.readouterr().out
        assert "Material type (Metal, Wood, Uncategorized)" in out
        assert "Spindle speed:" in out


class TestCategoryLabelLocalization:
    """Category labels go through the message catalog (Constitution VIII)."""

    @pytest.fixture(autouse=True)
    def _reset_catalog(self):
        yield
        i18n.clear_catalog_cache()

    def test_unsupported_locale_falls_back_to_english_labels(self, monkeypatch, capsys):
        monkeypatch.setenv("MACHINE_CALC_LOCALE", "xx-no-catalog")
        i18n.clear_catalog_cache()
        _feed(monkeypatch, ["metric", "", "Metal", "Mild Steel", "Carbide", "10", "25", "", "n"])

        run()

        out = capsys.readouterr().out
        assert "Material type (Metal, Wood)" in out
        assert "material_type.metal" not in out
