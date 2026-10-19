"""Unit tests for the shared runtime helpers (common.hashing / common.specparse).

These lock the compile/run contracts that used to be duplicated: the approval
fingerprint and the section-5 task parser.
"""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "skills" / "dev-agent" / "runtime" / "devagent"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from common.hashing import APPROVAL_CWD, approval_fingerprint
from common.specparse import (
    is_noop_verify,
    parse_target_files,
    parse_tasks,
    section5_tasks,
    spec_group_files,
    spec_identity,
    status_token,
    status_token_file,
    task_file_for,
)


class ApprovalFingerprintTest(unittest.TestCase):
    def test_is_the_documented_payload(self):
        payload = "pytest -q|OK|."
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.assertEqual(approval_fingerprint("pytest -q", "OK", "."), expected)
        self.assertEqual(APPROVAL_CWD, ".")

    def test_none_safe_and_stripped(self):
        self.assertEqual(
            approval_fingerprint("  pytest  ", None),
            approval_fingerprint("pytest", "", "."),
        )


class ParseTargetFilesTest(unittest.TestCase):
    def test_ops_inherit_and_backticks_are_stripped(self):
        entries = parse_target_files("[MODIFY] a.py, `b.py`, [NEW] c.py")
        self.assertEqual(
            entries,
            [
                {"op": "MODIFY", "path": "a.py"},
                {"op": "MODIFY", "path": "b.py"},
                {"op": "NEW", "path": "c.py"},
            ],
        )


class ParseTasksTest(unittest.TestCase):
    def test_parses_every_field_either_engine_reads(self):
        body = """### Task 1: add the cache

- Target Files: [NEW] src/cache.py
- Depends On: None
- Verify: `pytest -q`
- Expect: "OK"
- Outcomes: R1, R2
"""
        tasks = parse_tasks(body)
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task["num"], 1)
        self.assertEqual(task["title"], "add the cache")
        self.assertEqual(task["target_files"], [{"op": "NEW", "path": "src/cache.py"}])
        self.assertEqual(task["depends_on"], "None")
        self.assertEqual(task["verify"], "`pytest -q`")
        self.assertEqual(task["expect"], '"OK"')
        self.assertEqual(task["outcomes"], "R1, R2")

    def test_section5_uses_the_same_parser(self):
        text = "## 5. Tasks\n\n### Task 2: t\n- Depends On: Task 1\n"
        self.assertEqual(section5_tasks(text)[0]["depends_on"], "Task 1")
        self.assertEqual(section5_tasks("## 1. Goal\n"), [])


class StatusTest(unittest.TestCase):
    def test_token_ignores_trailing_metadata(self):
        text = "Status: PROVISIONAL - AUTONOMOUS DEFAULT\n"
        self.assertEqual(status_token(text), "PROVISIONAL")
        self.assertEqual(status_token("no status"), "")

    def test_file_token_tolerates_absence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.md"
            path.write_text("Status: COMPILED | Date: 2026-01-01\n", encoding="utf-8")
            self.assertEqual(status_token_file(path), "COMPILED")
            self.assertEqual(status_token_file(Path(tmp) / "missing.md"), "")


class SpecLookupTest(unittest.TestCase):
    def test_identity_group_and_task_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs = Path(tmp)
            spec = specs / "007-SPEC-cache.md"
            task = specs / "007-TASK-01-add.md"
            report = specs / "007-REPORT-cache.md"
            other = specs / "008-TASK-01-other.md"
            for path in (spec, task, report, other):
                path.write_text("# x\n", encoding="utf-8")
            self.assertEqual(spec_identity("007-SPEC-cache.md"), (7, "cache"))
            self.assertIsNone(spec_identity("007-TASK-01-add.md"))
            self.assertEqual(
                sorted(p.name for p in spec_group_files(specs, 7)),
                ["007-REPORT-cache.md", "007-SPEC-cache.md", "007-TASK-01-add.md"],
            )
            self.assertEqual(task_file_for(specs, 7, "Task 1"), task)
            self.assertEqual(task_file_for(specs, 7, "007-Task 1"), task)
            self.assertIsNone(task_file_for(specs, 7, "Task 9"))


class NoopVerifyTest(unittest.TestCase):
    def test_tautologies_are_rejected(self):
        for cmd in ("", "true", ":", "exit", "exit 0", "echo OK", "`true`"):
            self.assertTrue(is_noop_verify(cmd), cmd)

    def test_real_commands_are_kept(self):
        for cmd in ("pytest -q", "grep -o OK file.txt", "python -m unittest"):
            self.assertFalse(is_noop_verify(cmd), cmd)


if __name__ == "__main__":
    unittest.main()
