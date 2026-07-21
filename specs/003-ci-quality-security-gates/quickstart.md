# Quickstart: Validating Automated CI Quality & Security Gates

**Prerequisites**: Python 3.9+, a local clone of `machine-calc`, `pip install -e ".[dev]"`
(once this feature adds the new tool extras to `dev`, e.g., `mypy`, `radon`,
`bandit`, `pip-audit`).

## 1. Run each gate locally, exactly as CI will

```bash
# Complexity (ruff C90) and Maintainability Index (radon mi)
ruff check src/ tests/                # includes C90 once added to [tool.ruff.lint].select
python scripts/check_maintainability.py src/

# Static type-checking
mypy src/machine_calc

# Security
bandit -r src -ll

# Dependency vulnerability scan
pip-audit
```

**Expected outcome**: All five commands exit `0` on a clean checkout of `main` after this
feature's "gate rollout" task (research.md #8) has remediated/suppressed any pre-existing
findings.

## 2. Validate a deliberately failing pull request is blocked

1. On a scratch branch, introduce a function with cyclomatic complexity above the configured
   threshold (e.g., a chain of >10 `if`/`elif` branches).
2. Open a pull request against `main`.
3. **Expected**: the `lint` check (ruff C90) fails and is listed as a required, failing
   check; the merge button is disabled for every role, including the repository owner
   (contract: `contracts/ci-checks-contract.md`).
4. Revert the change; confirm the check turns green and merge becomes available again
   (subject to the separate review-approval requirement).

## 3. Validate the review-approval bypass still works, scoped correctly

1. As the repository owner, open a pull request with no complexity/type/security/dependency
   findings, but without an approving review.
2. **Expected**: only the "pull request approval" rule is bypassable by the owner; the merge
   proceeds without a review, but only because none of the other required checks are
   failing.
3. Repeat with a deliberately failing `security` check (step 2's scratch branch, adapted).
   **Expected**: the owner cannot bypass the failing `security` check; merge remains blocked
   until it is resolved or suppressed per the suppression contract.

## 4. Validate a documented suppression

1. Introduce a known bandit false positive with an inline `# nosec` and rationale comment.
2. Open a pull request.
3. **Expected**: the `security` check passes; the suppression and its rationale are visible
   in the PR diff (not only in CI config), satisfying spec.md User Story 3.

## 5. Validate the weekly dependency scan runs independent of pull requests

1. Confirm the `dependency-scan` workflow has a `schedule` trigger (e.g., weekly cron) in
   addition to `pull_request`.
2. **Expected**: a manually triggered run (`workflow_dispatch` or waiting for the schedule)
   against `main` succeeds/fails independent of any open pull request (FR-005).

See [spec.md](./spec.md) for full acceptance scenarios and
[contracts/ci-checks-contract.md](./contracts/ci-checks-contract.md) for the exact required
status check names and bypass rules this quickstart validates against.
