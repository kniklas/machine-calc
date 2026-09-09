"""Opt-in legacy-hardware startup budget check for the text GUI (tasks.md
T036, Constitution Principle V, plan.md's Constitution Check row V).

The pre-plan technical spike (spike-tui-framework.md) measured
prompt-toolkit's own footprint in isolation; this measures the cost of the
*shipped* app -- reaching a launchable console -- against the same budget
the rest of this suite uses for a single calculation call
(`budgets.MEMORY_BUDGET_BYTES`/`TIME_BUDGET_SECONDS`, the upper bound of
Principle V's ranges), since Principle V's constraint describes the whole
application, not a per-function ceiling.

Importing only `mfgparams.console.cli` under-measured this (Copilot review
on PR #94): `cli.py` imports just `terminal_capability`, and defers
`tui.app` to `main()`; `tui.app.run()` in turn defers every screen/menu
module (and therefore prompt-toolkit itself) to its own function body. So
that single import never actually reached prompt-toolkit or any screen
module, and a real regression there could not fail this budget. This
instead imports every module `tui.app.run()` imports before it ever blocks
on the first keystroke -- the same set, kept in sync with that function's
own import block -- without calling `run()` itself (which would block
waiting for real terminal input).

Skipped by default; run explicitly via::

    MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/test_tui_startup_budget.py \\
        -p no:cacheprovider --no-cov -v -s
"""

from __future__ import annotations

from . import budgets, harness


def _import_tui_launch_graph() -> bool:
    """Picklable, module-level target for `harness.run_case`'s isolated
    child process: the realistic cold-start cost of reaching a launchable
    console -- every module `tui.app.run()` imports before it ever blocks
    on the first keystroke, kept in sync with that function's own import
    block."""

    import mfgparams.console.cli  # noqa: F401 -- the entry-point wiring itself
    import mfgparams.console.tui.machining_menu  # noqa: F401
    import mfgparams.console.tui.menu  # noqa: F401
    import mfgparams.console.tui.screens.about  # noqa: F401
    import mfgparams.console.tui.screens.configuration  # noqa: F401
    import mfgparams.console.tui.screens.drilling  # noqa: F401
    import mfgparams.console.tui.screens.help  # noqa: F401
    import mfgparams.console.tui.screens.milling  # noqa: F401

    return True


CASES: list[harness.PerformanceTestCase] = [
    harness.PerformanceTestCase(
        name="import the TUI's real launch module graph (text GUI cold start)",
        target=_import_tui_launch_graph,
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
