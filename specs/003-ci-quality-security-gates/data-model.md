# Data Model: Automated CI Quality & Security Gates

This feature is CI/process configuration, not application data. It has no runtime
persistence layer, database, or API payload schema. The "entities" below are conceptual
records that live in version-controlled configuration and CI output, not in application
code or storage.

## Quality/Security Finding

Represents a single reported issue surfaced by one of the Principle IX gates.

| Field | Type | Description |
|---|---|---|
| `tool` | enum | Originating tool: `ruff-c90`, `xenon`, `mypy`, `bandit`, `pip-audit`, `codeql` |
| `location` | string | File path and line/function identifying where the finding occurs |
| `severity` | enum | `high`, `medium`, `low`/`info` (only `high`/`medium` block merge per FR-004; complexity/MI/type findings are pass/fail, not severity-graded) |
| `metric_value` | number \| null | The measured value where applicable (e.g., cyclomatic complexity count, MI grade) |
| `threshold` | number \| string | The configured limit the finding violates (from `pyproject.toml`/tool config, FR-010) |
| `status` | enum | `open`, `remediated`, `suppressed` |

**Validation rules**:
- A finding with `status = suppressed` MUST have an associated Suppression Record (below).
- A finding with `severity` in {`high`, `medium`} and `status = open` MUST block merge
  (FR-004, FR-007).

## Suppression Record

Represents a documented, tool-native exception for a specific finding (FR-009).

| Field | Type | Description |
|---|---|---|
| `finding_reference` | string | Tool-native identifier the suppression attaches to (e.g., bandit test ID, ruff rule code, mypy error code) |
| `mechanism` | enum | `inline-comment` (e.g., `# nosec`, `# noqa: C901`, `# type: ignore[code]`), `config-ignore` (e.g., `[tool.bandit] skips`, `mypy` per-module overrides) |
| `rationale` | string | Free-text justification, MUST be present and non-empty (FR-009) |
| `introduced_in` | string | Pull request reference the suppression was reviewed and approved in |

**Validation rules**:
- `rationale` MUST NOT be empty — an undocumented suppression is treated as a review
  rejection reason (spec.md User Story 3, Acceptance Scenario 2).
- Suppressions MUST be visible in the changed file or a checked-in tool config, never only in
  CI workflow YAML (spec.md User Story 3).

## Required Status Check (branch protection / ruleset entity)

Represents one CI job wired into the `main` ruleset as a required check.

| Field | Type | Description |
|---|---|---|
| `name` | string | Status check context name shown on the PR (see contracts/ci-checks-contract.md) |
| `gate` | enum | Which Principle IX (or pre-existing) requirement this check enforces |
| `bypassable_by` | enum | `none` — no actor may bypass a failing instance of this check (FR-008) |

No other entities apply; this feature introduces no application-facing data model.
