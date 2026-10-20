"""Spec/task parsing and lookup shared by the spec and verify engines.

One parser for the plan/spec contract: section headings, section 5 task blocks,
status receipts, spec-group file identity, and the task-file verification
oracle. Both engines import from here so compile-time and run-time can never
disagree about the same Markdown (the ``ISSUES.md`` drift class).
"""

from __future__ import annotations

import re
from pathlib import Path

# Canonical Status: receipt set - past-tense receipts of the last completed
# engine action, one per lifecycle status plus the gate/failure receipts.
# The two decimal consensus gates (Vetting, Sign-off) carry no receipt.
CANONICAL_STATUSES = frozenset(
    (
        "DRAFTED",
        "APPROVED",
        "PROVISIONAL",
        "COMPILED",
        "BUILDING",
        "BUILT",
        "REVIEWED",
        "COMPLETED",
        "PLAN_REVISION_REQUIRED",
        "REVIEW_REVISION_REQUIRED",
        "ESCALATED",
        "ABORTED",
    )
)

# Spec group file types: a group is NNN-SPEC-* + its NNN-TASK-* /
# NNN-REPORT-* / NNN-APPROVALS-* / NNN-ESCALATION-* companions.
SPEC_KIND = re.compile(r"^(\d{3})-SPEC-(.+)\.md$")
TASK_KIND = re.compile(r"^(\d{3})-TASK-(\d{2})-(.+)\.md$")
GROUP_COMPANION_RE = re.compile(r"^(\d{3})-(TASK|REPORT|APPROVALS|ESCALATION)-")

NOOP_VERIFY_RE = re.compile(r"^(true|:|exit(\s+0*)?)$")


def is_noop_verify(cmd: str) -> bool:
    """True when a Verify command cannot fail (tautological oracle)."""
    c = (cmd or "").strip()
    if len(c) >= 2 and c.startswith("`") and c.endswith("`"):
        c = c[1:-1].strip()
    if not c:
        return True
    if NOOP_VERIFY_RE.match(c):
        return True
    return c.split()[0] == "echo"


def parse_sections(text: str) -> set[int]:
    """Collect the section numbers present as '## N.' headings."""
    found: set[int] = set()
    for line in text.splitlines():
        match = re.match(r"^##\s+(\d+)\.", line.strip())
        if match:
            found.add(int(match.group(1)))
    return found


def section_body(text: str, number: int) -> str:
    """Return the body of the '## <number>.' section (up to the next '## ')."""
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


def section_body_by_name(text: str, name: str) -> str:
    """The body of the '## <name>' section (up to the next '## ' heading)."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+" + re.escape(name) + r"\s*$", line.strip()):
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


def append_section_entry(text: str, number: int, title: str, entry: str) -> str:
    """Append ``entry`` inside the ``## <number>. <title>`` section.

    Creates the section when absent and never touches text outside it. Used by
    the gate audit log and the Vetting receipt so both write the same shape.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(r"^##\s+" + str(number) + r"\.", line.strip()):
            start = index
            break
    block = entry.splitlines()
    if start is None:
        return text.rstrip("\n") + f"\n\n## {number}. {title}\n\n" + entry + "\n"
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
    return "\n".join(merged).rstrip("\n") + "\n"


def parse_target_files(value: str) -> list[dict]:
    """Parse a '- Target Files:' value into [{'op': ..., 'path': ...}]."""
    entries: list[dict] = []
    op = ""
    for raw in value.split(","):
        segment = raw.strip()
        if not segment:
            continue
        match = re.match(r"^\[(NEW|MODIFY|DELETE|RENAME)\]\s*(.*)$", segment)
        if match:
            op = match.group(1)
            segment = match.group(2).strip()
        segment = segment.strip("`").strip()
        if not segment:
            continue
        entries.append({"op": op, "path": segment})
    return entries


def _split_list(value: str) -> list[str]:
    """A comma-separated section-5 field value -> a clean list."""
    return [
        part.strip().strip("`").strip() for part in value.split(",") if part.strip()
    ]


