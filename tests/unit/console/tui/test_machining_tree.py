"""Unit tests for MachiningTree's expand/collapse state transitions
(018-tui-splitpane-redesign, data-model.md, tasks.md T006).
"""

from __future__ import annotations

from mfgparams.console.tui.app import MachiningTree


def test_starts_collapsed():
    tree = MachiningTree()
    assert tree.expanded is False
    assert tree.drilling_expanded is False


def test_toggle_machining_expands_then_collapses():
    tree = MachiningTree()

    tree.toggle_machining()
    assert tree.expanded is True

    tree.toggle_machining()
    assert tree.expanded is False


def test_collapsing_machining_implicitly_collapses_drilling_shortcut():
    """Acceptance Scenario 4: re-expanding Machining starts from a
    collapsed Drilling sub-node -- there is no independent sub-state to
    preserve across a Machining collapse."""

    tree = MachiningTree()
    tree.toggle_machining()
    tree.toggle_drilling()
    assert tree.drilling_expanded is True

    tree.toggle_machining()
    assert tree.expanded is False
    assert tree.drilling_expanded is False


def test_toggle_drilling_only_meaningful_while_machining_expanded():
    """Selecting the Drilling shortcut while Machining itself is collapsed
    has nothing to expand into -- a no-op, not an error."""

    tree = MachiningTree()
    tree.toggle_drilling()
    assert tree.drilling_expanded is False


def test_toggle_drilling_expands_and_collapses_independently_of_machining():
    tree = MachiningTree()
    tree.toggle_machining()

    tree.toggle_drilling()
    assert tree.drilling_expanded is True
    assert tree.expanded is True

    tree.toggle_drilling()
    assert tree.drilling_expanded is False
    assert tree.expanded is True


def test_validation_rule_drilling_expanded_never_true_while_collapsed():
    """data-model.md's validation rule, exercised via every public
    mutator -- not just the happy path above."""

    tree = MachiningTree()
    tree.toggle_machining()
    tree.toggle_drilling()
    tree.toggle_machining()  # collapse Machining while Drilling is expanded
    assert tree.expanded is False
    assert tree.drilling_expanded is False
