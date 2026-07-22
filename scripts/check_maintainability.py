#!/usr/bin/env python3
"""Enforce a minimum per-module Maintainability Index (MI) grade.

`xenon` (research.md originally assumed it enforced MI) only wraps radon's
*cyclomatic complexity* harvester (see `xenon.core`, which imports from
`radon.complexity`, not `radon.metrics`) -- it cannot enforce MI at all, and
`radon mi` itself has no CLI flag to fail the process on a threshold. This
script closes that gap: it runs `radon mi` and exits non-zero if any module
under the given path(s) ranks below ``MIN_GRADE`` (specs/003-ci-quality-security-gates
FR-002; supersedes the earlier `xenon --max-*` invocation documented in
pyproject.toml, which only ever duplicated FR-001's cyclomatic-complexity
check already enforced by the `lint` job's `ruff` C90 rule).

Usage: python scripts/check_maintainability.py <path> [<path> ...]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

# Version-controlled threshold (FR-010): the minimum acceptable Maintainability
# Index grade, per radon's A (best) > B > C > ... > F (worst) ranking.
MIN_GRADE = "B"


def main(paths: list[str]) -> int:
    if not paths:
        print("usage: check_maintainability.py <path> [<path> ...]", file=sys.stderr)
        return 2

    # -n <MIN_GRADE> -x F: display (and thus flag) only modules ranked
    # strictly worse than "A" (i.e., at or below MIN_GRADE), which is exactly
    # the set of modules that violate the FR-002 threshold.
    result = subprocess.run(
        ["radon", "mi", "-n", MIN_GRADE, "-x", "F", "-j", *paths],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    findings = json.loads(result.stdout or "{}")
    if not findings:
        print(f"All modules under {paths} meet the Maintainability Index threshold (rank A).")
        _emit_mi_summary(paths)
        return 0

    print("Maintainability Index threshold violations (FR-002):", file=sys.stderr)
    for path, info in findings.items():
        print(f"  {path}: MI={info['mi']:.2f} rank={info['rank']}", file=sys.stderr)
    return 1


def _emit_mi_summary(paths: list[str]) -> None:
    """Write an `mi_summary` line to `$GITHUB_OUTPUT`, if set (research.md #4).

    Re-runs `radon mi -j` *unfiltered* (no `-n`/`-x`) to get every module's
    rank/MI value -- the passing path above only received the (empty, by
    definition) set of modules *below* the threshold. Computes the average MI
    value and worst (alphabetically last, i.e. lowest) per-module rank across
    all modules. No-op if `GITHUB_OUTPUT` is unset (local/non-CI use), and
    intentionally best-effort: any failure here must not affect the script's
    CLI/stdout/exit-code contract for the passing path.
    """
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    try:
        result = subprocess.run(
            ["radon", "mi", "-j", *paths],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return
        modules = json.loads(result.stdout or "{}")
        if not modules:
            return

        mi_values = [info["mi"] for info in modules.values()]
        avg_mi = sum(mi_values) / len(mi_values)
        worst_rank = max(info["rank"] for info in modules.values())
    except (json.JSONDecodeError, KeyError, ValueError, ZeroDivisionError):
        return

    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"mi_summary=avg={avg_mi:.1f} worst={worst_rank}\n")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
