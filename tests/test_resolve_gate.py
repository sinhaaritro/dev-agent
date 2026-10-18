"""Unit tests for the phase-protocol gate engine (resolve_gate.py).

Covers the autonomy matrix: (blocking|non-blocking) x
(interactive|non-interactive) x (Lane-A surface) x (supervised|autonomous),
the Lane-A fail-closed exception, and the `autonomy_level` default read from
`AGENTS.md`.

The engine resolves its repo root from its own script location, so each test
patches `resolve_gate.find_root` to a throwaway sandbox and drives `main()`
with a patched `sys.argv`. Exit codes are the contract: 0 = proceed/resolved,
1 = halt for a human, 2 = fail-closed.
"""

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / ".agents" / "skills" / "phase-protocol" / "scripts" / "resolve_gate.py"

_spec = importlib.util.spec_from_file_location("resolve_gate", ENGINE)
assert _spec is not None and _spec.loader is not None
resolve_gate = importlib.util.module_from_spec(_spec)
sys.modules["resolve_gate"] = resolve_gate
_spec.loader.exec_module(resolve_gate)


class GateBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "AGENTS.md").write_text("# Test\n", encoding="utf-8")

    def run_gate(self, *argv):
        """Drive resolve_gate.main() against the sandbox; return (code, stdout)."""
        buf = io.StringIO()
        with (
            mock.patch.object(resolve_gate, "find_root", return_value=self.root),
            mock.patch.object(sys, "argv", ["resolve_gate.py", *argv]),
            contextlib.redirect_stdout(buf),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            code = resolve_gate.main()
        return code, buf.getvalue()

    def gate_log(self):
        return self.root / "specs" / "temp" / "gate-log.md"

    def escalation(self):
        return self.root / "specs" / "temp" / "escalation.md"

    def write_draft(self, with_gates: bool = True) -> Path:
        path = self.root / "specs" / "temp" / "draft-plan.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (
            "# [SPEC-ID]: Gate sandbox\n\n"
            "Status: DRAFTED | Date: 2026-10-18\n\n"
            "## 1. Goal & Context\n\nx\n\n"
        )
        if with_gates:
            body += "## 6. Gates\n\n_(empty)_\n\n"
        body += "## 7. Verification Commands\n\n- Build Command: x\n"
        path.write_text(body, encoding="utf-8")
        return path


class NonBlockingTest(GateBase):
    def test_non_blocking_proceeds_in_both_sessions(self):
        for session in ("interactive", "non-interactive"):
            code, out = self.run_gate(
                "--gate", "non-blocking", "--session", session, "--lane", "C"
            )
            self.assertEqual(code, 0, out)
            self.assertIn("PROCEED", out)
        self.assertFalse(self.gate_log().exists())
        self.assertFalse(self.escalation().exists())


class InteractiveTest(GateBase):
    def test_blocking_interactive_halts(self):
        code, out = self.run_gate(
            "--gate", "blocking", "--session", "interactive", "--lane", "B"
        )
        self.assertEqual(code, 1, out)
        self.assertIn("HALT", out)
        self.assertFalse(self.gate_log().exists())
        self.assertFalse(self.escalation().exists())

    def test_session_and_lane_are_case_insensitive(self):
        # The documented forms ("--session Interactive", "--lane A") must not
        # be mistaken for the fail-closed code.
        code, out = self.run_gate(
            "--gate", "blocking", "--session", "Interactive", "--lane", "c"
        )
        self.assertEqual(code, 1, out)


class SupervisedFailClosedTest(GateBase):
    def test_blocking_noni_supervised_fails_closed(self):
        code, out = self.run_gate(
            "--gate",
            "blocking",
            "--session",
            "non-interactive",
            "--lane",
            "B",
            "--autonomy",
            "supervised",
            "--question",
            "q",
            "--options",
            "A (Recommended): x; B: y",
        )
        self.assertEqual(code, 2, out)
        self.assertIn("FAIL-CLOSED", out)
        self.assertTrue(self.escalation().exists())
        self.assertFalse(self.gate_log().exists())


