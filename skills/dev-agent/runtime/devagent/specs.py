#!/usr/bin/env python3
"""spec-builder engine - draft validation, spec promotion, topic decisions, and spec compile.

Owns the mechanical parts of the spec lifecycle: template
enforcement, sequential numbering, promotion mechanics, Topic-Based
decision recording, and the task-file compile. The acceptance
gate itself is the caller's - the agent asserts it via --status
(APPROVED for human acceptance, PROVISIONAL for a compliant autonomous
resolution); this script never decides whether the gate passed. Topic
decisions are recorded only alongside APPROVED promotion (human
acceptance).

Modes:
    check    devagent spec check <draft> --lane <B|A>
              Parse the draft's "## N." section headings and verify the
              lane's required sections are present (B: 1, 4, 5; A: 1-8).
              Also validate the new section-5 "Tasks & Outcomes" shape:
              every "### Task N:" block carries a Depends On: line (may be
              None, or a "Task N" reference list for Lane B) and a
               Verify:/Expect: pair; the plan has >=1 task. A static oracle
               lint rejects no-op Verify commands (true, :, exit, echo) and
               trivially-satisfied Expect markers (the whole command, or a bare
               echo/printf); a marker the command emits from real state (e.g.
               grep -o MARKER) is allowed. The canonical Status:
              receipt set is DRAFTED, COMPILED, BUILDING, BUILT, REVIEWED,
              COMPLETED, PLAN_REVISION_REQUIRED, REVIEW_REVISION_REQUIRED,
              ESCALATED, ABORTED. Prints "structure: ok" on success. Exit 0
              when complete, 1 with the missing-sections list and/or
              structural violations when not.

    promote  devagent spec promote <draft> --lane <B|A>
                 --status <APPROVED|PROVISIONAL> [--dry-run]
                 [--slug <override>] [--specs-dir <dir>]
             Check the draft, then compute the next spec number by scanning
             the specs directory for the max 3-digit prefix + 1 (zero-padded,
             sequential - never guessed), derive the slug from the draft
             title, write the promoted file with its Status line replaced,
             and refuse if the target already exists. --specs-dir overrides
             the target directory (tests and evals use a sandbox; the real
             specs/ is never touched by verification).

    topic    devagent spec topic <name> --why <text> [--title <text>]
                  [--file <sub>] [--tags a,b] [--state <text>]
                  [--supersedes <ID>] [--affects <target>]
                  [--reciprocal <topic>] [--reciprocal-file <sub>]
                  [--reciprocal-why <text>] [--reciprocal-state <text>]
                  [--reciprocal-title <text>] [--date YYYY-MM-DD]
                  [--docs-dir <dir>] [--dry-run]
              The topic-doc path: create a topic doc
              (docs/<name>.md or docs/<name>/<sub>.md) or revise an existing
              one. A revision allocates the next <TOPIC>-D<nn> by scanning
              every file of the topic (IDs are topic-global, never reused),
              updates the Current State in place when --state is given, marks
              a --supersedes entry "(superseded)" (never deleted), appends the
              Decision Log entry (Date / Why / Supersedes / Affects / Ref),
              and, when --reciprocal is given, writes a terse Ref entry in the
              affected topic pointing back at the primary decision (the
              primary records the one-way Affects pointer). Links are plain
              heading anchors. --docs-dir overrides the target (tests and
              evals use a sandbox; the real docs/ is never touched by
              verification).

      toc      devagent spec toc [--root <dir>] [--dry-run]
                Regenerate the deterministic "## Index" marker block in the
                specs/README.md (specs only).
               --root is the repo root (default <repo>) - the engine scans
               <root>/specs and <root>/docs. A misused nested path (e.g.
               <repo>/docs) is auto-corrected to the repo root so stray
               folders are never created.
               --dry-run prints each computed block without writing. Never
               touches text outside the <!-- TOC:START -->/END markers.

    tag-list    devagent spec tag-list [--root <dir>]
              Read-only: print a sorted per-folder report of tag -> files
              with counts. No writes.
    tag-suggest devagent spec tag-suggest [--root <dir>]
              Read-only: print near-duplicate tag candidates (advisory
              only; never part of the promotion gate).
    tag-lint    devagent spec tag-lint [--root <dir>]
              Normative: exit 1 on any violation (lowercase-kebab, 2-30
              chars, max 7 tags/doc, no empty field). Wired into check, so
              a malformed tag also fails the promotion gate.
     tag-rename  devagent spec tag-rename <old> <new> [--root <dir>]
               The only tag writer: rewrites the tags frontmatter line of
               every doc carrying <old>. Prose outside the frontmatter is
               never touched.

    specs-lint devagent spec specs-lint [--root <dir>]
               Read-only one-way rule: docs/ and source must never reference
               into ``specs/``. Falls back to failing (exit 1) listing every
               ``file:line`` hit. A ``specs/`` file pointing *out* to docs/ or
               source is allowed (the dependency is one-way), and files under
               ``specs/`` are never scanned.

Usage:
    python .agents/scripts/devagent/main.py spec \
        check specs/temp/draft-plan.md --lane B
    python .agents/scripts/devagent/main.py spec \
        promote specs/temp/draft-plan.md --lane A --status APPROVED
    python .agents/scripts/devagent/main.py spec \
        topic auth --why "Cookies beat JWT here" --title "Session cookies"

Exit codes: 0 = ok; 1 = check failed, exists, or violation/error.
"""

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

from common.hashing import APPROVAL_CWD, approval_fingerprint
from common.root import find_root
from common.specparse import (
    CANONICAL_STATUSES,
    SPEC_KIND,
    append_section_entry,
    is_noop_verify,
    parse_sections,
    parse_tasks,
    section_body,
    section_body_by_name,
    spec_group_files,
    spec_identity,
    status_token,
    status_value,
)
from common.text import normalize_marker, strip_fenced_code

LANE_SECTIONS = {"B": {1, 4, 5}, "A": {1, 2, 3, 4, 5, 6, 7, 8}}
PROVISIONAL_STATUS = "PROVISIONAL - AUTONOMOUS DEFAULT"

SPEC_FOLDER = "specs"
TOC_START = "<!-- TOC:START -->"
TOC_END = "<!-- TOC:END -->"
TAG_LINE = re.compile(r"(?m)^tags:\s*\[([^\]]*)\]\s*$")
TAG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FM_BLOCK = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)

# Canonical task-file headings, in the order the engine requires
# (references/task-file-format.md). validate_task_file enforces them.
TASK_FILE_HEADINGS = (
    "Role & rules",
    "Project overview",
    "Task",
    "Owns",
    "Reads / Context (read-only)",
    "Skills to use",
    "Upstream interfaces",
    "Verification",
)


def read_text(path: Path) -> str:
    """Read UTF-8, tolerating a BOM (utf-8-sig strips it).

    Windows editors routinely prepend a BOM; without stripping it the
    first title line would not match "# " and the slug would degrade
    to the 'spec' fallback.
    """
    return path.read_text(encoding="utf-8-sig")


# Section-6 decision plan (B3.7): every planned decision is a '- **D<n> ...'
# bullet that MUST carry a blocking / non-blocking label, so the human chooses
# before build and the build never reopens a settled menu (B3.8).
DECISION_LINE_RE = re.compile(r"^-+\s+\*\*(D\d+)\b")
GATE_LABEL_RE = re.compile(r"(?i)\bblocking\b")

# specs-lint: the one-way rule. docs/ and source may not reference into
# specs/ (which is disposable); a specs/ file may link out to them.
SPECS_REF_RE = re.compile(r"(?<![\w.-])specs/")
SPECS_LINT_SUFFIXES = frozenset(
    (
        ".md",
        ".markdown",
        ".rst",
        ".txt",
        ".py",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".rb",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".cs",
        ".php",
        ".sql",
        ".html",
        ".htm",
        ".css",
        ".scss",
    )
)
SPECS_LINT_SKIP_DIRS = frozenset(
    (
        SPEC_FOLDER,
        ".git",
        ".hg",
        ".svn",
        ".agents",
        "node_modules",
        "__pycache__",
        ".ruff_cache",
        ".venv",
        ".venv-win",
        ".venv-linux",
        ".venv-macos",
        "skill-workspaces",
        "behavior-workspaces",
        ".behavior-review",
    )
)

# Dangling framework references: a shipped/durable file must not point at the
# framework's own spec or legacy decision-record IDs; those do not exist in a
# consumer repo. This is separate from the one-way ``specs/`` rule: workflow
# paths such as ``specs/temp/draft-plan.md`` are legitimate.
DANGLING_REF_RE = re.compile(r"\b(?:spec\s+00\d|ADR-\d+)\b", re.IGNORECASE)
# A consumer repo installs the runtime + skills under `.agents/`, so scan it;
# the one-way rule still skips it because those are shipped workflow docs.
DANGLING_SKIP_DIRS = SPECS_LINT_SKIP_DIRS - {".agents"}


def _unfailable_expect(verify: str, expect: str) -> str:
    """A static hint that a Verify/Expect oracle is trivially satisfied.

    Returns '' when the pair can fail. The marker appearing in the command is
    NOT itself a violation: a command that emits the marker from real state
    (``grep -o MARKER file``, a test runner's ``OK`` line) is a valid oracle.
    Only trivially satisfied markers are flagged — the whole command is the
    marker, or the command is a bare literal emitter (``echo``/``printf``).
    """
    if not expect:
        return ""
    if expect == verify:
        return "'Expect:' is the whole 'Verify:' command (oracle can never fail)"
    first = verify.split()[0] if verify.split() else ""
    if first in ("echo", "printf"):
        return f"'Expect:' is emitted unconditionally by a bare '{first}'"
    return ""


