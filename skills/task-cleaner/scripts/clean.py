#!/usr/bin/env python3
"""task-cleaner engine - scratchpad purge for the new framework.

Owns the mechanical parts of the framework's cleanup contract: purging the
ephemeral specs/temp/ scratchpad on human acceptance. In the new world the
scratchpad holds ONLY draft-stage scratch (draft-plan.md, active-task.md, flow
diagrams): per-task verification evidence lives in the task files under
specs/, the gate log lives in the spec's `Gates:` section, and approvals are a
gitignored per-spec file (NNN-APPROVALS-<slug>.json). So the scratchpad is
safe to purge on approval - there is no append-only audit file to preserve.

The engine never decides whether the task was accepted - the agent calls it when
the acceptance gate has passed (phase-protocol reviewed.md section 4). It never
touches specs/ group files, docs/, or BACKLOG.md: those are durable and live
outside specs/temp/.

Modes:
    clean    clean.py clean [--dry-run] [--preserve <list>] [--temp-dir <dir>]
              Delete every file and subdirectory inside the scratchpad except
              the preserved basenames. Default preserve list: .gitignore (the
              file that makes the directory ephemeral). --preserve "" purges
              everything, including .gitignore. --dry-run lists what would be
              purged/preserved without deleting. Prints: purged: <N>,
              preserved: <M>. Refuses targets at or above the repo root.

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

DEFAULT_PRESERVE = ".gitignore"


def find_root() -> Path:
    """Walk up from the script location until AGENTS.md is found (repo root marker)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit(
                "error: AGENTS.md not found above "
                + str(Path(__file__).resolve())
            )
        current = parent


def resolve_temp_dir(arg: str | None) -> Path:
    if arg is not None:
        return Path(arg).resolve()
    return (find_root() / "specs" / "temp").resolve()


def assert_scratchpad(target: Path, root: Path) -> None:
    """Refuse targets at or above the repo root - a purge must never walk up."""
    if not root.exists() or not root.is_dir():
        root = root.parent
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


def parse_preserve(arg: str | None) -> set[str]:
    return {
        part.strip()
        for part in (arg if arg is not None else DEFAULT_PRESERVE).split(",")
        if part.strip()
    }


def clean(temp_dir: Path, preserve: list[str], dry_run: bool) -> tuple[list[str], list[str]]:
    """Purge temp_dir, preserving the named basenames.

    Returns (purged_names, preserved_names) sorted. With dry_run, nothing is
    deleted - the returned lists are what *would* be purged/preserved.
    """
    preserve_set = {p for p in preserve if p}
    contents = list_contents(temp_dir)
    to_purge, to_preserve = classify(contents, preserve_set)
    if not dry_run:
        for path in to_purge:
            remove_path(path)
    return (
        sorted(p.name for p in to_purge),
        sorted(p.name for p in to_preserve),
    )


def cmd_clean(args: argparse.Namespace) -> int:
    root = find_root()
    target = resolve_temp_dir(args.temp_dir)
    assert_scratchpad(target, root)
    preserve = parse_preserve(args.preserve)
    purged, preserved = clean(target, sorted(preserve), args.dry_run)

    if args.dry_run:
        print(
            "dry-run - would purge "
            + str(len(purged))
            + ", would preserve "
            + str(len(preserved))
        )
    else:
        print("purged: " + str(len(purged)) + ", preserved: " + str(len(preserved)))
    for name in purged:
        print("purge: " + name)
    for name in preserved:
        print("preserve: " + name)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    target = resolve_temp_dir(args.temp_dir)
    preserve = parse_preserve(args.preserve)
    purged, preserved = clean(target, sorted(preserve), dry_run=True)
    print("scratchpad: " + str(target))
    print("preserve list: " + (", ".join(sorted(preserve)) or "(none)"))
    print(
        "contents: "
        + str(len(purged) + len(preserved))
        + " (would purge "
        + str(len(purged))
        + ", would preserve "
        + str(len(preserved))
        + ")"
    )
    for name in purged:
        print("purge: " + name)
    for name in preserved:
        print("preserve: " + name)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="task-cleaner: scratchpad purge (draft-stage scratch only)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    clean_p = sub.add_parser(
        "clean", help="purge the scratchpad (preserving .gitignore by default)"
    )
    clean_p.add_argument("--dry-run", action="store_true", help="list without deleting")
    clean_p.add_argument(
        "--preserve",
        default=None,
        help='comma-separated basenames to keep (default ".gitignore"; "" purges everything)',
    )
    clean_p.add_argument(
        "--temp-dir",
        type=Path,
        default=None,
        help="scratchpad to purge (default <repo-root>/specs/temp; sandbox for tests)",
    )
    clean_p.set_defaults(func=cmd_clean)

    status_p = sub.add_parser(
        "status", help="list the scratchpad and its classification"
    )
    status_p.add_argument(
        "--preserve",
        default=None,
        help='comma-separated basenames to treat as preserved (default ".gitignore")',
    )
    status_p.add_argument("--temp-dir", type=Path, default=None)
    status_p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
