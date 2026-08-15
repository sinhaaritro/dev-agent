#!/usr/bin/env python3
"""spec-builder engine - draft validation and spec promotion.

Owns the mechanical parts of the spec lifecycle (000 ss7, ss10): template
enforcement, sequential numbering, and promotion mechanics. The acceptance
gate itself is the caller's - the agent asserts it via --status (APPROVED
for human acceptance, PROVISIONAL for a compliant autonomous resolution);
this script never decides whether the gate passed.

Modes:
    check    promote_spec.py check <draft> --lane <B|A>
             Parse the draft's "## N." section headings and verify the
             lane's required sections are present (B: 1, 3, 4; A: 1-6).
             Exit 0 when complete, 1 with a missing-sections list when not.

    promote  promote_spec.py promote <draft> --lane <B|A>
                 --status <APPROVED|PROVISIONAL> [--dry-run]
                 [--slug <override>] [--specs-dir <dir>]
             Check the draft, then compute the next spec number by scanning
             the specs directory for the max 3-digit prefix + 1 (zero-padded,
             sequential - never guessed), derive the slug from the draft
             title, write the promoted file with its Status line replaced,
             and refuse if the target already exists. --specs-dir overrides
             the target directory (tests and evals use a sandbox; the real
             docs/specs/ is never touched by verification).

Usage:
    uv run python .agents/skills/spec-builder/scripts/promote_spec.py \
        check docs/temp/draft-plan.md --lane B
    uv run python .agents/skills/spec-builder/scripts/promote_spec.py \
        promote docs/temp/draft-plan.md --lane A --status APPROVED

Exit codes: 0 = check passed / promoted; 1 = check failed, exists, or error.
"""

import argparse
import re
import sys
from pathlib import Path

LANE_SECTIONS = {"B": {1, 3, 4}, "A": {1, 2, 3, 4, 5, 6}}
PROVISIONAL_STATUS = "PROVISIONAL - AUTONOMOUS DEFAULT"


def find_root() -> Path:
    """Walk up from the script location until AGENT.md is found (repo root marker)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENT.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit("error: AGENT.md not found above " + str(Path(__file__).resolve()))
        current = parent


def parse_sections(text: str) -> set[int]:
    """Collect the section numbers present as '## N.' headings."""
    found: set[int] = set()
    for line in text.splitlines():
        match = re.match(r"^##\s+(\d+)\.", line.strip())
        if match:
            found.add(int(match.group(1)))
    return found


def read_text(path: Path) -> str:
    """Read UTF-8, tolerating a BOM (utf-8-sig strips it).

    Windows editors routinely prepend a BOM; without stripping it the
    first title line would not match "# " and the slug would degrade
    to the 'spec' fallback.
    """
    return path.read_text(encoding="utf-8-sig")


def check_draft(draft: Path, lane: str) -> tuple[bool, list[int]]:
    """Return (passed, missing_sections) for the lane's required set."""
    try:
        text = read_text(draft)
    except (OSError, UnicodeDecodeError):
        return False, []
    found = parse_sections(text)
    missing = sorted(LANE_SECTIONS[lane] - found)
    return (not missing), missing


def next_number(specs_dir: Path) -> int:
    """Highest 3-digit prefix in the specs directory + 1 (1 if empty)."""
    highest = 0
    if specs_dir.is_dir():
        for entry in specs_dir.iterdir():
            if entry.is_file():
                match = re.match(r"^(\d{3})-", entry.name)
                if match:
                    highest = max(highest, int(match.group(1)))
    return highest + 1


def slug_from_title(text: str) -> str:
    """Derive a slug from the first '#' title: lowercase, non-alnum to hyphen.

    A leading '[SPEC-ID]:' or 'NNN:' token is stripped so a draft titled
    '# 103: Refresh Token Column' promotes to 'refresh-token-column'."
    """
    title = ""
    for line in text.splitlines():
        if line.strip().startswith("# "):
            title = line.strip().lstrip("# ").strip()
            break
    title = re.sub(r"^(\[\S+\]|\d{3}):\s*", "", title)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "spec"


