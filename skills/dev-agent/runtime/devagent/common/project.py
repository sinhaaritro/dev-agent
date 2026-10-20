"""Parse the project's ``AGENTS.md`` Commands block into area-scoped commands.

A single-stack project keeps one flat list (``- Build: ...`` / ``- Test: ...``)
and gets one implicit area named ``default``. A mixed-stack project groups its
commands under ``### <area>`` headings, each carrying its own commands and an
optional ``- Skills:`` line naming the skills its coders should read:

    ## Commands

    ### astro-site
    - Build: npm run build
    - Test: npm run test
    - Skills: astro-framework, shadcn

    ### python-scripts
    - Build: python -m compileall -q scripts

Both engines (``verify`` for command resolution, ``specs`` for the area lint)
read the same parser so compile-time and run-time never disagree.
"""

import re

COMMAND_LABELS = ("Build", "Test", "Lint")
DEFAULT_AREA = "default"
AREA_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
COMMAND_RE = re.compile(r"^\s*-\s*(Build|Test|Lint)\s*:\s*(.+)$")
SKILLS_RE = re.compile(r"^\s*-\s*Skills\s*:\s*(.+)$")


def _commands_section(text: str) -> list[str]:
    """The lines of the ``## Commands`` section (up to the next ``## ``)."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+Commands\s*$", line.strip()):
            start = i + 1
            break
    if start is None:
        return []
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^##\s", lines[j].strip()):
            end = j
            break
    return lines[start:end]


def parse_command_areas(text: str) -> dict[str, dict]:
    """Return ``{area: {"commands": [(label, command)], "skills": [...]}}``.

    Placeholder commands (``<command>``) are skipped. No ``###`` heading means
    a single implicit ``default`` area (the backwards-compatible shape). An
    area with only a ``Skills:`` line still appears (with an empty command
    list) so the area lint can report it.
    """
    areas: dict[str, dict] = {}
    current = DEFAULT_AREA

    def bucket(area: str) -> dict:
        return areas.setdefault(area, {"commands": [], "skills": []})

    for line in _commands_section(text):
        head = AREA_HEADING_RE.match(line.strip())
        if head:
            current = head.group(1).strip()
            bucket(current)
            continue
        cmd = COMMAND_RE.match(line)
        if cmd and cmd.group(2).strip() not in ("", "<command>"):
            bucket(current)["commands"].append((cmd.group(1), cmd.group(2).strip()))
            continue
        skills = SKILLS_RE.match(line)
        if skills:
            names = [
                name.strip()
                for name in re.split(r"[,\s]+", skills.group(1))
                if name.strip()
            ]
            bucket(current)["skills"].extend(names)
    return areas


def declared_areas(text: str) -> list[str]:
    """Area names declared with an ``###`` heading under ``## Commands``.

    A flat (heading-less) Commands block declares no named areas, which keeps
    the multi-area lint dormant for single-stack projects.
    """
    return [
        line.strip()[3:].strip()
        for line in _commands_section(text)
        if AREA_HEADING_RE.match(line.strip())
    ]


def area_skills(text: str, area: str) -> list[str]:
    """The ``Skills:`` list declared under one area heading (``[]`` if none)."""
    current = None
    skills: list[str] = []
    for line in _commands_section(text):
        head = AREA_HEADING_RE.match(line.strip())
        if head:
            current = head.group(1).strip()
            continue
        if current != area:
            continue
        match = SKILLS_RE.match(line)
        if match:
            skills.extend(
                name.strip()
                for name in re.split(r"[,\s]+", match.group(1))
                if name.strip()
            )
    return skills
