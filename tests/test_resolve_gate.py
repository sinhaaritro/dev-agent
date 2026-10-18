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
    def test_blocking_noni_autonomous_resolves_and_logs(self):
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
        self.assertTrue(self.gate_log().exists())
        text = self.gate_log().read_text(encoding="utf-8")
        self.assertIn("which cache?", text)
        self.assertIn("Choice made: A", text)
        self.assertFalse(self.escalation().exists())

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
