#!/usr/bin/env python3
"""phase-protocol engine - deterministic gate resolution & autonomy policy.

Decides the outcome of a Socratic gate from the autonomy matrix:
(gate: blocking|non-blocking) x (session: interactive|
non-interactive) x (lane A/B/C/D) x (autonomy: supervised|autonomous).

Outcomes:
    PROCEED     non-blocking gate in either session: state the default,
                make no file changes. Exit 0.
    HALT        blocking gate in an interactive session: await the
                human's answer. Exit 1.
    FAIL-CLOSED blocking gate in a non-interactive session under
                `supervised`, OR any Lane-A surface gate under
                `autonomous` (schema/auth/public-API never resolve
                 autonomously). Writes specs/temp/escalation.md and, when
                a spec/plan target exists, parks it for revision
                (PLAN_REVISION_REQUIRED for a Vetting-stage block,
                REVIEW_REVISION_REQUIRED for a Sign-off-stage block).
                Exit 2.
    RESOLVED    blocking gate in a non-interactive session under
                `autonomous` with no Lane-A surface: apply the
                Recommended Option and append an audit entry to the
                active plan/spec `## 6. Gates` section (append-only).
                The target is `--spec` if given, else the newest active
                NNN-SPEC-*.md, else specs/temp/draft-plan.md. No target
                => fail closed. Exit 0.

Autonomy defaults to the `autonomy_level` frontmatter of AGENTS.md
(supervised if absent); --autonomy overrides for testing.

Usage:
    python .agents/scripts/devagent/main.py gate \
        --gate blocking --session non-interactive --lane B \
        --question "which cache?" \
        --options "A (Recommended): redis; B: memcached" \
        [--autonomy autonomous] [--lane-a-surface] [--choice A]

Exit codes: 0 = proceed/resolved; 1 = halt (await human); 2 = fail-closed
(escalation.md written; target spec parked for revision when one exists).
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

from common.root import find_root


def read_autonomy(root: Path) -> str:
    """Parse `autonomy_level:` from AGENTS.md or AGENTS.md frontmatter; default supervised."""
    agent_file = root / "AGENTS.md"
    try:
        text = agent_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "supervised"
    match = re.search(r"(?m)^autonomy_level:\s*(\S+)", text)
    return match.group(1) if match else "supervised"


def parse_options(options_text: str) -> list[str]:
    """Split "--options 'A (Recommended): x; B: y'" into option lines."""
    parts = [p.strip() for p in options_text.split(";") if p.strip()]
    if not parts:
        return ["A (Recommended): <not provided>"]
    return parts


def gate_log_entry(
    question: str, option_lines: list[str], choice: str, autonomy: str
) -> str:
    """Markdown entry appended under the target's `## 6. Gates` heading."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    choice_line = option_lines[0] if choice == "A" and option_lines else choice
    lines = [
        f"### Gate {now} — blocking ({autonomy}) — RESOLVED",
        f"- Question: {question}",
        "- Options: " + "; ".join(option_lines),
        f"- Choice made: {choice} - {choice_line}",
        f"- Autonomy mode: {autonomy}",
    ]
    return "\n".join(lines)


