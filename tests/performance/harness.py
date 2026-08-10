"""Measurement + enforcement helpers for the legacy-hardware performance suite.

This module implements the harness described in
``specs/006-legacy-hardware-performance-tests/contracts/performance-suite-contract.md``
and ``data-model.md``: platform-capability detection, single-core CPU-pin
enforcement, memory-ceiling enforcement, peak-memory measurement, wall-clock
timing, the ``PerformanceTestCase``/``PerformanceReport`` data structures, and
an ``overage_detail`` message builder for actionable failure reporting.

**Isolated child-process memory measurement** (issue #23): each case's
``target`` call now runs in its own isolated child process
(:func:`run_case`/:func:`_run_case_in_child`), and the *absolute* peak RSS
(``resource.getrusage(...).ru_maxrss``) observed by that child is reported,
rather than subtracting two whole-pytest-process high-water marks. A
before/after delta within the long-lived pytest process is unreliable:
``ru_maxrss`` is monotonically non-decreasing for the process's entire
lifetime, so small calculations that don't exceed pytest's own already-high
baseline peak produce a ``0`` delta — a measurement that looks like a
passing "0 MB used" result but is actually not a real measurement at all.
Measuring the child's own absolute peak means interpreter/import overhead is
consistently included and the reported number is a genuine, meaningful
figure rather than an artifact of measurement order.

**Fail-safe validation**: any missing, non-positive, or otherwise
uninterpretable memory reading (e.g. the child crashed before reporting, or
``resource`` is unavailable on this platform) is treated as an invalid
measurement, not a passing "0 bytes used" result — it always fails the
case's memory check and produces an explicit ``invalid memory measurement``
diagnostic (FR-009/FR-010).
"""

from __future__ import annotations

import contextlib
import multiprocessing
import os
import platform
import time
from dataclasses import dataclass, field
from typing import Any, Callable

try:
    import resource
except ImportError:  # pragma: no cover - Windows has no `resource` module.
    resource = None  # type: ignore[assignment]

#: Generous ceiling on how long we wait for a child measurement process to
#: report back before treating it as hung/crashed. Deliberately much larger
#: than any real case's time budget so it never causes a false failure by
#: itself — it only guards against a truly stuck child process.
_CHILD_TIMEOUT_SECONDS = 30.0


# ---------------------------------------------------------------------------
# Platform-capability detection (contracts/performance-suite-contract.md)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlatformCapabilities:
    """Reports which enforcement mechanisms are usable on this host.

    Attributes:
        cpu_pin_available: Whether ``os.sched_setaffinity`` exists (Linux
            only per research.md #2).
        memory_ceiling_available: Whether the POSIX ``resource`` module (and
            therefore ``resource.setrlimit(RLIMIT_AS, ...)``) is usable
            (Linux/macOS per research.md #3).
    """

    cpu_pin_available: bool
    memory_ceiling_available: bool


def detect_platform_capabilities() -> PlatformCapabilities:
    """Detect which enforcement mechanisms are available on this host.

    Matches the platform-capability table in
    ``contracts/performance-suite-contract.md``: Linux supports both
    mechanisms, macOS supports only the memory ceiling, Windows supports
    neither.
    """

    cpu_pin_available = hasattr(os, "sched_setaffinity")
    memory_ceiling_available = resource is not None
    return PlatformCapabilities(
        cpu_pin_available=cpu_pin_available,
        memory_ceiling_available=memory_ceiling_available,
    )