def _validate_target_files(tasks: list[dict]) -> list[str]:
    """Section-5 'Target Files' lint: every task declares files, none collide.

    Enforces the one-file / one-task / one-writer invariant:
    a task with no target files cannot be dispatched, and two tasks claiming the
    same path would race. Paths are compared verbatim (backticks stripped by the
    parser).
    """
    violations: list[str] = []
    owners: dict[str, str] = {}
    for task in tasks:
        tlabel = f"Task {task['num']}"
        entries = task.get("target_files") or []
        if not entries:
            violations.append(tlabel + ": missing/empty 'Target Files:'")
            continue
        for entry in entries:
            path = entry["path"]
            if not entry["op"]:
                violations.append(
                    tlabel
                    + f": target file '{path}' has no [NEW|MODIFY|DELETE|RENAME] tag"
                )
            existing = owners.get(path)
            if existing is not None and existing != tlabel:
                violations.append(
                    tlabel + f": target file '{path}' is already owned by {existing}"
                )
            else:
                owners[path] = tlabel
    return violations


def _validate_tasks(tasks: list[dict], lane: str) -> list[str]:
    """Structural + static-oracle violations for the section-5 task list."""
    if not tasks:
        return ["section 5: no '### Task N:' blocks found (zero-gate plan rejected)"]
    violations: list[str] = []
    for task in tasks:
        tlabel = f"Task {task['num']}"
        if not task["depends_on"]:
            violations.append(tlabel + ": missing 'Depends On:'")
        elif task["depends_on"] != "None" and not re.match(
            r"^Task\s+\d+(\s*,\s*Task\s+\d+)*$", task["depends_on"]
        ):
            violations.append(
                tlabel
                + f": 'Depends On:' must be 'None' or a 'Task N' reference (got '{task['depends_on']}')"
            )
        verify = normalize_marker(task["verify"])
        if not task["verify"]:
            violations.append(tlabel + ": missing/empty 'Verify:'")
        else:
            if is_noop_verify(verify):
                violations.append(
                    tlabel + f": 'Verify:' is a no-op command ('{verify}')"
                )
            expect = normalize_marker(task["expect"])
            if not task["expect"]:
                violations.append(tlabel + ": missing/empty 'Expect:'")
            else:
                msg = _unfailable_expect(verify, expect)
                if msg:
                    violations.append(tlabel + ": " + msg)
    violations += _validate_target_files(tasks)
    return violations


def _validate_gate_labels(body: str) -> list[str]:
    """Section-6 decision-plan lint: each '- **D<n>' bullet carries a label.

    The label ('blocking' / 'non-blocking') is what makes the gate visible at
    spec-creation time (B3.7). Gate-log entries are not decision bullets, so
    they are unaffected.
    """
    violations: list[str] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        match = DECISION_LINE_RE.match(stripped)
        if not match:
            continue
        if not GATE_LABEL_RE.search(stripped):
            violations.append(
                "section 6: decision "
                + match.group(1)
                + " carries no blocking/non-blocking label"
            )
    return violations


def check_draft(draft: Path, lane: str) -> tuple[bool, list[int], list[str]]:
    """Return (passed, missing_sections, violations) for the lane's contract.

    'missing' is the lane's required '## N.' sections absent from the draft;
    'violations' are section-5 Task DAG structure problems, static-oracle
    lint findings, and (Lane A) unlabeled section-6 decisions. Both fail the
    gate.
    """
    try:
        text = read_text(draft)
    except (OSError, UnicodeDecodeError):
        return False, [], ["cannot read draft"]
    found = parse_sections(text)
    missing = sorted(LANE_SECTIONS[lane] - found)
    violations = []
    token = status_token(text)
    if token and token not in CANONICAL_STATUSES:
        violations.append("Status: " + repr(token) + " is not a canonical receipt")
    if 5 in found:
        violations += _validate_tasks(parse_tasks(section_body(text, 5)), lane)
    if lane == "A" and 6 in found:
        violations += _validate_gate_labels(section_body(text, 6))
    passed = not missing and not violations
    return passed, missing, violations


def validate_task_file(text: str) -> list[str]:
    """Structural violations for a canonical task file.

    Enforces the required ``##`` headings in order (references/
    task-file-format.md), the ``### Progress`` sub-heading under ``## Task``,
    and the ``## Verification`` fence + ``**Expect:**`` line. Returns [] when
    the file is well-formed; ``compile`` refuses to write a failing file.
    """
    violations: list[str] = []
    lines = text.splitlines()
    title = ""
    for line in lines:
        if line.strip().startswith("# "):
            title = line.strip()
            break
    if not title:
        violations.append("missing '# TASK NNN-NN — title' heading")
    elif not re.match(r"^#\s+TASK\s+\d{3}-\d{2}\b", title):
        violations.append("title must be '# TASK <NNN>-<NN> — <title>'")

    seen: list[str] = []
    for line in lines:
        match = re.match(r"^##\s+(?!#)(.+?)\s*$", line.strip())
        if match:
            seen.append(match.group(1).strip())
    for heading in TASK_FILE_HEADINGS:
        if heading not in seen:
            violations.append(f"missing heading '## {heading}'")
    ordered = [h for h in seen if h in TASK_FILE_HEADINGS]
    if ordered != [h for h in TASK_FILE_HEADINGS if h in ordered]:
        violations.append(f"headings out of order (got {' -> '.join(ordered)})")
    for heading in TASK_FILE_HEADINGS:
        if seen.count(heading) > 1:
            violations.append(f"duplicate heading '## {heading}'")

    if "Task" in seen:
        task_body = section_body_by_name(text, "Task")
        if "### Progress" not in task_body:
            violations.append("'## Task' has no '### Progress' sub-heading")

    if "Verification" in seen:
        ver_body = section_body_by_name(text, "Verification")
        if not re.search(r"^\s*```", ver_body, re.MULTILINE):
            violations.append("'## Verification' has no fenced command block")
        if not re.search(r"(?m)^\s*\*\*Expect:\*\*", ver_body):
            violations.append("'## Verification' has no '**Expect:**' line")
    return violations


def _slug_from_title_or_name(name: str, text: str) -> str:
    """A short slug for a task file: from the task title, else the spec slug."""
    m = re.match(r"^###\s+Task\s+\d+\s*:\s*(.+)$", text, re.MULTILINE)
    if m:
        raw = re.sub(r"[^a-z0-9]+", "-", m.group(1).lower()).strip("-")
        if len(raw) <= 40:
            return raw or "task"
        cut = raw[:40]
        if "-" in cut:
            cut = cut[: cut.rfind("-")]
        return cut.rstrip("-") or raw[:40].rstrip("-") or "task"
    ident = spec_identity(name)
    return ident[1] if ident else "spec"


def _write_approvals(specs_dir: Path, num: int, slug: str, tasks: list[dict]) -> Path:
    """Write NNN-APPROVALS-<slug>.json pre-approving every task verify command."""
    import json

    approvals = {
        "spec": f"{num:03d}",
        "approvals": [
            {
                "task": f"Task {t['num']}",
                "fingerprint": approval_fingerprint(
                    normalize_marker(t["verify"]),
                    normalize_marker(t["expect"]),
                    APPROVAL_CWD,
                ),
                "command": normalize_marker(t["verify"]),
                "expect": normalize_marker(t["expect"]),
                "cwd": APPROVAL_CWD,
            }
            for t in tasks
        ],
    }
    path = specs_dir / f"{num:03d}-APPROVALS-{slug}.json"
    path.write_text(json.dumps(approvals, indent=2) + "\n", encoding="utf-8")
    return path


def _render_task_file(
    num: int, task: dict, spec_name: str, spec_text: str, root: Path
) -> str:
    """Render one task file in the canonical shape (task-file-format.md)."""
    title = task["title"] or f"Task {task['num']}"
    # Project overview: the spec's section 1 body (trimmed), or a fallback.
    overview = section_body(spec_text, 1).strip() or "_(project overview)_"
    # Owns: this task's own section-5 'Target Files' (one file = one task = one
    # writer; the spec-level section 4 inventory is not copied into task files).
    owns_lines = [
        f"- [{entry['op']}] {entry['path']}"
        for entry in (task.get("target_files") or [])
    ]
    if not owns_lines:
        owns_lines = ["_(this task declares no Target Files)_"]
    deps = task["depends_on"] or "None"
    verify = normalize_marker(task["verify"]) or "_(verify command)_"
    expect = normalize_marker(task["expect"]) or "_(expect marker)_"
    return (
        f"# TASK {num:03d}-{task['num']:02d} — {title}\n\n"
        "## Role & rules\n"
        "Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you\n"
        "don't Own, do not commit.\n\n"
        "## Project overview\n" + overview + "\n"
        "(the global task list lives in the spec section 5 — not copied here)\n\n"
        "## Task\n"
        f"{title}. Depends On: {deps}.\n\n"
        "### Progress\n"
        "- [ ] implement the task\n"
        "- [ ] run the Verification command and match Expect\n\n"
        "## Owns\n" + "\n".join(owns_lines) + "\n\n"
        "## Reads / Context (read-only)\n"
        "- the spec: " + spec_name + "\n\n"
        "## Skills to use\n"
        "- spec-builder\n\n"
        "## Upstream interfaces\n"
        "```python\n"
        "def find_root() -> Path\n"
        "```\n\n"
        "## Verification\n"
        "```bash\n" + verify + "\n"
        "```\n"
        f"**Expect:** `{expect}`\n"
    )


