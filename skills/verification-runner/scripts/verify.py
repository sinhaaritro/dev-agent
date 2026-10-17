#!/usr/bin/env python3
"""verification-runner engine - retry counter, circuit breaker, escalation reports.

Owns the mechanical parts of the framework's verification contract:
the 3-consecutive-failure circuit breaker, the escalation report, the
Expect-marker pass criterion with recorded evidence, and
command approval separate from plan approval. The counter
lives on disk so the limit survives across agent turns and cannot be
silently reset by forgetting. The engine is a ledger, never a judge: it
records what the command actually returned and trips at the threshold.

State: specs/temp/verify-state.json (gitignored scratchpad, per-task keys,
purged by task-cleaner on acceptance). Escalation: specs/temp/escalation.md.
Approvals: specs/temp/approvals.json (gitignored scratch, per-task lifetime;
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
              hand-back; further runs on the same task are refused. With no
              --command and no --suggest: exit 3 (command source unresolved).

              --lane <A|B|C|D> makes command approval mandatory for lanes A
              and B: before executing, the engine checks the
              fingerprint sha256(command|expect|cwd) against the approvals
              store; a miss is exit 4 BEFORE execution - no state change, not
              a retry attempt. Lanes C/D (or no --lane) are exempt. Any change
              to the command, Expect, or CWD changes the fingerprint and
              re-arms approval; cached re-runs are free.

              The command always runs with cwd=<repo root> (find_root()), so
              approval fingerprints and AGENTS.md commands are root-relative
              and a human's pre-approval matches the coder's run (no
              executor in the fingerprint). On PASS with --expect the task
              file's evidence block (when the task file is found among the
              spec group) is stamped with the command, the pass timestamp,
              and a sha256 of every owned file at that moment.

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
              A task file path as <id> derives completion from its evidence
              block instead: MET (verify passed and every owned file's hash
              still matches) | NOT MET (no passing evidence) | STALE (an owned
              file changed since the evidence) | NO-EVIDENCE (no evidence
              block). Exit 0.

    doctor   verify.py doctor --spec <NNN> [--root <dir>]
              Run the 9 ordered per-spec preconditions (spec 002, section 2.6):
              repo root resolved; engine scripts importable; state files
              parseable; the spec is Status: COMPILED; a task file
              exists for every task in section 5; Depends On forms a valid DAG;
              every verify command is pre-approved (fingerprint =
              command | expect | cwd); the canonical AGENTS.md commands
              resolve; a branch can be created off main. Prints PRECONDITIONS
              OK on success, else a named list of gaps + exit 1.

    report   verify.py report --spec <NNN> [--root <dir>]
              Regenerate NNN-REPORT-<slug>.md: run state, per-task verify
              status (derived from each task file's evidence block), and the
              Review re-run result. Exit 0.

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
    """The repository root: the nearest AGENTS.md marker.

    Walks up from the CWD first so a run launched from inside the repo (or a
    self-contained sandbox that has its own AGENTS.md) resolves to that repo,
    not the engine's own tree. Falls back to walking up from the script
    location when the CWD has no marker. Commands run with cwd=<root> and
    the approval fingerprint uses this root (spec 002, section 2.5).
    """
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        current = start
        while True:
            if (current / "AGENTS.md").is_file():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
    sys.exit(
        "error: AGENTS.md not found above "
        + str(Path.cwd())
        + " or above "
        + str(Path(__file__).resolve().parent)
    )


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
        ln.strip().strip("/") in ("specs", "specs/temp")
        for ln in lines
        if ln.strip() and not ln.strip().startswith("#")
    ):
        text = root_ignore.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        root_ignore.write_text(text + "\nspecs/temp\n", encoding="utf-8")


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
                        executor: str = "") -> str:
    """sha256(command | expect | cwd) - the approval key.

    Any change to the command, the Expect marker, or the working directory
    yields a new fingerprint and re-arms approval; identical re-runs match the
    cached fingerprint and are free. The executor is deliberately out of the
    payload: a human's pre-approval must match the coder's run (spec 002,
    section 2.5). The ``executor`` argument is accepted for backward
    compatibility but never hashed.
    """
    payload = "|".join((command, expect or "", cwd))
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


def uses_shell(command: str) -> bool:
    """True when the command needs a shell: a pipe, a boolean/list operator,
    a command substitution, a backtick, or a redirect. Such commands cannot
    run as a plain argv (subprocess without shell) — e.g. ``a && b`` or
    ``test -z "$(grep ...)"`` — so they must be handed to ``sh -c``."""
    if any(op in command for op in ("&&", "||", "|", "`", ";", ">>", "<")):
        return True
    return "$(" in command


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
        f"Attempts: {attempts}/{max_attempts}",
        "",
        "## Attempts (verbatim logs)",
    ]
    if failures:
        for idx, log in enumerate(failures, start=1):
            lines.append("")
            lines.append(f"### Attempt {idx}")
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
    lines.append("## Hand-back")
    lines.append(
        f"Circuit breaker tripped ({max_attempts} consecutive failures). Cease all modifications, revert broken dirty edits, halt, and hand off to a human."
    )
    return "\n".join(lines)


def write_escalation(state_dir: Path, content: str) -> Path:
    path = state_dir / ESCALATION_FILE
    path.write_text(content, encoding="utf-8")
    return path


SPEC_KIND = re.compile(r"^(\d{3})-SPEC-(.+)\.md$")
TASK_KIND = re.compile(r"^(\d{3})-TASK-(\d{2})-(.+)\.md$")
GROUP_COMPANION_RE = re.compile(r"^(\d{3})-(TASK|REPORT|APPROVALS|ESCALATION)-")
EVIDENCE_START = "<!-- VERIFY:EVIDENCE:START -->"
EVIDENCE_END = "<!-- VERIFY:EVIDENCE:END -->"
AGENT_SCRIPT_GLOBS = (
    ".agents/skills/*/scripts/*.py",
    ".agents/scripts/*.py",
)


def spec_path(root: Path, num: int) -> Path:
    """The NNN-SPEC-*.md file for a spec number."""
    specs_dir = root / "specs"
    if specs_dir.is_dir():
        for entry in sorted(specs_dir.iterdir()):
            if not entry.is_file():
                continue
            m = SPEC_KIND.match(entry.name)
            if m and int(m.group(1)) == num:
                return entry
    return specs_dir / f"{num:03d}-SPEC-unknown.md"


def spec_group_files(root: Path, num: int) -> list[Path]:
    """Every file of the spec group for ``num`` (SPEC + companions)."""
    specs_dir = root / "specs"
    files: list[Path] = []
    if not specs_dir.is_dir():
        return files
    for entry in specs_dir.iterdir():
        if not entry.is_file():
            continue
        m = SPEC_KIND.match(entry.name)
        if m:
            if int(m.group(1)) == num:
                files.append(entry)
            continue
        m = GROUP_COMPANION_RE.match(entry.name)
        if m and int(m.group(1)) == num:
            files.append(entry)
    return files


def task_file_for(root: Path, num: int, task_id: str) -> Path | None:
    """Locate the task file whose title names ``task_id`` (e.g. 'Task 3').

    Prefers the NNN-TASK-NN-*.md companion group; falls back to any
    NNN-TASK-*.md (the repo's hand-written task files) whose '# TASK' title
    contains the id. Returns None when nothing matches.
    """
    m = re.match(r"^Task\s+(\d+)$", task_id) or re.match(r"^(\d+)$", task_id)
    if m:
        target = f"{num:03d}-TASK-{int(m.group(1)):02d}-"
        for path in spec_group_files(root, num):
            if path.name.startswith(target):
                return path
    # Fallback: a NNN-TASK-NN-* file whose NN matches a trailing number in the
    # task id (run passes task ids like '007-Task 1' or 'Task 1').
    for path in spec_group_files(root, num):
        if not path.name.startswith(f"{num:03d}-TASK-"):
            continue
        tm = TASK_KIND.match(path.name)
        if tm:
            trailing = re.search(r"(\d+)\s*$", task_id)
            if trailing and int(trailing.group(1)) == int(tm.group(2)):
                return path
        try:
            head = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        if task_id in head.split("\n", 1)[0]:
            return path
    return None


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _owned_files(task_file: Path, root: Path) -> list[Path]:
    """The task file's '## Owns' paths, resolved against the repo root."""
    m = re.search(
        r"(?ms)^##\s+Owns\s*$(.*?)(?=^##\s|\Z)", task_file.read_text(encoding="utf-8")
    )
    if not m:
        return []
    owned: list[Path] = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        item = re.sub(r"^\s*-\s*", "", s, count=1).strip()
        item = re.sub(r"^\[(NEW|MODIFY|DELETE|RENAME)\]\s*", "", item).strip()
        if len(item) >= 2 and item.startswith("`") and item.endswith("`"):
            item = item[1:-1].strip()
        if not item:
            continue
        owned.append((root / item).resolve())
    return owned


def _write_evidence(task_file: Path, evidence: dict) -> None:
    """Stamp/replace the fenced evidence block in the task file."""
    block = (
        EVIDENCE_START + "\n"
        + "```json\n"
        + json.dumps(evidence, indent=2)
        + "\n```\n"
        + EVIDENCE_END
    )
    text = task_file.read_text(encoding="utf-8")
    m = re.search(re.escape(EVIDENCE_START) + r".*?" + re.escape(EVIDENCE_END), text, re.DOTALL)
    if m:
        text = text[: m.start()] + block + text[m.end():]
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    task_file.write_text(text, encoding="utf-8")


def read_evidence(task_file: Path) -> dict | None:
    """The task file's evidence block, or None when absent/unreadable."""
    try:
        text = task_file.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    m = re.search(
        re.escape(EVIDENCE_START)
        + r".*?```json\s*\n(.*?)\n```.*?"
        + re.escape(EVIDENCE_END),
        text,
        re.DOTALL,
    )
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def status(task: Path) -> str:
    """Derive a task file's completion from its evidence block.

    MET: passing evidence and every owned file's current hash matches.
    NOT MET: no passing evidence (or the command no longer exists in the file).
    STALE: an owned file changed since the evidence was recorded.
    NO-EVIDENCE: no evidence block at all.
    """
    evidence = read_evidence(task)
    if evidence is None:
        return "NO-EVIDENCE"
    root = find_root()
    hashes = evidence.get("files") or {}
    if not hashes:
        return "NOT MET"
    for rel, recorded in hashes.items():
        current = _file_hash((root / rel).resolve())
        if current != recorded:
            return "STALE"
    return "MET"


def _engine_importable(root: Path) -> tuple[bool, str]:
    """The engine scripts must at least parse (syntax-check every agent script).

    A full exec-import would trip on helper scripts that use sibling imports
    only valid inside their package; the pre-flight only needs to catch a
    broken (unparseable) engine script.
    """
    import py_compile

    for pattern in AGENT_SCRIPT_GLOBS:
        for script in sorted(root.glob(pattern)):
            try:
                py_compile.compile(str(script), doraise=True)
            except py_compile.PyCompileError as exc:
                return False, f"{script} ({exc.msg})"
    return True, ""


def _state_files_parseable(root: Path) -> tuple[bool, str]:
    for name in (STATE_FILE, APPROVALS_FILE):
        path = root / "specs" / "temp" / name
        if not path.is_file():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return False, str(path) + " (" + str(exc) + ")"
    return True, ""


def _spec_compiled(path: Path) -> tuple[bool, str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False, "cannot read spec"
    m = re.search(r"(?m)^Status:\s*(\S+)", text)
    if not m or m.group(1) != "COMPILED":
        return False, "spec Status is not COMPILED"
    return True, ""


def _section5_tasks(text: str) -> list[dict]:
    """Minimal parse of the '## 5.' section's '### Task N:' blocks."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+5\.", line.strip()):
            start = i + 1
            break
    if start is None:
        return []
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^##\s", lines[j].strip()):
            end = j
            break
    body = "\n".join(lines[start:end])
    tasks: list[dict] = []
    current: dict | None = None
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        m = re.match(r"^###\s+Task\s+(\d+)\s*:\s*(.*)$", stripped)
        if m:
            current = {"num": int(m.group(1)), "depends_on": ""}
            tasks.append(current)
            continue
        if current is None:
            continue
        if stripped.startswith("###"):
            current = None
            continue
        m = re.match(r"^-\s*(Depends On|Verify|Expect)\s*:\s*(.*)$", stripped)
        if m:
            current[m.group(1).lower().replace(" ", "_")] = m.group(2).strip()
    return tasks


def _dag_ok(tasks: list[dict]) -> tuple[bool, str]:
    if not tasks:
        return False, "section 5 has no tasks"
    nums = {t["num"] for t in tasks}
    for task in tasks:
        deps = task.get("depends_on") or ""
        if deps == "None":
            continue
        for m in re.finditer(r"Task\s+(\d+)", deps):
            if int(m.group(1)) not in nums:
                return False, f"Task {task['num']} depends on missing Task {m.group(0)}"
    seen: set[int] = set()
    done: set[int] = set()
    while done != nums:
        progress = False
        for task in tasks:
            n = task["num"]
            if n in done or n in seen:
                continue
            deps = task.get("depends_on") or ""
            need = {
                int(m.group(1)) for m in re.finditer(r"Task\s+(\d+)", deps)
            } if deps != "None" else set()
            if need <= done:
                done.add(n)
                progress = True
            else:
                seen.add(n)
        if not progress:
            return False, "cycle in Depends On DAG"
    return True, ""


def _clean(value: str) -> str:
    """Strip a field's surrounding backticks/quotes (spec §5 'Verify:'/'Expect:')."""
    v = value.strip()
    if len(v) >= 2 and v.startswith("`") and v.endswith("`"):
        v = v[1:-1].strip()
    if len(v) >= 2 and v.startswith('"') and v.endswith('"'):
        v = v[1:-1].strip()
    return v


def _verify_preapproved(root: Path, num: int, text: str) -> tuple[bool, str]:
    candidates = [
        p for p in (root / "specs").glob(f"{num:03d}-APPROVALS-*.json") if p.is_file()
    ]
    if not candidates:
        return True, ""  # no pre-approval store yet; approvals are recorded at compile
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return False, str(path) + " (unreadable)"
        approved = {a.get("fingerprint") for a in data.get("approvals", [])}
        for task in _section5_tasks(text):
            verify = _clean(task.get("verify") or "")
            expect = _clean(task.get("expect") or "")
            if not verify:
                continue
            fp = command_fingerprint(verify, expect, str(find_root()))
            if fp not in approved:
                return False, f"Task {task['num']} verify command not pre-approved"
        break
    return True, ""


def _canonical_commands(root: Path) -> tuple[bool, str]:
    agents = root / "AGENTS.md"
    if not agents.is_file():
        return False, "AGENTS.md missing"
    text = agents.read_text(encoding="utf-8-sig")
    commands: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*(Build|Test|Lint)\s*:\s*(.+)$", line.strip())
        if m and m.group(2).strip() != "<command>":
            commands.append(m.group(2).strip())
    if not commands:
        return False, "AGENTS.md Build/Test/Lint commands are placeholders"
    return True, ""


def _branch_possible(root: Path) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            errors="replace",
        )
        if proc.returncode != 0:
            return False, "not a git repository"
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/main"],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            errors="replace",
        )
        if proc.returncode != 0:
            return False, "no 'main' branch to branch from"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"git unavailable ({exc})"
    return True, ""


