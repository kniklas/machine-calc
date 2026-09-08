"""The Configuration screen: read-only view of the active materials/tools
registry (FR-009, data-model.md's ConfigurationView, research.md #4).

Deliberately **not** a create/edit UI — v1 scope is parity with what the
REPL already exposed (viewing/selecting from an existing registry via
`--materials-config`), not new authoring capability. See research.md #4 for
the full reasoning; this is a plan-time judgment call flagged for the user
to confirm, not a spec-mandated restriction.
"""

from __future__ import annotations

from prompt_toolkit.shortcuts import message_dialog

from mfgparams import list_material_types, list_materials, list_tools
from mfgparams.console.i18n import translate
from mfgparams.console.tui import forms


def run_configuration_screen(materials_config_path: str | None, locale: str) -> None:
    """Loop showing a choice of what to view, until the user backs out."""

    path_key = (
        "tui.configuration.path_label.set"
        if materials_config_path
        else "tui.configuration.path_label.default"
    )
    path_line = (
        translate(locale, path_key, path=materials_config_path)
        if materials_config_path
        else translate(locale, path_key)
    )

    while True:
        material_types = list_material_types(config_path=materials_config_path)
        tools = list_tools(config_path=materials_config_path)

        options = {mt: forms.material_type_label(mt, locale) for mt in material_types}
        options = forms.unique_labels(options)
        options["__tools__"] = translate(locale, "tui.label.tool")

        choice = forms.ask_choice(
            title=translate(locale, "tui.configuration.title"),
            label=path_line,
            options=options,
            default=None,
            locale=locale,
        )
        if choice is None:
            return

        if choice == "__tools__":
            text = translate(
                locale, "tui.configuration.section.tools", items=", ".join(tools) or "-"
            )
        else:
            materials = list_materials(config_path=materials_config_path, material_type=choice)
            text = translate(
                locale,
                "tui.configuration.section.materials",
                material_type=forms.material_type_label(choice, locale),
                items=", ".join(materials) or "-",
            )

        message_dialog(
            title=translate(locale, "tui.configuration.title"),
            text=text,
            ok_text=translate(locale, "tui.action.ok"),
        ).run()
