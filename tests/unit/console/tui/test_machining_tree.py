"""Unit tests for MachiningTree's expand/collapse state transitions
(018-tui-splitpane-redesign, data-model.md, tasks.md T041).

Rewritten (revision, tasks.md Phase 8): `MachiningTree` lost
`toggle_drilling()`/`drilling_expanded` entirely -- Drilling's tree-level
tool-selection sub-expansion was retired (FR-003) via `/speckit-clarify`,
reopened after implementation. `expanded` is now the entity's only field,
so there is no longer a sub-state validation rule to exercise.
"""

from __future__ import annotations

from mfgparams.console.tui.app import MachiningTree


def test_starts_collapsed():
    tree = MachiningTree()
    assert tree.expanded is False


def test_toggle_machining_expands_then_collapses():
    tree = MachiningTree()

    tree.toggle_machining()
    assert tree.expanded is True

    tree.toggle_machining()
    assert tree.expanded is False