def doctor(spec: Path) -> list[str]:
    """The 9 ordered per-spec preconditions (spec 002, section 2.6).

    Returns the named list of gaps (empty when all preconditions hold);
    ``PRECONDITIONS OK`` is the caller's success output.
    """
    gaps: list[str] = []
    root = find_root()
    if root is None or not (root / "AGENTS.md").is_file():
        return ["1: repo root not resolved"]
    ok, detail = _engine_importable(root)
    if not ok:
        gaps.append("2: engine script not importable: " + detail)
    ok, detail = _state_files_parseable(root)
    if not ok:
        gaps.append("3: state file unparseable: " + detail)
    ok, detail = _spec_compiled(spec)
    if not ok:
        gaps.append("4: " + detail)
    text = ""
    try:
        text = spec.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        pass
    tasks = _section5_tasks(text)
    missing_tasks = [
        t["num"]
        for t in tasks
        if task_file_for(root, int(spec.name[:3]), f"Task {t['num']}") is None
    ]
    if missing_tasks:
        gaps.append(
            "5: no task file for Task "
            + ", Task ".join(str(n) for n in missing_tasks)
        )
    ok, detail = _dag_ok(tasks)
    if not ok:
        gaps.append("6: " + detail)
    ok, detail = _verify_preapproved(root, int(spec.name[:3]), text)
    if not ok:
        gaps.append("7: " + detail)
    ok, detail = _canonical_commands(root)
    if not ok:
        gaps.append("8: " + detail)
    ok, detail = _branch_possible(root)
    if not ok:
        gaps.append("9: " + detail)
    return gaps


