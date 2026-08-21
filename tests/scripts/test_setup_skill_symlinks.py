"""Unit tests for scripts/setup_skill_symlinks.py (Constitution Principle XI
v1.9.0's "genuinely shared, hand-authored skills" exception).

`scripts/` is not part of the installed `machine_calc` package (it is
CI-only tooling, mirroring scripts/sync_agent_integrations.py's test
setup), so the module under test is imported directly by path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import setup_skill_symlinks as sss  # noqa: E402


@pytest.fixture()
def dirs(tmp_path, monkeypatch):
    source = tmp_path / ".github" / "skills"
    dest = tmp_path / ".claude" / "skills"
    source.mkdir(parents=True)
    dest.mkdir(parents=True)
    monkeypatch.setattr(sss, "SOURCE_DIR", source)
    monkeypatch.setattr(sss, "DEST_DIR", dest)
    return source, dest


def _make_skill(source: Path, name: str) -> None:
    skill_dir = source / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\n")


# --- discover_source_skills ---------------------------------------------------


def test_discover_source_skills_finds_dirs_with_skill_md(dirs):
    source, _ = dirs
    _make_skill(source, "pr-review-loop")
    _make_skill(source, "skill-authoring")
    (source / "not-a-skill").mkdir()  # no SKILL.md - must be ignored

    assert sss.discover_source_skills() == ["pr-review-loop", "skill-authoring"]


def test_discover_source_skills_excludes_code_review(dirs):
    source, _ = dirs
    _make_skill(source, "code-review")
    _make_skill(source, "pr-review-loop")

    assert sss.discover_source_skills() == ["pr-review-loop"]


def test_discover_source_skills_missing_source_dir_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(sss, "SOURCE_DIR", tmp_path / "does-not-exist")
    monkeypatch.setattr(sss, "DEST_DIR", tmp_path / ".claude" / "skills")

    assert sss.discover_source_skills() == []


# --- sync_one ------------------------------------------------------------------


def test_sync_one_creates_missing_symlink(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert "created" in message
    link = dest / "pr-review-loop"
    assert link.is_symlink()
    assert (link / "SKILL.md").read_text() == "---\nname: pr-review-loop\n---\n"


def test_sync_one_check_only_reports_missing_without_writing(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")

    ok, message = sss.sync_one("pr-review-loop", check_only=True)

    assert ok is False
    assert "MISSING" in message
    assert not (dest / "pr-review-loop").exists()


def test_sync_one_already_correct_is_ok_and_untouched(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    sss.sync_one("pr-review-loop", check_only=False)

    ok, message = sss.sync_one("pr-review-loop", check_only=True)

    assert ok is True
    assert "already linked" in message


def test_sync_one_fixes_wrong_target(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    _make_skill(source, "skill-authoring")
    # Point the pr-review-loop destination at the wrong source skill.
    (dest / "pr-review-loop").symlink_to(source / "skill-authoring")

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is True
    assert "fixed" in message
    assert (dest / "pr-review-loop").resolve() == (source / "pr-review-loop").resolve()


def test_sync_one_check_only_reports_wrong_without_fixing(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    _make_skill(source, "skill-authoring")
    (dest / "pr-review-loop").symlink_to(source / "skill-authoring")

    ok, message = sss.sync_one("pr-review-loop", check_only=True)

    assert ok is False
    assert "WRONG" in message
    assert (dest / "pr-review-loop").resolve() == (source / "skill-authoring").resolve()


def test_sync_one_never_clobbers_a_real_directory(dirs):
    source, dest = dirs
    _make_skill(source, "pr-review-loop")
    real_dir = dest / "pr-review-loop"
    real_dir.mkdir()
    (real_dir / "unrelated.txt").write_text("contributor's own content")

    ok, message = sss.sync_one("pr-review-loop", check_only=False)

    assert ok is False
    assert "CONFLICT" in message
    assert not real_dir.is_symlink()
    assert (real_dir / "unrelated.txt").exists()


# --- main ------------------------------------------------------------------


def test_main_returns_zero_when_everything_ok(dirs, capsys):
    source, _ = dirs
    _make_skill(source, "pr-review-loop")

    assert sss.main([]) == 0
    assert sss.main(["--check"]) == 0


def test_main_returns_nonzero_when_check_finds_missing(dirs):
    source, _ = dirs
    _make_skill(source, "pr-review-loop")

    assert sss.main(["--check"]) == 1


def test_main_no_source_skills_returns_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sss, "SOURCE_DIR", tmp_path / "does-not-exist")
    monkeypatch.setattr(sss, "DEST_DIR", tmp_path / ".claude" / "skills")

    assert sss.main([]) == 0
    assert "nothing to do" in capsys.readouterr().out.lower()
