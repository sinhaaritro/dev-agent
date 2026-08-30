#!/usr/bin/env python3
"""verification-runner engine - retry counter, circuit breaker, escalation reports.

Owns the mechanical parts of the framework's verification contract:
the 3-consecutive-failure circuit breaker, the escalation report, the
Expect-marker pass criterion with recorded evidence, and
command approval separate from plan approval. The counter
lives on disk so the limit survives across agent turns and cannot be
silently reset by forgetting. The engine is a ledger, never a judge: it
records what the command actually returned and trips at the threshold.

State: docs/temp/verify-state.json (gitignored scratchpad, per-task keys,
purged by task-cleaner on acceptance). Escalation: docs/temp/escalation.md.
Approvals: docs/temp/approvals.json (gitignored scratch, per-task lifetime;
a new session re-approves - the safe default).

Modes:
    run      verify.py run --command "<cmd>" --task <id>
                  [--expect <marker>] [--lane <A|B|C|D>]
                  [--timeout <s>] [--hypothesis "<text>"]
                  [--options "A (Recommended): ...; B: ..."]
                  [--state-dir <dir>]
              Execute the command (300s default timeout, interactive commands
              refused). With --expect: PASS only when the command exits 0 AND
              the combined stdout+stderr contains the marker; on PASS the task
              entry records evidence {command, exit, expect, matched, at,
              output_sha256}. Without --expect: today's exit-0-only behavior
              (Lane C ad-hoc runs, legacy invocations). Exit 0 = PASS, counter
              reset to 0. Non-zero exit or marker mismatch = FAIL, counter
              incremented. At the 3rd consecutive failure the circuit breaker
              trips: escalation.md is written and exit 2 - halt, human
              handoff; further runs on the same task are refused. With no
              --command and no --suggest: exit 3 (command source unresolved).

              --lane <A|B|C|D> makes command approval mandatory for lanes A
              and B: before executing, the engine checks the
              fingerprint sha256(command|expect|cwd|executor) against the
              approvals store; a miss is exit 4 BEFORE execution - no state
              change, not a retry attempt. Lanes C/D (or no --lane) are
              exempt. Any change to the command, Expect, or CWD changes the
              fingerprint and re-arms approval; cached re-runs are free.

              --suggest prints the detected framework's canonical commands
              without running anything (exit 0) - the agent confirms Socratically
              before a real run.

    approve  verify.py approve --command "<cmd>" [--expect <marker>]
                  [--state-dir <dir>]
              Record the command's fingerprint in the approvals store
              (idempotent). Approving the plan does not approve its commands:
              a human inspects the exact command before its first execution.
              Exit 0.

    status   verify.py status --task <id> [--state-dir <dir>]
              Print the ledger: attempts and state (green | escalated). Exit 0.

    escalate verify.py escalate --task <id> --hypothesis "<text>"
                  --options "A (Recommended): ...; B: ..." [--state-dir <dir>]
              Finalize the escalation report: merge the stored attempt logs
              with the agent-supplied hypothesis and remediation options.
              Exit 0.

    detect   verify.py detect [--root <dir>]
              Scan repo manifests and print the framework + its reference page
              (pyproject.toml -> python, package.json -> node-npm,
              Cargo.toml -> rust-cargo, go.mod -> go, *.csproj -> dotnet).
              Exit 0.

Usage:
    python .agents/skills/verification-runner/scripts/verify.py \
        run --command "uv run pytest" --expect "3 passing" --task auth-001 --lane A
    python .agents/skills/verification-runner/scripts/verify.py \
        approve --command "uv run pytest" --expect "3 passing"
    python .agents/skills/verification-runner/scripts/verify.py \
        status --task auth-001

Exit codes: 0 = green / informational; 1 = failed (retry remaining);
2 = circuit breaker tripped (escalation.md written, halt); 3 = command source
unresolved; 4 = approval required (refused before execution, no state change,
not a retry attempt).
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

MAX_ATTEMPTS = 3
DEFAULT_TIMEOUT = 300
STATE_FILE = "verify-state.json"
ESCALATION_FILE = "escalation.md"
APPROVALS_FILE = "approvals.json"
APPROVAL_REQUIRED_LANES = {"A", "B"}
EXECUTOR = "verify.py"
FRAMEWORK_MANIFESTS = [
    ("pyproject.toml", "python"),
    ("package.json", "node-npm"),
    ("Cargo.toml", "rust-cargo"),
    ("go.mod", "go"),
]
INTERACTIVE_TOKENS = ("--interactive", "--watch", "--live-reload")


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


def read_state(state_dir: Path) -> dict:
    path = state_dir / STATE_FILE
    if not path.is_file():
        return {"version": 1, "tasks": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {"version": 1, "tasks": {}}


def ensure_scratchpad_guard(state_dir: Path) -> None:
    """Scratchpad guard: a root .gitignore entry for the dir and the inner stub.

    The inner stub (``*`` + ``!.gitignore``) is the effective protection - git
    refuses to descend into a gitignored directory even without a root
    .gitignore - while the root entry documents the exclusion for viewers that
    stop at the top level. Idempotent.

    The repo-root ``.gitignore`` is only written when the state dir resolves
    to a real repo (``AGENTS.md`` + ``.agents`` within 4 levels up). A
    sandboxed ``--state-dir`` test run (e.g. ``/tmp/...``) is outside any repo,
    so only the inner stub is written and no foreign ``.gitignore`` is touched.
    """
    inner = state_dir / ".gitignore"
    if not inner.is_file():
        inner.write_text("*\n!.gitignore\n", encoding="utf-8")

    root = state_dir
    found = False
    for _ in range(4):
        if (root / "AGENTS.md").is_file() and (root / ".agents").is_dir():
            found = True
            break
        root = root.parent
    if not found:
        return  # sandbox/external state dir - never write a foreign .gitignore
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


def write_state(state_dir: Path, state: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    ensure_scratchpad_guard(state_dir)
    (state_dir / STATE_FILE).write_text(json.dumps(state, indent=2), encoding="utf-8")


def task_state(state: dict, task_id: str) -> dict:
    task = state["tasks"].setdefault(
        task_id, {"attempts": 0, "failures": [], "tripped": False}
    )
    return task


def command_fingerprint(command: str, expect: str, cwd: str,
                        executor: str = EXECUTOR) -> str:
    """sha256(command | expect | cwd | executor) - the approval key.

    Any change to the command, the Expect marker, or the working directory
    yields a new fingerprint and re-arms approval; identical re-runs match the
    cached fingerprint and are free.
    """
    payload = "|".join((command, expect or "", cwd, executor))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_approvals(state_dir: Path) -> dict:
    path = state_dir / APPROVALS_FILE
    if not path.is_file():
        return {"version": 1, "approvals": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {"version": 1, "approvals": {}}
    if not isinstance(data, dict) or not isinstance(data.get("approvals"), dict):
        return {"version": 1, "approvals": {}}
    return data


def write_approvals(state_dir: Path, data: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    ensure_scratchpad_guard(state_dir)
    (state_dir / APPROVALS_FILE).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def split_command(command: str) -> list[str]:
    """Split a command string into argv.

    On Windows, posix-style splitting treats backslashes as escapes, which
    would corrupt paths like C:\\repo\\x.py into C:repox.py. Split with
    posix=False (quotes preserved) and strip surrounding double quotes so
    both "C:\\path with space\\x.py" and forward-slash paths survive.
    """
    if os.name == "nt":
        parts = shlex.split(command, posix=False)
        return [p[1:-1] if len(p) >= 2 and p[0] == p[-1] == '"' else p for p in parts]
    return shlex.split(command)


def is_interactive(command: str) -> bool:
    lowered = command.lower()
    return any(token in lowered for token in INTERACTIVE_TOKENS)


def parse_options(options: str) -> list[str]:
    """Normalize the guided options list: semicolon- or newline-separated."""
    if not options:
        return []
    return [part.strip() for part in re.split(r"[;\n]", options) if part.strip()]


def format_escalation(
    task_id: str,
    attempts: int,
    failures: list[str],
    hypothesis: str,
    options: str,
    max_attempts: int,
) -> str:
    """The escalation report structure - the audit record for a halted task."""
    lines = [
        "# ESCALATION - " + task_id,
        "",
        "Date: " + time.strftime("%Y-%m-%d %H:%M"),
        "Task: " + task_id,
        "Attempts: %d/%d" % (attempts, max_attempts),
        "",
        "## Attempts (verbatim logs)",
    ]
    if failures:
        for idx, log in enumerate(failures, start=1):
            lines.append("")
            lines.append("### Attempt %d" % idx)
            lines.append(log.strip() or "(no output captured)")
    else:
        lines.append("(no attempt logs recorded)")
    lines.append("")
    lines.append("## Hypothesis")
    lines.append(
        hypothesis
        or "Pending - run: verify.py escalate --task "
        + task_id
        + ' --hypothesis "..." --options "..."'
    )
    lines.append("")
    lines.append("## Remediation Options")
    options_list = parse_options(options)
    if options_list:
        lines.extend("- " + opt for opt in options_list)
    else:
        lines.append(
            "Pending - run: verify.py escalate --task "
            + task_id
            + ' --options "A (Recommended): ...; B: ..."'
        )
    lines.append("")
    lines.append("## Handoff")
    lines.append(
        "Circuit breaker tripped (%d consecutive failures). Cease all modifications, revert broken dirty edits, halt, and hand off to a human."
        % max_attempts
    )
    return "\n".join(lines)


def write_escalation(state_dir: Path, content: str) -> Path:
    path = state_dir / ESCALATION_FILE
    path.write_text(content, encoding="utf-8")
    return path


def cmd_run(args: argparse.Namespace) -> int:
    if not args.command:
        if args.suggest:
            print("suggest (no command run) - detected: " + (args.suggest or "none"))
            return 0
        print(
            "error: no command - provide --command, or --suggest for canonical commands"
        )
        return 3
    if is_interactive(args.command):
        print("refused: interactive command (no TTY allowed) - " + args.command)
        return 1

    # Command approval: mandatory for lanes A and B. Approving
    # the plan does not approve its commands - refuse BEFORE executing, with
    # no state change and no attempt counted.
    lane = getattr(args, "lane", None)
    if lane in APPROVAL_REQUIRED_LANES:
        fingerprint = command_fingerprint(args.command, args.expect or "", os.getcwd())
        if fingerprint not in read_approvals(args.state_dir)["approvals"]:
            print(
                "approval required (lane " + lane + "): command not approved - "
                + "refused before execution, no state change, not an attempt"
            )
            hint = "approve: verify.py approve --command " + shlex.quote(args.command)
            if args.expect:
                hint += " --expect " + shlex.quote(args.expect)
            print(hint)
            return 4

    state = read_state(args.state_dir)
    task = task_state(state, args.task_id)
    if task["tripped"]:
        print(
            "circuit breaker already tripped for task "
            + args.task_id
            + " - halt, human handoff"
        )
        return 2

    attempt = task["attempts"] + 1
    exit_code = 1
    try:
        proc = subprocess.run(
            split_command(args.command),
            capture_output=True,
            text=True,
            timeout=args.timeout,
            errors="replace",
        )
        log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        exit_code = proc.returncode
        # PASS = exit 0 AND Expect marker present. Without
        # --expect the engine keeps the exit-0-only behavior.
        if args.expect:
            ok = exit_code == 0 and args.expect in log
        else:
            ok = exit_code == 0
    except subprocess.TimeoutExpired:
        log = "TIMEOUT after %ds" % args.timeout
        ok = False
    except OSError as exc:
        log = "cannot execute: %s" % exc
        ok = False

    if ok:
        task["attempts"] = 0
        task["failures"] = []
        if args.expect:
            task["evidence"] = {
                "command": args.command,
                "exit": exit_code,
                "expect": args.expect,
                "matched": True,
                "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "output_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
            }
        write_state(args.state_dir, state)
        print("PASS (attempt %d)" % attempt)
        return 0

    task["attempts"] = attempt
    task["failures"].append(log)
    if attempt >= MAX_ATTEMPTS:
        task["tripped"] = True
        write_state(args.state_dir, state)
        content = format_escalation(
            args.task_id,
            attempt,
            task["failures"],
            args.hypothesis or "",
            args.options or "",
            MAX_ATTEMPTS,
        )
        path = write_escalation(args.state_dir, content)
        print("CIRCUIT BREAKER TRIPPED - attempt %d/%d" % (attempt, MAX_ATTEMPTS))
        print("escalation: " + str(path))
        return 2

    write_state(args.state_dir, state)
    print("FAIL (attempt %d/%d)" % (attempt, MAX_ATTEMPTS))
    return 1


def cmd_approve(args: argparse.Namespace) -> int:
    """Record the command's fingerprint in the approvals store (idempotent)."""
    cwd = os.getcwd()
    fingerprint = command_fingerprint(args.command, args.expect or "", cwd)
    data = read_approvals(args.state_dir)
    if fingerprint in data["approvals"]:
        print("already approved: " + fingerprint)
        return 0
    data["approvals"][fingerprint] = {
        "command": args.command,
        "expect": args.expect or "",
        "cwd": cwd,
        "executor": EXECUTOR,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    write_approvals(args.state_dir, data)
    print("approved: " + fingerprint)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = read_state(args.state_dir)
    task = state["tasks"].get(
        args.task_id, {"attempts": 0, "failures": [], "tripped": False}
    )
    label = "escalated" if task["tripped"] else "green"
    print("task: " + args.task_id)
    print("attempts: %d" % task["attempts"])
    print("state: " + label)
    return 0


def cmd_escalate(args: argparse.Namespace) -> int:
    state = read_state(args.state_dir)
    task = state["tasks"].get(
        args.task_id, {"attempts": 0, "failures": [], "tripped": False}
    )
    content = format_escalation(
        args.task_id,
        task["attempts"],
        task["failures"],
        args.hypothesis or "",
        args.options or "",
        MAX_ATTEMPTS,
    )
    path = write_escalation(args.state_dir, content)
    print("escalation: " + str(path))
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    root = args.root
    for manifest, framework in FRAMEWORK_MANIFESTS:
        if (root / manifest).is_file():
            print("framework: " + framework)
            print("reference: references/frameworks/" + framework + ".md")
            return 0
    if root.is_dir():
        for entry in root.iterdir():
            if entry.suffix.lower() == ".csproj":
                print("framework: dotnet")
                print("reference: references/frameworks/dotnet.md")
                return 0
    print("framework: none")
    print("reference: (no framework page - ask Socratically or use AGENTS.md Commands)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="verification-runner: retry counter, circuit breaker, escalation"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run a verification command under the ledger")
    run_p.add_argument("--command", default=None, help="command to execute")
    run_p.add_argument("--task", dest="task_id", required=True)
    run_p.add_argument(
        "--expect",
        default=None,
        help="success marker: PASS requires exit 0 AND this marker in the output",
    )
    run_p.add_argument(
        "--lane",
        default=None,
        choices=["A", "B", "C", "D"],
        help="lanes A/B require a prior 'approve' for this command fingerprint",
    )
    run_p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    run_p.add_argument("--hypothesis", default=None)
    run_p.add_argument(
        "--options", default=None, help='guided options: "A (Recommended): ...; B: ..."'
    )
    run_p.add_argument(
        "--suggest",
        action="store_true",
        help="print canonical commands without running",
    )
    run_p.add_argument("--state-dir", type=Path, default=None)
    run_p.set_defaults(func=cmd_run)

    approve_p = sub.add_parser(
        "approve", help="record a command's fingerprint in the approvals store"
    )
    approve_p.add_argument("--command", required=True, help="exact command to approve")
    approve_p.add_argument(
        "--expect", default=None, help="Expect marker bound to the approval"
    )
    approve_p.add_argument("--state-dir", type=Path, default=None)
    approve_p.set_defaults(func=cmd_approve)

    status_p = sub.add_parser("status", help="read the retry ledger")
    status_p.add_argument("--task", dest="task_id", required=True)
    status_p.add_argument("--state-dir", type=Path, default=None)
    status_p.set_defaults(func=cmd_status)

    escalate_p = sub.add_parser("escalate", help="finalize the escalation report")
    escalate_p.add_argument("--task", dest="task_id", required=True)
    escalate_p.add_argument("--hypothesis", required=True)
    escalate_p.add_argument(
        "--options",
        required=True,
        help='guided options: "A (Recommended): ...; B: ..."',
    )
    escalate_p.add_argument("--state-dir", type=Path, default=None)
    escalate_p.set_defaults(func=cmd_escalate)

    detect_p = sub.add_parser("detect", help="detect the project framework")
    detect_p.add_argument("--root", type=Path, default=Path.cwd())
    detect_p.set_defaults(func=cmd_detect)

    args = parser.parse_args()
    if getattr(args, "state_dir", None) is None:
        args.state_dir = find_root() / "docs" / "temp"
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