def compile_spec(spec: Path, root: Path | None = None) -> list[Path]:
    """compile: emit one task file per section 5 task + approvals + stamp.

    Reads the spec's section 5 Tasks & Outcomes, renders each task in the canonical
    task-file shape, validates it (refusing to write on violations), writes
    NNN-APPROVALS-<slug>.json, and stamps 'Status: COMPILED' on the spec.
    Returns the list of task-file paths written.
    """
    root = root or find_root()
    try:
        text = read_text(spec)
    except (OSError, UnicodeDecodeError):
        raise SystemExit(f"error: cannot read spec {spec}")
    ident = spec_identity(spec.name)
    if ident is None:
        raise SystemExit(f"error: '{spec.name}' is not an NNN-SPEC-<slug>.md file")
    num, slug = ident
    tasks = parse_tasks(section_body(text, 5))
    if not tasks:
        raise SystemExit(f"error: no '### Task N:' blocks in section 5 of {spec.name}")
    target_violations = _validate_target_files(tasks)
    if target_violations:
        for v in target_violations:
            print(f"task-file error: {v}")
        raise SystemExit(
            "error: section 5 'Target Files' failed validation; no task files written"
        )
    lane = "A" if LANE_SECTIONS["A"] <= parse_sections(text) else "B"
    passed, missing, violations = check_draft(spec, lane)
    if not passed:
        if missing:
            print(
                "compile error - missing sections: "
                + ", ".join(str(n) for n in missing)
            )
        for v in violations:
            print("compile error - structure: " + v)
        raise SystemExit("error: spec failed the check gate; no task files written")
    specs_dir = spec.parent
    rendered: list[tuple[Path, str]] = []
    for task in tasks:
        task_slug = _slug_from_title_or_name(
            spec.name, _task_line_block(text, task["num"])
        )
        content = _render_task_file(num, task, spec.name, text, root)
        violations = validate_task_file(content)
        if violations:
            for v in violations:
                print(f"task-file error: {v}")
            raise SystemExit(
                f"error: task {task['num']} file failed validation; not written"
            )
        target = specs_dir / f"{num:03d}-TASK-{task['num']:02d}-{task_slug}.md"
        rendered.append((target, content))
    # Stamp before writing companions: a spec that cannot be marked COMPILED
    # must not leave a half-written group behind.
    _stamp_compiled(spec, root)
    written: list[Path] = []
    for target, content in rendered:
        target.write_text(content, encoding="utf-8")
        written.append(target)
    _write_approvals(specs_dir, num, slug, tasks)
    _refresh_toc_for(root)
    return written


def _task_line_block(text: str, num: int) -> str:
    """The '### Task N:' block body for a task number (for slug derivation)."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(rf"^###\s+Task\s+{num}\s*:", line.strip()):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith("###"):
            end = j
            break
    return "\n".join(lines[start:end])


def _stamp_compiled(spec: Path, root: Path) -> None:
    """Set the spec's 'Status:' header to COMPILED (idempotent)."""
    text = read_text(spec)
    if status_value(text).startswith("COMPILED"):
        return
    updated = replace_status(text, "COMPILED")
    if updated == text:
        raise SystemExit(f"error: cannot stamp Status: COMPILED on {spec.name}")
    spec.write_text(updated, encoding="utf-8")


def purge_spec(spec: Path, root: Path | None = None) -> None:
    """Remove the whole spec group (SPEC + companions), then regenerate the TOC."""
    root = root or find_root()
    ident = spec_identity(spec.name)
    if ident is None:
        raise SystemExit(f"error: '{spec.name}' is not an NNN-SPEC-<slug>.md file")
    num = ident[0]
    specs_dir = spec.parent
    for f in spec_group_files(specs_dir, num):
        f.unlink()
        print(f"purged: {f.name}")
    _refresh_specs_readme(root)


def sync_specs_readme(root: Path) -> None:
    """Regenerate specs/README.md only (no deletes)."""
    _refresh_specs_readme(root)


def _refresh_specs_readme(root: Path) -> None:
    """Regenerate the specs/README.md TOC marker block (group-aware)."""
    root = _repo_root(root)
    _ensure_specs_readme(root)
    docs = _scan_docs(root)
    target = root / SPEC_FOLDER / "README.md"
    if not target.is_file():
        return
    block = _build_toc_lines(docs)
    new_text = _write_marker_block(read_text(target), TOC_START, TOC_END, block)
    if new_text is not None:
        target.write_text(new_text, encoding="utf-8")


def accept_spec(spec: Path, root: Path | None = None) -> None:
    """Stamp 'Status: COMPLETED' + 'Done: <date>' (no git)."""
    root = root or find_root()
    text = read_text(spec)
    if not status_value(text):
        raise SystemExit(f"error: {spec.name} has no 'Status:' line")
    today = date.today().isoformat()
    text = re.sub(r"(?m)^(Status:\s*).*$", r"\g<1>COMPLETED", text, count=1)
    if not re.search(r"(?m)^Done:\s*\d{4}-\d{2}-\d{2}\s*$", text):
        text = re.sub(
            r"(?m)^(Status:\s*COMPLETED.*)$", r"\g<1>\nDone: " + today, text, count=1
        )
    spec.write_text(text, encoding="utf-8")
    _refresh_specs_readme(root)


def parse_sub_id(name: str) -> tuple[int, str] | None:
    """Decode a sub-ID filename 'NNN-LNN[-LNN].md' to (parent, key).

    Key format: 'A01' for level 1, 'A01-B01' for level 2 (hyphen
    separator, letter + two digits). Returns None for non sub-IDs.
    """
    match = re.match(r"^(\d{3})-([A-Z]\d{2})(?:-([A-Z]\d{2}))?\.md$", name)
    if not match:
        return None
    parent = int(match.group(1))
    key = (
        match.group(2) if not match.group(3) else match.group(2) + "-" + match.group(3)
    )
    return (parent, key)


def next_number(specs_dir: Path) -> int:
    """Highest 3-digit spec number + 1 (1 if empty).

    Reads both the parent files ('NNN-<slug>.md') and the sub-IDs
    ('NNN-LNN.md' / 'NNN-LNN-MNN.md'): a parent N exists if either its file
    or at least one child of N is present, so a child promotion under 001
    never collides with the global max.
    """
    highest = 0
    if specs_dir.is_dir():
        for entry in specs_dir.iterdir():
            if not entry.is_file():
                continue
            match = re.match(r"^(\d{3})-", entry.name)
            if match:
                highest = max(highest, int(match.group(1)))
            else:
                sub = parse_sub_id(entry.name)
                if sub:
                    highest = max(highest, sub[0])
    return highest + 1


def slug_from_title(text: str) -> str:
    """Derive a slug from the first '#' title: lowercase, non-alnum to hyphen.

    Leading ID tokens are stripped so a draft titled '# 103: Refresh Token
    Column' promotes to 'refresh-token-column' and a sub-ID draft titled
    '# 001-A01: Child Plan' promotes to 'child-plan' (sub-ID titles carry
    no numeric prefix in the filename).
    """
    title = ""
    for line in text.splitlines():
        if line.strip().startswith("# "):
            title = line.strip().lstrip("# ").strip()
            break
    title = re.sub(r"^(\[\S+\]|\d{3}-[A-Z]\d{2}(?:-[A-Z]\d{2})?|\d{3}):\s*", "", title)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "spec"


def _title_key(line: str) -> str:
    """Identity key for a '#' title: drop the ID token, normalize whitespace/case.

    A promoted title ('# 001-SPEC: Cache Layer'), a draft title
    ('# [SPEC-ID]: Cache Layer'), and a sub-ID title all compare equal, so a
    repeat promotion of the same plan is refused no matter which number the
    engine would assign.
    """
    body = line.strip().lstrip("#").strip()
    body = re.sub(
        r"^(\[\S+\]|\d{3}-SPEC|\d{3}-[A-Z]\d{2}(?:-[A-Z]\d{2})?|\d{3})(?=:|\s)",
        "",
        body,
    )
    body = body.lstrip(":- ").strip()
    return re.sub(r"\s+", " ", body).strip().lower()


def find_existing_by_title(specs_dir: Path, title: str) -> Path | None:
    """Return an existing spec whose first '#' title matches the draft's.

    The SPEC-ID/title is the plan's identity - a repeat promotion of the
    same draft must be refused even though the sequential number is new.
    Titles are compared with the leading ID token stripped, so re-promoting a
    retitled-but-same plan is still refused. Scans parent and sub-ID files
    alike, so sub-IDs never bypass the check.
    """
    if not specs_dir.is_dir():
        return None
    wanted = _title_key(title)
    if not wanted:
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
                if _title_key(line) == wanted:
                    return entry
                break
    return None


