#!/usr/bin/env python3
"""spec-builder engine - draft validation, spec promotion, ADR filing, and handoff.

Owns the mechanical parts of the spec lifecycle: template
enforcement, sequential numbering, promotion mechanics, Architectural
Decision Record filing, and the Phase 1.5 handoff record. The
acceptance gate itself is the caller's - the agent asserts it via --status
(APPROVED for human acceptance, PROVISIONAL for a compliant autonomous
resolution); this script never decides whether the gate passed. ADRs are
filed only alongside APPROVED promotion (human acceptance).

Modes:
    check    promote_spec.py check <draft> --lane <B|A>
             Parse the draft's "## N." section headings and verify the
             lane's required sections are present (B: 1, 4, 5; A: 1-7).
             Also validate the section-5 Task DAG structure:
             every "### Task N:" block carries Target Files:, Depends On:
             (may be None), >=1 subtask, and Phase Gate: (Lane A; optional
             for B, where the value must be None or a "Task N" reference);
             every subtask line ("- [ ] N.M ...") carries non-empty
             Input:/Output:/Verify:/Expect:; the plan has >=1 task. A static
             oracle lint rejects no-op Verify commands (true, :, exit, echo)
             and Expect markers that are a substring of the Verify command
             line (unconditionally-present oracle). Exit 0 when complete,
             1 with the missing-sections list and/or structural violations
             when not.

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
              Record the Phase 1.5 handoff for an approved spec.
              Validates the spec exists with Status: APPROVED (Lane A also
              requires at least one ADR whose Source: points at the spec;
              Lane B allows zero), writes docs/temp/handoff.md (ephemeral
              record), and stamps "Handoff: <YYYY-MM-DD>" on the spec's
              status header (durable marker). Idempotent - re-running against
              an already-handoffed spec reports the existing record and exits
              0. --dry-run prints what would be written without writing.
              --handoff-dir/--decisions-dir override the targets (tests and
              evals use a sandbox; the real docs/ are never touched).

    toc      promote_spec.py toc [--root <dir>] [--dry-run]
              Regenerate the deterministic "## Index" marker blocks in the
              README.md of the three committed docs folders (specs/,
              decisions/, reference/) and the docs/ landing README.
              --dry-run prints each computed block without writing. Never
              touches text outside the <!-- TOC:START -->/END markers.

    tag-list    promote_spec.py tag-list [--root <dir>]
              Read-only: print a sorted per-folder report of tag -> files
              with counts. No writes.
    tag-suggest promote_spec.py tag-suggest [--root <dir>]
              Read-only: print near-duplicate tag candidates (advisory
              only; never part of the promotion gate).
    tag-lint    promote_spec.py tag-lint [--root <dir>]
              Normative: exit 1 on any violation (lowercase-kebab, 2-30
              chars, max 7 tags/doc, no empty field). Wired into check, so
              a malformed tag also fails the promotion gate.
    tag-rename  promote_spec.py tag-rename <old> <new> [--root <dir>]
              The only tag writer: rewrites the tags frontmatter line of
              every doc carrying <old>. Prose outside the frontmatter is
              never touched.
    tag-index   promote_spec.py tag-index [--root <dir>] [--dry-run]
              Write the "## Tag Index" marker block into each folder
              README's docs/README.md.

Usage:
    python .agents/skills/spec-builder/scripts/promote_spec.py \
        check docs/temp/draft-plan.md --lane B
    python .agents/skills/spec-builder/scripts/promote_spec.py \
        promote docs/temp/draft-plan.md --lane A --status APPROVED
    python .agents/skills/spec-builder/scripts/promote_spec.py \
        adr docs/temp/adr-draft-<topic>.md \
        --source <promoted-spec>
    python .agents/skills/spec-builder/scripts/promote_spec.py \
        handoff docs/specs/<NNN>-<slug>.md --lane A

Exit codes: 0 = ok; 1 = check failed, exists, or violation/error.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

LANE_SECTIONS = {"B": {1, 4, 5}, "A": {1, 2, 3, 4, 5, 6, 7}}
PROVISIONAL_STATUS = "PROVISIONAL - AUTONOMOUS DEFAULT"

COMMIT_FOLDERS = ("specs", "decisions", "reference")
TOC_START = "<!-- TOC:START -->"
TOC_END = "<!-- TOC:END -->"
TAG_START = "<!-- TAG-INDEX:START -->"
TAG_END = "<!-- TAG-INDEX:END -->"
TAG_LINE = re.compile(r"(?m)^tags:\s*\[([^\]]*)\]\s*$")
TAG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FM_BLOCK = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
SUB_ID_RE = re.compile(r"^(\d{3})-([A-Z]\d{2})(?:-([A-Z]\d{2}))?$")


def find_root() -> Path:
    """The repository root: the nearest AGENTS.md marker.

    Walks up from the CWD first so sandboxed runs (``--specs-dir`` /
    ``--decisions-dir`` / ``--handoff-dir`` under /tmp) resolve their docs
    root to the sandbox, not the engine's own repo. Falls back to walking up
    from the script location when the CWD has no marker (e.g. the engine is
    invoked from an unrelated directory with explicit target dirs).
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


