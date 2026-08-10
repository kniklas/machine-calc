"""Unit tests proving invalid memory measurements always fail (issue #23).

Most of these exercise ``tests.performance.harness``'s pure validation/
report-building helpers directly with hand-built child-process result
payloads, so they run as part of the normal (non-opt-in) test suite —
unlike ``tests/performance/test_calculation_budgets.py``, which lives under
the auto-skipped ``tests/performance/`` directory (see
``tests/performance/conftest.py``) and only runs when
``MACHINE_CALC_RUN_PERFORMANCE_TESTS=1`` is set. Most of these tests spawn
no subprocess at all — :func:`tests.performance.harness._build_report` is
deterministic given a result dict, which is what makes them unit-testable
without paying for/depending on real process isolation.

A few tests below (named ``test_run_case_in_child_*``) are the exception:
they deliberately DO exercise the real subprocess boundary via
:func:`tests.performance.harness._run_case_in_child` (a real spawned child,
a real target exception, and a real (shortened) timeout/hang/reap case),
since this is the only way to cover the pipe/serialization/process-lifecycle
code that hand-built payloads for ``_build_report`` cannot reach. These
still run in the default (non-opt-in) suite — unlike
``tests/performance/test_calculation_budgets.py`` — but pay the (small, sub-
second) cost of real process spawns.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `tests/` has no `__init__.py` (it is not a regular package, and pytest's
# default "prepend" import mode does not add the repository root to
# `sys.path` on its own — only the nearest package-free ancestor of each
# collected file, per file). Insert the repository root explicitly so
# `tests.performance` resolves as an (implicit namespace) package regardless
# of which test file pytest collects first or how it is invoked in CI.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.performance import harness, results  # noqa: E402 — must follow the sys.path fix-up above


def _case(**overrides: object) -> harness.PerformanceTestCase:
    defaults: dict[str, object] = {
        "name": "dummy-case",
        "target": lambda: None,
        "time_budget_seconds": 1.0,
        "memory_budget_bytes": 128 * 1024 * 1024,
    }
    defaults.update(overrides)
    return harness.PerformanceTestCase(**defaults)  # type: ignore[arg-type]


def _child_result(**overrides: object) -> dict:
    defaults: dict[str, object] = {
        "elapsed_seconds": 0.01,
        "memory_bytes": 1024,
        "error_type": None,
        "error_message": None,
        "cpu_pin_enforced": True,
        "memory_ceiling_enforced": True,
    }
    defaults.update(overrides)
    return defaults


def test_is_valid_memory_measurement_rejects_zero_and_none_and_negative():
    assert harness._is_valid_memory_measurement(1) is True
    assert harness._is_valid_memory_measurement(0) is False
    assert harness._is_valid_memory_measurement(None) is False
    assert harness._is_valid_memory_measurement(-1) is False


def test_zero_byte_memory_reading_fails_the_case():
    """A `0 B` reading (this issue's original symptom) must never pass."""

    case = _case()
    child_result = _child_result(memory_bytes=0)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.measured_memory_bytes == 0
    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail


def test_none_memory_reading_fails_the_case():
    """An unavailable/never-taken reading (e.g. no `resource` module, or a
    crashed child) must also never pass."""

    case = _case()
    child_result = _child_result(memory_bytes=None)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.measured_memory_bytes == 0
    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail


def test_negative_memory_reading_fails_the_case():
    case = _case()
    child_result = _child_result(memory_bytes=-5)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail


def test_positive_memory_reading_within_budget_passes():
    case = _case(memory_budget_bytes=1000)
    child_result = _child_result(memory_bytes=500)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is True
    assert report.measured_memory_bytes == 500
    assert report.memory_measurement_valid is True
    assert report.overage_detail is None


def test_positive_memory_reading_over_budget_fails_without_invalid_note():
    """A real (valid) over-budget reading fails for being over budget, not
    for being "invalid" — the two failure modes must stay distinguishable."""

    case = _case(memory_budget_bytes=100)
    child_result = _child_result(memory_bytes=500)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.memory_measurement_valid is True
    assert "budget exceeded" in report.overage_detail
    assert "invalid memory measurement" not in report.overage_detail


def test_child_process_error_fails_both_dimensions():
    case = _case()
    child_result = _child_result(
        memory_bytes=None,
        error_type="ChildProcessError",
        error_message="measurement child process exited without reporting a result (exit code -9)",
    )

    report = harness._build_report(case, child_result)

    assert report.time_passed is False
    assert report.memory_passed is False
    assert report.memory_measurement_valid is False
    assert "ChildProcessError" in report.overage_detail


def test_crashed_child_with_invalid_memory_includes_invalid_note_not_fabricated_overage():
    """A crashed child with no usable memory reading must state the reading
    is invalid, not compute a bogus overage against a `0`/`None` value."""

    case = _case()
    child_result = _child_result(
        memory_bytes=None,
        error_type="ChildProcessError",
        error_message="measurement child process exited without reporting a result (exit code -9)",
    )

    report = harness._build_report(case, child_result)

    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail
    assert "over by -" not in report.overage_detail


def test_crashed_target_with_valid_memory_reports_real_overage():
    """A target exception with a real memory reading captured beforehand
    (e.g. hit the enforced ceiling) should still report a genuine overage,
    not an invalid-measurement note."""

    case = _case(memory_budget_bytes=100)
    child_result = _child_result(
        memory_bytes=500,
        error_type="MemoryError",
        error_message="",
    )

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.memory_measurement_valid is True
    assert "invalid memory measurement" not in report.overage_detail
    assert "over by 400 bytes" in report.overage_detail


def test_crashed_target_with_valid_within_budget_memory_reports_no_negative_overage():
    """A target exception with a real, *within-budget* memory reading (e.g.
    a `MemoryError` triggered by something other than the tracked resource,
    with only 500 bytes measured against a 128MB budget) must never report
    a fabricated negative "over by" figure — it should instead say the
    reading was within budget."""

    case = _case(memory_budget_bytes=128 * 1024 * 1024)
    child_result = _child_result(
        memory_bytes=500,
        error_type="MemoryError",
        error_message="",
    )

    report = harness._build_report(case, child_result)

    assert report.memory_measurement_valid is True
    assert "invalid memory measurement" not in report.overage_detail
    assert "over by" not in report.overage_detail
    assert "within the" in report.overage_detail
    assert "byte memory budget" in report.overage_detail


def _sum_small_range() -> int:
    return sum(range(1000))


def test_run_case_in_child_measures_a_real_subprocess():
    """Exercises the actual subprocess boundary (:func:`_run_case_in_child`),
    not just :func:`_build_report` with a synthetic payload — proves a real
    spawned child reports a genuine positive RSS reading and a valid
    measurement, end-to-end through the pipe/serialization boundary.

    Uses a module-level (picklable) target: the ``spawn`` context requires
    the target be importable by name in the fresh child interpreter, unlike
    a lambda/closure.
    """

    case = _case(target=_sum_small_range)

    child_result = harness._run_case_in_child(case)

    assert child_result["error_type"] is None
    assert child_result["memory_bytes"] is not None
    assert harness._is_valid_memory_measurement(child_result["memory_bytes"]) is True
    assert child_result["elapsed_seconds"] >= 0.0

    report = harness._build_report(case, child_result)
    assert report.memory_measurement_valid is True
    assert report.time_passed is True


def _raise_value_error() -> None:
    raise ValueError("boom")


def test_run_case_in_child_reports_target_exception_without_crashing_harness():
    """A target that raises inside the child process must be reported as an
    error result (not propagate/crash the parent), through the real
    subprocess boundary."""

    case = _case(target=_raise_value_error)

    child_result = harness._run_case_in_child(case)

    assert child_result["error_type"] == "ValueError"
    assert "boom" in (child_result["error_message"] or "")

    report = harness._build_report(case, child_result)
    assert report.time_passed is False
    assert report.memory_passed is False


def test_run_case_in_child_times_out_and_is_reaped_promptly():
    """A hung child (never returns) must be terminated and reported as an
    invalid/failed measurement, and must not block for materially longer
    than one timeout window (regression test for the double-timeout bug
    fixed in an earlier review round)."""

    import time as _time

    original_timeout = harness._CHILD_TIMEOUT_SECONDS
    harness._CHILD_TIMEOUT_SECONDS = 0.5
    try:
        case = _case(target=_hang_forever)

        start = _time.perf_counter()
        child_result = harness._run_case_in_child(case)
        elapsed = _time.perf_counter() - start

        # Generous upper bound: should be roughly 1x the (shortened) timeout,
        # never ~2x it (the double-timeout bug this test guards against).
        assert elapsed < harness._CHILD_TIMEOUT_SECONDS * 3
        assert child_result["error_type"] is not None
        assert child_result["memory_bytes"] is None

        report = harness._build_report(case, child_result)
        assert report.memory_measurement_valid is False
        assert report.memory_passed is False
    finally:
        harness._CHILD_TIMEOUT_SECONDS = original_timeout


def _hang_forever() -> None:
    import time

    time.sleep(3600)


def test_build_suite_run_summary_flags_any_invalid_memory_measurement():
    """Covers the aggregation step Copilot's review flagged as untested:
    a suite containing one invalid-measurement report must still surface
    ``any_invalid_memory_measurement=True`` in the Suite Run Summary, even
    when every other report in the run is perfectly valid — this is the
    signal ``ci.yml`` relies on to give a hard "fail" precedence over the
    weaker "⚠️ degraded" label (issue #23)."""

    valid_case = _case(name="valid-case")
    valid_report = harness._build_report(valid_case, _child_result(memory_bytes=1024))
    assert valid_report.memory_measurement_valid is True

    invalid_case = _case(name="invalid-case")
    invalid_report = harness._build_report(invalid_case, _child_result(memory_bytes=None))
    assert invalid_report.memory_measurement_valid is False

    summary = results.build_suite_run_summary([valid_report, invalid_report])

    assert summary["any_invalid_memory_measurement"] is True
    # A single invalid case must not be washed out by an otherwise-valid run.
    assert summary["has_measurements"] is True


def test_build_suite_run_summary_reports_no_invalid_measurement_when_all_valid():
    case_a = _case(name="case-a")
    case_b = _case(name="case-b")
    report_a = harness._build_report(case_a, _child_result(memory_bytes=1024))
    report_b = harness._build_report(case_b, _child_result(memory_bytes=2048))

    summary = results.build_suite_run_summary([report_a, report_b])

    assert summary["any_invalid_memory_measurement"] is False