def _extract_tags(text: str) -> list[str] | None:
    """Parse 'tags: [a, b]' from frontmatter; None when absent.

    Prefers the YAML frontmatter block (the canonical contract); falls back
    to a bare 'tags:' line anywhere in the document so pre-frontmatter
    committed docs keep scanning until they are normalized by tag-rename.
    """
    fm = FM_BLOCK.match(text)
    match = TAG_LINE.search(fm.group(1)) if fm else None
    if not match:
        match = TAG_LINE.search(text)
    if not match:
        return None
    return [t.strip() for t in match.group(1).strip().split(",") if t.strip()]


def ensure_frontmatter_tags(text: str) -> str:
    """Ensure 'tags: [...]' sits inside a leading YAML frontmatter block.

    Canonical contract: tags are metadata, wrapped in '---' fences at the top
    of the file. A bare 'tags:' line (pre-frontmatter docs) is moved into a
    new or existing block; text already carrying frontmatter tags is returned
    unchanged.
    """
    fm = FM_BLOCK.match(text)
    if fm and TAG_LINE.search(fm.group(1)):
        return text
    match = TAG_LINE.search(text)
    if not match:
        return text
    tag_line = match.group(0).rstrip()
    if fm:
        body = text[fm.end() :]
        new_body = (
            body[: match.start() - fm.end()]
            + body[match.start() - fm.end() : match.end() - fm.end()].replace(
                tag_line, "", 1
            )
            + body[match.end() - fm.end() :]
        )
        new_body = re.sub(r"^\n+", "\n", new_body)
        return (
            text[: fm.start()]
            + "---\n"
            + fm.group(1)
            + "\n"
            + tag_line
            + "\n---\n"
            + new_body
        )
    rest = text[: match.start()] + text[match.end() :]
    rest = rest.lstrip("\n")
    return "---\n" + tag_line + "\n---\n\n" + rest


def _lint_tags(tags: list[str]) -> list[str]:
    """Normative lint: lowercase-kebab, 2-30 chars, max 7/doc."""
    problems = []
    if len(tags) > 7:
        problems.append("more than 7 tags")
    for tag in tags:
        if not (2 <= len(tag) <= 30):
            problems.append(f"tag '{tag}' has length {len(tag)} (allowed 2-30 chars)")
        elif not TAG_RE.match(tag):
            problems.append(f"tag '{tag}' is not lowercase-kebab")
    return problems


def _fm_stripped(text: str) -> str:
    """Drop a leading YAML frontmatter block so scans see body content only."""
    return FM_BLOCK.sub("", text, count=1)


def draft_title(text: str) -> str:
    """The draft's first '#' heading line (its identity).

    Frontmatter (and code fences) are stripped first so a 'tags:' or any
    other frontmatter line can never be mistaken for the title.
    """
    for line in strip_fenced_code(_fm_stripped(text)).splitlines():
        if line.strip().startswith("# "):
            return line.strip()
    return ""


def _folder_sort_key(folder: str, name: str) -> tuple:
    """Deterministic sort key per folder ID scheme."""
    if folder == "specs":
        match = re.match(r"^(\d{3})-([A-Z]\d{2})(?:-([A-Z]\d{2}))?\.md$", name)
        if match:
            return (
                int(match.group(1)),
                match.group(2) + ("-" + match.group(3) if match.group(3) else ""),
            )
        match = re.match(r"^(\d{3})-", name)
        if match:
            return (int(match.group(1)), "~")
        return (9999, name)
    return (0, name)


def _doc_title(text: str) -> str:
    """First '#' heading outside code fences, minus its leading number token."""
    for line in strip_fenced_code(text).splitlines():
        if line.strip().startswith("# "):
            t = line.strip()[1:].strip()
            return re.sub(r"^(\d{3}:|\[\S+\]:\s*)", "", t).strip() or t
    return ""


def _doc_backlinks(text: str) -> list[str]:
    """The 'Source:'/'Governed-by:' backlink targets on the status header."""
    links = []
    for label in ("Source", "Governed-by"):
        match = re.search(r"(?m)^" + label + r":\s*(\S.*)$", strip_fenced_code(text))
        if match:
            links.append(match.group(1).strip())
    return links


def _scan_docs(root: Path) -> dict:
    """Scan the committed docs into sorted doc entries.

    ``root`` is the repo root. Returns a dict keyed by section:
    ``"specs"`` -> ``root/specs/*.md`` and ``"topics"`` -> every topic doc
    under ``root/docs/`` (flat files and ``docs/<topic>/*.md`` folders;
    ``README.md``, generated underscore files, and reserved non-topic dirs are
    skipped). ``sync-docs`` still builds the separate AI routing index.
    Shared by the TOC roll-up and every tag-governance function - one
    frontmatter parse, no cross-subcommand drift.
    """

    def collect(paths: list[Path], base: Path | None = None) -> list[dict]:
        entries = []
        for f in paths:
            if not f.is_file() or f.name == "README.md":
                continue
            try:
                text = read_text(f)
            except (OSError, UnicodeDecodeError):
                continue
            clean = strip_fenced_code(text)
            m1 = re.search(r"(?m)^version_pin:\s*(\S+)", clean)
            m2 = re.search(r"(?m)^fallback_pin:\s*(\S+)", clean)
            name = f.relative_to(base).as_posix() if base is not None else f.name
            entries.append(
                {
                    "name": name,
                    "text": text,
                    "title": _doc_title(text),
                    "status": _ref_status(text),
                    "tags": _extract_tags(text) or [],
                    "version_pin": m1.group(1) if m1 else "",
                    "fallback_pin": m2.group(1) if m2 else "",
                    "backlinks": _doc_backlinks(text),
                }
            )
        return entries

    docs: dict[str, list[dict]] = {}
    spec_dir = root / SPEC_FOLDER
    specs = collect(sorted(spec_dir.glob("*.md"))) if spec_dir.is_dir() else []
    docs["specs"] = sorted(specs, key=lambda e: _folder_sort_key("specs", e["name"]))
    docs_dir = root / "docs"
    topic_paths: list[Path] = []
    if docs_dir.is_dir():
        for f in sorted(docs_dir.rglob("*.md")):
            rel = f.relative_to(docs_dir)
            if len(rel.parts) > 1 and rel.parts[0] in TOPIC_RESERVED:
                continue  # reserved non-topic trees (reference/specs/temp)
            topic_paths.append(f)
    topics = collect(topic_paths, base=docs_dir)
    topics = [e for e in topics if not e["name"].split("/")[-1].startswith("_")]
    docs["topics"] = sorted(topics, key=lambda e: e["name"])
    return docs


def _write_marker_block(text: str, start: str, end: str, block: str) -> str | None:
    """Replace everything between the start and end markers with block.

    Idempotent: only the marker block is rewritten, surrounding prose is
    byte-identical before and after. Returns None when the
    markers are missing.
    """
    m1 = re.search(re.escape(start) + r"\n", text)
    m2 = re.search(re.escape(end) + r"\n", text)
    if not (m1 and m2 and m1.start() < m2.start()):
        return None
    return text[: m1.start()] + start + "\n" + block + end + "\n" + text[m2.end() :]


def _specs_readme_stub() -> str:
    """Rich specs/README.md scaffold (creator half, D6).

    Carries human-curated prose (heading, purpose, naming/ID convention,
    frontmatter note) plus the TOC marker block, so a fresh repo's specs README
    reads like the hand-curated one on first creation.
    """
    body = (
        "# Specs\n\n"
        "Permanent functional & technical specs. Promotion pipeline:\n\n"
        "- Draft: `specs/temp/draft-plan.md` (gitignored)\n"
        "- Acceptance: promoted to `specs/<NNN>-SPEC-<slug>.md` and committed\n\n"
        "Naming: `NNN-SPEC-<slug>.md` (e.g. `001-SPEC-topic-decisions.md`). Sub-documents use\n"
        "sub-IDs that share the parent `NNN` prefix: `NNN-<letter><NN>` (e.g. `001-A01`),\n"
        "deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`). Parent and child\n"
        "share the `NNN` so a worktree can claim the subtree.\n\n"
        "Every spec carries `tags: [lowercase-kebab, ...]`; the promotion gate runs\n"
        "`tag-lint` on them.\n\n"
    )
    return body + f"{TOC_START}\n" + f"{TOC_END}\n"


def _repo_root(root: Path) -> Path:
    """Resolve the canonical repo root the TOC writers scan from.

    ``--root`` now means the repo root (the engine scans ``root/specs`` and
    ``root/docs``). A misused nested path (e.g. ``<repo>/docs``) is
    self-corrected by walking up to the nearest ``AGENTS.md`` marker, so a
    wrong path never materializes ``specs``/``docs`` in an unexpected place.
    """
    r = root
    for _ in range(6):
        if (r / "AGENTS.md").is_file():
            return r
        if r.parent == r:
            break
        r = r.parent
    return root


def _ensure_specs_readme(root: Path) -> None:
    """Bootstrap specs/README.md if missing (creator half).

    ``root`` is the repo root. Creates ``specs/README.md`` with marker
    scaffolding when absent (idempotent - an existing file is never touched)
    so the first promote/topic/compile/toc run can roll the index up
    immediately.
    """
    specs_readme = root / SPEC_FOLDER / "README.md"
    if not specs_readme.is_file():
        specs_readme.parent.mkdir(parents=True, exist_ok=True)
        specs_readme.write_text(_specs_readme_stub(), encoding="utf-8")


