#!/usr/bin/env python3
"""spec-builder engine - draft validation, spec promotion, ADR filing, and handoff.

Owns the mechanical parts of the spec lifecycle (000 ss7, ss10): template
enforcement, sequential numbering, promotion mechanics, Architectural
Decision Record filing, and the Phase 1.5 handoff record (spec 008). The
acceptance gate itself is the caller's - the agent asserts it via --status
(APPROVED for human acceptance, PROVISIONAL for a compliant autonomous
resolution); this script never decides whether the gate passed. ADRs are
filed only alongside APPROVED promotion (human acceptance).

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

    adr      promote_spec.py adr <draft-adr> [--source <spec-path>]
                 [--dry-run] [--decisions-dir <dir>]
             Validate an ADR draft against references/adr-template.md (title,
             "Status: Accepted", "Date: YYYY-MM-DD", and the Context, Decision,
             Consequences sections), compute the next adr number by scanning
             the decisions directory for the max "adr-<NNN>-" prefix + 1,
             derive the slug from the title, stamp the Source: line from
             --source when given, refuse to overwrite an existing ADR (ADRs
             are protected files - system.md section 3), and write the record
             to docs/decisions/. --decisions-dir overrides the target
             directory (tests and evals use a sandbox; the real
             docs/decisions/ is never touched by verification).

    handoff  promote_spec.py handoff <spec> --lane <B|A>
                 [--dry-run] [--handoff-dir <dir>] [--decisions-dir <dir>]
             Record the Phase 1.5 handoff for an approved spec (spec 008).
             Validates the spec exists with Status: APPROVED (Lane A also
             requires at least one ADR whose Source: points at the spec;
             Lane B allows zero), writes docs/temp/handoff.md (ephemeral
             record), and stamps "Handoff: <YYYY-MM-DD>" on the spec's
             status header (durable marker). Idempotent - re-running against
             an already-handoffed spec reports the existing record and exits
             0. --dry-run prints what would be written without writing.
             --handoff-dir/--decisions-dir override the targets (tests and
             evals use a sandbox; the real docs/ are never touched).

Usage:
    uv run python .agents/skills/spec-builder/scripts/promote_spec.py \
        check docs/temp/draft-plan.md --lane B
    uv run python .agents/skills/spec-builder/scripts/promote_spec.py \
        promote docs/temp/draft-plan.md --lane A --status APPROVED
    uv run python .agents/skills/spec-builder/scripts/promote_spec.py \
        adr docs/temp/adr-draft-in-memory-storage.md \
        --source docs/specs/001-bday-001-birthday-tracker-greenfield.md
    uv run python .agents/skills/spec-builder/scripts/promote_spec.py \
        handoff docs/specs/008-post-approval-handoff-guard.md --lane A

Exit codes: 0 = check passed / promoted / adr filed / handoff recorded;
1 = check failed, exists, or error.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

LANE_SECTIONS = {"B": {1, 3, 4}, "A": {1, 2, 3, 4, 5, 6}}
PROVISIONAL_STATUS = "PROVISIONAL - AUTONOMOUS DEFAULT"


def find_root() -> Path:
    """Walk up from the script location until AGENT.md or AGENTS.md is found (repo root marker)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENT.md").is_file() or (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit(
                "error: AGENT.md / AGENTS.md not found above "
                + str(Path(__file__).resolve())
            )
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

    A leading '[SPEC-ID]:', 'NNN:', or 'ADR-NNN:' token is stripped so a draft
    titled '# 103: Refresh Token Column' promotes to 'refresh-token-column'
    and an ADR titled '# ADR-001: In-Memory Storage' files to
    'in-memory-storage'."
    """
    title = ""
    for line in text.splitlines():
        if line.strip().startswith("# "):
            title = line.strip().lstrip("# ").strip()
            break
    title = re.sub(r"^(\[\S+\]|\d{3}|ADR-\d{3}):\s*", "", title)
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


def adr_required_sections() -> list[str]:
    """The body sections an ADR must carry (references/adr-template.md)."""
    return ["Context", "Decision", "Consequences"]


def check_adr(text: str) -> tuple[bool, list[str]]:
    """Return (ok, missing) for the ADR template's required elements."""
    lines = text.splitlines()
    missing: list[str] = []
    if not any(line.strip().startswith("# ") for line in lines):
        missing.append("title")
    if not re.search(r"(?m)^Status:\s*Accepted\s*$", text):
        missing.append("Status: Accepted")
    if not re.search(r"(?m)^Date:\s*\d{4}-\d{2}-\d{2}\s*$", text):
        missing.append("Date: YYYY-MM-DD")
    for section in adr_required_sections():
        if not any(
            re.match(r"^##\s+" + section + r"\s*$", line.strip()) for line in lines
        ):
            missing.append(section)
    return (not missing), missing


