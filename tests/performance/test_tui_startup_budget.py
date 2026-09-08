"""Opt-in legacy-hardware startup budget check for the text GUI (tasks.md
T036, Constitution Principle V, plan.md's Constitution Check row V).

The pre-plan technical spike (spike-tui-framework.md) measured
prompt-toolkit's own footprint in isolation; this measures the cost of the
*shipped* app -- importing `mfgparams.console.cli` (which transitively
imports prompt-toolkit, every `console/tui/` screen, and the core
calculation/registry modules those screens call) -- against the same
budget the rest of this suite uses for a single calculation call
(`budgets.MEMORY_BUDGET_BYTES`/`TIME_BUDGET_SECONDS`, the upper bound of
Principle V's ranges), since Principle V's constraint describes the whole
application, not a per-function ceiling.

Skipped by default; run explicitly via::

    MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/test_tui_startup_budget.py \\
        -p no:cacheprovider --no-cov -v -s
"""

from __future__ import annotations

from . import budgets, harness


def _import_console_cli() -> bool:
    """Picklable, module-level target for `harness.run_case`'s isolated
    child process: the realistic cold-start cost of reaching a launchable
    console -- everything `mfgparams.console.cli` pulls in transitively."""

    import mfgparams.console.cli  # noqa: F401

    return True


CASES: list[harness.PerformanceTestCase] = [
    harness.PerformanceTestCase(
        name="import mfgparams.console.cli (text GUI cold start)",
        target=_import_console_cli,
        time_budget_seconds=budgets.TIME_BUDGET_SECONDS,
        memory_budget_bytes=budgets.MEMORY_BUDGET_BYTES,
    ),
]


def test_tui_cold_start_budget():
    reports = [harness.run_case(case) for case in CASES]
    failures = [r.overage_detail for r in reports if r.overage_detail]
    assert not failures, "\n".join(failures)
    for report in reports:
        assert report.memory_measurement_valid, report.case_name