def _tag_lint(docs: dict, verbose: bool = False) -> list[str]:
    """Lint tags across ``specs/`` and ``docs/``.

    Every committed spec (``NNN-SPEC-*.md``) and every topic doc must carry a
    ``tags:`` field; any doc that carries one is linted for shape. Companion
    files (TASK/REPORT/APPROVALS/ESCALATION) are not tag-bearing and are
    skipped by the presence rule.

    Returns violation strings; exit code is always 1 on any violation here or
    in-check (no --warn-only), so the two entry points behave identically.
    """
    violations: list[str] = []
    for folder, label in (("specs", "specs"), ("topics", "docs")):
        for e in docs.get(folder, []):
            if re.search(r"(?m)^tags:\s*\[\s*\]\s*$", e["text"]):
                violations.append(f"{label}/{e['name']}: empty tags field")
            elif not e["tags"] and (folder == "topics" or SPEC_KIND.match(e["name"])):
                violations.append(f"{label}/{e['name']}: missing 'tags:' field")
            for p in _lint_tags(e["tags"]):
                violations.append(f"{label}/{e['name']}: {p}")
    if verbose:
        for v in violations:
            print("tag-lint: " + v)
    return violations


def _tag_list(docs: dict) -> int:
    """Read-only sorted tag -> files report with counts. No writes."""
    for folder, label in (("specs", "specs"), ("topics", "docs")):
        tagmap: dict[str, list[str]] = {}
        for e in docs.get(folder, []):
            for tag in e["tags"]:
                tagmap.setdefault(tag, []).append(e["name"])
        if not tagmap:
            print(f"{label}: (no tags)")
            continue
        print(f"{label}:")
        for tag in sorted(tagmap):
            print(f"  {tag} ({len(tagmap[tag])}): " + ", ".join(sorted(tagmap[tag])))
    return 0


def _tag_suggest(docs: dict) -> int:
    """Read-only advisory: near-duplicate candidates across all folders."""
    all_tags: set[str] = set()
    for entries in docs.values():
        for e in entries:
            all_tags.update(e["tags"])
    cands = []
    for t in sorted(all_tags):
        base = t.replace("-", "")
        for u in sorted(all_tags):
            if u != t and u.replace("-", "") == base:
                pair = " / ".join(sorted({t, u}))
                if pair not in cands:
                    cands.append(pair)
    if cands:
        print("suggest-merge candidates (advisory):")
        for c in cands:
            print("  " + c)
    else:
        print("no near-duplicate tags")
    return 0


def _tag_list_cmd(args: argparse.Namespace) -> int:
    return _tag_list(_scan_docs(args.root))


def _tag_suggest_cmd(args: argparse.Namespace) -> int:
    return _tag_suggest(_scan_docs(args.root))


def _tag_lint_cmd(args: argparse.Namespace) -> int:
    docs = _scan_docs(args.root)
    violations = _tag_lint(docs, verbose=True)
    if violations:
        print(f"tag-lint: {len(violations)} violation(s)")
        return 1
    print("tag-lint: ok")
    return 0


def _tag_rename(args: argparse.Namespace) -> int:
    """The only tag writer: rewrite the frontmatter tags of matched docs."""
    root = args.root
    changed = 0
    for folder, fdir in (("specs", root / "specs"), ("docs", root / "docs")):
        if not fdir.is_dir():
            continue
        for f in sorted(fdir.rglob("*.md")):
            if not f.is_file() or f.name == "README.md":
                continue
            rel = f.relative_to(fdir)
            if folder == "specs" and len(rel.parts) > 1:
                continue  # companion trees under specs/ are not docs
            if (
                folder == "docs"
                and len(rel.parts) > 1
                and rel.parts[0] in TOPIC_RESERVED
            ):
                continue  # reserved non-topic trees
            relname = rel.as_posix()
            try:
                text = read_text(f)
            except (OSError, UnicodeDecodeError):
                continue
            match = TAG_LINE.search(text)
            if not match:
                continue
            tags = [t.strip() for t in match.group(1).strip().split(",") if t.strip()]
            if args.old not in tags:
                continue
            new_tags = list(
                dict.fromkeys(args.new if t == args.old else t for t in tags)
            )
            new_line = "tags: [" + ", ".join(new_tags) + "]"
            new_text = text[: match.start()] + new_line + text[match.end() :]
            f.write_text(ensure_frontmatter_tags(new_text), encoding="utf-8")
            changed += 1
            print(f"renamed: {folder}/{relname}: {args.old} -> {args.new}")
    if not changed:
        print(f"no docs carry tag '{args.old}'")
    return 0


def substitute_spec_id(text: str, num: int) -> str:
    """Replace the title's leading ID placeholder with the computed NNN-SPEC.

    The template title is '# [SPEC-ID]: Feature Title'; promotion must stamp the
    engine-derived number onto it so the committed title matches the filename
    ('001-SPEC-feature-title.md' -> '# 001-SPEC: Feature Title'). Accepts the
    bracket placeholder, a bare 3-digit number, a sub-ID prefix, or an existing
    NNN-SPEC token, and rewrites only the leading token of the first '#' heading.
    Text with no such token is returned unchanged.
    """
    id_token = re.compile(
        r"^(\[\S+\]|\d{3}-SPEC|\d{3}-[A-Z]\d{2}(?:-[A-Z]\d{2})?|\d{3})(?=:|\s)"
    )
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            body = stripped[1:].strip()
            m = id_token.match(body)
            if not m:
                return text
            new_title = "# " + f"{num:03d}-SPEC" + body[m.end() :]
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = indent + new_title
            return "\n".join(lines)
    return text


def normalize_status(status: str) -> str:
    """Expand shorthand: PROVISIONAL -> 'PROVISIONAL - AUTONOMOUS DEFAULT'."""
    if status.upper() == "PROVISIONAL":
        return PROVISIONAL_STATUS
    return "APPROVED"


def replace_status(text: str, status: str) -> str:
    """Replace the 'Status:' frontmatter/header value with the new one."""
    return re.sub(r"(?m)^(Status:\s*).*$", r"\g<1>" + status, text, count=1)


# The legal edges of the single Status: lifecycle. The
# explicit `transition` command enforces these; the automatic owners
# (the verify engine's build/report, the gate engine's blocks) set their own edge
# directly. DRAFTED -> APPROVED is promote; APPROVED -> COMPILED is compile.
STATUS_EDGES = {
    "DRAFTED": ("APPROVED", "COMPILED", "ABORTED"),
    "APPROVED": ("COMPILED", "PLAN_REVISION_REQUIRED", "ABORTED"),
    "PROVISIONAL": ("COMPILED", "PLAN_REVISION_REQUIRED", "ABORTED"),
    "COMPILED": ("BUILDING", "PLAN_REVISION_REQUIRED", "ABORTED"),
    "BUILDING": ("BUILT", "REVIEWED", "ESCALATED", "ABORTED"),
    "BUILT": ("REVIEWED", "REVIEW_REVISION_REQUIRED", "ESCALATED", "ABORTED"),
    "REVIEWED": ("COMPLETED", "REVIEW_REVISION_REQUIRED", "ESCALATED", "ABORTED"),
    "PLAN_REVISION_REQUIRED": ("DRAFTED", "COMPILED", "ABORTED"),
    "REVIEW_REVISION_REQUIRED": ("BUILDING", "BUILT", "ABORTED"),
    "ESCALATED": ("BUILDING", "COMPILED", "DRAFTED", "ABORTED"),
    "COMPLETED": (),
    "ABORTED": (),
}


def transition_spec(spec: Path, to: str, root: Path | None = None) -> None:
    """Move ``spec`` to the canonical status ``to``, refusing an illegal edge.

    The explicit transition owner for steps with no dedicated command (a human
    stop to ``ABORTED``, a gate block to ``PLAN_REVISION_REQUIRED`` /
    ``REVIEW_REVISION_REQUIRED``) and for manual corrections. The build/report
    owners (the ``verify`` engine) set ``BUILDING`` / ``BUILT`` / ``REVIEWED`` directly.
    """
    target = to.upper()
    if target not in CANONICAL_STATUSES:
        raise SystemExit(f"error: '{target}' is not a canonical Status")
    root = root or find_root()
    text = read_text(spec)
    current = status_token(text)
    if not current:
        raise SystemExit(f"error: {spec.name} has no 'Status:' line")
    if current == target:
        return
    if target not in STATUS_EDGES.get(current, ()):
        raise SystemExit(
            f"error: illegal transition {current} -> {target} on {spec.name}"
        )
    spec.write_text(replace_status(text, target), encoding="utf-8")
    _refresh_specs_readme(root)


def _ref_status(text: str) -> str:
    """Status value from the header region only (before the first '## ').

    Reference docs carry no lifecycle and may embed template examples in
    fenced code blocks - only the real header region counts.
    """
    body = strip_fenced_code(text)
    cut = body.find("\n## ")
    head = body if cut == -1 else body[:cut]
    return status_value(head)


def _toc_entry_line(e: dict, rel: str) -> str:
    """One 📄 file row: relative link + optional status/pin/backlink metadata.

    The link label is the filename so the rendered tree reads like a real
    directory; the path ``rel`` is computed by the caller relative to the
    README the block lands in. Metadata stays out of the anchor.
    """
    line = f"  - 📄 [{e['name']}]({rel})"
    if e["status"]:
        line += f" — {e['status']}"
    if e["version_pin"]:
        line += f" (pin {e['version_pin']})"
    if e["fallback_pin"]:
        line += f" (fallback {e['fallback_pin']})"
    if e["backlinks"]:
        line += " — backlinks: " + "; ".join(e["backlinks"])
    return line


