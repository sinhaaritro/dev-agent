"""Drift test: the canonical phase + status sets appear, the old ones are gone.

Covers spec 002 TASK-14. The framework renumbered the phases and collapsed the
lifecycle to a single `Status:` receipt; this test guards against drift back to
the old model in the files that are already migrated (`.agents`, `README.md`,
`AGENTS.md`). The `docs/` reference series is updated by TASK-15 and is checked
by a dedicated assertion there, so it is excluded here.

Canonical sets (the single source of truth is `promote_spec.CANONICAL_STATUSES`
and the phase flow documented in phase-protocol):
    phases   = 1-Plan, 1.5-Vetting, 2-Handoff, 3-Build, 4-Review, 4.5-Sign-off, 5-Done
    statuses = DRAFTED, COMPILED, BUILDING, BUILT, REVIEWED, COMPLETED,
               PLAN_REVISION_REQUIRED, REVIEW_REVISION_REQUIRED, ESCALATED, ABORTED
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

CANONICAL_PHASES = [
    "1-Plan",
    "1.5-Vetting",
    "2-Handoff",
    "3-Build",
    "4-Review",
    "4.5-Sign-off",
    "5-Done",
]
CANONICAL_STATUSES = sorted(_promote_spec.CANONICAL_STATUSES)
# The old phase names that must be gone (superseded by the canonical set).
OLD_PHASES = ["1.5-Handoff", "1.5-Consensus", "4.5-Consensus", "2-Build", "3-Review"]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _agent_sources() -> list[tuple[str, str]]:
    """(label, text) for every markdown file under .agents/ (rules + skills)."""
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
    return out


class CanonicalPhaseSetTest(unittest.TestCase):
    def test_canonical_statuses_match_engine(self):
        """The test's status set is exactly the engine's canonical set."""
        expected = {
            "DRAFTED",
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

    def test_each_canonical_phase_appears_somewhere(self):
        """Every canonical phase name is documented in .agents or AGENTS.md."""
        sources = _agent_sources() + _root_sources()
        for phase in CANONICAL_PHASES:
            self.assertTrue(
                any(phase in text for _, text in sources),
                f"canonical phase {phase!r} not found in .agents / AGENTS.md",
            )

    def test_each_canonical_status_appears_somewhere(self):
        """Every canonical status is referenced (the engine knows all of them)."""
        sources = _agent_sources() + _root_sources()
        for status in CANONICAL_STATUSES:
            self.assertTrue(
                any(status in text for _, text in sources),
                f"canonical status {status!r} not found in .agents / AGENTS.md",
            )


class NoPhaseFieldTest(unittest.TestCase):
    """No `Phase:` header field survives (collapsed into the single `Status:`)."""

    def _violations(self) -> list[str]:
        hits = []
        for label, text in _agent_sources() + _root_sources():
            for i, line in enumerate(text.splitlines(), start=1):
                # A `Phase:` used as a field/header (line-start or ` <Phase>`),
                # not a `Status:` or prose mention of the word "phase".
                if re.match(r"^\s*Phase\s*:", line) or re.search(r"<Phase\s*>", line):
                    hits.append(f"{label}:{i}: {line.strip()}")
        return hits

    def test_no_phase_field_in_agents_or_root(self):
        self.assertEqual(self._violations(), [], "a `Phase:` field still exists:\n" + "\n".join(self._violations()))


class NoOldPhasesTest(unittest.TestCase):
    """The old phase names are gone from .agents, README.md, AGENTS.md."""

    def test_no_old_phase_names(self):
        hits = []
        for label, text in _agent_sources() + _root_sources():
            for old in OLD_PHASES:
                # Word-boundary match so "3-Review" does not hit "3-Build" etc.
                if re.search(r"\b" + re.escape(old) + r"\b", text):
                    hits.append(f"{label}: {old!r}")
        self.assertEqual(
            hits, [],
            "old phase name(s) still present in .agents / AGENTS.md:\n" + "\n".join(hits),
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
            cwd=REPO, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
