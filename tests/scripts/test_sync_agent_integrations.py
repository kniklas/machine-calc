"""Unit/integration tests for scripts/sync_agent_integrations.py
(specs/011-multi-agent-skill-sync tasks.md T007, T012, T015).

`scripts/` is not part of the installed `machine_calc` package (it is
CI-only tooling, research.md #5), so the module under test is imported
directly by path rather than via a package import.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sync_agent_integrations as sai  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_status_cache():
    sai._global_status.cache_clear()
    yield
    sai._global_status.cache_clear()


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# --- load_installed_integrations (T007) -------------------------------------


def test_load_installed_integrations_reads_config(tmp_path, monkeypatch):
    config = tmp_path / "integration.json"
    config.write_text(json.dumps({"installed_integrations": ["copilot", "claude", "cursor"]}))
    monkeypatch.setattr(sai, "INTEGRATION_CONFIG", config)

    assert sai.load_installed_integrations() == ["copilot", "claude", "cursor"]


# --- run_integration_status (T007) -------------------------------------------


def test_run_integration_status_returns_manifest_for_key_and_caches():
    status_json = json.dumps(
        {
            "manifests": {
                "copilot": {"modified_files": [], "missing_files": []},
                "claude": {"modified_files": ["skills/x.md"], "missing_files": []},
            }
        }
    )
    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)) as mock_run:
        result_copilot = sai.run_integration_status("copilot")
        result_claude = sai.run_integration_status("claude")

    assert result_copilot == {"modified_files": [], "missing_files": []}
    assert result_claude == {"modified_files": ["skills/x.md"], "missing_files": []}
    # Two integrations queried, but the underlying CLI is invoked once (cached).
    assert mock_run.call_count == 1


def test_run_integration_status_parses_json_even_on_nonzero_exit():
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": ["a"]}}})
    with patch.object(sai.subprocess, "run", return_value=_completed(1, status_json)):
        result = sai.run_integration_status("copilot")
    assert result == {"modified_files": ["a"]}


# --- run_integration_upgrade (T007) ------------------------------------------


def test_run_integration_upgrade_modified_blocked_skips_upgrade_call():
    status_json = json.dumps(
        {"manifests": {"copilot": {"modified_files": [".github/prompts/x.md"]}}}
    )
    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)) as mock_run:
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_MODIFIED_BLOCKED
    assert result.blocked_file == ".github/prompts/x.md"
    # Only the status call happened; upgrade must never be invoked when blocked.
    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0][:3] == ["specify", "integration", "status"]


def test_run_integration_upgrade_generic_failure():
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(1, "", "network error contacting upstream")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_FAILED
    assert "network error" in result.error


def test_run_integration_upgrade_with_changes(monkeypatch):
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: [".github/prompts/x.md"])

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, " M .github/prompts/x.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_UPGRADED_WITH_CHANGES
    assert result.changed_files == [".github/prompts/x.md"]


def test_run_integration_upgrade_no_change(monkeypatch):
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: [".github/prompts/x.md"])

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, "")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        result = sai.run_integration_upgrade("copilot")

    assert result.status == sai.STATUS_UPGRADED_NO_CHANGE
    assert result.changed_files == []


# --- derive_run_outcome (T007) -----------------------------------------------


def _result(key, status, **kw):
    return sai.IntegrationResult(key=key, status=status, **kw)


def test_derive_run_outcome_no_drift():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_UPGRADED_NO_CHANGE),
            _result("claude", sai.STATUS_UPGRADED_NO_CHANGE),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_NO_DRIFT


def test_derive_run_outcome_pull_request():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_UPGRADED_NO_CHANGE),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_PR


def test_derive_run_outcome_mixed_blocked_and_changed_is_still_pull_request():
    """A blocked integration doesn't sink a run that has real changes to PR
    elsewhere - it's disclosed transparently in that PR's body instead
    (FR-008), not treated as a silent partial-failure omission."""
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_MODIFIED_BLOCKED, blocked_file="x.md"),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_PR


def test_derive_run_outcome_all_blocked_with_no_changes_is_failed():
    """When nothing at all changed, a blocked integration has no PR to be
    disclosed in, so the run is failed instead of a pointless empty PR."""
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_MODIFIED_BLOCKED, blocked_file="x.md"),
            _result("claude", sai.STATUS_UPGRADED_NO_CHANGE),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_FAILED


def test_derive_run_outcome_failed_takes_priority_over_upgraded_with_changes():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_FAILED, error="boom"),
            _result("claude", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_FAILED


def test_derive_run_outcome_failed_takes_priority_over_modified_blocked():
    outcome = sai.derive_run_outcome(
        [
            _result("copilot", sai.STATUS_FAILED, error="boom"),
            _result("claude", sai.STATUS_MODIFIED_BLOCKED, blocked_file="x.md"),
        ]
    )
    assert outcome.outcome == sai.OUTCOME_FAILED


# --- compose_pull_request_body (T015) ----------------------------------------


def test_compose_pull_request_body_names_all_changed_integrations():
    body = sai.compose_pull_request_body(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["b"]),
        ]
    )
    assert "`copilot`" in body
    assert "`claude`" in body
    assert "Not updated" not in body


def test_compose_pull_request_body_includes_blocked_callout_alongside_changes():
    body = sai.compose_pull_request_body(
        [
            _result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"]),
            _result("claude", sai.STATUS_MODIFIED_BLOCKED, blocked_file=".claude/skills/x.md"),
        ]
    )
    assert "`copilot`" in body
    assert "Not updated" in body
    assert "`claude`" in body
    assert ".claude/skills/x.md" in body


def test_compose_pull_request_body_no_blocked_section_when_nothing_blocked():
    body = sai.compose_pull_request_body(
        [_result("copilot", sai.STATUS_UPGRADED_WITH_CHANGES, changed_files=["a"])]
    )
    assert "Not updated" not in body


# --- main() end-to-end (T012) -------------------------------------------------


def test_main_no_drift_writes_has_changes_false(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot"])
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, "")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    assert exit_code == 0
    assert "has_changes=false" in output_file.read_text()


def test_main_drift_found_writes_has_changes_true(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot"])
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: ["x.md"])
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": []}}})

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, " M x.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    output_content = output_file.read_text()
    assert exit_code == 0
    assert "has_changes=true" in output_content
    assert "copilot" in output_content


def test_main_failure_exits_nonzero(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot"])
    status_json = json.dumps({"manifests": {"copilot": {"modified_files": ["x.md"]}}})

    with patch.object(sai.subprocess, "run", return_value=_completed(0, status_json)):
        exit_code = sai.main()

    assert exit_code == 1
    assert "has_changes=false" in output_file.read_text()


def test_main_mixed_blocked_and_changed_still_opens_pr_with_callout(tmp_path, monkeypatch):
    """End-to-end proof that a blocked integration alongside a genuinely
    changed one reaches OUTCOME_PR through main() (not just through
    compose_pull_request_body() called directly) - closing the gap where
    the blocked-callout branch was previously unreachable in production."""
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot", "claude"])
    monkeypatch.setattr(sai, "_manifest_tracked_paths", lambda key: ["x.md"])
    status_json = json.dumps(
        {
            "manifests": {
                "copilot": {"modified_files": []},
                "claude": {"modified_files": [".claude/skills/y.md"]},
            }
        }
    )

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, " M x.md\n")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    output_content = output_file.read_text()
    assert exit_code == 0
    assert "has_changes=true" in output_content
    assert "`copilot`" in output_content
    assert "Not updated" in output_content
    assert ".claude/skills/y.md" in output_content


def test_main_all_blocked_no_changes_fails(tmp_path, monkeypatch):
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setattr(sai, "load_installed_integrations", lambda: ["copilot", "claude"])
    status_json = json.dumps(
        {
            "manifests": {
                "copilot": {"modified_files": ["x.md"]},
                "claude": {"modified_files": []},
            }
        }
    )

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["specify", "integration", "status"]:
            return _completed(0, status_json)
        if cmd[:3] == ["specify", "integration", "upgrade"]:
            return _completed(0, "")
        if cmd[:2] == ["git", "status"]:
            return _completed(0, "")
        raise AssertionError(f"unexpected command: {cmd}")

    with patch.object(sai.subprocess, "run", side_effect=fake_run):
        exit_code = sai.main()

    assert exit_code == 1
    assert "has_changes=false" in output_file.read_text()