# ---------------------------------------------------------------------------
# Single-core CPU pin enforcement (FR-002, FR-009)
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def pin_to_single_core(core_id: int = 0):
    """Pin the current process to exactly one CPU core, if possible.

    Restores the prior affinity mask on exit. When ``os.sched_setaffinity``
    is unavailable (macOS, Windows), this is a no-op that does not raise
    (FR-009) — callers should check :func:`detect_platform_capabilities`'s
    ``cpu_pin_available`` to know whether the pin was actually applied.

    Yields:
        ``True`` if the pin was applied, ``False`` if skipped/best-effort.
    """

    if not hasattr(os, "sched_setaffinity"):
        yield False
        return

    try:
        previous_affinity = os.sched_getaffinity(0)  # type: ignore[attr-defined]
    except (OSError, ValueError):
        yield False
        return

    try:
        os.sched_setaffinity(0, {core_id})  # type: ignore[attr-defined]
    except (OSError, ValueError):
        yield False
        return

    try:
        yield True
    finally:
        with contextlib.suppress(OSError, ValueError):
            os.sched_setaffinity(0, previous_affinity)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Memory-ceiling enforcement + peak-memory measurement (FR-003, FR-009)
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def enforce_memory_ceiling(ceiling_bytes: int):
    """Cap the process's virtual address space for the duration of a block.

    Uses ``resource.setrlimit(resource.RLIMIT_AS, (ceiling_bytes,
    ceiling_bytes))`` when the ``resource`` module is available (Linux,
    macOS). Restores the prior limit on exit. When ``resource`` is
    unavailable (Windows) or ``setrlimit`` raises ``ValueError``/``OSError``
    for the chosen limit, this is a no-op that does not raise (FR-009).

    Yields:
        ``True`` if the ceiling was applied, ``False`` if skipped/best-effort.
    """

    if resource is None:
        yield False
        return

    try:
        previous_limit = resource.getrlimit(resource.RLIMIT_AS)
    except (ValueError, OSError):
        yield False
        return

    # Only lower the *soft* limit, keeping the process's existing hard limit
    # untouched. Setting the hard limit to `ceiling_bytes` too would make the
    # cap effectively permanent for an unprivileged process: raising a hard
    # limit back up requires privilege, so the `finally` block's restore
    # below would silently fail (caught by `contextlib.suppress`) and leave
    # every subsequent test in the process capped at 128 MB.
    _previous_soft, previous_hard = previous_limit
    try:
        resource.setrlimit(resource.RLIMIT_AS, (ceiling_bytes, previous_hard))
    except (ValueError, OSError):
        yield False
        return

    try:
        yield True
    finally:
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(resource.RLIMIT_AS, previous_limit)


def _ru_maxrss_bytes() -> int | None:
    """Read the current process's peak RSS (``ru_maxrss``), normalized to
    bytes.

    Linux reports ``ru_maxrss`` in kilobytes; macOS/BSD report it in bytes
    (research.md #3) — this normalizes the platform difference so callers
    always receive a byte count.

    Returns ``None`` on Windows, where the ``resource`` module does not
    exist and peak RSS cannot be measured at all. Callers MUST NOT treat
    ``None`` as "0 bytes used" — that would silently report a passing
    memory check for a measurement that never happened (FR-009/FR-010).
    """

    if resource is None:  # pragma: no cover - Windows has no `resource`.
        return None

    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Linux":
        return raw * 1024
    return raw


# ---------------------------------------------------------------------------
# Wall-clock timing (research.md #5)
# ---------------------------------------------------------------------------


