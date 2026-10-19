"""Content hashes shared by the engines.

The approval fingerprint is a hard contract between compile (which writes
``NNN-APPROVALS-*.json``) and run (which checks it). One function means the
two sides cannot drift (the backtick-Expect / ``_fingerprint`` class of bug).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Commands run at the repo root; recording it repo-relative keeps approval
# files portable across clones and OSes.
APPROVAL_CWD = "."


def approval_fingerprint(command: str, expect: str, cwd: str = APPROVAL_CWD) -> str:
    """sha256(command | expect | cwd) - the single approval key."""
    payload = "|".join(((command or "").strip(), (expect or "").strip(), cwd))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """The hex sha256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    """The hex sha256 of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