def _task_verify_command(task_file: Path) -> str:
    """The task file's '## Verification' fenced command block (the canonical oracle)."""
    body = re.search(r"(?ms)^##\s+Verification\s*$(.*?)(?=^##\s|\Z)",
                     task_file.read_text(encoding="utf-8"))
    if not body:
        return ""
    fence = re.search(r"```[a-z]*\s*\n(.*?)```", body.group(1), re.DOTALL)
    return fence.group(1).strip() if fence else ""


def _rereun_verify(root: Path, num: int, text: str) -> list[str]:
    """Review: fresh re-run of every task's verify command (pass/fail lines).

    The command source is the task file's '## Verification' fenced block (the
    canonical, possibly revised oracle) - not the spec's section-5 copy, which
    can lag when a task's oracle is rewritten mid-build. The Expect marker
    still comes from section 5.
    """
    lines: list[str] = []
    for task in _section5_tasks(text):
        tf = task_file_for(root, num, f"Task {task['num']}")
        verify = _task_verify_command(tf) if tf is not None else _clean(task.get("verify") or "")
        expect = _clean(task.get("expect") or "")
        label = f"Task {task['num']}"
        if not verify or _is_noop_verify(verify):
            lines.append("- " + label + ": SKIPPED (no verify command)")
            continue
        ok = False
        try:
            if uses_shell(verify):
                proc = subprocess.run(
                    verify,
                    shell=True,
                    cwd=str(root),
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_TIMEOUT,
                    errors="replace",
                )
            else:
                proc = subprocess.run(
                    split_command(verify),
                    cwd=str(root),
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_TIMEOUT,
                    errors="replace",
                )
            log = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
            ok = proc.returncode == 0 and (not expect or expect in log)
        except (subprocess.TimeoutExpired, OSError):
            ok = False
        lines.append("- " + label + ": " + ("PASS" if ok else "FAIL"))
    return lines


