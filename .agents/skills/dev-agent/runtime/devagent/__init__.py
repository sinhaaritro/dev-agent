"""devagent - the Dev Agent framework's shared runtime package.

This package is the single home for every engine. It is installed into a
consumer repository at ``.agents/scripts/devagent/`` by the ``dev-agent``
skill's ``bootstrap.py setup`` and invoked through ``main.py``:

    python .agents/scripts/devagent/main.py <command> [args]

Commands map to engine modules (see ``cli.py``). The package is stdlib-only.
"""

__version__ = "0.1.0"
