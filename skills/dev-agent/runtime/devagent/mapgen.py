#!/usr/bin/env python3
"""map-generator engine — scans skills, verifies freshness, rebuilds .agents/MAP.md.

Usage:
    python .agents/scripts/devagent/main.py map          # freshness check or rebuild
    python .agents/scripts/devagent/main.py map --force  # unconditional rebuild

Exit codes: 0 = index is fresh (or regenerated); 1 = fatal error.
Output strings follow dev-agent-framework.md section 2 step 1 verbatim:
"MAP.md is fresh" (exit 0) or "regenerated".
"""

import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from common.frontmatter import parse_front_matter
from common.root import find_root
from common.skillmeta import normalize_scope, normalize_tags
from common.text import sanitize_ascii

ENGINE_RELPATH = ".agents/scripts/devagent/main.py"
FRESH_MSG = "MAP.md is fresh"
REGEN_MSG = "regenerated"


def scan_skills(root: Path) -> list[Path]:
    """Every SKILL.md under .agents/skills/ (one per skill)."""
    skills_dir = root / ".agents" / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.glob("*/SKILL.md"))


def scan_personas(root: Path) -> list[Path]:
    """Every persona file under .agents/agents/ (rendered as Personas & Roles)."""
    agents_dir = root / ".agents" / "agents"
    if not agents_dir.is_dir():
        return []
    return sorted(agents_dir.glob("*.md"))


def indexed_sources(root: Path) -> list[Path]:
    """Every file whose content the generated index covers.

    Skills (``SKILL.md``) and personas (``.agents/agents/*.md``) are both
    rendered into MAP.md, so both must feed the freshness snapshot (M1).
    """
    return scan_skills(root) + scan_personas(root)


def all_mtime_sources(root: Path) -> list[Path]:
    """Every indexed file (skills + personas) that can invalidate the index."""
    sources: list[Path] = []
    for base in (root / ".agents" / "skills", root / ".agents" / "agents"):
        if base.is_dir():
            for p in sorted(base.rglob("*")):
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
    tags = [sanitize_ascii(t) for t in normalize_tags(fields)]
    scope = normalize_scope(fields)
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


RESERVED_TOPIC_HEADINGS = ("Current State", "Decision Log")
DECISION_HEADING_RE = re.compile(r"^[A-Z0-9-]+-D\d{2}\b")


