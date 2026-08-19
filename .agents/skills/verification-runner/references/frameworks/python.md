# Framework: Python

Canonical commands and failure patterns for Python projects. Two styles are covered: `uv`-managed (uv.lock / [tool.uv] present) and plain system Python + venv. Pick the style by detection, then use that style's commands verbatim. For plain Python projects, the project declares a `Run Prefix` in `AGENTS.md` (for example `source .venv/bin/ && `, or empty for PATH python) - the canonical commands below apply with that prefix when set.

## Detection

- `uv.lock` or pyproject.toml with a `[tool.uv]` section -> **uv style**
- `pyproject.toml` only (or `setup.py` / `requirements.txt`) -> **plain style**

## Canonical commands

### uv style (this repository)

- Install / sync dependencies: `uv sync` (uv reads pyproject.toml + uv.lock; never use bare `pip install` in a uv project - it bypasses the lockfile)
- Run a script: `python <script>` (or `uv run <tool>` for tools declared in `[dependency-groups]` / `[project.scripts]`)
- Test (full suite): `uv run pytest`
- Test (single file): `uv run pytest tests/path/to/test_module.py`
- Test (single test): `uv run pytest tests/path/to/test_module.py::test_name`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type check (if mypy/pyright configured): `uv run mypy src`

### Plain style (system python + venv)

- Provision the venv (once): `python -m venv .venv`
- Install / sync dependencies: `python -m pip install -r requirements.txt` (or `python -m pip install -e .` for a pyproject.toml package); optionally `python -m pip freeze > requirements.lock` for a lockfile
- Test (full suite): `pytest`
- Test (single file): `pytest tests/path/to/test_module.py`
- Test (single test): `pytest tests/path/to/test_module.py::test_name`
- Lint: `ruff check .`
- Format check: `ruff format --check .`
- Type check (if mypy/pyright configured): `mypy src`

When the venv is not already activated, run the plain commands through the project's `Run Prefix` from `AGENTS.md` (e.g. `source .venv/bin/ && pytest` on Unix, `call .venv\Scripts\activate && pytest` on Windows).

## Failure patterns & fixes

- `ModuleNotFoundError` on a test run: the package isn't installed in the active environment - sync (`uv sync`) or install (`python -m pip install -r requirements.txt`) first, then re-run. Check the test imports against `[project]` packages in pyproject.toml (or requirements.txt).
- `command not found: pytest` (plain style): the venv is not activated - prefix the command with the project's `Run Prefix` from `AGENTS.md`, or activate the venv before running.
- Tests pass locally but fail in verification: usually a working-directory or env mismatch - run pytest from the repo root, confirm the venv is active (`uv run` for uv style; the `Run Prefix` for plain style, never a bare `pytest`).
- Ruff failures: run the autofix (`uv run ruff check --fix .` uv style, `ruff check --fix .` plain), then re-verify; formatting-only changes go through `ruff format`.
- Lockfile mismatch errors (uv style): the project files changed since `uv.lock` - `uv sync --frozen` fails deliberately; run `uv lock` then `uv sync` only if the change was intentional.
- Timeouts on first test run (uv style): `uv sync` compiling dependencies can exceed a short timeout - run `uv sync` as its own verification step before the test suite.
- Stale bytecode after moving files: `python -m compileall` or delete `__pycache__` before re-running tests.

## Verification checklist

- Build/install step: `uv sync` (uv, frozen when the lockfile is authoritative) or `python -m pip install -r requirements.txt` (plain)
- Test step: `uv run pytest` (uv) or `pytest` (plain, with the project's `Run Prefix` when the venv is not activated) - full suite or the scoped invocation from the plan's section 5
- Lint step: `uv run ruff check .` (uv) or `ruff check .` (plain; and `ruff format --check .` when the plan says formatting)