class AutonomousResolveTest(GateBase):
    def test_blocking_noni_autonomous_resolves_into_gates_section(self):
        draft = self.write_draft()
        code, out = self.run_gate(
            "--gate",
            "blocking",
            "--session",
            "non-interactive",
            "--lane",
            "B",
            "--autonomy",
            "autonomous",
            "--question",
            "which cache?",
            "--options",
            "A (Recommended): redis; B: memcached",
            "--choice",
            "A",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("RESOLVED", out)

        text = draft.read_text(encoding="utf-8")
        self.assertIn("which cache?", text)
        self.assertIn("Choice made: A", text)
        gates = text.split("## 6. Gates", 1)[1].split("## 7.", 1)[0]
        self.assertIn("Choice made: A", gates)
        self.assertIn("### Gate ", gates)
        self.assertFalse(self.gate_log().exists())
        self.assertFalse(self.escalation().exists())

    def test_appends_a_second_entry_without_losing_the_first(self):
        draft = self.write_draft()
        args = (
            "--gate", "blocking", "--session", "non-interactive", "--lane", "B",
            "--autonomy", "autonomous", "--question", "q1", "--options", "A: x; B: y",
        )
        self.assertEqual(self.run_gate(*args)[0], 0)
        self.assertEqual(self.run_gate(*args)[0], 0)
        text = draft.read_text(encoding="utf-8")
        self.assertEqual(text.count("### Gate "), 2)
        self.assertEqual(text.count("Choice made:"), 2)
        self.assertIn("## 7. Verification Commands", text)

    def test_spec_argument_targets_that_file(self):
        spec = self.root / "specs" / "001-SPEC-x.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(
            "# Spec\n\nStatus: COMPILED\n\n## 6. Gates\n\n_(empty)_\n\n## 7. V\n",
            encoding="utf-8",
        )
        code, out = self.run_gate(
            "--gate", "blocking", "--session", "non-interactive", "--lane", "B",
            "--autonomy", "autonomous", "--question", "pick", "--options", "A: x; B: y",
            "--spec", "specs/001-SPEC-x.md",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("Choice made: A", spec.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "specs" / "temp" / "draft-plan.md").exists())

    def test_active_spec_wins_over_a_stale_draft(self):
        self.write_draft()
        spec = self.root / "specs" / "001-SPEC-x.md"
        spec.write_text("# Spec\n\nStatus: BUILDING\n\n## 6. Gates\n", encoding="utf-8")
        code, out = self.run_gate(
            "--gate", "blocking", "--session", "non-interactive", "--lane", "B",
            "--autonomy", "autonomous", "--question", "q", "--options", "A: x; B: y",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("Choice made: A", spec.read_text(encoding="utf-8"))
        draft = self.root / "specs" / "temp" / "draft-plan.md"
        self.assertNotIn("Choice made", draft.read_text(encoding="utf-8"))

    def test_creates_the_gates_section_when_missing(self):
        draft = self.write_draft(with_gates=False)
        code, out = self.run_gate(
            "--gate", "blocking", "--session", "non-interactive", "--lane", "B",
            "--autonomy", "autonomous", "--question", "q", "--options", "A: x; B: y",
        )
        self.assertEqual(code, 0, out)
        text = draft.read_text(encoding="utf-8")
        self.assertIn("## 6. Gates", text)
        self.assertIn("Choice made: A", text)

    def test_no_target_fails_closed_without_scratch_log(self):
        code, out = self.run_gate(
            "--gate", "blocking", "--session", "non-interactive", "--lane", "B",
            "--autonomy", "autonomous", "--question", "q", "--options", "A: x; B: y",
        )
        self.assertEqual(code, 2, out)
        self.assertIn("no plan or spec", out)
        self.assertFalse(self.gate_log().exists())

    def test_lane_a_surface_never_resolves_autonomously(self):
        # Surface via --lane-a-surface ...
        code, _ = self.run_gate(
            "--gate",
            "blocking",
            "--session",
            "non-interactive",
            "--lane",
            "B",
            "--autonomy",
            "autonomous",
            "--lane-a-surface",
        )
        self.assertEqual(code, 2)
        self.assertFalse(self.gate_log().exists())

    def test_lane_a_always_fails_closed(self):
        # ... and implicit via --lane A.
        code, _ = self.run_gate(
            "--gate",
            "blocking",
            "--session",
            "non-interactive",
            "--lane",
            "A",
            "--autonomy",
            "autonomous",
        )
        self.assertEqual(code, 2)


class AutonomyDefaultTest(GateBase):
    def test_default_is_supervised(self):
        code, _ = self.run_gate(
            "--gate", "blocking", "--session", "non-interactive", "--lane", "B"
        )
        self.assertEqual(code, 2)

    def test_autonomy_level_read_from_agents_md(self):
        (self.root / "AGENTS.md").write_text(
            "# Test\nautonomy_level: autonomous\n", encoding="utf-8"
        )
        self.assertEqual(resolve_gate.read_autonomy(self.root), "autonomous")
        self.write_draft()
        code, _ = self.run_gate(
            "--gate", "blocking", "--session", "non-interactive", "--lane", "B"
        )
        self.assertEqual(code, 0)


class UsageTest(GateBase):
    def test_parse_options_splits_and_defaults(self):
        self.assertEqual(
            resolve_gate.parse_options("A (Recommended): x; B: y"),
            ["A (Recommended): x", "B: y"],
        )
        self.assertEqual(
            resolve_gate.parse_options(""), ["A (Recommended): <not provided>"]
        )

    def test_invalid_gate_argument_exits(self):
        with self.assertRaises(SystemExit):
            self.run_gate(
                "--gate", "sometimes", "--session", "interactive", "--lane", "B"
            )

    def test_invalid_lane_argument_exits(self):
        with self.assertRaises(SystemExit):
            self.run_gate(
                "--gate", "blocking", "--session", "interactive", "--lane", "Z"
            )


if __name__ == "__main__":
    unittest.main()
