"""Regenerate installed coding-agent integrations (Copilot, Claude Code, ...)
from Spec Kit's upstream template source and report whether anything
changed, for the periodic multi-agent skill sync workflow
(specs/011-multi-agent-skill-sync).

Not part of the machine_calc package: this is CI-only tooling invoked by
.github/workflows/ci.yml's sync-agent-integrations job.
"""

from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_CONFIG = REPO_ROOT / ".specify" / "integration.json"

# data-model.md "Sync Run" outcome vocabulary.
OUTCOME_NO_DRIFT = "no-drift"
OUTCOME_PR = "pull-request-opened-or-updated"
OUTCOME_FAILED = "failed"

# data-model.md "Integration" status vocabulary.
STATUS_MODIFIED_BLOCKED = "modified-blocked"
STATUS_UPGRADED_NO_CHANGE = "upgraded-no-change"
STATUS_UPGRADED_WITH_CHANGES = "upgraded-with-changes"
STATUS_FAILED = "failed"


def load_installed_integrations() -> list[str]:
    """Read the installed integration keys from .specify/integration.json.

    Reading this list (rather than hard-coding integration names) is what
    lets a future integration be picked up with zero workflow/script
    changes (FR-010).
    """
    data = json.loads(INTEGRATION_CONFIG.read_text())
    return list(data["installed_integrations"])