def _topic_headings(path: Path) -> list[str]:
    """H2 headings of one topic file, with the H3 decision-log fallback.

    ``Current State`` and ``Decision Log`` are the contract sections, not
    routing topics, so they are skipped. When a file carries no other ``##``
    heading the deeper ``###`` headings are used instead - but the decision-log
    entries themselves (``AUTH-D01`` style IDs) are never sections.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    in_fm = 0
    h2: list[str] = []
    h3: list[str] = []
    for line in text.splitlines():
        if line.strip() == "---":
            in_fm = 1 - in_fm
            continue
        if in_fm:
            continue
        if re.match(r"^##\s+\S", line) and not re.match(r"^###", line):
            heading = line.lstrip("#").strip()
            if heading not in RESERVED_TOPIC_HEADINGS:
                h2.append(heading)
        elif re.match(r"^###\s+\S", line):
            h3.append(line.lstrip("#").strip())
    if h2:
        return h2
    return [h for h in h3 if not DECISION_HEADING_RE.match(h)]


def _topic_tags(path: Path) -> list[str]:
    fields = parse_front_matter(path.read_text(encoding="utf-8"))
    return [sanitize_ascii(t) for t in normalize_tags(fields)]


def _reserved_name(name: str) -> bool:
    """Names under docs/ that are not topic docs.

    The generated index, the human landing README, and every underscore-
    prefixed name are reserved (matches the spec-builder reserved-name
    contract); everything else is a legitimate topic.
    """
    return name == "_topics.md" or name == "README.md" or name.startswith("_")


def _topic_file_entry(root: Path, path: Path) -> dict:
    """One nested topic file: full path, covers, sections."""
    return {
        "path": path.relative_to(root).as_posix(),
        "covers": _topic_tags(path),
        "sections": _topic_headings(path),
    }


def build_topics_index(root: Path) -> str:
    """Scan docs/ for topic files/folders and render the AI routing index."""
    docs = root / "docs"
    entries: list[tuple[str, str, dict]] = []
    if docs.is_dir():
        for entry in sorted(docs.iterdir()):
            name = entry.name
            if _reserved_name(name):
                continue
            if entry.is_file() and entry.suffix == ".md":
                tags = _topic_tags(entry)
                sections = _topic_headings(entry)
                rel = entry.relative_to(root).as_posix()
                entries.append(
                    (
                        name,
                        rel,
                        {
                            "path": rel,
                            "covers": tags,
                            "sections": sections,
                        },
                    )
                )
            elif entry.is_dir():
                sub = sorted(entry.glob("*.md"))
                tags: list[str] = []
                files = []
                for f in sub:
                    detail = _topic_file_entry(root, f)
                    for t in detail["covers"]:
                        if t not in tags:
                            tags.append(t)
                    files.append(detail)
                if tags or files:
                    rel = entry.relative_to(root).as_posix() + "/"
                    entries.append(
                        (
                            name,
                            rel,
                            {
                                "path": rel,
                                "covers": tags,
                                "files": files,
                            },
                        )
                    )
    lines = [
        "# Topic Index (`_topics.md`)",
        "",
        "> [!NOTE]",
        "> Auto-generated by `sync-docs` (`python .agents/scripts/devagent/main.py map sync-docs`).",
        "> Do not edit by hand - re-run `sync-docs` after changing topic docs.",
        "",
    ]
    for name, _, data in entries:
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"  path: {data['path']}")
        lines.append(
            f"  covers: {', '.join(data['covers']) if data['covers'] else '(none)'}"
        )
        if "files" in data:
            lines.append("  files:")
            for f in data["files"]:
                lines.append(f"    - {f['path']}")
                fc = ", ".join(f["covers"]) if f["covers"] else "(none)"
                lines.append(f"      covers: {fc}")
                if f["sections"]:
                    lines.append("      sections:")
                    for s in f["sections"]:
                        lines.append(f"        - {s}")
        elif data.get("sections"):
            lines.append("  sections:")
            for s in data["sections"]:
                lines.append(f"    - {s}")
        lines.append("")
    return "\n".join(lines)


def sync_docs(root: Path) -> Path:
    """Rebuild the AI topic index at docs/_topics.md from the docs/ topic layout."""
    content = build_topics_index(root)
    out = root / "docs" / "_topics.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8", newline="\n")
    return out


def topics_index_is_fresh(root: Path) -> tuple[bool, Path]:
    """Compare the on-disk docs/_topics.md with a fresh in-memory rebuild."""
    out = root / "docs" / "_topics.md"
    if not out.is_file():
        return False, out
    try:
        current = out.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False, out
    return current == build_topics_index(root), out


def build_map(root: Path, skills: list[Path], snapshot: str, generated: str) -> str:
    lines: list[str] = []
    lines.append("# Workspace Agent Map (`MAP.md`)")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> This file is auto-generated by the dev-agent runtime")
    lines.append("> (`python .agents/scripts/devagent/main.py map`).")
    lines.append(
        "> Do not modify this file manually - update individual SKILL.md frontmatters instead."
    )
    lines.append("")
    lines.append(f"- Generated: {generated}")
    lines.append(f"- Snapshot: {snapshot}")
    lines.append("")

    agents_dir = root / ".agents" / "agents"
    agent_files = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    if agent_files:
        lines.append("## Personas & Roles")
        lines.append("")
        lines.append(
            "| Persona | Description | Required Skills | Activation Trigger | Source File |"
        )
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for p in agent_files:
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


def _root_from_args(args: list[str]) -> Path | None:
    for i, arg in enumerate(args):
        if arg == "--root" and i + 1 < len(args):
            return Path(args[i + 1])
        if arg.startswith("--root="):
            return Path(arg.split("=", 1)[1])
    return None


def main() -> int:
    if "sync-docs" in sys.argv[1:]:
        root = _root_from_args(sys.argv[1:]) or find_root()
        if "--check" in sys.argv[1:]:
            fresh, _out = topics_index_is_fresh(root)
            if fresh:
                print("docs/_topics.md is fresh")
                return 0
            print(
                "docs/_topics.md is stale - run "
                "`python .agents/scripts/devagent/main.py map sync-docs`"
            )
            return 1
        out = sync_docs(root)
        print(f"synced {out}")
        return 0
    root = find_root()
    force = "--force" in sys.argv[1:]
    map_file = map_path(root)
    skills = scan_skills(root)
    sources = indexed_sources(root)

    if not force and is_fresh(root, map_file, sources):
        print(FRESH_MSG)
        return 0

    snapshot = snapshot_of(sources)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = build_map(root, skills, snapshot, generated)
    map_file.parent.mkdir(parents=True, exist_ok=True)
    map_file.write_text(content, encoding="utf-8", newline="\n")
    print(REGEN_MSG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
