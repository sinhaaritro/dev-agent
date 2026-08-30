#!/usr/bin/env python3
"""task-cleaner engine - scratchpad purge with a gate-log preservation guarantee.

Owns the mechanical parts of the framework's cleanup contract: purging the
ephemeral docs/temp/ scratchpad on human acceptance
while never touching gate-log.md until a human explicitly clears it. The
engine never decides whether the task was accepted - the agent calls it when
the acceptance gate has passed (phase-protocol review.md section 4.2).

Modes:
    clean    clean.py clean [--dry-run] [--preserve <list>] [--temp-dir <dir>]
             Delete every file and subdirectory inside the scratchpad except
             the preserved basenames. Default preserve list: gate-log.md
             (append-only audit file) and .gitignore (the file
             that makes the directory ephemeral). --preserve "" is the
             explicit override that allows purging everything - only lawful
             after a human has reviewed and cleared the gate-log. --dry-run
             lists what would be purged/preserved without deleting.
             Prints: purged: <N>, preserved: <M>. Refuses targets at or above
             the repo root.

    status   clean.py status [--temp-dir <dir>]
             List the scratchpad's contents with would-purge/would-preserve
             classification and the current preserve list. Read-only.

Usage:
    python .agents/skills/task-cleaner/scripts/clean.py clean
    python .agents/skills/task-cleaner/scripts/clean.py clean --dry-run

Exit codes: 0 = clean ran / status listed (even with nothing to purge);
1 = error (root-or-above target refused, bad arguments).
"""

import argparse
import sys
from pathlib import Path

DEFAULT_PRESERVE = "gate-log.md,.gitignore"
STATE_FILE_NAMES = ("verify-state.json",)  # documented in 005 D1 for reference


def find_root() -> Path:
    """Walk up from the script location until AGENTS.md or AGENTS.md is found (repo root marker)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENTS.md").is_file() or (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit(
                "error: AGENTS.md / AGENTS.md not found above "
                + str(Path(__file__).resolve())
            )
        current = parent


def resolve_temp_dir(arg: str | None) -> Path:
    if arg is not None:
        return Path(arg).resolve()
    return (find_root() / "docs" / "temp").resolve()


def assert_scratchpad(target: Path, root: Path) -> None:
    """Refuse targets at or above the repo root - a purge must never walk up."""
    if target == root or target == root.parent or root.is_relative_to(target):
        sys.exit(
            "error: refusing to purge "
            + str(target)
            + " - target must be a scratchpad "
            "inside the repository, never the repo root or above"
        )


def list_contents(target: Path) -> list[Path]:
    if not target.is_dir():
        return []
    return [p for p in target.iterdir()]


def classify(contents: list[Path], preserve: set[str]) -> tuple[list[Path], list[Path]]:
    to_purge, to_preserve = [], []
    for path in contents:
        if path.name in preserve:
            to_preserve.append(path)
        else:
            to_purge.append(path)
    return to_purge, to_preserve


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        for child in sorted(path.iterdir(), key=lambda p: len(p.parts), reverse=True):
            remove_path(child)
        path.rmdir()
    else:
        path.unlink()


def cmd_clean(args: argparse.Namespace) -> int:
    root = find_root()
    target = resolve_temp_dir(args.temp_dir)
    assert_scratchpad(target, root)
    preserve = set(
        part.strip()
        for part in (
            args.preserve if args.preserve is not None else DEFAULT_PRESERVE
        ).split(",")
        if part.strip()
    )
    contents = list_contents(target)
    to_purge, to_preserve = classify(contents, preserve)

    if args.dry_run:
        print(
            "dry-run - would purge "
            + str(len(to_purge))
            + ", would preserve "
            + str(len(to_preserve))
        )
        for path in sorted(to_purge, key=lambda p: p.name):
            print("purge: " + path.name)
        for path in sorted(to_preserve, key=lambda p: p.name):
            print("preserve: " + path.name)
        return 0

    for path in to_purge:
        remove_path(path)
    print("purged: " + str(len(to_purge)) + ", preserved: " + str(len(to_preserve)))
    for path in sorted(to_preserve, key=lambda p: p.name):
        print("preserved: " + path.name)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    target = resolve_temp_dir(args.temp_dir)
    preserve = set(
        part.strip()
        for part in (
            args.preserve if args.preserve is not None else DEFAULT_PRESERVE
        ).split(",")
        if part.strip()
    )
    contents = list_contents(target)
    to_purge, to_preserve = classify(contents, preserve)
    print("scratchpad: " + str(target))
    print("preserve list: " + (", ".join(sorted(preserve)) or "(none)"))
    print(
        "contents: "
        + str(len(contents))
        + " (would purge "
        + str(len(to_purge))
        + ", would preserve "
        + str(len(to_preserve))
        + ")"
    )
    for path in sorted(to_purge, key=lambda p: p.name):
        print("purge: " + path.name)
    for path in sorted(to_preserve, key=lambda p: p.name):
        print("preserve: " + path.name)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="task-cleaner: scratchpad purge with gate-log preservation"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    clean_p = sub.add_parser(
        "clean", help="purge the scratchpad (preserving the default list)"
    )
    clean_p.add_argument("--dry-run", action="store_true", help="list without deleting")
    clean_p.add_argument(
        "--preserve",
        default=None,
        help='comma-separated basenames to keep (default "gate-log.md,.gitignore"; "" purges everything - only after a human clears the gate-log)',
    )
    clean_p.add_argument(
        "--temp-dir",
        type=Path,
        default=None,
        help="scratchpad to purge (default <root>/docs/temp; sandbox for tests)",
    )
    clean_p.set_defaults(func=cmd_clean)

    status_p = sub.add_parser(
        "status", help="list the scratchpad and its classification"
    )
    status_p.add_argument(
        "--preserve",
        default=None,
        help='comma-separated basenames to treat as preserved (default "gate-log.md,.gitignore")',
    )
    status_p.add_argument("--temp-dir", type=Path, default=None)
    status_p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
