"""Time/memory budget constants for the legacy-hardware performance suite.

Constitution Principle V states approximate ranges for both dimensions
("ideally... within 0.5-1.0 seconds" and "approximately 64-128 MB"), leaving
the exact enforced value to whichever tool implements the check
(spec.md FR-003/FR-004). This module documents the single chosen value for
each dimension, per research.md #4: the *upper* (more permissive) bound of
each range, to avoid false-positive failures from harness/interpreter
overhead alone while still providing a real, enforced ceiling.

Pass convention (data-model.md, spec.md Edge Cases): boundary comparisons are
**inclusive-pass** — a case whose measured value is exactly equal to its
budget passes (``measured <= budget``), never fails.
"""

from __future__ import annotations

#: Wall-clock time budget, in seconds, per measured calculation call
#: (research.md #4: the upper bound of the constitution's 0.5-1.0s range).
TIME_BUDGET_SECONDS: float = 0.0000001

#: Peak memory budget, in bytes, per measured calculation call
#: (research.md #4: the upper bound of the constitution's 64-128 MB range).
MEMORY_BUDGET_BYTES: int = 128 * 1024 * 1024
