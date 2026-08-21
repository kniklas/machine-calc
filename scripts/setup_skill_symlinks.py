#!/usr/bin/env python3
"""Symlink genuinely shared, hand-authored skills from `.github/skills/`
(GitHub Copilot's skill directory) into `.claude/skills/` (Claude Code's),
per Constitution Principle XI's "genuinely shared, hand-authored skills"
exception (v1.9.0): each skill stays a single canonical file under
`.github/skills/<name>/SKILL.md`, referenced elsewhere only via a symlink,
never a hand-copied duplicate.

Safe to re-run: an already-correct symlink is left untouched, a symlink
pointing at the wrong target is corrected, and a real file/directory
already at the destination is never overwritten (reported as a conflict
instead, since it may be a contributor's unrelated content).

Usage: python scripts/setup_skill_symlinks.py [--check]

    --check: report what would change (or is already correct) without
        writing anything; exits non-zero if any skill is missing/wrong,
        for use as a manual verification step.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / ".github" / "skills"
DEST_DIR = REPO_ROOT / ".claude" / "skills"

# Skills deliberately excluded from the symlink even though they have a
# `.github/skills/<name>/SKILL.md`. `code-review` collides with Claude
# Code's own bundled `/code-review` skill (correctness/bug-hunting review,
# `--fix`/`--comment`/`ultra`); Claude Code resolves same-name conflicts by
# giving a project skill precedence over a bundled one, so symlinking it
# would silently shadow the bundled skill instead of adding to it. Add a
# name here (with a comment explaining why) if a future `.github/skills/`
# entry turns out to collide with another Claude Code bundled skill.
EXCLUDED = {"code-review"}


def discover_source_skills() -> list[str]:
    if not SOURCE_DIR.is_dir():
        return []
    return sorted(
        p.name
        for p in SOURCE_DIR.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file() and p.name not in EXCLUDED
    )


def _relative_target(name: str) -> str:
    # Relative to DEST_DIR, so the symlink still resolves if the repo is
    # moved/cloned elsewhere rather than baking in an absolute path.
    return os.path.relpath(SOURCE_DIR / name, DEST_DIR)


def _windows_symlink_hint(error: OSError) -> str:
    static_hint = (
        "On Windows, creating symlinks requires either Developer Mode "
        "(Settings > Update & Security > For developers > Developer Mode) "
        "or an elevated (Administrator) terminal, plus `git config --global "
        "core.symlinks true` set *before* cloning (a clone made without it "
        "checks symlinks out as plain text files instead)."
    )
    return f"    Could not create the symlink ({error}). {static_hint}"


def sync_one(name: str, *, check_only: bool) -> tuple[bool, str]:
    """Return (is_ok, message). is_ok is True if the destination already
    is, or was just made, a correct symlink to the source skill.
    """

    dest = DEST_DIR / name
    expected_target = _relative_target(name)

    if dest.is_symlink():
        actual_target = os.readlink(dest)
        if actual_target == expected_target and (SOURCE_DIR / name / "SKILL.md").is_file():
            return True, f"ok      {name} (already linked)"
        if check_only:
            return False, (
                f"WRONG   {name} (points to {actual_target!r}, expected {expected_target!r})"
            )
        dest.unlink()
        os.symlink(expected_target, dest)
        return True, f"fixed   {name} (was pointing to {actual_target!r})"

    if dest.exists():
        # A real file/directory, not a symlink: never clobber it, it may be
        # a contributor's own unrelated content.
        return False, (
            f"CONFLICT {name} (a real file/directory already exists at {dest}, not touching it)"
        )

    if check_only:
        return False, f"MISSING {name} (would create -> {expected_target})"

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(expected_target, dest)
    except OSError as exc:
        return False, f"FAILED  {name}\n{_windows_symlink_hint(exc)}"
    return True, f"created {name} -> {expected_target}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report status without writing anything; exit non-zero if anything is missing/wrong",
    )
    args = parser.parse_args(argv)

    names = discover_source_skills()
    if not names:
        print(f"No skills found under {SOURCE_DIR} - nothing to do.")
        return 0

    all_ok = True
    for name in names:
        ok, message = sync_one(name, check_only=args.check)
        print(message)
        all_ok = all_ok and ok

    if EXCLUDED:
        print(f"skipped {', '.join(sorted(EXCLUDED))} (see EXCLUDED in this script for why)")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