def _build_toc_lines(docs: dict) -> str:
    """Render the '## Index' block of specs/README.md (specs only)."""
    lines = ["## Index"]
    for e in docs.get("specs", []):
        lines.append(_toc_entry_line(e, f"./{e['name']}"))
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _refresh_toc_for(root: Path) -> None:
    """Regenerate the TOC block in specs/README.md.

    ``root`` is the repo root. ``specs/README.md`` is a specs-only index.
    Missing READMEs are bootstrapped with marker scaffolding first, so a fresh
    repo gets its index on the first lifecycle event.
    """
    root = _repo_root(root)
    _ensure_specs_readme(root)
    docs = _scan_docs(root)
    target = root / SPEC_FOLDER / "README.md"
    if not target.is_file():
        return
    block = _build_toc_lines(docs)
    new_text = _write_marker_block(read_text(target), TOC_START, TOC_END, block)
    if new_text is not None:
        target.write_text(new_text, encoding="utf-8")


def cmd_toc(args: argparse.Namespace) -> int:
    root = _repo_root(args.root)
    _ensure_specs_readme(root)
    docs = _scan_docs(root)
    target = root / SPEC_FOLDER / "README.md"
    block = _build_toc_lines(docs)
    new_text = _write_marker_block(read_text(target), TOC_START, TOC_END, block)
    if new_text is None:
        print(f"warning: no TOC markers in {target} (skipped)")
        return 1
    if args.dry_run:
        print(f"would update {target}:")
        print(new_text)
    else:
        target.write_text(new_text, encoding="utf-8")
        print(f"up to date: {target}")
    return 0


TOPIC_RESERVED = ("reference", "specs", "temp", "readme")
TOPIC_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _topic_ns(name: str) -> str:
    """The decision ID namespace: the full topic name, uppercased (auth -> AUTH)."""
    return name.upper()


def _topic_display(name: str, sub_file: str | None) -> str:
    """Human display name for a new topic doc's H1 (may exceed the filename)."""
    base = " ".join(w.capitalize() for w in name.split("-"))
    if not sub_file:
        return base
    return base + " " + " ".join(w.capitalize() for w in sub_file.split("-"))


def _topic_paths(docs_dir: Path, name: str, sub_file: str | None):
    """Return (target file, all topic files) for one revision.

    A topic is either one file ``docs/<name>.md`` or a folder ``docs/<name>/``
    of sub-files - never both. The second value lists every file of the topic
    so ID allocation stays topic-global across sub-files.
    """
    file_topic = docs_dir / (name + ".md")
    folder = docs_dir / name
    if sub_file:
        if not TOPIC_NAME_RE.match(sub_file):
            sys.exit(f"error: sub-file name '{sub_file}' must be lowercase-kebab")
        if file_topic.is_file():
            sys.exit(f"error: topic '{name}' is a file; a file topic takes no --file")
        target = folder / (sub_file + ".md")
        files = sorted(folder.glob("*.md")) if folder.is_dir() else []
    else:
        if folder.is_dir():
            sys.exit(f"error: topic '{name}' is a folder; pass --file <sub>")
        target = file_topic
        files = []
    if target not in files:
        files.append(target)
    return target, files


def _next_topic_id(files: list[Path], ns: str) -> int:
    """Next <ns>-D<nn> number: the max across every topic file + 1 (1 if none)."""
    pattern = re.compile(r"^###\s+" + re.escape(ns) + r"-D(\d+)(?:\s|$)", re.MULTILINE)
    highest = 0
    for f in files:
        if not f.is_file():
            continue
        try:
            text = read_text(f)
        except (OSError, UnicodeDecodeError):
            continue
        for match in pattern.finditer(text):
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _id_present(files: list[Path], decision_id: str) -> bool:
    """True when any topic file carries a '### <decision_id>' log subheading."""
    pattern = re.compile(
        r"^###\s+" + re.escape(decision_id) + r"(?:\s|$)", re.MULTILINE
    )
    for f in files:
        if not f.is_file():
            continue
        try:
            if pattern.search(read_text(f)):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


def _log_entry(
    decision_id: str,
    title: str,
    entry_date: str,
    why: str,
    supersedes: str | None,
    affects: str | None,
    ref: str | None,
) -> str:
    """One Decision Log entry: '### <ID> - <title>' + its field lines."""
    lines = [
        f"### {decision_id} - {title}",
        f"- **Date:** {entry_date}",
        f"- **Why:** {why}",
    ]
    if supersedes:
        lines.append(f"- **Supersedes:** {supersedes}")
    if affects:
        lines.append(f"- **Affects:** {affects}")
    if ref:
        lines.append(f"- **Ref:** {ref}")
    return "\n".join(lines) + "\n"


def _topic_scaffold(display: str, tags: list[str], state: str) -> str:
    """A new topic doc matching references/topic-template.md (format-of-truth)."""
    body = state.strip("\n") if state.strip() else "_(to be described)_"
    return (
        "---\n"
        "tags: [" + ", ".join(tags) + "]\n"
        "---\n\n"
        f"# {display}\n\n"
        "## Current State\n\n" + body + "\n\n## Decision Log\n"
    )


def _ensure_sections(text: str) -> str:
    """Guarantee both contract sections exist (Current State before the Log)."""
    if "## Current State" not in text:
        if "## Decision Log" in text:
            text = text.replace(
                "## Decision Log",
                "## Current State\n\n_(to be described)_\n\n## Decision Log",
                1,
            )
        else:
            text = text.rstrip("\n") + "\n\n## Current State\n\n_(to be described)_\n"
    if "## Decision Log" not in text:
        text = text.rstrip("\n") + "\n\n## Decision Log\n"
    return text


def _mark_superseded(text: str, decision_id: str) -> str:
    """Mark an existing log entry's heading '(superseded)'. Never removes it."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^###\s+" + re.escape(decision_id) + r"(?:\s|$)", line):
            if "(superseded)" not in line:
                lines[i] = line.rstrip() + " (superseded)"
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return text


def _replace_state(text: str, state: str) -> str:
    """Replace the '## Current State' body in place (up to the next '## ')."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Current State":
            start = i + 1
            break
    if start is None:
        return text
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    lines[start:end] = state.strip("\n").splitlines()
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _append_log_entry(text: str, entry: str) -> str:
    """Append one entry at the end of the '## Decision Log' section (file end)."""
    return text.rstrip("\n") + "\n\n" + entry


