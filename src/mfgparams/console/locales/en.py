"""English (``en``) message catalog for the console — the default and fallback locale.

Message IDs are stable and language-independent; do not rename an existing
key when editing its English text (other locale modules and tests key off
these IDs). See ``specs/015-console-i18n-relocation/data-model.md`` for the
entity definition this module implements, and
``specs/017-console-text-gui/contracts/console-tui-contract.md`` §4 for which
strings belong here versus in :mod:`mfgparams.locales.en`.

specs/017-console-text-gui replaces the REPL with a full-screen text GUI: the
``cli.*`` keys this catalog held for the REPL are retired along with the REPL
code that used them, replaced by the ``tui.*`` keys below (contracts §4 --
new keys introduced by that feature are namespaced ``tui.*``).
"""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    # --- Top-level menu and Machining submenu (FR-009, FR-010) ---
    "tui.menu.title": "mfgparams",
    "tui.menu.hint": "Arrow keys or the highlighted letter to choose, Enter to select.",
    "tui.menu.machining": "Machining",
    "tui.menu.configuration": "Configuration",
    "tui.menu.about": "About",
    "tui.menu.help": "Help",
    # 018-tui-splitpane-redesign FR-001: new to the persistent bar -- 017 had
    # no labeled Exit item, only an unlabeled Escape/Ctrl-Q handler.
    "tui.menu.exit": "Exit",
    "tui.machining_menu.title": "Machining",
    "tui.machining_menu.milling": "Milling",
    "tui.machining_menu.drilling": "Drilling",
    # 018-tui-splitpane-redesign FR-003/FR-005a: the Machining tree's
    # drilling-type leaf -- a navigation shortcut into the same
    # tool-selection field FR-005's left pane always shows (not a
    # duplicate/independent value); "Tool" not "Drilling tool" since it's
    # already nested under Drilling, mirroring how "Milling"/"Drilling"
    # themselves don't repeat "Machining".
    "tui.machining_menu.drilling_tool": "Tool",
    # --- Shared dialog chrome ---
    "tui.action.ok": "OK",
    "tui.action.back": "Back",
    "tui.error.title": "Invalid input",
    # --- Unit system / calculation mode (shared by Milling and Drilling) ---
    "tui.label.unit_system": "Unit system",
    "tui.unit_system.metric": "metric",
    "tui.unit_system.imperial": "imperial",
    "tui.label.mode": "Calculation mode",
    "tui.mode.standard": "standard",
    "tui.mode.power_constrained": "power-constrained",
    "tui.mode.fixed_rpm": "fixed-rpm",
    "tui.label.power": "Available power",
    "tui.label.power_required": "Available power",
    "tui.prompt.power_required.invalid": (
        "Please enter a positive numeric value for available power."
    ),
    "tui.label.target_rpm": "Target spindle speed",
    "tui.prompt.target_rpm.invalid": (
        "Please enter a positive numeric value for target spindle speed."
    ),
    # --- Material / tool selection (shared by Milling and Drilling) ---
    "tui.label.material_type": "Material type",
    "material_type.metal": "Metal",
    "material_type.wood": "Wood",
    "material_type.uncategorized": "Uncategorized",
    "tui.label.material": "Material",
    "tui.label.tool": "Drilling tool",
    "tui.label.unit_system_suffix": "{name} [{unit_system}]",
    # --- Drilling form (FR-002) ---
    "tui.drilling.title": "Drilling",
    "tui.label.diameter": "Drill diameter",
    "tui.label.depth": "Hole depth",
    # --- Milling form (FR-002) ---
    "tui.milling.title": "Milling",
    "tui.label.milling_sub_operation": "Milling operation",
    "tui.milling_sub_operation.end_milling": "end milling",
    "tui.milling_sub_operation.face_milling": "face milling",
    "tui.label.mill_diameter": "Cutter diameter",
    "tui.label.end_mill_tool": "End-mill tool",
    "tui.label.face_mill_tool": "Face-mill tool",
    # These three are deliberately NOT tui.*-namespaced (contracts §4's
    # dual-presence exception, unchanged from the REPL): core's
    # validate_depth_of_cut_mm/validate_engagement_mm embed a label inside
    # English error text by this exact key name (mfgparams.locales.en carries
    # the same three, untouched by this feature), and this module's own
    # error-rendering must resolve the identical key to re-translate it. The
    # TUI's own field labels reuse them rather than inventing tui.* aliases,
    # so there is exactly one key per concept, not two that could drift.
    "cli.label.axial_depth_of_cut": "Axial depth of cut",
    "cli.label.radial_depth_of_cut": "Radial depth of cut",
    "cli.label.width_of_cut": "Width of cut",
    "tui.label.feed_per_tooth": "Feed per tooth",
    "tui.label.number_of_teeth": "Number of teeth",
    "tui.label.length_of_cut": "Length of cut",
    "tui.unit.teeth": "teeth",
    # --- Numeric input prompt/validation (shared) ---
    "tui.prompt.number": "{label} ({unit})",
    "tui.prompt.number.with_default": "{label} ({unit}, default {default})",
    # Reused unchanged for 018-tui-splitpane-redesign FR-006b's unparseable-
    # number message: still a complete, actionable sentence shown next to
    # the field, not just inside 017's now-replaced modal dialog -- no
    # wording change needed for the new inline context.
    "tui.prompt.number.invalid": "Please enter a numeric value.",
    "tui.prompt.power.optional_hint": "Leave blank if unknown.",
    # --- Result display ---
    # Reused unchanged as the right pane's title (018-tui-splitpane-redesign
    # FR-006/FR-006a) -- "Result" reads correctly whether it labels a modal
    # dialog (017) or a persistent pane (018).
    "tui.result.title": "Result",
    # 018-tui-splitpane-redesign FR-006: the right pane's placeholder state
    # while required left-pane inputs are still incomplete.
    "tui.result.placeholder": "Enter every input to see a result.",
    "tui.result.spindle_speed": "Spindle speed:     {value} RPM{mode_suffix}",
    "tui.result.spindle_speed.mode_suffix": " ({label})",
    "tui.result.spindle_speed.mode.standard": "recommended",
    "tui.result.spindle_speed.mode.power_constrained": "adjusted to fit available power",
    "tui.result.spindle_speed.mode.fixed_rpm": "user-specified",
    "tui.result.feed_rate": "Feed rate:         {value} {unit}",
    "tui.result.machining_time": "Machining time:    {value} min",
    "tui.result.torque": "Torque:            {value} {unit}",
    "tui.result.power_required": "Power required:    {value} {unit}",
    "tui.result.material_removal_rate": "Material removal:  {value} {unit}",
    "tui.result.warning": "\nWarning: {message}",
    "tui.result.error.title": "Calculation error",
    # --- Configuration screen (read-only, research.md #4) ---
    "tui.configuration.title": "Configuration",
    "tui.configuration.path_label.set": "Configuration file: {path}",
    "tui.configuration.path_label.default": "Configuration file: (bundled defaults)",
    "tui.configuration.section.material_types": "Material types: {items}",
    "tui.configuration.section.materials": "Materials ({material_type}): {items}",
    "tui.configuration.section.tools": "Drilling tools: {items}",
    # 018-tui-splitpane-redesign FR-015: closes the gap PR #94's review found
    # (Configuration only loaded the drilling registry) -- same screen being
    # rebuilt for this feature, don't patch it twice.
    "tui.configuration.section.end_mill_tools": "End-mill tools: {items}",
    "tui.configuration.section.face_mill_tools": "Face-mill tools: {items}",
    # --- About screen ---
    "tui.about.title": "About",
    "tui.about.text": (
        "{name} version {version}\n\nLicensed under the PolyForm Noncommercial License 1.0.0.\n"
        "See LICENSE.md for details."
    ),
    # --- Help screen (placeholder, FR-009) ---
    "tui.help.title": "Help",
    "tui.help.text": (
        "Use the arrow keys and Enter to navigate, or the highlighted letter shown "
        "on a menu item to jump to it directly. Press Tab to move between a screen's "
        "fields and its buttons. Choose Back to return to the previous screen."
    ),
}