def parse_tasks(body: str) -> list[dict]:
    """Parse '### Task N:' blocks into structured task dicts.

    The union of every field either engine reads: title, Target Files,
    Depends On, Verify/Expect, Outcomes, and the optional authoring fields
    Area, Skills, Contract Changes, Callers, and Compatibility. Extra keys are
    harmless to a consumer that ignores them.
    """
    tasks: list[dict] = []
    current: dict | None = None
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        task_m = re.match(r"^###\s+Task\s+(\d+)\s*:\s*(.*)$", stripped)
        if task_m:
            current = {
                "num": int(task_m.group(1)),
                "title": task_m.group(2).strip(),
                "depends_on": "",
                "verify": "",
                "expect": "",
                "outcomes": "",
                "target_files": [],
                "area": "",
                "skills": [],
                "contract_changes": "",
                "callers": [],
                "compatibility": "",
            }
            tasks.append(current)
            continue
        if current is None:
            continue
        if stripped.startswith("###"):
            current = None
            continue
        field_m = re.match(
            r"^-\s*(Depends On|Verify|Expect|Target Files|Outcomes|Area|Skills|"
            r"Contract Changes|Callers|Compatibility)\s*:\s*(.*)$",
            stripped,
        )
        if field_m:
            label = field_m.group(1)
            value = field_m.group(2).strip()
            if label == "Target Files":
                current["target_files"] = parse_target_files(value)
            elif label == "Skills":
                current["skills"] = _split_list(value)
            elif label == "Callers":
                current["callers"] = _split_list(value)
            elif label == "Contract Changes":
                current["contract_changes"] = value
            elif label == "Area":
                current["area"] = value.strip().strip("`").strip()
            elif label == "Compatibility":
                current["compatibility"] = value.strip().strip("`").strip().lower()
            else:
                current[label.lower().replace(" ", "_")] = value
    return tasks


def section5_body(text: str) -> str:
    """The text of the '## 5.' section ('' when absent)."""
    return section_body(text, 5)


def section5_tasks(text: str) -> list[dict]:
    """Parse the '## 5.' section's '### Task N:' blocks."""
    return parse_tasks(section5_body(text))


def section5_outcome_ids(text: str) -> list[str]:
    """The 'R#' IDs declared in section 5's Outcomes table, in table order."""
    ids: list[str] = []
    for m in re.finditer(r"(?m)^\|\s*(R\d+)\s*\|", section5_body(text)):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def status_value(text: str) -> str:
    """The current 'Status:' header value ('' if absent)."""
    match = re.search(r"(?m)^Status:\s*(\S.*)$", text)
    return match.group(1).strip() if match else ""


def status_token(text: str) -> str:
    """The first token of the 'Status:' value ('' when absent)."""
    value = status_value(text)
    return value.split()[0] if value else ""


def status_token_file(path: Path) -> str:
    """The first token of a file's 'Status:' line ('' when unreadable/absent)."""
    try:
        return status_token(path.read_text(encoding="utf-8-sig"))
    except OSError:
        return ""


def spec_identity(name: str) -> tuple[int, str] | None:
    """Decode an NNN-SPEC-<slug>.md name to (number, slug); None otherwise."""
    match = SPEC_KIND.match(name)
    if not match:
        return None
    return (int(match.group(1)), match.group(2))


def spec_path(specs_dir: Path, num: int) -> Path:
    """The NNN-SPEC-*.md file for a spec number."""
    specs_dir = Path(specs_dir)
    if specs_dir.is_dir():
        for entry in sorted(specs_dir.iterdir()):
            if not entry.is_file():
                continue
            match = SPEC_KIND.match(entry.name)
            if match and int(match.group(1)) == num:
                return entry
    return specs_dir / f"{num:03d}-SPEC-unknown.md"


def spec_group_files(specs_dir: Path, num: int) -> list[Path]:
    """Every file of the spec group for ``num`` (SPEC + all companions)."""
    specs_dir = Path(specs_dir)
    files: list[Path] = []
    if not specs_dir.is_dir():
        return files
    for entry in specs_dir.iterdir():
        if not entry.is_file():
            continue
        match = SPEC_KIND.match(entry.name)
        if match:
            if int(match.group(1)) == num:
                files.append(entry)
            continue
        match = GROUP_COMPANION_RE.match(entry.name)
        if match and int(match.group(1)) == num:
            files.append(entry)
    return files


def task_file_for(specs_dir: Path, num: int, task_id: str) -> Path | None:
    """Locate the task file whose title names ``task_id`` (e.g. 'Task 3')."""
    match = re.match(r"^Task\s+(\d+)$", task_id) or re.match(r"^(\d+)$", task_id)
    if match:
        target = f"{num:03d}-TASK-{int(match.group(1)):02d}-"
        for path in spec_group_files(specs_dir, num):
            if path.name.startswith(target):
                return path
    for path in spec_group_files(specs_dir, num):
        if not path.name.startswith(f"{num:03d}-TASK-"):
            continue
        task_match = TASK_KIND.match(path.name)
        if task_match:
            trailing = re.search(r"(\d+)\s*$", task_id)
            if trailing and int(trailing.group(1)) == int(task_match.group(2)):
                return path
        try:
            head = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        if task_id in head.split("\n", 1)[0]:
            return path
    return None


def task_verify_command(task_file: Path) -> str:
    """The task file's '## Verification' fenced command block (the oracle)."""
    try:
        text = task_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    body = section_body_by_name(text, "Verification")
    if not body:
        return ""
    fence = re.search(r"```[a-z]*\s*\n(.*?)```", body, re.DOTALL)
    return fence.group(1).strip() if fence else ""