def escalation_entry(
    question: str, option_lines: list[str], lane: str, session: str
) -> str:
    """Fail-closed report per the format declared in specs/temp/escalation.md."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"Date: {now}",
        "Trigger: supervised fail-closed (blocking gate)",
        f"Lane: {lane}",
        f"Session: {session}",
        "",
        "## 1. Pending Question / Problem",
        "What blocked execution. For gates: the exact question with its guided options.",
        "",
        question,
        "",
        "## 4. Remediation Options",
    ]
    for opt in option_lines:
        if ":" in opt:
            label, _, rest = opt.partition(":")
            lines.append(f"- Option {label.strip()}: {rest.strip()}")
        else:
            lines.append(f"- {opt}")
    lines.append("")
    lines.append("## 5. State Preserved")
    lines.append("- Dirty edits reverted: no (a run never reverts mid-build)")
    lines.append("- Working tree state: left as-is for human inspection")
    lines.append("- Related artifacts: specs/temp/<files>")
    lines.append("")
    return "\n".join(lines)


def ensure_scratchpad_guard(root: Path, temp_dir: Path) -> None:
    """Scratchpad guard: the dir, a root .gitignore entry for it, and the inner stub.

    The inner stub (``*`` + ``!.gitignore``) is the effective protection - git
    refuses to descend into a gitignored directory even without a root
    .gitignore - while the root entry documents the exclusion for viewers that
    stop at the top level. Idempotent; only touched when acting on the default
    specs/temp/ location.
    """
    root_ignore = root / ".gitignore"
    if not root_ignore.is_file():
        root_ignore.write_text("# DEV Agent framework\n", encoding="utf-8")
    lines = root_ignore.read_text(encoding="utf-8").splitlines()
    if not any(
        ln.strip().strip("/") in ("specs", "specs/temp")
        for ln in lines
        if ln.strip() and not ln.strip().startswith("#")
    ):
        text = root_ignore.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        root_ignore.write_text(text + "\nspecs/temp\n", encoding="utf-8")
    inner = temp_dir / ".gitignore"
    if not inner.is_file():
        inner.write_text("*\n!.gitignore\n", encoding="utf-8")


def append_gate_entry(target: Path, entry: str) -> None:
    """Append `entry` inside the target's `## 6. Gates` section.

    Creates the section when the plan/spec has none, and never touches text
    outside it. The plan is promoted *with* its section 6, so the entry survives into
    the spec and is no longer scratchpad content.
    """
    text = target.read_text(encoding="utf-8-sig") if target.is_file() else ""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(r"^##\s+6\.", line.strip()):
            start = index
            break

    block = entry.splitlines()
    if start is None:
        new_text = text.rstrip("\n")
        new_text += "\n\n## 6. Gates\n\n" + entry + "\n"
    else:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if re.match(r"^##\s", lines[index].strip()):
                end = index
                break
        before = lines[:end]
        after = lines[end:]
        while before and not before[-1].strip():
            before.pop()
        merged = before + [""] + block + [""]
        if after:
            merged += after
        new_text = "\n".join(merged).rstrip("\n") + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_text, encoding="utf-8")


ACTIVE_STATUSES = (
    "DRAFTED",
    "APPROVED",
    "PROVISIONAL",
    "COMPILED",
    "BUILDING",
    "BUILT",
    "REVIEWED",
    "PLAN_REVISION_REQUIRED",
)
PLANNING_STATUSES = ("DRAFTED", "APPROVED", "PROVISIONAL")
BUILD_STATUSES = ("BUILDING", "BUILT", "REVIEWED")


def _status_token(path: Path) -> str:
    """The 'Status:' token of a plan/spec file ('' when absent/unreadable)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = re.search(r"(?m)^Status:\s*([A-Z_]+)", text)
    return match.group(1) if match else ""