def _section_body(text: str, number: int) -> str:
    """Return the body of the '## <number>.' section (up to the next '## ' heading).

    Level-2 headings terminate the section; '### ' sub-headings are part of the
    body (the Task DAG's task blocks and completion-rules list live inside
    section 5). Returns '' when the section is absent.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+" + str(number) + r"\.", line.strip()):
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^##\s", lines[j].strip()):
            end = j
            break
    return "\n".join(lines[start:end])


NOOP_VERIFY_RE = re.compile(r"^(true|:|exit(\s+0*)?)$")


def _is_noop_verify(cmd: str) -> bool:
    """True when a Verify command cannot fail (tautological oracle).

    Rejects empty commands, 'true', ':', 'exit'/'exit 0', and any command whose
    first token is 'echo' (echo always exits 0, so it proves nothing).
    """
    c = cmd.strip()
    if not c:
        return True
    if NOOP_VERIFY_RE.match(c):
        return True
    return c.split()[0] == "echo"


def _parse_task_dag(body: str) -> list[dict]:
    """Parse '### Task N:' blocks of a section-5 body into structured task dicts.

    Each task carries its Target Files / Depends On / Phase Gate values and a
    list of subtasks; each subtask carries its (possibly empty) Input/Output/
    Verify/Expect field values. Field lines are indented; task-level lines sit
    at column 0, which is how the two are told apart.
    """
    tasks: list[dict] = []
    current: dict | None = None
    current_sub: dict | None = None
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        task_m = re.match(r"^###\s+Task\s+(\d+)\s*:\s*(.*)$", stripped)
        if task_m:
            current = {
                "num": int(task_m.group(1)),
                "title": task_m.group(2).strip(),
                "target_files": "",
                "depends_on": "",
                "phase_gate": "",
                "subtasks": [],
            }
            tasks.append(current)
            current_sub = None
            continue
        if current is None:
            continue
        # any other '###' heading (e.g. '### Completion rules') ends the block
        if stripped.startswith("###"):
            current = None
            current_sub = None
            continue
        tf_m = re.match(r"^-\s*Target Files\s*:\s*(.*)$", stripped)
        if tf_m:
            current["target_files"] = tf_m.group(1).strip()
            current_sub = None
            continue
        dep_m = re.match(r"^-\s*Depends On\s*:\s*(.*)$", stripped)
        if dep_m:
            current["depends_on"] = dep_m.group(1).strip()
            current_sub = None
            continue
        pg_m = re.match(r"^-\s*Phase Gate\s*:\s*(.*)$", stripped)
        if pg_m:
            current["phase_gate"] = pg_m.group(1).strip()
            current_sub = None
            continue
        sub_m = re.match(r"^\s+-\s*\[[ xX/]\]\s*(\d+)\.(\d+)\b\s*(.*)$", raw)
        if sub_m:
            current_sub = {
                "id": sub_m.group(1) + "." + sub_m.group(2),
                "input": "",
                "output": "",
                "verify": "",
                "expect": "",
            }
            current["subtasks"].append(current_sub)
            continue
        fld_m = re.match(r"^\s+-\s*(Input|Output|Verify|Expect)\s*:\s*(.*)$", raw)
        if fld_m and current_sub is not None:
            current_sub[fld_m.group(1).lower()] = fld_m.group(2).strip()
    return tasks


def _validate_task_dag(tasks: list[dict], lane: str) -> list[str]:
    """Structural + static-oracle violations for the section-5 Task DAG (D6)."""
    if not tasks:
        return ["section 5: no '### Task N:' blocks found (zero-gate plan rejected)"]
    violations: list[str] = []
    for task in tasks:
        tlabel = "Task %d" % task["num"]
        if not task["target_files"]:
            violations.append(tlabel + ": missing 'Target Files:'")
        if not task["depends_on"]:
            violations.append(tlabel + ": missing 'Depends On:'")
        elif lane == "B" and task["depends_on"] != "None" and not re.match(
            r"^Task\s+\d+(\s*,\s*Task\s+\d+)*$", task["depends_on"]
        ):
            violations.append(
                tlabel + ": 'Depends On:' must be 'None' or a 'Task N' reference (got '%s')"
                % task["depends_on"]
            )
        if lane == "A" and not task["phase_gate"]:
            violations.append(tlabel + ": missing 'Phase Gate:'")
        if not task["subtasks"]:
            violations.append(tlabel + ": has no subtasks (need >= 1)")
        for sub in task["subtasks"]:
            slabel = "%s subtask %s" % (tlabel, sub["id"])
            for field in ("Input", "Output", "Verify", "Expect"):
                if not sub[field.lower()]:
                    violations.append(slabel + ": missing/empty '%s:'" % field)
            verify = sub["verify"]
            expect = sub["expect"]
            if verify and _is_noop_verify(verify):
                violations.append(slabel + ": 'Verify:' is a no-op command ('%s')" % verify)
            if expect and verify and expect in verify:
                violations.append(
                    slabel + ": 'Expect:' is a substring of the 'Verify:' command (oracle can never fail)"
                )
    return violations


def check_draft(draft: Path, lane: str) -> tuple[bool, list[int], list[str]]:
    """Return (passed, missing_sections, violations) for the lane's contract.

    'missing' is the lane's required '## N.' sections absent from the draft;
    'violations' are section-5 Task DAG structure problems and static-oracle
    lint findings. Both fail the gate.
    """
    try:
        text = read_text(draft)
    except (OSError, UnicodeDecodeError):
        return False, [], ["cannot read draft"]
    found = parse_sections(text)
    missing = sorted(LANE_SECTIONS[lane] - found)
    violations = []
    if 5 in found:
        violations = _validate_task_dag(_parse_task_dag(_section_body(text, 5)), lane)
    passed = not missing and not violations
    return passed, missing, violations


def parse_sub_id(name: str) -> tuple[int, str] | None:
    """Decode a sub-ID filename 'NNN-LNN[-LNN].md' to (parent, key).

    Key format: 'A01' for level 1, 'A01-B01' for level 2 (hyphen
    separator, letter + two digits). Returns None for non sub-IDs.
    """
    match = re.match(r"^(\d{3})-([A-Z]\d{2})(?:-([A-Z]\d{2}))?\.md$", name)
    if not match:
        return None
    parent = int(match.group(1))
    key = match.group(2) if not match.group(3) else match.group(2) + "-" + match.group(3)
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
    Column' promotes to 'refresh-token-column', a sub-ID draft titled
    '# 001-A01: Child Plan' promotes to 'child-plan', and an ADR titled
    '# ADR-001: In-Memory Storage' files to 'in-memory-storage'
    (sub-ID titles carry no numeric prefix in the filename).
    """
    title = ""
    for line in text.splitlines():
        if line.strip().startswith("# "):
            title = line.strip().lstrip("# ").strip()
            break
    title = re.sub(r"^(\[\S+\]|\d{3}-[A-Z]\d{2}(?:-[A-Z]\d{2})?|\d{3}|ADR-\d{3}):\s*", "", title)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "spec"