def _revise_topic(
    path: Path,
    display: str,
    tags: list[str],
    entry: str,
    supersedes: str | None,
    state: str | None,
) -> None:
    """Apply one revision to a topic file (create from the template if missing).

    Never deletes or recreates: a superseded entry stays in the log (marked),
    the Current State is updated in place, and the new entry takes the next
    ID - one decision, one reason, one approval.
    """
    if path.is_file():
        text = _ensure_sections(read_text(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = _topic_scaffold(display, tags, state or "")
    if supersedes:
        text = _mark_superseded(text, supersedes)
    if state is not None:
        text = _replace_state(text, state)
    path.write_text(_append_log_entry(text, entry), encoding="utf-8")


def cmd_topic(args: argparse.Namespace) -> int:
    """Create or revise a topic doc (Current State + Decision Log)."""
    name = args.name
    if not (2 <= len(name) <= 30) or not TOPIC_NAME_RE.match(name):
        print(f"error: topic name '{name}' must be lowercase-kebab (2-30 chars)")
        return 1
    if name in TOPIC_RESERVED:
        print(f"error: topic name '{name}' is reserved")
        return 1

    tags = (
        [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else [name]
    )
    tag_problems = _lint_tags(tags)
    if tag_problems:
        for p in tag_problems:
            print("error: " + p)
        return 1

    docs = _repo_root(args.docs_dir) / "docs"
    target, files = _topic_paths(docs, name, args.file)
    ns = _topic_ns(name)

    if args.supersedes and not _id_present(files, args.supersedes):
        print(f"error: {args.supersedes} not found in topic '{name}'")
        return 1

    num = _next_topic_id(files, ns)
    decision_id = f"{ns}-D{num:02d}"
    title = args.title or args.why
    entry_date = args.date or date.today().isoformat()

    entry = _log_entry(
        decision_id, title, entry_date, args.why, args.supersedes, args.affects, None
    )

    # Validate the reciprocal side fully before any write: a rejected
    # --reciprocal must not leave a half-applied revision behind.
    reciprocal = None
    if args.reciprocal:
        rname = args.reciprocal
        if rname == name:
            print("error: --reciprocal must name a different topic")
            return 1
        if not (2 <= len(rname) <= 30) or not TOPIC_NAME_RE.match(rname):
            print(
                f"error: reciprocal topic name '{rname}' must be lowercase-kebab (2-30 chars)"
            )
            return 1
        if rname in TOPIC_RESERVED:
            print(f"error: reciprocal topic name '{rname}' is reserved")
            return 1
        rtarget, rfiles = _topic_paths(docs, rname, args.reciprocal_file)
        rnum = _next_topic_id(rfiles, _topic_ns(rname))
        rid = f"{_topic_ns(rname)}-D{rnum:02d}"
        ref = target.relative_to(docs).as_posix() + "#" + decision_id.lower()
        rentry = _log_entry(
            rid,
            args.reciprocal_title or f"Cross-topic: {decision_id}",
            entry_date,
            args.reciprocal_why or "(cross-topic revision)",
            None,
            None,
            ref,
        )
        reciprocal = (rtarget, rname, rid, rentry)

    if args.dry_run:
        print(f"target: {target}")
        print(f"decision: {decision_id}")
        if reciprocal is not None:
            print(f"reciprocal: {reciprocal[0]} ({reciprocal[2]})")
        return 0

    _revise_topic(
        target,
        _topic_display(name, args.file),
        tags,
        entry,
        args.supersedes,
        args.state,
    )
    print(f"topic: {target}")
    print(f"decision: {decision_id}")

    if reciprocal is not None:
        rtarget, rname, rid, rentry = reciprocal
        _revise_topic(
            rtarget,
            _topic_display(rname, args.reciprocal_file),
            [rname],
            rentry,
            None,
            args.reciprocal_state,
        )
        print(f"reciprocal: {rtarget} ({rid})")
    return 0


def _draft_tag_violations(draft: Path) -> list[str]:
    """Normative lint of the draft file's own tags (check gate).

    The promotion gate must reject a draft whose frontmatter tags are
    malformed or absent, independent of the pre-existing tree. Returns []
    only when the draft is absent or unreadable.
    """
    try:
        text = read_text(draft)
    except (OSError, UnicodeDecodeError):
        return []
    tags = _extract_tags(text)
    if tags is None:
        return ["draft: missing 'tags:' field in frontmatter"]
    if not tags:
        return ["draft: empty tags field"]
    return _lint_tags(tags)


def _gitignore_dir_names(root: Path) -> set[str]:
    """Plain directory names listed in the repo-root ``.gitignore``.

    Gitignored trees are not part of the repo (e.g. generated
    ``.behavior-review/`` HTML), so specs-lint never scans them. Only
    simple names are honored - glob patterns and negations are ignored -
    as a dependency-free approximation of git's own ignore rules.
    """
    names: set[str] = set()
    ignore = root / ".gitignore"
    if not ignore.is_file():
        return names
    try:
        lines = ignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return names
    for line in lines:
        entry = line.strip().strip("/")
        if not entry or entry.startswith(("#", "!")):
            continue
        if re.fullmatch(r"[A-Za-z0-9_.-]+", entry):
            names.add(entry)
    return names


def is_framework_repo(root: Path) -> bool:
    """True when ``root`` is the Dev Agent framework's own product repo.

    The one-way rule protects *consumer* repos: their docs and source never
    depend on the disposable ``specs/``. The framework repo is the product -
    its ``skills/``, ``docs/``, and ``tests/`` describe the specs system by
    design - so it is exempt from its own gate.

    The marker is the *source* runtime (``skills/dev-agent/runtime/devagent``),
    which only exists in the framework checkout. Consumer repos install the
    runtime under ``.agents/scripts/devagent``, so they never match - and a
    consumer that happens to keep a top-level ``skills/`` tree stays strict.
    """
    return (root / "skills" / "dev-agent" / "runtime" / "devagent").is_dir()


def scan_specs_references(root: Path) -> list[tuple[str, int, str]]:
    """Return (relative path, line number, line) for every inbound specs/ ref.

    Files under ``specs/`` and vendored/ignored trees are skipped: the rule is
    one-way (specs/ may link out; nothing durable may link in).
    """
    root = Path(root)
    hits: list[tuple[str, int, str]] = []
    if not root.is_dir():
        return hits
    skip_dirs = SPECS_LINT_SKIP_DIRS | _gitignore_dir_names(root)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in skip_dirs for part in rel.parts[:-1]):
            continue
        if path.suffix.lower() not in SPECS_LINT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if SPECS_REF_RE.search(line):
                hits.append((rel.as_posix(), lineno, line.strip()))
    return hits


def scan_dangling_refs(
    base: Path, skip_dirs: frozenset[str] | None = None
) -> list[tuple[str, int, str]]:
    """Find references to the framework's own spec/decision IDs in durable files.

    A consumer repo has no framework spec or legacy decision-record IDs to point
    at. Workflow paths (``specs/temp/draft-plan.md``) do not match this pattern
    and stay legitimate. For the framework repo, pass ``skills/`` so only the
    shipped product is scanned.
    """
    base = Path(base)
    if not base.is_dir():
        return []
    skip = set(DANGLING_SKIP_DIRS if skip_dirs is None else skip_dirs)
    hits: list[tuple[str, int, str]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(base)
        if any(part in skip for part in rel.parts[:-1]):
            continue
        if "skill-creator" in rel.parts:
            continue  # vendored third-party skill; not ours to reword
        if path.suffix.lower() not in SPECS_LINT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if DANGLING_REF_RE.search(line):
                hits.append((rel.as_posix(), lineno, line.strip()))
    return hits


def cmd_specs_lint(args: argparse.Namespace) -> int:
    root = args.root if args.root is not None else find_root()
    framework = is_framework_repo(root)
    if framework:
        print(
            "specs-ref: skipped (framework repo - the product describes specs/ by design)"
        )
        spec_hits: list[tuple[str, int, str]] = []
        dangling = scan_dangling_refs(root / "skills")
    else:
        spec_hits = scan_specs_references(root)
        dangling = scan_dangling_refs(root)

    failed = False
    if not framework:
        if spec_hits:
            for rel, lineno, line in spec_hits:
                print(f"specs-ref: {rel}:{lineno}: {line}")
            print(
                f"specs-ref: {len(spec_hits)} reference(s) into specs/ "
                "(specs/ is disposable)"
            )
            failed = True
        else:
            print("specs-ref: ok (docs/ and source reference nothing under specs/)")

    if dangling:
        for rel, lineno, line in dangling:
            print(f"framework-ref: {rel}:{lineno}: {line}")
        print(
            f"framework-ref: {len(dangling)} dangling framework spec/decision "
            "reference(s) - these do not exist in a consumer repo"
        )
        failed = True
    else:
        print("framework-ref: ok (no dangling framework spec/decision references)")
    return 1 if failed else 0


def cmd_check(args: argparse.Namespace) -> int:
    passed, missing, struct_violations = check_draft(args.draft, args.lane)
    tag_violations = _tag_lint(_scan_docs(args.root))
    tag_violations += _draft_tag_violations(args.draft)
    if passed and not tag_violations:
        print("structure: ok")
        return 0
    if missing:
        print("missing sections: " + ", ".join(str(n) for n in missing))
    for v in struct_violations:
        print("structure: " + v)
    for v in tag_violations:
        print("tag-lint: " + v)
    return 1


def cmd_promote(args: argparse.Namespace) -> int:
    passed, missing, struct_violations = check_draft(args.draft, args.lane)
    tag_violations = _tag_lint(_scan_docs(args.root), verbose=True)
    tag_violations += _draft_tag_violations(args.draft)
    if not passed or tag_violations:
        if missing:
            print(
                "check failed - missing sections: " + ", ".join(str(n) for n in missing)
            )
        if struct_violations:
            for v in struct_violations:
                print("check failed - structure: " + v)
        if tag_violations:
            print(f"check failed - {len(tag_violations)} tag violation(s)")
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
    target = args.specs_dir / f"{num:03d}-SPEC-{slug}.md"
    print(f"next: {num:03d}")
    if target.exists():
        print(f"already exists: {target}")
        return 1
    if args.dry_run:
        print(f"target: {target}")
        return 0

    args.specs_dir.mkdir(parents=True, exist_ok=True)
    status = normalize_status(args.status)
    text = substitute_spec_id(text, num)
    target.write_text(
        ensure_frontmatter_tags(replace_status(text, status)), encoding="utf-8"
    )
    print(f"promoted: {target}")
    _refresh_toc_for(args.root)
    return 0


def _flow_flag(text: str, name: str) -> str:
    """The value of a frontmatter flow flag (``vetting: on``), default off."""
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(\S+)", text)
    return match.group(1).strip().lower() if match else "off"


def _vetting_blocks(text: str) -> int:
    """How many prior Vetting block receipts are in section 6."""
    return len(re.findall(r"(?mi)^-\s*Verdict:\s*block\b", section_body(text, 6)))


def _vetting_entry(verdict: str, note: str, accepted: bool = False) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"### Vetting {now} - {verdict}", f"- Verdict: {verdict}"]
    if accepted:
        lines.append("- Accepted: human override (accept-as-is)")
    if note:
        lines.append(f"- Note: {note}")
    return "\n".join(lines)


def cmd_vetting(args: argparse.Namespace) -> int:
    """Record a Vetting critic verdict on a draft and enforce the 3-block cap."""
    draft = args.draft
    try:
        text = read_text(draft)
    except (OSError, UnicodeDecodeError):
        print(f"vetting: cannot read draft {draft}")
        return 1

    if _flow_flag(text, "vetting") != "on":
        print(f"vetting: off - no gate recorded for {draft.name}")
        return 0
    if not args.accept and args.verdict is None:
        print("vetting: pass --verdict pass|block, or --accept for a human override")
        return 2

    verdict = "pass" if args.accept else args.verdict
    accepted = bool(args.accept)
    text = append_section_entry(
        text, 6, "Gates", _vetting_entry(verdict, args.note or "", accepted)
    )
    if verdict == "block":
        text = replace_status(text, "PLAN_REVISION_REQUIRED")
    elif accepted and status_token(text) == "PLAN_REVISION_REQUIRED":
        text = replace_status(text, "DRAFTED")
    draft.write_text(text, encoding="utf-8")

    print(f"vetting: {verdict} recorded in {draft.name}")
    if verdict == "block":
        blocks = _vetting_blocks(text)
        print(f"status: PLAN_REVISION_REQUIRED (block {blocks}/3)")
        if blocks >= 3:
            print(
                "cap: 3 blocks reached - hand back to the human; "
                "status stays PLAN_REVISION_REQUIRED"
            )
    elif accepted:
        print("status: accepted as-is")
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    try:
        written = compile_spec(args.spec, args.root)
    except SystemExit as e:
        print(str(e))
        return 1
    for f in written:
        print(f"task-file: {f.name}")
    print(f"compiles: {len(written)}")
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    try:
        purge_spec(args.spec, args.root)
    except SystemExit as e:
        print(str(e))
        return 1
    print("purged spec group")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    sync_specs_readme(args.root)
    print("synced specs/README.md")
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    try:
        accept_spec(args.spec, args.root)
    except SystemExit as e:
        print(str(e))
        return 1
    print(f"accepted: {args.spec.name} -> COMPLETED")
    return 0


def cmd_transition(args: argparse.Namespace) -> int:
    try:
        transition_spec(args.spec, args.to, args.root)
    except SystemExit as e:
        print(str(e))
        return 1
    print(f"transitioned: {args.spec.name} -> {args.to.upper()}")
    return 0


def main() -> int:
    # Never crash on a non-UTF-8 console (e.g. a cp1252 Windows pipe): a
    # line carrying a non-ASCII glyph degrades to '?' instead of raising.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(
        prog="devagent spec",
        description="spec-builder check, promotion, topic decisions, compile, TOC & tag governance",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check", help="validate a draft against the lane template")
    check_p.add_argument("draft", type=Path)
    check_p.add_argument("--lane", required=True, choices=["B", "A"])
    check_p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repo root for the tag-lint scan (default <repo-root>)",
    )
    check_p.set_defaults(func=cmd_check)

    promote_p = sub.add_parser("promote", help="promote an approved draft to specs/")
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
        help="target specs directory (default <repo-root>/specs; sandbox for tests)",
    )
    promote_p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repo root for the tag-lint scan + TOC refresh",
    )
    promote_p.set_defaults(func=cmd_promote)

    toc_p = sub.add_parser(
        "toc", help="regenerate the deterministic TOC blocks in the docs READMEs"
    )
    toc_p.add_argument(
        "--root", type=Path, default=None, help="repo root (default <repo-root>)"
    )
    toc_p.add_argument("--dry-run", action="store_true")
    toc_p.set_defaults(func=cmd_toc)

    topic_p = sub.add_parser(
        "topic", help="create/revise a topic doc decision (Decision Log)"
    )
    topic_p.add_argument(
        "name", help="topic name (lowercase-kebab; e.g. auth, data-storage)"
    )
    topic_p.add_argument(
        "--why", required=True, help="decision rationale (the Why field)"
    )
    topic_p.add_argument(
        "--title", default=None, help="decision display title (default: the why)"
    )
    topic_p.add_argument(
        "--file",
        default=None,
        help="sub-file of a folder topic (e.g. core -> docs/<name>/core.md)",
    )
    topic_p.add_argument(
        "--tags",
        default=None,
        help="comma-separated frontmatter tags (default: the topic name)",
    )
    topic_p.add_argument(
        "--state",
        default=None,
        help="replace the Current State section body (revision)",
    )
    topic_p.add_argument(
        "--supersedes",
        default=None,
        help="existing decision ID being reversed (marked superseded)",
    )
    topic_p.add_argument(
        "--affects",
        default=None,
        help="one-way pointer to the ripple target (topic.md#anchor)",
    )
    topic_p.add_argument(
        "--reciprocal",
        default=None,
        help="topic name gaining a decision because of this one",
    )
    topic_p.add_argument(
        "--reciprocal-file",
        default=None,
        help="sub-file of the reciprocal folder topic",
    )
    topic_p.add_argument(
        "--reciprocal-why", default=None, help="rationale for the reciprocal entry"
    )
    topic_p.add_argument(
        "--reciprocal-state",
        default=None,
        help="replace the reciprocal topic's Current State body",
    )
    topic_p.add_argument(
        "--reciprocal-title", default=None, help="display title of the reciprocal entry"
    )
    topic_p.add_argument("--date", default=None, help="decision date (default today)")
    topic_p.add_argument(
        "--docs-dir",
        type=Path,
        default=None,
        help="repo root (default <repo-root>; sandbox for tests)",
    )
    topic_p.add_argument("--dry-run", action="store_true")
    topic_p.set_defaults(func=cmd_topic)

    tag_ls_p = sub.add_parser("tag-list", help="read-only sorted tag -> files report")
    tag_ls_p.add_argument("--root", type=Path, default=None)
    tag_ls_p.set_defaults(func=_tag_list_cmd)

    tag_sug_p = sub.add_parser(
        "tag-suggest", help="read-only advisory near-dup tag candidates"
    )
    tag_sug_p.add_argument("--root", type=Path, default=None)
    tag_sug_p.set_defaults(func=_tag_suggest_cmd)

    tag_lint_p = sub.add_parser(
        "tag-lint", help="normative tag lint (exit 1 on violation; in check)"
    )
    tag_lint_p.add_argument("--root", type=Path, default=None)
    tag_lint_p.set_defaults(func=_tag_lint_cmd)

    tag_ren_p = sub.add_parser(
        "tag-rename", help="the only tag writer: rewrite the frontmatter tag"
    )
    tag_ren_p.add_argument("old")
    tag_ren_p.add_argument("new")
    tag_ren_p.add_argument("--root", type=Path, default=None)
    tag_ren_p.set_defaults(func=_tag_rename)

    specs_lint_p = sub.add_parser(
        "specs-lint",
        help="fail when docs/ or source references into specs/ (one-way rule)",
    )
    specs_lint_p.add_argument("--root", type=Path, default=None)
    specs_lint_p.set_defaults(func=cmd_specs_lint)

    vetting_p = sub.add_parser(
        "vetting",
        help="record a Vetting gate pass/block on a draft (optional)",
    )
    vetting_p.add_argument("draft", type=Path, help="the draft/plan file")
    vetting_p.add_argument("--verdict", choices=["pass", "block"], default=None)
    vetting_p.add_argument(
        "--accept",
        action="store_true",
        help="human accepts a critic block as-is (records a pass)",
    )
    vetting_p.add_argument("--note", default="", help="critic note / issues")
    vetting_p.set_defaults(func=cmd_vetting)

    compile_p = sub.add_parser(
        "compile",
        help="compile: emit one task file per section 5 task + approvals + stamp",
    )
    compile_p.add_argument("spec", type=Path, help="promoted spec NNN-SPEC-<slug>.md")
    compile_p.add_argument("--root", type=Path, default=None)
    compile_p.set_defaults(func=cmd_compile)

    purge_p = sub.add_parser(
        "purge", help="remove the whole spec group, then regenerate specs/README.md"
    )
    purge_p.add_argument("spec", type=Path, help="promoted spec NNN-SPEC-<slug>.md")
    purge_p.add_argument("--root", type=Path, default=None)
    purge_p.set_defaults(func=cmd_purge)

    sync_p = sub.add_parser("sync", help="regenerate specs/README.md only (no deletes)")
    sync_p.add_argument("--root", type=Path, default=None)
    sync_p.set_defaults(func=cmd_sync)

    accept_p = sub.add_parser(
        "accept", help="stamp Status: COMPLETED + Done: <date> (no git)"
    )
    accept_p.add_argument("spec", type=Path, help="promoted spec NNN-SPEC-<slug>.md")
    accept_p.add_argument("--root", type=Path, default=None)
    accept_p.set_defaults(func=cmd_accept)

    transition_p = sub.add_parser(
        "transition", help="move a spec to a canonical Status (edge-checked)"
    )
    transition_p.add_argument(
        "spec", type=Path, help="promoted spec NNN-SPEC-<slug>.md"
    )
    transition_p.add_argument("--to", required=True, help="target canonical Status")
    transition_p.add_argument("--root", type=Path, default=None)
    transition_p.set_defaults(func=cmd_transition)

    args = parser.parse_args()
    root_default = find_root()
    if args.command == "check" and args.root is None:
        args.root = root_default
    if args.command == "promote":
        if args.root is None:
            args.root = root_default
        # Resolve the root before deriving specs_dir: a nested --root such as
        # <repo>/docs must not materialize <repo>/docs/specs/.
        args.root = _repo_root(args.root)
        if args.specs_dir is None:
            args.specs_dir = args.root / SPEC_FOLDER
    if args.command == "toc" and args.root is None:
        args.root = root_default
    if (
        args.command
        in (
            "tag-list",
            "tag-suggest",
            "tag-lint",
            "tag-rename",
            "compile",
            "purge",
            "sync",
            "accept",
            "transition",
            "specs-lint",
        )
        and args.root is None
    ):
        args.root = root_default
    if args.command == "topic" and args.docs_dir is None:
        args.docs_dir = root_default
    # Resolve a misused nested path to the repo root for every --root subcommand,
    # so no engine entry point can materialize specs/docs in an unexpected place.
    for attr in ("root", "docs_dir"):
        if getattr(args, attr, None) is not None:
            setattr(args, attr, _repo_root(getattr(args, attr)))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
