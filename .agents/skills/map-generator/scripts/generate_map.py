#!/usr/bin/env python3
"""map-generator engine — scans skills, verifies freshness, rebuilds .agents/MAP.md.

Usage:
    python .agents/skills/map-generator/scripts/generate_map.py          # freshness check or rebuild
    python .agents/skills/map-generator/scripts/generate_map.py --force  # unconditional rebuild

Exit codes: 0 = index is fresh (or regenerated); 1 = fatal error.
Output strings follow system.md section 2 step 1 verbatim:
"MAP.md is fresh" (exit 0) or "regenerated".
"""

import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ENGINE_RELPATH = ".agents/skills/map-generator/scripts/generate_map.py"
FRESH_MSG = "MAP.md is fresh"
REGEN_MSG = "regenerated"

ASCII_MAP = {
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2026": "...",  # ellipsis
    "\u2192": "->",  # right arrow
}


def sanitize_ascii(text: str) -> str:
    """Map common Unicode punctuation to ASCII and drop everything non-ASCII.

    Keeps MAP.md rendering clean in viewers that default to Windows-1252.
    """
    for src, dst in ASCII_MAP.items():
        text = text.replace(src, dst)
    return "".join(ch for ch in text if ord(ch) < 128)


def find_root() -> Path:
    """Walk up from the script location until AGENTS.md is found (repo root marker)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit(
                "error: AGENTS.md not found above "
                + str(Path(__file__).resolve())
            )
        current = parent


def parse_front_matter(text: str) -> dict:
    """Parse a YAML-ish front-matter block (--- delimited). Returns {} if absent."""
    match = re.match(r"^\ufeff?---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if not key:
            i += 1
            continue
        if line[0].isspace() and value == "" and i + 1 < len(lines):
            continue  # blank nested line: handled by the block case below
        if value == "":
            # Block form: dash items -> list, indented "key: value" -> nested dict.
            j = i + 1
            items: list[str] = []
            sub: dict = {}
            while j < len(lines):
                nline = lines[j]
                if nline.strip() == "":
                    j += 1
                    continue
                if not nline[0].isspace():
                    break
                body = nline.strip()
                if body.startswith("-"):
                    items.append(body[1:].strip().strip("\"'"))
                    j += 1
                elif ":" in body:
                    skey, _, sval = body.partition(":")
                    if sval.strip() == "":
                        break  # two-level nesting unsupported; stop the block
                    sub[skey.strip().lower()] = sval.strip()
                    j += 1
                else:
                    break
            if sub:
                fields[key] = sub
            elif items:
                fields[key] = items
            i = j - 1
            continue
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("\"'") for v in value[1:-1].split(",")]
            fields[key] = [x for x in items if x]
        elif value.startswith('"') and value.endswith('"'):
            fields[key] = value[1:-1]
        else:
            fields[key] = value
        i += 1
    return fields


def scan_skills(root: Path) -> list[Path]:
    """Every SKILL.md under .agents/skills/ (one per skill)."""
    skills_dir = root / ".agents" / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.glob("*/SKILL.md"))


def all_mtime_sources(root: Path) -> list[Path]:
    """Every file under .agents/skills/ that can invalidate the index (mtime check)."""
    sources: list[Path] = []
    skills_dir = root / ".agents" / "skills"
    if skills_dir.is_dir():
        for p in sorted(skills_dir.rglob("*")):
            if p.is_file():
                sources.append(p)
    return sources


def map_path(root: Path) -> Path:
    return root / ".agents" / "MAP.md"


def is_fresh(root: Path, map_file: Path, skills: list[Path]) -> bool:
    """Freshness = stored snapshot matches the recomputed one.

    Content-hash comparison is mtime-independent: it catches skills copied in
    with old timestamps (git restore, worktree checkout, clock skew) that a
    pure mtime check would silently miss. Falls back to mtime when the index
    predates snapshot support (no Snapshot line).
    """
    if not map_file.is_file():
        return False
    try:
        text = map_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    match = re.search(r"^- Snapshot: ([0-9a-f]{8})", text, re.MULTILINE)
    if match:
        return snapshot_of(skills) == match.group(1)
    map_mtime = os.path.getmtime(map_file)
    for p in all_mtime_sources(root):
        if os.path.getmtime(p) > map_mtime:
            return False
    return True


def snapshot_of(files: list[Path]) -> str:
    """SHA-256 over all scanned SKILL.md contents (8-char prefix)."""
    digest = hashlib.sha256()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        digest.update(text.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()[:8]


def active_condition(scope: str, tags: list[str]) -> str:
    if scope == "always":
        return "*Always active*"
    if tags:
        rendered = ", ".join(f"`{t}`" for t in tags)
        return f"*Use when: {rendered}*"
    return "*On-demand*"


def skill_entry(path: Path) -> tuple[str, str, str, str]:
    """Return (name, description, active_condition, source_link) for one SKILL.md."""
    fields = parse_front_matter(path.read_text(encoding="utf-8"))
    name = sanitize_ascii(fields.get("name") or path.parent.name)
    desc = sanitize_ascii(fields.get("description", ""))
    tags = [
        sanitize_ascii(t)
        for t in (fields.get("tags") or fields.get("trigger_tags") or [])
    ]
    scope = fields.get("scope", "on-demand")
    rel = path.relative_to(find_root()).as_posix()
    display = f"{path.parent.name}/SKILL.md"
    return name, desc, active_condition(scope, tags), f"[{display}]({rel})"


def persona_entry(path: Path) -> tuple[str, str, str, str]:
    """Return (name, description, required_skills, source_link) for one persona file."""
    fields = parse_front_matter(path.read_text(encoding="utf-8"))
    name = sanitize_ascii(fields.get("name") or path.stem)
    desc = sanitize_ascii(fields.get("description", ""))
    skills = [
        sanitize_ascii(s)
        for s in (fields.get("requires") or fields.get("skills") or [])
    ]
    rel = path.relative_to(find_root()).as_posix()
    return name, desc, ", ".join(f"`{s}`" for s in skills), f"[{path.stem}.md]({rel})"


def build_map(root: Path, skills: list[Path], snapshot: str, generated: str) -> str:
    lines: list[str] = []
    lines.append("# Workspace Agent Map (`MAP.md`)")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> This file is auto-generated by the `map-generator` skill script")
    lines.append("> (`.agents/skills/map-generator/scripts/generate_map.py`).")
    lines.append(
        "> Do not modify this file manually - update individual SKILL.md frontmatters instead."
    )
    lines.append("")
    lines.append(f"- Generated: {generated}")
    lines.append(f"- Snapshot: {snapshot}")
    lines.append("")

    personas_dir = root / ".agents" / "personas"
    persona_files = sorted(personas_dir.glob("*.md")) if personas_dir.is_dir() else []
    if persona_files:
        lines.append("## Personas & Roles")
        lines.append("")
        lines.append(
            "| Persona | Description | Required Skills | Activation Trigger | Source File |"
        )
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for p in persona_files:
            name, desc, req_skills, link = persona_entry(p)
            trigger = sanitize_ascii(
                parse_front_matter(p.read_text(encoding="utf-8")).get("trigger", "")
            )
            lines.append(f"| **{name}** | {desc} | {req_skills} | {trigger} | {link} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Skills & Instructions")
    lines.append("")
    lines.append("| Skill | Description | Active Condition | Source File |")
    lines.append("| :--- | :--- | :--- | :--- |")
    rows = [skill_entry(p) for p in skills]
    rows.sort(key=lambda r: r[0].lower())
    for name, desc, cond, link in rows:
        lines.append(f"| **{name}** | {desc} | {cond} | {link} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    force = "--force" in sys.argv[1:]
    root = find_root()
    map_file = map_path(root)
    skills = scan_skills(root)

    if not force and is_fresh(root, map_file, skills):
        print(FRESH_MSG)
        return 0

    snapshot = snapshot_of(skills)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = build_map(root, skills, snapshot, generated)
    map_file.parent.mkdir(parents=True, exist_ok=True)
    map_file.write_text(content, encoding="utf-8", newline="\n")
    print(REGEN_MSG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
