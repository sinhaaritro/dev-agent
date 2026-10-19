"""The single `Status:` lifecycle: canonical set + documented commands.

The lifecycle is one receipt — `Status:` — whose value set is owned by the engine
(`promote_spec.CANONICAL_STATUSES`). This test asserts the canonical set and that
`AGENTS.md` carries the real Build/Test/Lint commands.

Canonical statuses (single source of truth: `promote_spec.CANONICAL_STATUSES`):
    DRAFTED, APPROVED, PROVISIONAL, COMPILED, BUILDING, BUILT, REVIEWED,
    COMPLETED, PLAN_REVISION_REQUIRED, REVIEW_REVISION_REQUIRED, ESCALATED,
    ABORTED
"""

import importlib.util
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Import the engine's canonical status set so the test tracks the engine, not a
# hand-copied list (no drift between the two).
_ENGINE = REPO / ".agents" / "skills" / "spec-builder" / "scripts" / "promote_spec.py"
_spec = importlib.util.spec_from_file_location("promote_spec", _ENGINE)
assert _spec is not None and _spec.loader is not None
_promote_spec = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("promote_spec", _promote_spec)
_spec.loader.exec_module(_promote_spec)

CANONICAL_STATUSES = sorted(_promote_spec.CANONICAL_STATUSES)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _agent_sources() -> list[tuple[str, str]]:
    """(label, text) for every markdown file under .agents/."""
    agents = REPO / ".agents"
    out = []
    if agents.is_dir():
        for f in sorted(agents.rglob("*.md")):
            out.append((str(f.relative_to(REPO)), _read(f)))
    return out


def _root_sources() -> list[tuple[str, str]]:
    out = []
    for name in ("README.md", "AGENTS.md"):
        p = REPO / name
        if p.is_file():
            out.append((name, _read(p)))
    docs = REPO / "docs"
    if docs.is_dir():
        for f in sorted(docs.rglob("*.md")):
            if f.name == "_topics.md":  # generated index, not hand-maintained
                continue
            out.append((str(f.relative_to(REPO)), _read(f)))
    return out


def _sources() -> list[tuple[str, str]]:
    return _agent_sources() + _root_sources()


class CanonicalStatusSetTest(unittest.TestCase):
    def test_canonical_statuses_match_engine(self):
        """The test's status set is exactly the engine's canonical set."""
        expected = {
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
        }
        self.assertEqual(set(CANONICAL_STATUSES), expected)

    def test_each_canonical_status_appears_somewhere(self):
        """Every canonical status is referenced in .agents, README.md, AGENTS.md, docs/."""
        sources = _sources()
        for status in CANONICAL_STATUSES:
            self.assertTrue(
                any(status in text for _, text in sources),
                f"canonical status {status!r} not found in .agents / README.md / AGENTS.md / docs",
            )


class AgCommandsTest(unittest.TestCase):
    """AGENTS.md carries the canonical Build/Test/Lint commands (placeholders filled)."""

    def test_agents_md_commands_filled(self):
        text = _read(REPO / "AGENTS.md")
        self.assertNotIn("Build: <command>", text, "AGENTS.md Build command is still a placeholder")
        self.assertNotIn("Test: <command>", text, "AGENTS.md Test command is still a placeholder")
        self.assertNotIn("Lint: <command>", text, "AGENTS.md Lint command is still a placeholder")
        self.assertIn("compileall", text, "AGENTS.md Build command should be the compileall canonical")
        self.assertIn("unittest discover", text, "AGENTS.md Test command should be the canonical suite")

    def test_canonical_commands_resolve(self):
        """The canonical Build command actually passes in this repo."""
        import subprocess
        proc = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", ".agents", "tests"],
            cwd=REPO, capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class SpecStatusDriftTest(unittest.TestCase):
    """C4: every committed spec carries a canonical Status: receipt."""

    def test_every_spec_status_is_canonical(self):
        specs = REPO / "specs"
        self.assertTrue(specs.is_dir(), "no specs/ directory")
        offenders = []
        for path in sorted(specs.glob("*-SPEC-*.md")):
            if "-SPEC-" not in path.name:  # Windows glob is case-insensitive
                continue
            m = re.search(r"(?m)^Status:\s*(\S+)", _read(path))
            token = m.group(1) if m else ""
            if token not in CANONICAL_STATUSES:
                offenders.append(f"{path.name}: {token or 'MISSING'}")
        self.assertEqual(offenders, [], f"non-canonical spec statuses: {offenders}")



class DraftedLaneSectionsTest(unittest.TestCase):
    """H1: the Lane checklists in drafted.md match the engine's LANE_SECTIONS."""

    def _line(self, prefix):
        text = _read(
            REPO / ".agents" / "skills" / "phase-protocol" / "references" / "drafted.md"
        )
        for line in text.splitlines():
            if line.strip().startswith(prefix):
                return line
        self.fail(f"drafted.md has no line starting with {prefix!r}")

    def _section_list(self, prefix):
        line = self._line(prefix)
        self.assertIn("\u2014", line, "checklist should separate the list with an em dash")
        return line.split("\u2014")[-1]

    def test_lane_a_checklist_lists_every_enforced_section(self):
        tail = self._section_list("2. Lane A:")
        self.assertNotIn("all seven", tail)
        for n in sorted(_promote_spec.LANE_SECTIONS["A"]):
            self.assertRegex(
                tail, rf"\b{n}\b", f"section {n} missing from the Lane A checklist"
            )

    def test_lane_b_checklist_lists_its_enforced_sections(self):
        tail = self._section_list("1. Lane B:")
        for n in sorted(_promote_spec.LANE_SECTIONS["B"]):
            self.assertRegex(
                tail, rf"\b{n}\b", f"section {n} missing from the Lane B checklist"
            )


class SpecFilenameConventionTest(unittest.TestCase):
    """H2: shipped docs use the single NNN-SPEC-<slug>.md convention."""

    def test_no_wrong_nnn_spec_placeholder(self):
        offenders = []
        for root in (REPO / "skills", REPO / ".agents" / "rules"):
            for path in sorted(root.rglob("*.md")):
                if "specs/<NNN>-<SPEC>-" in _read(path):
                    offenders.append(str(path.relative_to(REPO)))
        self.assertEqual(offenders, [], f"wrong <NNN>-<SPEC> form in: {offenders}")


if __name__ == "__main__":
    unittest.main()
