"""Measurement + enforcement helpers for the legacy-hardware performance suite.

This module implements the harness described in
``specs/006-legacy-hardware-performance-tests/contracts/performance-suite-contract.md``
and ``data-model.md``: platform-capability detection, single-core CPU-pin
enforcement, memory-ceiling enforcement, peak-memory measurement, wall-clock
timing, the ``PerformanceTestCase``/``PerformanceReport`` data structures, and
an ``overage_detail`` message builder for actionable failure reporting.

**Known measurement-isolation limitations** (research.md #5, spec.md Edge
Cases): ``resource.getrusage(...).ru_maxrss`` reports a **whole-process**,
monotonically-non-decreasing peak resident-set size. It is not scoped to a
single function call, so it can only *approximate* the incremental cost of
one measured call amid pytest's own baseline footprint (interpreter startup,
plugin loading, fixture setup, etc.) — it can never be lower than that
baseline, and repeated calls within the same process cannot show memory
being "freed" between them. Running each performance test case in relative
process isolation (i.e. not accumulating many heavy measurements in a single
long-lived process) reduces, but does not eliminate, this shared-baseline
effect. This is a documented, accepted limitation of the approach, not a
defect to be silently ignored.
"""

from __future__ import annotations

import contextlib
import os
import platform
import time
from dataclasses import dataclass, field
from typing import Any, Callable

try:
    import resource
except ImportError:  # pragma: no cover - Windows has no `resource` module.
    resource = None  # type: ignore[assignment]


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

    try:
        resource.setrlimit(resource.RLIMIT_AS, (ceiling_bytes, ceiling_bytes))
    except (ValueError, OSError):
        yield False
        return

    try:
        yield True
    finally:
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(resource.RLIMIT_AS, previous_limit)


def _ru_maxrss_bytes() -> int:
    """Read the current process's peak RSS (``ru_maxrss``), normalized to
    bytes.

    Linux reports ``ru_maxrss`` in kilobytes; macOS/BSD report it in bytes
    (research.md #3) — this normalizes the platform difference so callers
    always receive a byte count.
    """

    if resource is None:  # pragma: no cover - Windows has no `resource`.
        return 0

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


# ---------------------------------------------------------------------------
# Orchestration (composes the helpers above)
# ---------------------------------------------------------------------------


def run_case(case: PerformanceTestCase) -> PerformanceReport:
    """Run one :class:`PerformanceTestCase` and produce its
    :class:`PerformanceReport`.

    Applies the single-core pin and memory ceiling (best-effort, per
    platform capability), measures wall-clock time and peak memory for the
    single call to ``case.target``, compares both against the case's
    budgets (inclusive-pass: ``measured <= budget``), and builds an
    actionable ``overage_detail`` message when either check fails.
    """

    with pin_to_single_core(0) as cpu_pin_enforced:
        with enforce_memory_ceiling(case.memory_budget_bytes) as memory_ceiling_enforced:
            memory_before = _ru_maxrss_bytes()
            try:
                _result, elapsed_seconds = time_call(
                    case.target, *case.call_args, **case.call_kwargs
                )
            except Exception as exc:  # noqa: BLE001 — MemoryError/OSError/etc. → failing report
                # KeyboardInterrupt and SystemExit are BaseException subclasses,
                # not Exception subclasses, so they propagate naturally here.
                error_detail = (
                    f"{case.name}: ERROR during measurement — {type(exc).__name__}: {exc}"
                )
                return PerformanceReport(
                    case_name=case.name,
                    measured_time_seconds=0.0,
                    measured_memory_bytes=0,
                    time_passed=False,
                    memory_passed=False,
                    cpu_pin_enforced=cpu_pin_enforced,
                    memory_ceiling_enforced=memory_ceiling_enforced,
                    overage_detail=error_detail,
                )
            memory_after = _ru_maxrss_bytes()

    # Reported figure: the before/after delta (clamped at 0), not the raw
    # absolute ru_maxrss value, so the case's measured memory approximates
    # the incremental cost of this call rather than pytest's/the
    # interpreter's entire baseline footprint (research.md #5's documented
    # isolation approach; module docstring above details the limitation).
    measured_memory_bytes = max(memory_after - memory_before, 0)

    time_passed = elapsed_seconds <= case.time_budget_seconds
    memory_passed = measured_memory_bytes <= case.memory_budget_bytes

    overage_detail = build_overage_detail(
        case.name,
        time_passed=time_passed,
        measured_time_seconds=elapsed_seconds,
        time_budget_seconds=case.time_budget_seconds,
        memory_passed=memory_passed,
        measured_memory_bytes=measured_memory_bytes,
        memory_budget_bytes=case.memory_budget_bytes,
    )

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
