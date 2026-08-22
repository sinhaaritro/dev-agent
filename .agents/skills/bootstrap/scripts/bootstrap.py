#!/usr/bin/env python3
"""bootstrap engine - install the Dev Agent framework into a target repo.

Copies the canonical seed files from this skill's reference/ folder to
their proper locations in the target repository:

    reference/AGENTS.md        -> <target>/AGENTS.md
    reference/rules/system.md  -> <target>/.agents/rules/system.md
    reference/.cursorrules     -> <target>/.cursorrules
    reference/.windsurfrules   -> <target>/.windsurfrules

The engine is location-agnostic (finds reference/ relative to itself) and
stdlib-only. It never guesses the target: --target is required and is
refused when it points at this framework's own source tree.

Usage:
    python <skill>/scripts/bootstrap.py --target /path/to/repo
    python <skill>/scripts/bootstrap.py --target /path/to/repo --dry-run

Per-file report lines:
    dry-run: new: <rel>  ok: <rel>  overwrite: <rel>
    install: installed: <rel>  unchanged: <rel>  updated: <rel>
Summary line (install): bootstrap complete: <N> installed, <M> updated, <K> unchanged

Exit codes: 0 = success (including dry-run); 1 = error (bad target,
missing seed file, self-bootstrap refused).
"""

import argparse
import shutil
import sys
from pathlib import Path

# (path inside reference/, path inside the target repo)
SEED_FILES = (
    ("AGENTS.md", "AGENTS.md"),
    ("rules/system.md", ".agents/rules/system.md"),
    (".cursorrules", ".cursorrules"),
    (".windsurfrules", ".windsurfrules"),
)


def find_skill_root() -> Path:
    """Walk up from this script until the skill root (the dir holding reference/)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "reference").is_dir():
            return current
        parent = current.parent
        if parent == current:
            sys.exit("error: reference/ folder not found above " + str(Path(__file__).resolve()))
        current = parent


def find_source_repo_root(skill_root: Path) -> Path:
    """Walk up from just above the skill root to the framework's own repo root.

    The marker is an AGENTS.md file, and the search starts at skill_root.parent so a
    stray AGENTS.md inside the skill itself can never be mistaken for the repo root.
    """
    current = skill_root.parent
    while True:
        if (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit("error: AGENTS.md not found above the skill - is the skill installed correctly?")
        current = parent


def verify_seeds(skill_root: Path) -> None:
    missing = [rel for rel, _ in SEED_FILES if not (skill_root / "reference" / rel).is_file()]
    if missing:
        sys.exit(
            "error: missing seed file(s) in reference/: "
            + ", ".join("reference/" + rel for rel in missing)
        )


def rel_or_root(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return path.name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="bootstrap: install the Dev Agent framework into a target repository"
    )
    parser.add_argument(
        "--target",
        required=True,
        help="absolute (or cwd-relative) path of the repository to bootstrap",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be installed without writing anything",
    )
    args = parser.parse_args()

    skill_root = find_skill_root()
    source_root = find_source_repo_root(skill_root)
    verify_seeds(skill_root)

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        sys.exit("error: target is not a directory: " + str(target))

    if target == source_root or target.is_relative_to(source_root):
        sys.exit(
            "error: refusing to bootstrap the framework's own source tree ("
            + str(source_root)
            + ") - this repo is the source of truth, not a target"
        )

    results = []  # (seed_rel, dest_rel, status)
    for seed_rel, dest_rel in SEED_FILES:
        src = skill_root / "reference" / seed_rel
        dst = target / dest_rel
        if not dst.exists():
            status = "new"
        elif dst.is_file() and dst.read_bytes() == src.read_bytes():
            status = "ok"
        else:
            status = "overwrite"
        results.append((seed_rel, dest_rel, status))

    if args.dry_run:
        for _, rel, status in results:
            print(status + ": " + rel)
        return 0

    installed = updated = unchanged = 0
    for seed_rel, rel, status in results:
        src = skill_root / "reference" / seed_rel
        dst = target / rel
        if status == "ok":
            print("unchanged: " + rel)
            unchanged += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        if status == "new":
            print("installed: " + rel)
            installed += 1
        else:
            print("updated: " + rel)
            updated += 1
    print(
        "bootstrap complete: "
        + str(installed)
        + " installed, "
        + str(updated)
        + " updated, "
        + str(unchanged)
        + " unchanged"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
