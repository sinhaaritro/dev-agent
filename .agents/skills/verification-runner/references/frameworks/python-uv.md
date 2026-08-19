# Framework: Python + uv

Canonical commands and failure patterns for Python projects managed with uv (this repository uses uv + pytest + ruff).

## Detection

`pyproject.toml` at the repo root (with or without a `[tool.uv]` section) -> this page.

## Canonical commands

- Install / sync dependencies: `uv sync` (uv reads pyproject.toml + uv.lock; never use bare `pip install` in a uv project - it bypasses the lockfile)
- Run a script: `python <script>` (or `uv run <tool>` for tools declared in `[dependency-groups]` / `[project.scripts]`)
- Test (full suite): `uv run pytest`
- Test (single file): `uv run pytest tests/path/to/test_module.py`
- Test (single test): `uv run pytest tests/path/to/test_module.py::test_name`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type check (if mypy/pyright configured): `uv run mypy src`

## Failure patterns & fixes

- `ModuleNotFoundError` on a test run: the package isn't installed - `uv sync` first, then re-run. Check the test imports against `[project]` packages in pyproject.toml.
- Tests pass locally but fail in verification: usually a working-directory or env mismatch - run pytest from the repo root, confirm `.venv` is active via `uv run` (never a bare `pytest`).
- Ruff failures: run `uv run ruff check --fix .` for autofixable issues, then re-verify; formatting-only changes go through `ruff format`.
- Lockfile mismatch errors: the project files changed since `uv.lock` - `uv sync --frozen` fails deliberately; run `uv lock` then `uv sync` only if the change was intentional.
- Timeouts on first test run: `uv sync` compiling dependencies can exceed a short timeout - run `uv sync` as its own verification step before the test suite.

## Verification checklist

- Build/install step: `uv sync` (frozen when the lockfile is authoritative)
- Test step: `uv run pytest` (full suite) or the scoped invocation from the plan's section 5
- Lint step: `uv run ruff check .` (and `ruff format --check .` when the plan says formatting)