def report(spec: Path) -> Path:
    """Regenerate NNN-REPORT-<slug>.md from the spec group's current state."""
    root = find_root()
    m = SPEC_KIND.match(spec.name)
    num = int(m.group(1)) if m else int(spec.name[:3])
    slug = m.group(2) if m else "spec"
    try:
        text = spec.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        text = ""
    tasks = _section5_tasks(text)
    status_m = re.search(r"(?m)^Status:\s*(\S+)", text)
    lines = [
        f"# REPORT - {num:03d} - {slug}",
        "",
        "Date: " + time.strftime("%Y-%m-%d %H:%M"),
        "Spec: " + spec.name,
        "Status: " + (status_m.group(1) if status_m else "UNKNOWN"),
        "",
        "## Task Status (derived from evidence blocks)",
    ]
    for task in tasks:
        tf = task_file_for(root, num, f"Task {task['num']}")
        if tf is None:
            lines.append(f"- Task {task['num']}: NO TASK FILE")
            continue
        derived = status(tf)
        lines.append(f"- Task {task['num']}: {derived} ({tf.name})")
    lines += [
        "",
        "## Review (fresh re-run of verify commands)",
    ]
    lines.extend(_rereun_verify(root, num, text))
    lines.append("")
    target = spec.parent / f"{num:03d}-REPORT-{slug}.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _is_noop_verify(cmd: str) -> bool:
    c = cmd.strip()
    if len(c) >= 2 and c.startswith("`") and c.endswith("`"):
        c = c[1:-1].strip()
    if not c:
        return True
    if c in ("true", ":"):
        return True
    if re.match(r"^exit(\s+0*)?$", c):
        return True
    return c.split()[0] == "echo"


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

    root = find_root()

    # Command approval: mandatory for lanes A and B. Approving
    # the plan does not approve its commands - refuse BEFORE executing, with
    # no state change and no attempt counted.
    lane = getattr(args, "lane", None)
    if lane in APPROVAL_REQUIRED_LANES:
        fingerprint = command_fingerprint(args.command, args.expect or "", str(root))
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
            + " - halt, human hand-back"
        )
        return 2

    attempt = task["attempts"] + 1
    exit_code = 1
    try:
        if uses_shell(args.command):
            proc = subprocess.run(
                args.command,
                shell=True,
                cwd=str(root),
                check=False,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                errors="replace",
            )
        else:
            proc = subprocess.run(
                split_command(args.command),
                cwd=str(root),
                check=False,
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
        log = f"TIMEOUT after {args.timeout}s"
        ok = False
    except OSError as exc:
        log = f"cannot execute: {exc}"
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
            # Stamp the task file's evidence block (spec 002, section 2.5):
            # the command, the pass timestamp, and a sha256 of every owned
            # file at that moment.
            m = re.match(r"^(\d{3})-", args.task_id)
            if m:
                tf = task_file_for(root, int(m.group(1)), args.task_id)
                if tf is not None:
                    files = {}
                    for owned in _owned_files(tf, root):
                        files[str(owned.relative_to(root))] = _file_hash(owned)
                    evidence = dict(task["evidence"])
                    evidence["files"] = files
                    _write_evidence(tf, evidence)
        write_state(args.state_dir, state)
        print(f"PASS (attempt {attempt})")
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
        print(f"CIRCUIT BREAKER TRIPPED - attempt {attempt}/{MAX_ATTEMPTS}")
        print("escalation: " + str(path))
        return 2

    write_state(args.state_dir, state)
    print(f"FAIL (attempt {attempt}/{MAX_ATTEMPTS})")
    return 1


def cmd_approve(args: argparse.Namespace) -> int:
    """Record the command's fingerprint in the approvals store (idempotent)."""
    cwd = str(find_root())
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
    # A task file path derives completion from its evidence block.
    if args.task_id.endswith(".md") and Path(args.task_id).is_file():
        print("task: " + args.task_id)
        print("state: " + status(Path(args.task_id)))
        return 0
    state = read_state(args.state_dir)
    task = state["tasks"].get(
        args.task_id, {"attempts": 0, "failures": [], "tripped": False}
    )
    label = "escalated" if task["tripped"] else "green"
    print("task: " + args.task_id)
    print(f"attempts: {task['attempts']}")
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


def cmd_doctor(args: argparse.Namespace) -> int:
    gaps = doctor(args.spec)
    if gaps:
        print("PRECONDITIONS FAILED:")
        for gap in gaps:
            print("- " + gap)
        return 1
    print("PRECONDITIONS OK")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    path = report(args.spec)
    print("report: " + str(path))
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

    doctor_p = sub.add_parser(
        "doctor", help="run the 9 ordered per-spec preconditions"
    )
    doctor_p.add_argument("--spec", type=Path, required=True,
                          help="the NNN-SPEC-<slug>.md spec to pre-flight")
    doctor_p.set_defaults(func=cmd_doctor)

    report_p = sub.add_parser(
        "report", help="regenerate the spec's NNN-REPORT-<slug>.md"
    )
    report_p.add_argument("--spec", type=Path, required=True,
                          help="the NNN-SPEC-<slug>.md spec to report on")
    report_p.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if getattr(args, "state_dir", None) is None:
        args.state_dir = find_root() / "specs" / "temp"
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