def find_existing_by_title(specs_dir: Path, title: str) -> Path | None:
    """Return an existing spec whose first '#' title matches the draft's.

    The SPEC-ID/title is the plan's identity - a repeat promotion of the
    same draft must be refused even though the sequential number is new.
    """
    if not specs_dir.is_dir():
        return None
    for entry in specs_dir.iterdir():
        if not entry.is_file() or not re.match(r"^\d{3}-", entry.name):
            continue
        try:
            first = read_text(entry).splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in first:
            if line.strip().startswith("# "):
                if line.strip() == title.strip():
                    return entry
                break
    return None


def draft_title(text: str) -> str:
    """The draft's first '#' heading line (its identity)."""
    for line in text.splitlines():
        if line.strip().startswith("# "):
            return line.strip()
    return ""


def normalize_status(status: str) -> str:
    """Expand shorthand: PROVISIONAL -> 'PROVISIONAL - AUTONOMOUS DEFAULT'."""
    if status.upper() == "PROVISIONAL":
        return PROVISIONAL_STATUS
    return "APPROVED"


def replace_status(text: str, status: str) -> str:
    """Replace the 'Status:' frontmatter/header value with the new one."""
    return re.sub(r"(?m)^(Status:\s*).*$", r"\g<1>" + status, text, count=1)


def cmd_check(args: argparse.Namespace) -> int:
    passed, missing = check_draft(args.draft, args.lane)
    if passed:
        print("check passed")
        return 0
    print("missing sections: " + ", ".join(str(n) for n in missing))
    return 1


def cmd_promote(args: argparse.Namespace) -> int:
    passed, missing = check_draft(args.draft, args.lane)
    if not passed:
        print("check failed - missing sections: " + ", ".join(str(n) for n in missing))
        return 1

    try:
        text = read_text(args.draft)
    except (OSError, UnicodeDecodeError):
        print("error: cannot read " + str(args.draft))
        return 1

    title = draft_title(text)
    existing = find_existing_by_title(args.specs_dir, title) if title else None
    if existing is not None:
        print(f"already exists: {existing}")
        return 1

    num = next_number(args.specs_dir)
    slug = args.slug or slug_from_title(text)
    target = args.specs_dir / f"{num:03d}-{slug}.md"
    print(f"next: {num:03d}")
    if target.exists():
        print(f"already exists: {target}")
        return 1
    if args.dry_run:
        print(f"target: {target}")
        return 0

    args.specs_dir.mkdir(parents=True, exist_ok=True)
    status = normalize_status(args.status)
    target.write_text(replace_status(text, status), encoding="utf-8")
    print(f"promoted: {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="spec-builder draft check & promotion")
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check", help="validate a draft against the lane template")
    check_p.add_argument("draft", type=Path)
    check_p.add_argument("--lane", required=True, choices=["B", "A"])
    check_p.set_defaults(func=cmd_check)

    promote_p = sub.add_parser(
        "promote", help="promote an approved draft to docs/specs"
    )
    promote_p.add_argument("draft", type=Path)
    promote_p.add_argument("--lane", required=True, choices=["B", "A"])
    promote_p.add_argument(
        "--status",
        required=True,
        choices=["APPROVED", "PROVISIONAL"],
        help="APPROVED = human acceptance; PROVISIONAL = autonomous resolution",
    )
    promote_p.add_argument("--dry-run", action="store_true")
    promote_p.add_argument("--slug", default=None)
    promote_p.add_argument(
        "--specs-dir",
        type=Path,
        default=None,
        help="target specs directory (default <root>/docs/specs; sandbox for tests)",
    )
    promote_p.set_defaults(func=cmd_promote)

    args = parser.parse_args()
    if args.command == "promote" and args.specs_dir is None:
        args.specs_dir = find_root() / "docs" / "specs"
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