def find_active_spec(root: Path) -> Path | None:
    """Newest specs/*-SPEC-*.md whose Status is still active."""
    specs = sorted(
        (root / "specs").glob("*-SPEC-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in specs:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = re.search(r"(?m)^Status:\s*([A-Z_]+)", text)
        if match and match.group(1) in ACTIVE_STATUSES:
            return path
    return None


def resolve_gate_target(root: Path, spec_arg: str | None) -> Path | None:
    """Pick where the audit entry belongs: --spec, the in-flight draft, active spec.

    Planning-stage work owns the draft: while the active spec is merely
    COMPILED (or similar) and a DRAFTED/APPROVED draft exists, the gate belongs
    to the draft. A spec that is actually being built (BUILDING/BUILT/REVIEWED)
    keeps ownership so a stale draft cannot capture mid-build gates.
    """
    if spec_arg:
        target = Path(spec_arg)
        if not target.is_absolute():
            target = root / target
        return target
    draft = root / "specs" / "temp" / "draft-plan.md"
    draft_status = _status_token(draft) if draft.is_file() else ""
    active = find_active_spec(root)
    if active is not None:
        if _status_token(active) in BUILD_STATUSES:
            return active
        if draft_status in PLANNING_STATUSES:
            return draft
        return active
    if draft.is_file():
        return draft
    return None


def write_escalation(root: Path, report: str) -> None:
    """Write the fail-closed report to specs/temp/escalation.md (ephemeral scratchpad)."""
    temp_dir = root / "specs" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    ensure_scratchpad_guard(root, temp_dir)
    (temp_dir / "escalation.md").write_text(report, encoding="utf-8")


def mark_revision_required(root: Path, spec_arg: str | None) -> None:
    """Gate owner: a blocked gate parks the plan/spec for revision.

    A Vetting-stage block (the plan is not compiled yet) or a Sign-off-stage
    block (the spec is built/reviewed) both stop the run; the target drops to
    PLAN_REVISION_REQUIRED or REVIEW_REVISION_REQUIRED respectively. No target
    (Lane C, or no plan yet) leaves the status untouched.
    """
    if spec_arg:
        target = Path(spec_arg)
        if not target.is_absolute():
            target = root / target
    else:
        # Never guess an unrelated active spec: without --spec, only the
        # in-flight draft can be the target of a planning-stage block.
        target = root / "specs" / "temp" / "draft-plan.md"
    if not target.is_file():
        return
    text = target.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?m)^Status:\s*(\S+)", text)
    if not match:
        return
    current = match.group(1)
    if current in ("DRAFTED", "APPROVED", "PROVISIONAL", "COMPILED"):
        new = "PLAN_REVISION_REQUIRED"
    elif current in ("BUILDING", "BUILT", "REVIEWED"):
        new = "REVIEW_REVISION_REQUIRED"
    else:
        return
    updated = re.sub(r"(?m)^(Status:\s*)\S+", r"\g<1>" + new, text, count=1)
    target.write_text(updated, encoding="utf-8")
    print("status: " + current + " -> " + new + " (" + target.name + ")")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="devagent gate",
        description="phase-protocol gate resolution engine",
    )
    # No choices= here: case-insensitive normalization happens after parsing -
    # the documented forms ("--session Interactive") must not fail with exit 2.
    parser.add_argument("--gate", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--autonomy", default=None)
    parser.add_argument(
        "--lane-a-surface",
        action="store_true",
        help="gate touches database schema, auth, or a public API",
    )
    parser.add_argument("--question", default="")
    parser.add_argument("--options", default="")
    parser.add_argument("--choice", default="A")
    parser.add_argument(
        "--spec",
        default=None,
        help=(
            "plan/spec to record the gate in (default: the in-flight draft "
            "while planning, otherwise the newest active spec)"
        ),
    )
    args = parser.parse_args()

    # Normalize case, then validate: an argparse error would exit 2, the
    # FAIL-CLOSED code, indistinguishable from a real policy outcome.
    args.gate = args.gate.lower()
    args.session = args.session.lower()
    args.lane = args.lane.upper()
    if args.autonomy:
        args.autonomy = args.autonomy.lower()
    args.choice = args.choice.upper()

    if args.gate not in ("blocking", "non-blocking"):
        parser.error(f"--gate must be blocking or non-blocking, got {args.gate!r}")
    if args.session not in ("interactive", "non-interactive"):
        parser.error(
            f"--session must be interactive or non-interactive, got {args.session!r}"
        )
    if args.lane not in ("A", "B", "C", "D"):
        parser.error(f"--lane must be A, B, C, or D, got {args.lane!r}")
    if args.autonomy and args.autonomy not in ("supervised", "autonomous"):
        parser.error(
            f"--autonomy must be supervised or autonomous, got {args.autonomy!r}"
        )
    if args.choice not in ("A", "B"):
        parser.error(f"--choice must be A or B, got {args.choice!r}")

    root = find_root()
    autonomy = args.autonomy or read_autonomy(root)
    option_lines = parse_options(args.options)

    if args.gate == "non-blocking":
        print("PROCEED: non-blocking gate - state the default and proceed immediately")
        print("(no files written; identical behavior in both session types)")
        return 0

    if args.session == "interactive":
        print(
            "HALT: blocking gate in an interactive session - await the human's answer"
        )
        print("(no files written; nothing ships without a human reply)")
        return 1

    lane_a_surface = args.lane_a_surface or args.lane == "A"
    if autonomy == "supervised" or lane_a_surface:
        report = escalation_entry(args.question, option_lines, args.lane, args.session)
        write_escalation(root, report)
        mark_revision_required(root, args.spec)
        reason = (
            "Lane-A surface (schema/auth/public-API) - always fail closed, "
            "even under autonomous"
            if lane_a_surface and autonomy == "autonomous"
            else "supervised fail-closed policy"
        )
        print("FAIL-CLOSED: " + reason)
        print("escalation.md written; no gate log entry; no changes made")
        return 2

    target = resolve_gate_target(root, args.spec)
    if target is None:
        print("FAIL-CLOSED: no plan or spec to record the autonomous gate in")
        print(
            "create specs/temp/draft-plan.md, promote the spec, or pass --spec <path>"
        )
        return 2
    entry = gate_log_entry(args.question, option_lines, args.choice, autonomy)
    append_gate_entry(target, entry)
    print(f"RESOLVED: autonomous default {args.choice} (Recommended) applied")
    print(f"gate entry appended to {target} section 6; no code changes made")
    return 0


if __name__ == "__main__":
    sys.exit(main())
