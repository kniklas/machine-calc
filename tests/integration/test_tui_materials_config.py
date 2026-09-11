"""Integration test: the left pane's material-type radio is data-driven,
not hardcoded to Metal/Wood (018-tui-splitpane-redesign spec User Story 2,
quickstart.md Scenario 6, tasks.md T019).

`list_material_types()` already builds this dynamically from whatever a
`--materials-config` file registers (extending the existing
`test_milling_config_isolation.py` fixture pattern); this test confirms
`drilling.rows_for` actually surfaces that extra category to the user, not
just that the underlying registry call supports it.
"""

from __future__ import annotations

import pytest

from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens.drilling import DrillingSessionState, rows_for
from mfgparams.registry_config import clear_cache


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    clear_cache()
    yield
    clear_cache()


def _write_plastic_materials_config(tmp_path) -> str:
    path = tmp_path / "config.toml"
    path.write_text("""
        [[materials]]
        name = "ABS"
        material_type = "plastic"
        reference_cutting_speed = 90.0
        reference_feed_per_rev = 0.15
        specific_cutting_force = 300.0
        unit_system = "metric"
        """)
    return str(path)


def test_material_type_radio_includes_a_category_beyond_the_bundled_metal_and_wood(tmp_path):
    materials_config_path = _write_plastic_materials_config(tmp_path)
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    rows = rows_for(screen, materials_config_path, "en", "en")
    material_type_row = next(row for row in rows if row.field_id is FieldId.MATERIAL_TYPE)
    values = {value for value, _label in material_type_row.options}
    assert "plastic" in values
    assert "metal" in values  # the bundled defaults are still present too


def test_selecting_the_new_category_narrows_the_material_radio_to_its_own_materials(tmp_path):
    materials_config_path = _write_plastic_materials_config(tmp_path)
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    rows = rows_for(screen, materials_config_path, "en", "en")
    next(row for row in rows if row.field_id is FieldId.MATERIAL_TYPE).on_select("plastic")

    rows = rows_for(screen, materials_config_path, "en", "en")
    material_row = next(row for row in rows if row.field_id is FieldId.MATERIAL)
    values = {value for value, _label in material_row.options}
    assert values == {"ABS"}


def _write_colliding_material_type_config(tmp_path) -> str:
    """Two `material_type` IDs ("cast_iron"/"cast-iron") that both
    title-case to the identical fallback label "Cast Iron"
    (`forms.material_type_label`'s own `.replace("_", " ").replace("-", "
    ").title()` logic, since neither has its own `material_type.<id>`
    catalog key)."""

    path = tmp_path / "config.toml"
    path.write_text("""
        [[materials]]
        name = "Grey Iron"
        material_type = "cast_iron"
        reference_cutting_speed = 60.0
        reference_feed_per_rev = 0.2
        specific_cutting_force = 900.0
        unit_system = "metric"

        [[materials]]
        name = "Ductile Iron"
        material_type = "cast-iron"
        reference_cutting_speed = 65.0
        reference_feed_per_rev = 0.2
        specific_cutting_force = 850.0
        unit_system = "metric"
        """)
    return str(path)


def test_material_type_radio_disambiguates_colliding_fallback_labels(tmp_path):
    """Regression test for a bug a round-3 code-review pass on PR #96
    found: two user-supplied `material_type` IDs that title-case to the
    same fallback label rendered as two indistinguishable radio options,
    unlike the Material/Tool rows built two lines below in `rows_for`,
    which already wrap their own options in `forms.unique_labels()` for
    exactly this reason -- the Material type row alone was missing it."""

    materials_config_path = _write_colliding_material_type_config(tmp_path)
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    rows = rows_for(screen, materials_config_path, "en", "en")
    material_type_row = next(row for row in rows if row.field_id is FieldId.MATERIAL_TYPE)
    labels = [label for _value, label in material_type_row.options]
    assert len(labels) == len(set(labels)), f"colliding labels: {labels}"


def test_milling_material_type_radio_disambiguates_colliding_fallback_labels(tmp_path):
    """Milling's own `rows_for` had the identical gap, independently
    (FR-009's "same pattern" requirement applies to the fix too, not just
    the original bug)."""

    from mfgparams.console.tui.app import MenuBar, MillingSubOperation, SessionUI
    from mfgparams.console.tui.menu import MenuEntry
    from mfgparams.console.tui.screens.milling import rows_for as milling_rows_for

    materials_config_path = _write_colliding_material_type_config(tmp_path)
    ui = SessionUI(menu_bar=MenuBar(entries=(MenuEntry("exit", "Exit"),)))
    screen = OperationScreen(
        operation="milling",
        session_state=ui.milling_states[MillingSubOperation.END_MILLING],
        selected_field=FieldId.UNIT_SYSTEM,
    )
    rows = milling_rows_for(ui, screen, materials_config_path, "en", "en")
    material_type_row = next(row for row in rows if row.field_id is FieldId.MATERIAL_TYPE)
    labels = [label for _value, label in material_type_row.options]
    assert len(labels) == len(set(labels)), f"colliding labels: {labels}"