def next_adr_number(decisions_dir: Path) -> int:
    """Highest 'adr-<NNN>' prefix in the decisions directory + 1 (1 if empty)."""
    highest = 0
    if decisions_dir.is_dir():
        for entry in decisions_dir.iterdir():
            if entry.is_file():
                match = re.match(r"^adr-(\d{3})-", entry.name)
                if match:
                    highest = max(highest, int(match.group(1)))
    return highest + 1


def find_existing_adr_by_title(decisions_dir: Path, title: str) -> Path | None:
    """Return an existing ADR whose first '#' title matches the draft's.

    The ADR topic is its identity - re-filing the same decision must be
    refused even though the sequential number is new.
    """
    if not decisions_dir.is_dir():
        return None
    for entry in decisions_dir.iterdir():
        if not entry.is_file() or not re.match(r"^adr-\d{3}-", entry.name):
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


def stamp_source(text: str, source: str) -> str:
    """Replace or insert the 'Source:' line pointing back to the spec."""
    if re.search(r"(?m)^Source:\s*", text):
        return re.sub(r"(?m)^Source:\s*.*$", "Source: " + source, text, count=1)
    return re.sub(r"(?m)^(Date:\s*\S+.*)$", r"\g<1>\nSource: " + source, text, count=1)


def cmd_adr(args: argparse.Namespace) -> int:
    try:
        text = read_text(args.draft)
    except (OSError, UnicodeDecodeError):
        print("error: cannot read " + str(args.draft))
        return 1

    ok, missing = check_adr(text)
    if not ok:
        print("missing: " + ", ".join(missing))
        return 1

    title = draft_title(text)
    existing = find_existing_adr_by_title(args.decisions_dir, title) if title else None
    if existing is not None:
        print(f"already exists: {existing}")
        return 1

    num = next_adr_number(args.decisions_dir)
    slug = slug_from_title(text)
    target = args.decisions_dir / f"adr-{num:03d}-{slug}.md"
    print(f"next: adr-{num:03d}")
    if target.exists():
        print(f"already exists: {target}")
        return 1
    if args.dry_run:
        print(f"target: {target}")
        return 0

    args.decisions_dir.mkdir(parents=True, exist_ok=True)
    if args.source:
        text = stamp_source(text, args.source)
    target.write_text(text, encoding="utf-8")
    print(f"adr: {target}")
    return 0


def draft_title(text: str) -> str:
    """The draft's first '#' heading line (its identity)."""
    for line in text.splitlines():
        if line.strip().startswith("# "):
            return line.strip()
    return ""


def status_value(text: str) -> str:
    """The current 'Status:' header value ('' if absent).

    The Status line also carries the phase marker in build (e.g.
    "APPROVED | Phase: 2-Build"), so callers match on the leading token.
    """
    match = re.search(r"(?m)^Status:\s*(\S.*)$", text)
    return match.group(1).strip() if match else ""


def adrs_sourced_to(decisions_dir: Path, spec_ref: str) -> list[str]:
    """ADR filenames whose 'Source:' line points at the spec (normalized).

    Matches either on the full normalized path or on the filename alone, so
    an absolute caller path still matches an ADR stamped with a relative
    docs/specs/... Source: line.
    """
    norm = spec_ref.replace("\\", "/")
    norm_base = norm.rsplit("/", 1)[-1]
    found: list[str] = []
    if not decisions_dir.is_dir():
        return found
    for entry in decisions_dir.iterdir():
        if not entry.is_file() or not re.match(r"^adr-\d{3}-", entry.name):
            continue
        try:
            text = read_text(entry)
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            if line.strip().startswith("Source:"):
                src = line.split(":", 1)[1].strip().replace("\\", "/")
                if src == norm or src.rsplit("/", 1)[-1] == norm_base:
                    found.append(entry.name)
                break
    return found


