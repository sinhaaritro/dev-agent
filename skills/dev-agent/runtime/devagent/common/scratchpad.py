"""Scratchpad guard shared by the gate and verify engines.

The inner stub (``*`` + ``!.gitignore``) is the effective protection - git
refuses to descend into a gitignored directory even without a root .gitignore -
while the root entry documents the exclusion for viewers that stop at the top
level. Idempotent.
"""

from __future__ import annotations

from pathlib import Path


def find_guard_root(state_dir: Path) -> Path | None:
    """The nearest repo root (AGENTS.md + .agents) above ``state_dir``."""
    root = Path(state_dir)
    for _ in range(4):
        if (root / "AGENTS.md").is_file() and (root / ".agents").is_dir():
            return root
        root = root.parent
    return None


def ensure_scratchpad_guard(state_dir: Path, root: Path | None = None) -> None:
    """Create the scratchpad dir stub and the root ``.gitignore`` entry.

    ``root`` is the repo root when the caller already knows it (the gate
    engine). When omitted, it is discovered from ``state_dir``; a sandboxed
    state dir outside any repo gets only the inner stub, never a foreign
    ``.gitignore``.
    """
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    inner = state_dir / ".gitignore"
    if not inner.is_file():
        inner.write_text("*\n!.gitignore\n", encoding="utf-8")

    root = Path(root) if root is not None else find_guard_root(state_dir)
    if root is None:
        return
    root_ignore = root / ".gitignore"
    if not root_ignore.is_file():
        root_ignore.write_text("# DEV Agent framework\n", encoding="utf-8")
    lines = root_ignore.read_text(encoding="utf-8").splitlines()
    if any(
        line.strip().strip("/") in ("specs", "specs/temp")
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ):
        return
    text = root_ignore.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    root_ignore.write_text(text + "\nspecs/temp\n", encoding="utf-8")
