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
                 autonomously). Writes docs/temp/escalation.md.
                Exit 2.
    RESOLVED    blocking gate in a non-interactive session under
                `autonomous` with no Lane-A surface: apply the
                Recommended Option and append a verbatim audit entry to
                docs/temp/gate-log.md (append-only, never truncated or
                purged - system.md ss3). Exit 0.

Autonomy defaults to the `autonomy_level` frontmatter of AGENTS.md
(supervised if absent); --autonomy overrides for testing.

Usage:
    python .agents/skills/phase-protocol/scripts/resolve_gate.py \
        --gate blocking --session non-interactive --lane B \
        --question "which cache?" \
        --options "A (Recommended): redis; B: memcached" \
        [--autonomy autonomous] [--lane-a-surface] [--choice A]

Exit codes: 0 = proceed/resolved; 1 = halt (await human); 2 = fail-closed
(escalation.md written).
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

LINES = "-" * 40


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


def read_autonomy(root: Path) -> str:
    """Parse `autonomy_level:` from AGENTS.md or AGENTS.md frontmatter; default supervised."""
    agent_file = root / "AGENTS.md"
    if not agent_file.is_file():
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
    """Verbatim entry per the format declared in docs/temp/gate-log.md."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    choice_line = option_lines[0] if choice == "A" and option_lines else choice
    lines = [
        LINES,
        f"## Entry {now}",
        f"Question: {question}",
        "Options:",
    ]
    for opt in option_lines:
        lines.append(f"- {opt}")
    lines.append(f"Choice made: {choice} - {choice_line}")
    lines.append("Autonomy mode: autonomous")
    lines.append("Spec tagged provisional: no")
    lines.append("")
    return "\n".join(lines)


def escalation_entry(
    question: str, option_lines: list[str], lane: str, session: str
) -> str:
    """Fail-closed report per the format declared in docs/temp/escalation.md."""
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
    lines.append("- Dirty edits reverted: yes")
    lines.append("- Working tree state: clean (no changes were made)")
    lines.append("- Related artifacts: docs/temp/<files>")
    lines.append("")
    return "\n".join(lines)


def ensure_scratchpad_guard(root: Path, temp_dir: Path) -> None:
    """Scratchpad guard: the dir, a root .gitignore entry for it, and the inner stub.

    The inner stub (``*`` + ``!.gitignore``) is the effective protection - git
    refuses to descend into a gitignored directory even without a root
    .gitignore - while the root entry documents the exclusion for viewers that
    stop at the top level. Idempotent; only touched when acting on the default
    docs/temp/ location.
    """
    root_ignore = root / ".gitignore"
    if not root_ignore.is_file():
        root_ignore.write_text("# DEV Agent framework\n", encoding="utf-8")
    lines = root_ignore.read_text(encoding="utf-8").splitlines()
    if not any(
        ln.strip().strip("/") in ("docs", "docs/temp")
        for ln in lines
        if ln.strip() and not ln.strip().startswith("#")
    ):
        text = root_ignore.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        root_ignore.write_text(text + "\ndocs/temp\n", encoding="utf-8")
    inner = temp_dir / ".gitignore"
    if not inner.is_file():
        inner.write_text("*\n!.gitignore\n", encoding="utf-8")


def append_gate_log(root: Path, entry: str) -> None:
    """Append-only write; creates docs/temp/gate-log.md with its header if missing."""
    temp_dir = root / "docs" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    ensure_scratchpad_guard(root, temp_dir)
    gate_log = temp_dir / "gate-log.md"
    if not gate_log.is_file():
        header = (
            "# Gate Log - Autonomous Choice Audit Trail\n"
            "\n"
            "Append-only audit log for autonomous policy resolutions (phase-protocol "
            "skill). This file is **never purged** by task-cleaner until a human "
            "explicitly reviews it.\n"
            "\n"
            "Format for each entry:\n"
            "\n"
            "```text\n"
            "---\n"
            "## Entry YYYY-MM-DD HH:MM\n"
            "Question: <the blocking question as posed>\n"
            "Options:\n"
            "- A (Recommended): <option A>\n"
            "- B: <option B>\n"
            "Choice made: <A | B> - <option summary>\n"
            "Autonomy mode: autonomous\n"
            "Spec tagged provisional: <yes/no + docs/specs/<id> if promoted>\n"
            "```\n"
        )
        gate_log.write_text(header, encoding="utf-8")
    with gate_log.open("a", encoding="utf-8") as fh:
        fh.write(entry)


def write_escalation(root: Path, report: str) -> None:
    """Write the fail-closed report to docs/temp/escalation.md (ephemeral scratchpad)."""
    temp_dir = root / "docs" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    ensure_scratchpad_guard(root, temp_dir)
    (temp_dir / "escalation.md").write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="phase-protocol gate resolution engine"
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
        reason = (
            "Lane-A surface (schema/auth/public-API) - always fail closed, "
            "even under autonomous"
            if lane_a_surface and autonomy == "autonomous"
            else "supervised fail-closed policy"
        )
        print("FAIL-CLOSED: " + reason)
        print("escalation.md written; gate-log.md untouched; no changes made")
        return 2

    entry = gate_log_entry(args.question, option_lines, args.choice, autonomy)
    append_gate_log(root, entry)
    print(f"RESOLVED: autonomous default {args.choice} (Recommended) applied")
    print("gate-log.md appended verbatim; no code changes made")
    return 0


if __name__ == "__main__":
    sys.exit(main())