def time_call(target: Callable[..., Any], *call_args: Any, **call_kwargs: Any) -> tuple[Any, float]:
    """Call ``target`` and return ``(result, elapsed_seconds)``.

    Wraps only the target call itself with ``time.perf_counter()``, not
    fixture setup or pytest's own collection/reporting (research.md #5).
    """

    start = time.perf_counter()
    result = target(*call_args, **call_kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


# ---------------------------------------------------------------------------
# Data structures (data-model.md)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerformanceTestCase:
    """One measured calculation: target, representative input, and budgets."""

    name: str
    target: Callable[..., Any]
    call_args: tuple[Any, ...] = field(default_factory=tuple)
    call_kwargs: dict[str, Any] = field(default_factory=dict)
    time_budget_seconds: float = 0.0
    memory_budget_bytes: int = 0


@dataclass(frozen=True)
class PerformanceReport:
    """The outcome of running one :class:`PerformanceTestCase`."""

    case_name: str
    measured_time_seconds: float
    measured_memory_bytes: int
    time_passed: bool
    memory_passed: bool
    cpu_pin_enforced: bool
    memory_ceiling_enforced: bool
    overage_detail: str | None = None


# ---------------------------------------------------------------------------
# Actionable overage reporting (FR-005, User Story 3)
# ---------------------------------------------------------------------------


def _percentage_over(measured: float, budget: float) -> float:
    """Return the percentage by which ``measured`` exceeds ``budget``.

    Returns ``0.0`` for a non-positive budget (defensive; budgets are always
    positive constants in this suite) to avoid a division-by-zero.
    """

    if budget <= 0:
        return 0.0
    return ((measured - budget) / budget) * 100


def build_overage_detail(
    case_name: str,
    *,
    time_passed: bool,
    measured_time_seconds: float,
    time_budget_seconds: float,
    memory_passed: bool,
    measured_memory_bytes: int,
    memory_budget_bytes: int,
) -> str | None:
    """Compose one distinct, human-readable overage message per failed
    dimension, or ``None`` when both dimensions passed.

    Per data-model.md's validation rule, a time failure and a memory failure
    are always reported as separate messages, never merged into one
    ambiguous message, and each message names the calculation, the failed
    dimension, the measured value, the configured budget, and the
    amount/percentage exceeded (FR-005).
    """

    messages: list[str] = []

    if not time_passed:
        overage_seconds = measured_time_seconds - time_budget_seconds
        percent = _percentage_over(measured_time_seconds, time_budget_seconds)
        messages.append(
            f"{case_name}: TIME budget exceeded — measured {measured_time_seconds:.4f}s "
            f"> budget {time_budget_seconds:.4f}s "
            f"(over by {overage_seconds:.4f}s, {percent:.1f}%)"
        )

    if not memory_passed:
        overage_bytes = measured_memory_bytes - memory_budget_bytes
        percent = _percentage_over(measured_memory_bytes, memory_budget_bytes)
        messages.append(
            f"{case_name}: MEMORY budget exceeded — measured {measured_memory_bytes} bytes "
            f"> budget {memory_budget_bytes} bytes "
            f"(over by {overage_bytes} bytes, {percent:.1f}%)"
        )

    if not messages:
        return None
    return "; ".join(messages)


def _is_valid_memory_measurement(memory_bytes: int | None) -> bool:
    """Return whether ``memory_bytes`` is a real, usable RSS reading.

    A valid measurement is a positive integer. ``None`` (measurement never
    taken — e.g. no ``resource`` module, or the child crashed before
    reporting) and non-positive values (``0`` or negative — never a
    meaningful RSS reading; a live process always occupies some resident
    memory) are both invalid (issue #23): a zero-byte reading is an artifact
    of a broken measurement, not a real "0 bytes used" result, and must never
    be treated as a passing memory check.
    """

    return memory_bytes is not None and memory_bytes > 0


# ---------------------------------------------------------------------------
# Child-process worker (isolated measurement, issue #23)
# ---------------------------------------------------------------------------


def _child_worker(
    target: Callable[..., Any],
    call_args: tuple[Any, ...],
    call_kwargs: dict[str, Any],
    memory_budget_bytes: int,
    conn: Any,
) -> None:
    """Run inside the isolated child process spawned by :func:`run_case`.

    Applies the single-core pin and memory ceiling *inside the child* (they
    must be scoped to the process actually performing the measured call),
    times only the call to ``target``, and reports the child's own absolute
    peak RSS — not a delta against some other process's baseline — back to
    the parent over ``conn``. Any exception raised by ``target`` is caught
    and reported (by type name + message) rather than propagated, so the
    parent always receives a result instead of a silently-dead pipe.
    """

    error_type: str | None = None
    error_message: str | None = None
    with pin_to_single_core(0) as cpu_pin_enforced:
        with enforce_memory_ceiling(memory_budget_bytes) as memory_ceiling_enforced:
            start = time.perf_counter()
            try:
                target(*call_args, **call_kwargs)
            except Exception as exc:  # noqa: BLE001 — MemoryError/OSError/etc. → failing report
                # KeyboardInterrupt and SystemExit are BaseException
                # subclasses, not Exception subclasses, so they propagate
                # naturally here (and terminate the child process, which the
                # parent detects via a closed connection/exit code).
                error_type = type(exc).__name__
                error_message = str(exc)
            elapsed_seconds = time.perf_counter() - start
            # The child's own absolute peak RSS, observed even on error:
            # e.g. the enforced ceiling's `MemoryError` fires right around
            # the peak, so a crash is reported using whatever was actually
            # observed, never a fabricated "0 bytes" reading.
            memory_bytes = _ru_maxrss_bytes()

    conn.send(
        {
            "elapsed_seconds": elapsed_seconds,
            "memory_bytes": memory_bytes,
            "error_type": error_type,
            "error_message": error_message,
            "cpu_pin_enforced": cpu_pin_enforced,
            "memory_ceiling_enforced": memory_ceiling_enforced,
        }
    )
    conn.close()


def _run_case_in_child(case: PerformanceTestCase) -> dict[str, Any]:
    """Run ``case.target`` in an isolated child process and return its
    reported result dict (see :func:`_child_worker`).

    If the child dies before reporting anything (crash, OS-level kill,
    timeout), returns a result dict with ``memory_bytes=None`` and an
    explicit ``error_type``/``error_message`` describing the failure, so the
    caller always has a well-formed result to build a
    :class:`PerformanceReport` from — never a bare exception or a fabricated
    zero.
    """

    # "fork" (Linux/macOS) starts a fresh child fast; where unavailable
    # (Windows — which also has no `resource` module, so memory is already
    # reported invalid there) fall back to the platform default.
    start_methods = multiprocessing.get_all_start_methods()
    context = multiprocessing.get_context("fork" if "fork" in start_methods else None)

    parent_conn, child_conn = context.Pipe(duplex=False)
    process = context.Process(
        target=_child_worker,
        args=(case.target, case.call_args, case.call_kwargs, case.memory_budget_bytes, child_conn),
    )
    process.start()
    child_conn.close()

    payload: dict[str, Any] | None = None
    if parent_conn.poll(_CHILD_TIMEOUT_SECONDS):
        with contextlib.suppress(EOFError, OSError):
            payload = parent_conn.recv()
    parent_conn.close()

    process.join(_CHILD_TIMEOUT_SECONDS)
    if process.is_alive():  # pragma: no cover - only on a genuinely hung child
        process.terminate()
        process.join()

    if payload is not None:
        return payload

    return {
        "elapsed_seconds": 0.0,
        "memory_bytes": None,
        "error_type": "ChildProcessError",
        "error_message": (
            "measurement child process exited without reporting a result "
            f"(exit code {process.exitcode})"
        ),
        "cpu_pin_enforced": False,
        "memory_ceiling_enforced": False,
    }


# ---------------------------------------------------------------------------
# Orchestration (composes the helpers above)
# ---------------------------------------------------------------------------


def _build_report(case: PerformanceTestCase, child_result: dict[str, Any]) -> PerformanceReport:
    """Turn one child-process result dict into a :class:`PerformanceReport`.

    Pure/deterministic given ``child_result`` (no subprocess involved), so
    it is unit-testable directly with hand-built payloads (see
    ``tests/unit/performance/test_harness_memory_validation.py``) — in
    particular to prove that a ``0`` or ``None`` memory reading always
    fails the case rather than reporting a false pass (issue #23).
    """

    elapsed_seconds: float = child_result["elapsed_seconds"]
    measured_memory_bytes_raw: int | None = child_result["memory_bytes"]
    error_type: str | None = child_result["error_type"]
    error_message: str | None = child_result["error_message"]
    cpu_pin_enforced: bool = child_result["cpu_pin_enforced"]
    memory_ceiling_enforced: bool = child_result["memory_ceiling_enforced"]

    memory_valid = _is_valid_memory_measurement(measured_memory_bytes_raw)
    # Reported figure is always an int for the report/summary/CI consumers,
    # even when invalid — the `memory_passed=False` below (never bypassed by
    # this substitution) is what actually blocks the run, not this display
    # value.
    measured_memory_bytes = (
        measured_memory_bytes_raw if measured_memory_bytes_raw is not None else 0
    )

    time_passed = elapsed_seconds <= case.time_budget_seconds
    memory_passed = memory_valid and measured_memory_bytes <= case.memory_budget_bytes

    overage_detail: str | None
    if error_type is not None:
        time_passed = False
        memory_passed = False
        overage_bytes = measured_memory_bytes - case.memory_budget_bytes
        overage_detail = (
            f"{case.name}: ERROR during measurement — {error_type}: {error_message} "
            f"(observed {elapsed_seconds:.4f}s / {measured_memory_bytes} bytes before "
            f"the error; memory budget {case.memory_budget_bytes} bytes, "
            f"over by {overage_bytes} bytes)"
        )
    else:
        # Suppress build_overage_detail's own memory message when the
        # reading is invalid — that already-generic message would otherwise
        # misleadingly claim "measured 0 bytes > budget" instead of
        # explaining that no real measurement was taken at all.
        overage_detail = build_overage_detail(
            case.name,
            time_passed=time_passed,
            measured_time_seconds=elapsed_seconds,
            time_budget_seconds=case.time_budget_seconds,
            memory_passed=memory_passed or not memory_valid,
            measured_memory_bytes=measured_memory_bytes,
            memory_budget_bytes=case.memory_budget_bytes,
        )
        if not memory_valid:
            invalid_note = (
                f"{case.name}: invalid memory measurement — reading was "
                f"{measured_memory_bytes_raw!r} bytes (must be a positive integer); "
                "reported as failing rather than a false pass (FR-009/FR-010)."
            )
            overage_detail = "; ".join(filter(None, [overage_detail, invalid_note]))

    return PerformanceReport(
        case_name=case.name,
        measured_time_seconds=elapsed_seconds,
        measured_memory_bytes=measured_memory_bytes,
        time_passed=time_passed,
        memory_passed=memory_passed,
        cpu_pin_enforced=cpu_pin_enforced,
        memory_ceiling_enforced=memory_ceiling_enforced,
        overage_detail=overage_detail,
    )


def run_case(case: PerformanceTestCase) -> PerformanceReport:
    """Run one :class:`PerformanceTestCase` and produce its
    :class:`PerformanceReport`.

    Runs ``case.target`` in an isolated child process (:func:`_run_case_in_child`)
    and reports that child's absolute peak RSS rather than a delta between
    two whole-pytest-process readings, comparing both time and memory
    against the case's budgets (inclusive-pass: ``measured <= budget``). Any
    missing, zero, or negative memory reading is always treated as an
    invalid measurement — never a passing "0 bytes used" result
    (issue #23) — and builds an actionable ``overage_detail`` message when
    either check fails.
    """

    child_result = _run_case_in_child(case)
    return _build_report(case, child_result)
