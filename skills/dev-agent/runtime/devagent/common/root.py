"""Repository-root discovery shared by every engine.

The contract (the framework rulebook): the project
root is the nearest directory containing an ``AGENTS.md`` marker, preferring a
walk up from the current working directory so a globally-installed skill still
resolves the project it runs in. The script-location walk-up is a fallback for
runs launched from outside the project (sandboxes with explicit target dirs).
"""

import sys
from pathlib import Path

AGENTS_MARKER = "AGENTS.md"
MANIFEST_RELPATH = ".agents/.devagent.json"
RUNTIME_DIR_RELPATH = ".agents/scripts/devagent"
LAUNCHER_RELPATH = ".agents/scripts/devagent/main.py"


def _walk_up(start: Path) -> Path | None:
    current = start
    while True:
        if (current / AGENTS_MARKER).is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def find_root() -> Path:
    """Walk up from CWD for ``AGENTS.md``, then from this script's location."""
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        found = _walk_up(start)
        if found is not None:
            return found
    sys.exit(
        "error: AGENTS.md not found above "
        + str(Path.cwd())
        + " or above "
        + str(Path(__file__).resolve().parent)
    )


def find_runtime(start: Path | None = None) -> Path | None:
    """Locate the installed runtime's manifest by walking up from the CWD.

    Returns the ``.agents/.devagent.json`` path, or ``None`` when no manifest is
    found. Unlike :func:`find_root`, this never consults the script's own
    location: runtime discovery must be scope-independent, so a globally
    installed skill resolves the project it is *run in*, never its own
    directory (spec: global-install fix).
    """
    current = (start or Path.cwd()).resolve()
    while True:
        manifest = current.joinpath(*MANIFEST_RELPATH.split("/"))
        if manifest.is_file():
            return manifest
        parent = current.parent
        if parent == current:
            return None
        current = parent
