"""devagent command dispatch + runtime preflight.

The single entry point every engine is reached through:

    python .agents/scripts/devagent/main.py <command> [args]

Each command maps to an engine module whose own ``main()`` parses the
remaining argv. The dispatch layer only resolves the command and runs the
runtime preflight; argv (after the command) is handed through untouched so an
engine's CLI contract is exactly what its module defines.

Runtime preflight: a consumer project must have a runtime manifest at
``.agents/.devagent.json`` (written by the ``dev-agent`` skill's ``setup``).
When it is missing, every command fails with the setup instruction instead of
an ``ImportError`` further down. The framework's own source checkout is exempt
(it intentionally has no manifest).
"""

import importlib
import json
import re
import sys
from pathlib import Path

from common.root import find_root, find_runtime

SOURCE_RUNTIME_RELPATH = ("skills", "dev-agent", "runtime", "devagent")

# command -> engine module name (sibling module in this package)
COMMANDS = {
    "route": "routing",
    "map": "mapgen",
    "gate": "gates",
    "spec": "specs",
    "verify": "verify",
    "clean": "clean",
}

HELP = """usage: devagent <command> [args]

commands:
  route   <prompt>            skill recall over .agents/MAP.md (auto-router)
  map     [--force|sync-docs] build/refresh .agents/MAP.md and docs index
  gate    --gate ...          resolve a Socratic gate (phase-protocol)
  spec    <subcommand>        drafts, promotion, compile, topics (spec-builder)
  verify  <subcommand>        run / approve / status / doctor (verification-runner)
  clean   clean|status        purge the scratchpad (task-cleaner)

Run a command with -h for its own help, e.g. `devagent verify -h`.
"""


def _is_source_tree(root: Path) -> bool:
    """True when ``root`` is the framework's own source checkout.

    The source tree ships the runtime under ``skills/dev-agent/runtime`` and
    deliberately has no installed manifest, so the preflight must not block
    running the engines from here.
    """
    return root.joinpath(*SOURCE_RUNTIME_RELPATH).is_dir()


def _runtime_version() -> str:
    """This runtime build's version, read from ``__init__.py`` (no import)."""
    text = (Path(__file__).resolve().parent / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return match.group(1) if match else "0"


def _version_tuple(value: str) -> tuple:
    parts = re.findall(r"\d+", value or "")
    return tuple(int(p) for p in parts) if parts else (0,)


def preflight() -> Path:
    """Return the project root, or exit with a setup/upgrade instruction.

    Discovery is scope-independent: the manifest is found by walking up from the
    CWD (:func:`find_runtime`), never from the running script's location, so a
    globally installed skill resolves the project it is run in.
    """
    root = find_root()
    manifest_path = find_runtime()
    if manifest_path is None:
        if _is_source_tree(root):
            return root
        sys.stderr.write(
            "error: this project has no dev-agent runtime installed\n"
            "       run the dev-agent skill's setup:\n"
            "       python <dev-agent-skill>/scripts/bootstrap.py setup --target .\n"
        )
        raise SystemExit(2)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        manifest = {}
    installed = str(manifest.get("runtime_version", "0"))
    current = _runtime_version()
    if _version_tuple(installed) < _version_tuple(current):
        sys.stderr.write(
            "error: the installed dev-agent runtime is out of date ("
            + installed
            + " < "
            + current
            + ")\n"
            "       run the dev-agent skill's setup --update\n"
        )
        raise SystemExit(2)
    return root


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP)
        return 0

    command = argv[0]
    module_name = COMMANDS.get(command)
    if module_name is None:
        sys.stderr.write("error: unknown command " + repr(command) + "\n\n" + HELP)
        return 2

    preflight()
    module = importlib.import_module(module_name)
    # Hand the engine its own argv: [prog, <args...>] with the command consumed.
    sys.argv = ["devagent " + command, *argv[1:]]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