@functools.lru_cache(maxsize=1)
def _global_status() -> dict[str, Any]:
    """Run `specify integration status --json` once per process and cache
    the parsed result; every installed integration's status is reported in
    a single call, so callers should not re-invoke the CLI per integration.

    The command exits non-zero whenever *any* installed integration has a
    finding (missing/modified files) - that is normal, expected input for
    this drift check, not a tooling failure, so stdout is parsed regardless
    of the exit code.
    """
    proc = subprocess.run(
        ["specify", "integration", "status", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    result: dict[str, Any] = json.loads(proc.stdout)
    return result


def run_integration_status(key: str) -> dict[str, Any]:
    """Return the parsed `specify integration status --json` entry for one
    integration (research.md #1): its `modified_files`/`missing_files`.
    """
    manifests: dict[str, Any] = _global_status().get("manifests", {})
    entry: dict[str, Any] = manifests.get(key, {})
    return entry


@dataclass
class IntegrationResult:
    key: str
    status: str
    changed_files: list[str] = field(default_factory=list)
    blocked_file: str | None = None
    error: str | None = None


def _manifest_tracked_paths(key: str) -> list[str]:
    manifest_path = REPO_ROOT / ".specify" / "integrations" / f"{key}.manifest.json"
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text())
    return list(data.get("files", {}).keys())


def run_integration_upgrade(key: str) -> IntegrationResult:
    """Run `specify integration upgrade <key>` (never `--force`) and
    classify the outcome for that integration (data-model.md "Integration").

    A locally-modified file is detected via `run_integration_status()`
    *before* attempting the upgrade, so that case is reported precisely as
    `modified-blocked` (FR-008) rather than inferred by parsing the CLI's
    own block message - and the upgrade subprocess, which would only block
    anyway, is never invoked for that integration (FR-012's "don't silently
    discard a hand-edit" intent).
    """
    try:
        status = run_integration_status(key)
    except Exception as exc:  # subprocess/JSON failure querying status itself
        return IntegrationResult(key=key, status=STATUS_FAILED, error=str(exc))

    modified_files = status.get("modified_files") or []
    if modified_files:
        return IntegrationResult(
            key=key,
            status=STATUS_MODIFIED_BLOCKED,
            blocked_file=modified_files[0],
        )

    proc = subprocess.run(
        ["specify", "integration", "upgrade", key, "--script", "py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return IntegrationResult(
            key=key,
            status=STATUS_FAILED,
            error=proc.stderr.strip() or proc.stdout.strip(),
        )

    tracked_paths = _manifest_tracked_paths(key)
    changed_files: list[str] = []
    if tracked_paths:
        diff = subprocess.run(
            ["git", "status", "--porcelain", "--", *tracked_paths],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        changed_files = [line[3:] for line in diff.stdout.splitlines() if line.strip()]

    if changed_files:
        return IntegrationResult(
            key=key, status=STATUS_UPGRADED_WITH_CHANGES, changed_files=changed_files
        )
    return IntegrationResult(key=key, status=STATUS_UPGRADED_NO_CHANGE)


@dataclass
class SyncRunOutcome:
    outcome: str
    integrations: list[IntegrationResult]


def derive_run_outcome(integrations: list[IntegrationResult]) -> SyncRunOutcome:
    """Priority-ordered derivation per data-model.md "Sync Run":
    failed > upgraded-with-changes > modified-blocked > no-drift.

    A generic tooling/network failure (`failed`) always aborts the run: it
    is not a safe, disclosed condition, so no partial pull request is ever
    opened over it (spec.md's partial-failure edge case). A locally-modified
    file (`modified-blocked`) is different in kind - it is the CLI's own
    deliberate, expected safety mechanism (research.md #1) - so it does not
    by itself block a pull request for *other* integrations that did have
    real changes; it is instead surfaced transparently in that same pull
    request's body (FR-008; compose_pull_request_body()). Only when nothing
    at all changed (every integration is either blocked or already
    up to date) does a modified-blocked integration make the run `failed`,
    since there would otherwise be nothing to actually put in a pull
    request.
    """
    if any(r.status == STATUS_FAILED for r in integrations):
        return SyncRunOutcome(outcome=OUTCOME_FAILED, integrations=integrations)
    if any(r.status == STATUS_UPGRADED_WITH_CHANGES for r in integrations):
        return SyncRunOutcome(outcome=OUTCOME_PR, integrations=integrations)
    if any(r.status == STATUS_MODIFIED_BLOCKED for r in integrations):
        return SyncRunOutcome(outcome=OUTCOME_FAILED, integrations=integrations)
    return SyncRunOutcome(outcome=OUTCOME_NO_DRIFT, integrations=integrations)


def compose_pull_request_body(integrations: list[IntegrationResult]) -> str:
    """Produce the pull-request body per contracts/sync-workflow-contract.md
    "Sync Pull Request body contract": changed integrations named first,
    then (only when at least one other integration also changed) a callout
    for any integration blocked by a locally-modified file (FR-008;
    data-model.md "Sync Pull Request".blocked_integrations).
    """
    changed = [r.key for r in integrations if r.status == STATUS_UPGRADED_WITH_CHANGES]
    blocked = [
        (r.key, r.blocked_file)
        for r in integrations
        if r.status == STATUS_MODIFIED_BLOCKED and r.blocked_file
    ]

    lines = [
        "Automated sync: regenerated the following coding-agent "
        "integration(s) from Spec Kit's upstream template source "
        "(specs/011-multi-agent-skill-sync).",
        "",
        "**Changed integrations:**",
    ]
    lines.extend(f"- `{key}`" for key in changed)

    if blocked:
        lines.append("")
        lines.append("**Not updated (locally-modified file detected — review before " "merging):**")
        lines.extend(f"- `{key}`: `{file}`" for key, file in blocked)

    return "\n".join(lines) + "\n"


def _write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        if "\n" in value:
            delimiter = "SYNC_OUTPUT_EOF"
            fh.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
        else:
            fh.write(f"{name}={value}\n")


def write_workflow_output(result: SyncRunOutcome) -> None:
    """Write `has_changes`/`pr_body` to `$GITHUB_OUTPUT` (FR-004;
    contracts/sync-workflow-contract.md "no-drift" guarantee) so the
    workflow can conditionally invoke the PR-creation step.
    """
    has_changes = result.outcome == OUTCOME_PR
    _write_github_output("has_changes", "true" if has_changes else "false")
    body = compose_pull_request_body(result.integrations) if has_changes else ""
    _write_github_output("pr_body", body)


def main() -> int:
    results = [run_integration_upgrade(key) for key in load_installed_integrations()]

    outcome = derive_run_outcome(results)
    write_workflow_output(outcome)

    failed_run = outcome.outcome == OUTCOME_FAILED
    for r in results:
        if r.status == STATUS_MODIFIED_BLOCKED:
            # A blocked integration doesn't fail the run by itself when at
            # least one other integration still has real changes to PR
            # (derive_run_outcome); it's a warning there, not an error,
            # since it's already disclosed in the PR body (FR-008).
            level = "error" if failed_run else "warning"
            print(
                f"::{level}::Integration '{r.key}' blocked: locally-modified "
                f"file {r.blocked_file!r} detected (run `specify integration "
                f"status --json` for details)",
                file=sys.stderr,
            )
        elif r.status == STATUS_FAILED:
            print(
                f"::error::Integration '{r.key}' failed: {r.error}",
                file=sys.stderr,
            )

    return 1 if failed_run else 0


if __name__ == "__main__":
    sys.exit(main())