def find_existing_by_title(specs_dir: Path, title: str) -> Path | None:
    """Return an existing spec whose first '#' title matches the draft's.

    The SPEC-ID/title is the plan's identity - a repeat promotion of the
    same draft must be refused even though the sequential number is new.
    Scans parent and sub-ID files alike, so sub-IDs never bypass the check.
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
        body = text[fm.end():]
        new_body = (body[:match.start() - fm.end()]
                    + body[match.start() - fm.end():match.end() - fm.end()].replace(tag_line, "", 1)
                    + body[match.end() - fm.end():])
        new_body = re.sub(r"^\n+", "\n", new_body)
        return (text[:fm.start()] + "---\n" + fm.group(1) + "\n" + tag_line + "\n---\n"
                + new_body)
    rest = text[:match.start()] + text[match.end():]
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
    target.write_text(ensure_frontmatter_tags(text), encoding="utf-8")
    print(f"adr: {target}")
    _refresh_toc_for(find_root())
    return 0


def _fm_stripped(text: str) -> str:
    """Drop a leading YAML frontmatter block so scans see body content only."""
    return FM_BLOCK.sub("", text, count=1)


def draft_title(text: str) -> str:
    """The draft's first '#' heading line (its identity).

    Frontmatter (and code fences) are stripped first so a 'tags:' or any
    other frontmatter line can never be mistaken for the title.
    """
    for line in _strip_fenced_code(_fm_stripped(text)).splitlines():
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


def ensure_scratchpad_guard(handoff_dir: Path) -> None:
    """Scratchpad guard: a root .gitignore entry for the dir and the inner stub.

    The inner stub (``*`` + ``!.gitignore``) is the effective protection - git
    refuses to descend into a gitignored directory even without a root
    .gitignore - while the root entry documents the exclusion for viewers that
    stop at the top level. Idempotent. Runs only on the DEFAULT handoff dir;
    sandboxed ``--handoff-dir`` test runs never touch the real repo root.
    """
    root = handoff_dir
    for _ in range(4):
        if (root / "AGENTS.md").is_file() and (root / ".agents").is_dir():
            break
        root = root.parent
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
    inner = handoff_dir / ".gitignore"
    if not inner.is_file():
        inner.write_text("*\n!.gitignore\n", encoding="utf-8")


def cmd_handoff(args: argparse.Namespace) -> int:
    """Validate and record the Phase 1.5 handoff."""
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
    ensure_scratchpad_guard(args.handoff_dir)
    args.spec.write_text(stamped, encoding="utf-8")
    _refresh_toc_for(args.root)

    adr_line = ", ".join(adrs) if adrs else "none (Lane B)"
    handoff_file.write_text(
        "# Handoff - Session Ends Here\n\n"
        f"Date: {today}\n"
        f"Spec: {spec_ref}\n"
        f"Lane: {args.lane}\n"
        f"ADRs: {adr_line}\n\n"
        "Implementation runs in a new session that reads the promoted spec. "
        "The session that recorded this handoff must not open "
        "references/build.md.\n",
        encoding="utf-8",
    )
    print(f"handoff: {handoff_file}")
    # the TOC refresh is skipped on sandboxed handoff runs (no docs root)
    if args.handoff_dir == (find_root() / "docs" / "temp"):
        _refresh_toc_for(find_root() / "docs")
    return 0


def _folder_sort_key(folder: str, name: str) -> tuple:
    """Deterministic sort key per folder ID scheme."""
    if folder == "specs":
        match = re.match(r"^(\d{3})-([A-Z]\d{2})(?:-([A-Z]\d{2}))?\.md$", name)
        if match:
            return (int(match.group(1)), match.group(2)
                    + ("-" + match.group(3) if match.group(3) else ""))
        match = re.match(r"^(\d{3})-", name)
        if match:
            return (int(match.group(1)), "~")
        return (9999, name)
    if folder == "decisions":
        match = re.match(r"^adr-(\d{3})-", name)
        return (int(match.group(1)), name) if match else (9999, name)
    return (0, name)


def _strip_fenced_code(text: str) -> str:
    """Blank out fenced code blocks so they cannot fake frontmatter lines."""
    out: list[str] = []
    fence = 0
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fence ^= 1
            out.append("")
            continue
        out.append(line if fence == 0 else "")
    return "\n".join(out)


def _doc_title(text: str) -> str:
    """First '#' heading outside code fences, minus its leading number token."""
    for line in _strip_fenced_code(text).splitlines():
        if line.strip().startswith("# "):
            t = line.strip()[1:].strip()
            return re.sub(r"^(ADR-\d{3}:|\d{3}:|\[\S+\]:\s*)", "", t).strip() or t
    return ""


def _doc_backlinks(text: str) -> list[str]:
    """The 'Source:'/'Governed-by:' backlink targets on the status header."""
    links = []
    for label in ("Source", "Governed-by"):
        match = re.search(r"(?m)^" + label + r":\s*(\S.*)$", _strip_fenced_code(text))
        if match:
            links.append(match.group(1).strip())
    return links


def _scan_docs(root: Path) -> dict:
    """Scan the three committed folders into sorted per-folder doc entries.

    Shared by the TOC roll-up, tag-index, and every tag-governance function -
    one frontmatter parse, no cross-subcommand drift.
    """
    docs: dict[str, list[dict]] = {}
    for folder in COMMIT_FOLDERS:
        fdir = root / folder
        entries = []
        if fdir.is_dir():
            for f in fdir.iterdir():
                if not f.is_file() or f.name == "README.md":
                    continue
                try:
                    text = read_text(f)
                except (OSError, UnicodeDecodeError):
                    continue
                clean = _strip_fenced_code(text)
                m1 = re.search(r"(?m)^version_pin:\s*(\S+)", clean)
                m2 = re.search(r"(?m)^fallback_pin:\s*(\S+)", clean)
                entries.append({
                    "name": f.name,
                    "text": text,
                    "title": _doc_title(text),
                    "status": _ref_status(text),
                    "tags": _extract_tags(text) or [],
                    "version_pin": m1.group(1) if m1 else "",
                    "fallback_pin": m2.group(1) if m2 else "",
                    "backlinks": _doc_backlinks(text),
                })
        entries.sort(key=lambda e: _folder_sort_key(folder, e["name"]))
        docs[folder] = entries
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
    return text[:m1.start()] + start + "\n" + block + end + "\n" + text[m2.end():]


def _folder_readme_stub(folder: str) -> str:
    """Rich committed README scaffold for a docs subfolder (creator half, D6).

    Carries human-curated prose (heading, purpose, naming/ID convention,
    frontmatter note) plus both marker blocks, so a fresh repo's folder README
    reads like the hand-curated one on first creation. ``folder`` is one of
    COMMIT_FOLDERS (specs / decisions / reference).
    """
    prose = {
        "specs": (
            "# Specs\n\n"
            "Permanent functional & technical specs. Promotion pipeline:\n\n"
            "- Draft: `docs/temp/draft-plan.md` (gitignored)\n"
            "- Acceptance: promoted to `docs/specs/<NNN>-<feature-slug>.md` and committed\n\n"
            "Naming: `NNN-<feature-slug>.md` (e.g. `001-feature-spec.md`). Sub-documents use\n"
            "sub-IDs that share the parent `NNN` prefix: `NNN-<letter><NN>` (e.g. `001-A01`),\n"
            "deeper `NNN-<letter><NN>-<letter><NN>` (e.g. `001-A01-B01`). Parent and child\n"
            "share the `NNN` so a worktree can claim the subtree.\n\n"
            "Every spec carries `tags: [lowercase-kebab, ...]`; the promotion gate runs\n"
            "`tag-lint` on them.\n\n"
        ),
        "decisions": (
            "# Decisions\n\n"
            "Architectural Decision Records (ADRs). Naming: `adr-<NNN>-<topic>.md`\n"
            "(e.g. `adr-001-database-selection.md`). Flat — ADRs never nest; nesting is\n"
            "expressed by the backlink graph (`Source:` points at the spec, optional\n"
            "`Governed-by:` points at a reference doc).\n\n"
            "Protected files: ADRs in this directory must not be edited or deleted without\n"
            "explicit human confirmation.\n\n"
            "Every ADR carries `tags: [lowercase-kebab, ...]`.\n\n"
        ),
        "reference": (
            "# Reference\n\n"
            "Living reference docs — the authoritative, lookup surface of current system\n"
            "truth (living, version-pinable; no DRAFT/APPROVED lifecycle). Distinct from\n"
            "`docs/specs/` (what to build, lifecycle) and `docs/decisions/` (why we chose,\n"
            "immutable, backlinked).\n\n"
            "ID convention: `<slug>.md` (no numeric prefix; the filename is the single\n"
            "identity). Display title comes from the filename or H1, never a `name:` field.\n\n"
            "Version pin (opt-in): `version_pin: <git-tag>` (primary) or `fallback_pin:\n"
            "<commit-hash>` (when no tag exists). Absent by default; when present the value\n"
            "must be a real tag / reachable commit.\n\n"
        ),
    }
    body = prose.get(folder, f"# {folder.capitalize()}\n\n")
    return (
        body
        + f"{TOC_START}\n"
        + f"{TOC_END}\n\n"
        + f"{TAG_START}\n"
        + f"{TAG_END}\n"
    )


def _landing_readme_stub() -> str:
    """Rich docs/ landing README scaffold with TOC + Tag-Index marker blocks."""
    return (
        "# Docs\n\n"
        "Human + AI shared space: the committed knowledge of this repository.\n\n"
        "| Folder | Holds | ID convention |\n"
        "| :--- | :--- | :--- |\n"
        "| `specs/` | What to build — permanent functional & technical specs with a lifecycle (DRAFT → APPROVED) | `NNN-<slug>.md`, sub-IDs `NNN-<letter><NN>` |\n"
        "| `decisions/` | Why we chose — immutable ADRs, backlinked to specs | `adr-<NNN>-<slug>.md` (flat, never nested) |\n"
        "| `reference/` | What is — living, lookup, authoritative docs (no lifecycle) | `<slug>.md` |\n"
        "| `temp/` | Ephemeral working memory (gitignored; purged by task-cleaner) | none |\n\n"
        "## Index\n\n"
        "Deterministic per-folder index — regenerated by `promote_spec.py toc` on every\n"
        "promotion, ADR filing, and handoff. Marker block only; surrounding prose is\n"
        "untouched.\n\n"
        f"{TOC_START}\n"
        f"{TOC_END}\n\n"
        "## Frontmatter conventions\n\n"
        "- `tags: [lowercase-kebab, ...]` on every doc in `specs/`, `decisions/`,\n"
        "  `reference/` (governed by `promote_spec.py tag-lint`, also inside `check`).\n"
        "- Optional on `reference/` only: `version_pin: <git-tag>` or `fallback_pin:\n"
        "  <commit-hash>` (validated when present).\n"
        "- The filename is the single identity — no `name:` field anywhere.\n\n"
        f"{TAG_START}\n"
        f"{TAG_END}\n"
    )


def _ensure_docs_readmes(root: Path) -> None:
    """Bootstrap the four docs READMEs if missing (creator half).

    The engine previously only *regenerated* marker blocks and silently skipped
    files that did not exist, so a fresh repo never got its docs/README.md or
    folder READMEs. This creates any missing README with the marker scaffolding
    (idempotent - existing files are never touched) so the first promote/adr/
    handoff/toc run can roll the index up immediately.
    """
    landing = root / "README.md"
    if not landing.is_file():
        root.mkdir(parents=True, exist_ok=True)
        landing.write_text(_landing_readme_stub(), encoding="utf-8")
    for folder in COMMIT_FOLDERS:
        target = root / folder / "README.md"
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_folder_readme_stub(folder), encoding="utf-8")


def _tag_lint(docs: dict, verbose: bool = False) -> list[str]:
    """Lint every scanned doc's tags.

    Returns violation strings; exit code is always 1 on any violation here or
    in-check (no --warn-only), so the two entry points behave identically.
    """
    violations: list[str] = []
    for folder in COMMIT_FOLDERS:
        for e in docs[folder]:
            if re.search(r"(?m)^tags:\s*\[\s*\]\s*$", e["text"]):
                violations.append(f"{folder}/{e['name']}: empty tags field")
            for p in _lint_tags(e["tags"]):
                violations.append(f"{folder}/{e['name']}: {p}")
    if verbose:
        for v in violations:
            print("tag-lint: " + v)
    return violations


def _tag_list(docs: dict) -> int:
    """Read-only sorted tag -> files report with counts. No writes."""
    for folder in COMMIT_FOLDERS:
        tagmap: dict[str, list[str]] = {}
        for e in docs[folder]:
            for tag in e["tags"]:
                tagmap.setdefault(tag, []).append(e["name"])
        if not tagmap:
            print(f"{folder}: (no tags)")
            continue
        print(f"{folder}:")
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
    for folder in COMMIT_FOLDERS:
        fdir = root / folder
        if not fdir.is_dir():
            continue
        for f in fdir.iterdir():
            if not f.is_file() or f.name == "README.md":
                continue
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
            new_tags = list(dict.fromkeys(
                args.new if t == args.old else t for t in tags
            ))
            new_line = "tags: [" + ", ".join(new_tags) + "]"
            new_text = text[:match.start()] + new_line + text[match.end():]
            f.write_text(ensure_frontmatter_tags(new_text), encoding="utf-8")
            changed += 1
            print(f"renamed: {folder}/{f.name}: {args.old} -> {args.new}")
    if not changed:
        print(f"no docs carry tag '{args.old}'")
    return 0


def _tag_index(args: argparse.Namespace) -> int:
    """Write the '## Tag Index' marker block into docs/README.md."""
    root = args.root
    docs = _scan_docs(root)
    lines = ["## Tag Index", ""]
    for folder in COMMIT_FOLDERS:
        tagmap: dict[str, int] = {}
        for e in docs[folder]:
            for tag in e["tags"]:
                tagmap[tag] = tagmap.get(tag, 0) + 1
        if tagmap:
            lines.append(f"- {folder}: " + ", ".join(
                f"{t} ({n})" for t, n in sorted(tagmap.items())
            ))
    block = "\n".join(lines) + "\n"
    target = root / "README.md"
    if not target.is_file():
        target.write_text(
            "# Docs\n\n" + block + f"\n{TAG_START}\n{TAG_END}\n",
            encoding="utf-8",
        )
        print("tag-index: created " + str(target))
        return 0
    text = read_text(target)
    new_text = _write_marker_block(text, TAG_START, TAG_END, block)
    if new_text is None:
        print("error: no " + TAG_START + " marker in " + str(target))
        return 1
    if not args.dry_run:
        target.write_text(new_text, encoding="utf-8")
    print("tag-index: " + ("would update " if args.dry_run else "updated ") + str(target))
    return 0


def substitute_spec_id(text: str, num: int) -> str:
    """Replace the title's leading ID placeholder with the computed NNN.

    The template title is '# [SPEC-ID]: Feature Title'; promotion must stamp the
    engine-derived number onto it so the committed title matches the filename
    ('001-feature-title.md' -> '# 001: Feature Title'). Accepts the bracket
    placeholder, a bare 3-digit number, or a sub-ID prefix, and rewrites only the
    leading token of the first '#' heading. Text with no such token is returned
    unchanged.
    """
    id_token = re.compile(r"^(\[\S+\]|\d{3}-[A-Z]\d{2}(?:-[A-Z]\d{2})?|\d{3})(?=:|\s)")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            body = stripped[1:].strip()
            m = id_token.match(body)
            if not m:
                return text
            new_title = "# " + f"{num:03d}" + body[m.end():]
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


def _ref_status(text: str) -> str:
    """Status value from the header region only (before the first '## ').

    Reference docs carry no lifecycle and may embed template examples in
    fenced code blocks - only the real header region counts.
    """
    body = _strip_fenced_code(text)
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


def _build_toc_lines(docs: dict, folders: tuple[str, ...] | None = None,
                     landing: bool = True) -> str:
    """Render the '## Index' block as a linked, iconed directory tree.

    Folders act as header nodes and files as relative 📄 links - the standard
    Markdown TOC shape. The block carries its own heading, so callers pass it
    whole. ``folders`` scopes which folders appear (landing = all, folder =
    itself); ``landing`` picks the link base: the landing README sits in
    docs/ and links ``./<folder>/<file>``, while a folder README sits inside
    the folder and links ``./<file>``.
    """
    lines = ["## Index"]
    for folder in (folders or COMMIT_FOLDERS):
        entries = docs.get(folder, [])
        if not entries:
            continue
        lines.append(f"- 📁 {folder}/")
        for e in entries:
            rel = f"./{folder}/{e['name']}" if landing else f"./{e['name']}"
            lines.append(_toc_entry_line(e, rel))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _refresh_toc_for(root: Path) -> None:
    """Regenerate the TOC blocks in all four READMEs.

    The landing README shows the whole tree; each folder README shows only its
    own folder, so ``docs/specs/README.md`` stays a specs-only index. Missing
    READMEs are bootstrapped with marker scaffolding first, so a fresh repo
    gets its index on the first lifecycle event.
    """
    _ensure_docs_readmes(root)
    docs = _scan_docs(root)
    targets = [
        (root / "README.md", _build_toc_lines(docs, landing=True)),
    ] + [
        (root / folder / "README.md", _build_toc_lines(docs, (folder,), landing=False))
        for folder in COMMIT_FOLDERS
    ]
    for target, block in targets:
        if not target.is_file():
            continue
        new_text = _write_marker_block(read_text(target), TOC_START, TOC_END, block)
        if new_text is not None:
            target.write_text(new_text, encoding="utf-8")


def cmd_toc(args: argparse.Namespace) -> int:
    _ensure_docs_readmes(args.root)
    docs = _scan_docs(args.root)
    targets = [
        (args.root / "README.md", _build_toc_lines(docs, landing=True)),
    ] + [
        (args.root / folder / "README.md", _build_toc_lines(docs, (folder,), landing=False))
        for folder in COMMIT_FOLDERS
    ]
    for target, block in targets:
        if not target.is_file():
            continue
        new_text = _write_marker_block(read_text(target), TOC_START, TOC_END, block)
        if new_text is None:
            print(f"warning: no TOC markers in {target} (skipped)")
            continue
        if args.dry_run:
            print(f"would update {target}:")
            print(new_text)
        else:
            target.write_text(new_text, encoding="utf-8")
            print(f"up to date: {target}")
    return 0


def _draft_tag_violations(draft: Path) -> list[str]:
    """Normative lint of the draft file's own tags (check gate).

    The promotion gate must reject a draft whose frontmatter tags are
    malformed, independent of the pre-existing tree. Returns [] when the
    draft is absent or carries no tags field.
    """
    try:
        text = read_text(draft)
    except (OSError, UnicodeDecodeError):
        return []
    tags = _extract_tags(text)
    if not tags:
        return []
    return _lint_tags(tags)


def cmd_check(args: argparse.Namespace) -> int:
    passed, missing, struct_violations = check_draft(args.draft, args.lane)
    tag_violations = _tag_lint(_scan_docs(args.root))
    tag_violations += _draft_tag_violations(args.draft)
    if passed and not tag_violations:
        print("check passed")
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
            print("check failed - missing sections: " + ", ".join(str(n) for n in missing))
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
    text = substitute_spec_id(text, num)
    target.write_text(ensure_frontmatter_tags(replace_status(text, status)), encoding="utf-8")
    print(f"promoted: {target}")
    _refresh_toc_for(args.root)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="spec-builder check, promotion, ADR filing, handoff, TOC & tag governance"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check", help="validate a draft against the lane template")
    check_p.add_argument("draft", type=Path)
    check_p.add_argument("--lane", required=True, choices=["B", "A"])
    check_p.add_argument("--root", type=Path, default=None,
                         help="docs root for the tag-lint scan (default <root>/docs)")
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
    promote_p.add_argument("--root", type=Path, default=None,
                           help="docs root for the tag-lint scan + TOC refresh")
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

    toc_p = sub.add_parser(
        "toc", help="regenerate the deterministic TOC blocks in the docs READMEs"
    )
    toc_p.add_argument("--root", type=Path, default=None,
                       help="docs root (default <root>/docs)")
    toc_p.add_argument("--dry-run", action="store_true")
    toc_p.set_defaults(func=cmd_toc)

    tag_ls_p = sub.add_parser(
        "tag-list", help="read-only sorted tag -> files report"
    )
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

    tag_idx_p = sub.add_parser(
        "tag-index", help="write the Tag Index block into docs/README.md"
    )
    tag_idx_p.add_argument("--root", type=Path, default=None)
    tag_idx_p.add_argument("--dry-run", action="store_true")
    tag_idx_p.set_defaults(func=_tag_index)

    args = parser.parse_args()
    root_default = find_root() / "docs"
    if args.command == "check":
        if args.root is None:
            args.root = root_default
    if args.command == "promote":
        if args.root is None:
            args.root = root_default
        if args.specs_dir is None:
            args.specs_dir = args.root / "specs"
    if args.command == "adr" and args.decisions_dir is None:
        args.decisions_dir = root_default / "decisions"
    if args.command == "handoff":
        if args.handoff_dir is None:
            args.handoff_dir = root_default / "temp"
        if args.decisions_dir is None:
            args.decisions_dir = root_default / "decisions"
        if getattr(args, "root", None) is None:
            args.root = find_root() / "docs"
    if args.command == "toc" and args.root is None:
        args.root = root_default
    if args.command in ("tag-list", "tag-suggest", "tag-lint", "tag-rename", "tag-index") and args.root is None:
        args.root = root_default
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
