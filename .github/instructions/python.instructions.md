---
applyTo: "**/*.py"
---

# Python Coding Instructions

These instructions apply to all Python source files in this repository. This
is a starter set of conventions to adopt once Python is confirmed as (part
of) this project's tech stack via the Spec Kit workflow
(`speckit.constitution` / `speckit.plan`). Update this file as real project
decisions are made — it is not a substitute for the constitution.

## Style & Formatting

- Follow [PEP 8](https://peps.python.org/pep-0008/) for style.
- Use `black` for formatting and `ruff` (or `flake8`) for linting; keep line
  length consistent with the formatter's default (88 chars for `black`).
- Use `snake_case` for functions/variables, `PascalCase` for classes,
  `UPPER_SNAKE_CASE` for constants.
- Group imports: standard library, third-party, local — separated by a
  blank line, alphabetized within each group (`isort` compatible).
- Prefer f-strings for string formatting over `%` or `.format()`.

## Type Hints

- Add type hints to all public function/method signatures (PEP 484/526).
- Run `mypy` (or `pyright`) in CI once the project has a defined package
  layout; treat type errors as build failures where practical.
- Prefer `Optional[X]` / `X | None` explicitly over implicit `None` defaults
  without annotation.

## Documentation

- Use docstrings (Google or NumPy style — pick one and stay consistent) on
  all public modules, classes, and functions.
- Keep docstrings focused: summary line, then Args/Returns/Raises as needed.

## Testing

- Use `pytest` as the test runner and test discovery convention
  (`test_*.py` / `*_test.py`).
- Co-locate tests under a `tests/` directory mirroring the source layout.
- Prefer fixtures over setup/teardown methods; avoid shared mutable state
  between tests.
- Write tests for new behavior and bug fixes; do not rely on manual testing
  alone.

## Error Handling & Patterns

- Avoid bare `except:`; catch specific exception types.
- Avoid mutable default arguments (e.g. `def f(x=[])`).
- Prefer `dataclasses` (or `pydantic` models, if already a dependency) over
  manual `__init__` boilerplate for simple data containers.
- Avoid global mutable state; pass dependencies explicitly.

## Packaging & Dependencies

- Declare dependencies in `pyproject.toml` (preferred) rather than a bare
  `requirements.txt` when starting new packaging setup.
- Pin dependency versions for reproducibility; use a lockfile if the chosen
  tool supports one (e.g. `poetry.lock`, `uv.lock`).

## Anti-patterns to avoid

- Wildcard imports (`from module import *`).
- Deep nesting instead of early returns / guard clauses.
- Silent exception swallowing (`except Exception: pass`).
- Business logic embedded directly in `__main__` scripts instead of
  importable, testable modules/functions.