def cmd_handoff(args: argparse.Namespace) -> int:
    """Validate and record the Phase 1.5 handoff (spec 008)."""
    try:
        text = read_text(args.spec)
    except (OSError, UnicodeDecodeError):
        print("error: cannot read spec " + str(args.spec))
        return 1

    if not status_value(text).startswith("APPROVED"):
        print("error: spec is not Status: APPROVED")
        return 1

    spec_ref = str(args.spec).replace("\\", "/")
    adrs = adrs_sourced_to(args.decisions_dir, spec_ref)
    if args.lane == "A" and not adrs:
        print("error: Lane A handoff requires an ADR sourced to this spec")
        return 1

    today = date.today().isoformat()
    handoff_file = args.handoff_dir / "handoff.md"

    if re.search(r"(?m)^Handoff:\s*\d{4}-\d{2}-\d{2}\s*$", text):
        print(f"already handed off: {handoff_file}")
        return 0

    if args.dry_run:
        print(f"record: {handoff_file}")
        print(f"stamp: Handoff: {today} on {spec_ref}")
        return 0

    stamped = re.sub(
        r"(?m)^(Status:\s*.*)$", r"\g<1>\nHandoff: " + today, text, count=1
    )
    if stamped == text:
        print("error: cannot stamp Handoff on spec header")
        return 1

    args.handoff_dir.mkdir(parents=True, exist_ok=True)
    args.spec.write_text(stamped, encoding="utf-8")

    adr_line = ", ".join(adrs) if adrs else "none (Lane B)"
    handoff_file.write_text(
        "# Handoff - Session Ends Here\n\n"
        f"Date: {today}\n"
        f"Spec: {spec_ref}\n"
        f"Lane: {args.lane}\n"
        f"ADRs: {adr_line}\n\n"
        "Implementation runs in a new session that reads the promoted spec "
        "(spec 008 D1). The session that recorded this handoff must not open "
        "references/build.md.\n",
        encoding="utf-8",
    )
    print(f"handoff: {handoff_file}")
    return 0


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
    parser = argparse.ArgumentParser(
        description="spec-builder check, promotion & ADR filing"
    )
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

    adr_p = sub.add_parser(
        "adr", help="validate and file an ADR draft to docs/decisions"
    )
    adr_p.add_argument("draft", type=Path, help="ADR draft in docs/temp")
    adr_p.add_argument(
        "--source",
        default=None,
        help="spec path to stamp on the Source: line (e.g. docs/specs/001-<slug>.md)",
    )
    adr_p.add_argument("--dry-run", action="store_true")
    adr_p.add_argument(
        "--decisions-dir",
        type=Path,
        default=None,
        help="target decisions directory (default <root>/docs/decisions; sandbox for tests)",
    )
    adr_p.set_defaults(func=cmd_adr)

    handoff_p = sub.add_parser(
        "handoff", help="record the Phase 1.5 handoff for an approved spec"
    )
    handoff_p.add_argument("spec", type=Path, help="promoted spec in docs/specs")
    handoff_p.add_argument("--lane", required=True, choices=["B", "A"])
    handoff_p.add_argument("--dry-run", action="store_true")
    handoff_p.add_argument(
        "--handoff-dir",
        type=Path,
        default=None,
        help="target record directory (default <root>/docs/temp; sandbox for tests)",
    )
    handoff_p.add_argument(
        "--decisions-dir",
        type=Path,
        default=None,
        help="decisions directory for the Lane A ADR check (default <root>/docs/decisions)",
    )
    handoff_p.set_defaults(func=cmd_handoff)

    args = parser.parse_args()
    if args.command == "promote" and args.specs_dir is None:
        args.specs_dir = find_root() / "docs" / "specs"
    if args.command == "adr" and args.decisions_dir is None:
        args.decisions_dir = find_root() / "docs" / "decisions"
    if args.command == "handoff":
        if args.handoff_dir is None:
            args.handoff_dir = find_root() / "docs" / "temp"
        if args.decisions_dir is None:
            args.decisions_dir = find_root() / "docs" / "decisions"
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
