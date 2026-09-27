"""Drift test: the framework uses a single `Status:` lifecycle, not phases.

The lifecycle is one receipt — `Status:` — whose value set is owned by the engine
(`promote_spec.CANONICAL_STATUSES`). This test guards the migrated files
(`.agents`, `README.md`, `AGENTS.md`, `docs/`) against drift back to a parallel
"phase" vocabulary or the retired numbered step labels.

Canonical statuses (single source of truth: `promote_spec.CANONICAL_STATUSES`):
    DRAFTED, COMPILED, BUILDING, BUILT, REVIEWED, COMPLETED,
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

CANONICAL_STATUSES = sorted(_promote_spec.CANONICAL_STATUSES)
# The retired numbered step labels (current and older generations) — a parallel
# vocabulary that must not return to the living files.
OLD_STEP_LABELS = [
    "1-Plan",
    "1.5-Vetting",
    "2-Handoff",
    "3-Build",
    "4-Review",
    "4.5-Sign-off",
    "5-Done",
    "1.5-Handoff",
    "1.5-Consensus",
    "4.5-Consensus",
    "2-Build",
    "3-Review",
]
# The skill identifier `phase-protocol` is the only place the word "phase" survives.
_PHASE_WORD = re.compile(r"phase", re.IGNORECASE)
_PHASE_ALLOWED = re.compile(r"phase-protocol", re.IGNORECASE)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _agent_sources() -> list[tuple[str, str]]:
    """(label, text) for every markdown and Python file under .agents/."""
    agents = REPO / ".agents"
    out = []
    if agents.is_dir():
        for pattern in ("*.md", "*.py"):
            for f in sorted(agents.rglob(pattern)):
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


class NoStepLabelTest(unittest.TestCase):
    """The retired numbered step labels (1-Plan … 5-Done) are gone."""

    def test_no_step_labels(self):
        hits = []
        for label, text in _sources():
            for old in OLD_STEP_LABELS:
                if re.search(r"\b" + re.escape(old) + r"\b", text):
                    hits.append(f"{label}: {old!r}")
        self.assertEqual(
            hits, [],
            "retired step label(s) still present:\n" + "\n".join(hits),
        )


class NoPhaseWordTest(unittest.TestCase):
    """The word "phase" survives only inside the skill identifier `phase-protocol`."""

    def _violations(self) -> list[str]:
        hits = []
        for label, text in _sources():
            for i, line in enumerate(text.splitlines(), start=1):
                stripped = _PHASE_ALLOWED.sub("", line)
                if _PHASE_WORD.search(stripped):
                    hits.append(f"{label}:{i}: {line.strip()}")
        return hits

    def test_no_phase_word(self):
        self.assertEqual(
            self._violations(), [],
            "the word 'phase' survives outside `phase-protocol`:\n" + "\n".join(self._violations()),
        )


class NoPhaseFieldTest(unittest.TestCase):
    """No `Phase:` header field survives (collapsed into the single `Status:`)."""

    def _violations(self) -> list[str]:
        hits = []
        for label, text in _sources():
            for i, line in enumerate(text.splitlines(), start=1):
                if re.match(r"^\s*Phase\s*:", line) or re.search(r"<Phase\s*>", line):
                    hits.append(f"{label}:{i}: {line.strip()}")
        return hits

    def test_no_phase_field(self):
        self.assertEqual(self._violations(), [], "a `Phase:` field still exists:\n" + "\n".join(self._violations()))


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
