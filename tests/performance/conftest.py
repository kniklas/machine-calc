"""Auto-skip hook for the opt-in ``tests/performance/`` suite.

``pyproject.toml``'s ``testpaths = ["tests"]`` means a bare ``pytest`` run
(what CI's ``test`` job and any local default invocation use) discovers
files under ``tests/performance/`` by default, since it is a subdirectory of
``tests/``. This hook applies ``pytest.mark.skip`` to every item collected
under this directory unless ``MACHINE_CALC_RUN_PERFORMANCE_TESTS`` is set to
a truthy value, so the existing default/blocking suite's duration,
pass/fail outcome, and coverage percentage are unaffected (FR-006, FR-007,
SC-004, research.md #1) — the new tests are collected but auto-skipped at
near-zero cost, not the actual multi-second measurement runs.
"""

from __future__ import annotations

import os

import pytest

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _opt_in_enabled() -> bool:
    raw = os.environ.get("MACHINE_CALC_RUN_PERFORMANCE_TESTS", "")
    return raw.strip().lower() in _TRUTHY_VALUES


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _opt_in_enabled():
        return

    skip_marker = pytest.mark.skip(
        reason=(
            "tests/performance/ is opt-in — set MACHINE_CALC_RUN_PERFORMANCE_TESTS=1 "
            "to run (see specs/006-legacy-hardware-performance-tests/quickstart.md)"
        )
    )
    for item in items:
        if "tests/performance/" in str(item.fspath).replace(os.sep, "/"):
            item.add_marker(skip_marker)
