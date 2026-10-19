#!/usr/bin/env python3
"""Path launcher for the devagent runtime CLI.

Run from a bootstrapped repository:

    python .agents/scripts/devagent/main.py <command> [args]

This shim exists because ``.agents`` is not a valid Python identifier, so
``python -m .agents.scripts.devagent`` cannot work. Running this file by path
puts its own directory on ``sys.path`` (and re-asserts it below), which is where
the ``common`` package and the engine modules live.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import main

if __name__ == "__main__":
    raise SystemExit(main())
