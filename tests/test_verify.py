"""Unit tests for the verification-runner engine (verify.py).

Covers spec 002 TASK-03: root-cwd execution, the executor-free approval
fingerprint, the per-task hash evidence block (MET / STALE / NO-EVIDENCE),
and the doctor / status / report subcommands.

Each test runs in a self-contained git sandbox (its own AGENTS.md + .agents),
so verify.find_root() resolves to the sandbox, not the engine's own repo.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / ".agents" / "skills" / "verification-runner" / "scripts" / "verify.py"

_spec = importlib.util.spec_from_file_location("verify", ENGINE)
assert _spec is not None and _spec.loader is not None
verify = importlib.util.module_from_spec(_spec)
sys.modules["verify"] = verify
_spec.loader.exec_module(verify)

VERIFY_SCRIPT = REPO / ".agents" / "skills" / "verification-runner" / "scripts" / "verify.py"


def _sandbox(tmp: Path) -> Path:
    """A self-contained git repo with its own AGENTS.md + .agents.

    The .agents marker keeps find_root() from walking up past the sandbox to
    the engine's own repo (its CWD-walk would otherwise find the real
    AGENTS.md first). A main branch lets doctor precondition 9 pass.
    """
    (tmp / "AGENTS.md").write_text(
        "# Test\n\n## Commands\n\n- Build: python -m compileall .\n"
        "- Test: python -m unittest\n- Lint: true\n",
        encoding="utf-8",
    )
    (tmp / "specs").mkdir()
    (tmp / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    script_dir = tmp / ".agents" / "skills" / "verification-runner" / "scripts"
    script_dir.mkdir(parents=True)
    shutil.copy2(VERIFY_SCRIPT, script_dir / "verify.py")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", "init"], cwd=tmp, check=True
    )
    return tmp


def _task_file(tmp: Path) -> Path:
    path = tmp / "specs" / "007-TASK-01-do-things.md"
    path.write_text(
        "# TASK 007-01 — do things\n\n"
        "## Role & rules\nImplement only this task.\n\n"
        "## Project overview\nA sandbox.\n\n"
        "## Task\nDo things.\n\n"
        "### Progress\n- [ ] do it\n\n"
        "## Owns\n- `src.py`\n\n"
        "## Reads / Context (read-only)\n- none\n\n"
        "## Skills to use\n- verification-runner\n\n"
        "## Upstream interfaces\n```python\ndef find_root() -> Path\n```\n\n"
        "## Verification\n```bash\npython -c \"print('MARKER')\"\n```\n"
        "**Expect:** `MARKER`\n",
        encoding="utf-8",
    )
    return path


def _spec_file(tmp: Path) -> Path:
    path = tmp / "specs" / "007-SPEC-do-things.md"
    path.write_text(
        "# 007: Do things\n\n"
        "Status: COMPILED | Date: 2026-09-26\n\n"
        "## 1. Goal\nDo things.\n\n"
        "## 5. Tasks & Outcomes\n\n"
        "### Task 1: do things\n"
        "- Depends On: None\n"
        '- Verify: `python -c "print(\'MARKER\')"`\n'
        "- Expect: MARKER\n",
        encoding="utf-8",
    )
    return path


def _ns(**kwargs):
    return argparse.Namespace(**kwargs)


def _evidence_for(tmp: Path, task_file: Path) -> dict:
    files = {
        str(p.relative_to(tmp)): verify._file_hash(p)
        for p in verify._owned_files(task_file, tmp)
    }
    return {"at": "2026-01-01T00:00:00", "files": files}


class SandboxCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        _sandbox(self.tmp)
        self._orig_cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._orig_cwd)


class FingerprintTest(unittest.TestCase):
    def test_executor_dropped(self):
        a = verify.command_fingerprint("cmd", "exp", "/root")
        b = verify.command_fingerprint("cmd", "exp", "/root", executor="human")
        c = verify.command_fingerprint("cmd", "exp", "/root", executor="coder")
        self.assertEqual(a, b)
        self.assertEqual(a, c)

    def test_fields_affect_fingerprint(self):
        base = verify.command_fingerprint("cmd", "exp", "/root")
        self.assertNotEqual(base, verify.command_fingerprint("cmd2", "exp", "/root"))
        self.assertNotEqual(base, verify.command_fingerprint("cmd", "exp2", "/root"))
        self.assertNotEqual(base, verify.command_fingerprint("cmd", "exp", "/other"))


class EvidenceStatusTest(SandboxCase):
    def setUp(self):
        super().setUp()
        self.task_file = _task_file(self.tmp)

    def test_no_evidence_when_absent(self):
        self.assertIsNone(verify.read_evidence(self.task_file))
        self.assertEqual(verify.status(self.task_file), "NO-EVIDENCE")

    def test_met_when_hashes_match(self):
        verify._write_evidence(self.task_file, _evidence_for(self.tmp, self.task_file))
        self.assertEqual(verify.status(self.task_file), "MET")

    def test_stale_when_owned_file_changes(self):
        verify._write_evidence(self.task_file, _evidence_for(self.tmp, self.task_file))
        (self.tmp / "src.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.assertEqual(verify.status(self.task_file), "STALE")

    def test_read_evidence_roundtrip(self):
        verify._write_evidence(self.task_file, _evidence_for(self.tmp, self.task_file))
        data = verify.read_evidence(self.task_file)
        self.assertIsNotNone(data)
        self.assertIn("src.py", data["files"])

    def test_missing_owned_file_is_stale(self):
        verify._write_evidence(self.task_file, _evidence_for(self.tmp, self.task_file))
        (self.tmp / "src.py").unlink()
        self.assertEqual(verify.status(self.task_file), "STALE")


class RunEvidenceTest(SandboxCase):
    def test_run_writes_hash_evidence_on_pass(self):
        _task_file(self.tmp)
        state_dir = self.tmp / "specs" / "temp"
        rc = verify.cmd_run(
            _ns(
                command='python -c "print(\'MARKER\')"',
                task_id="007-Task 1",
                expect="MARKER",
                lane=None,
                timeout=60,
                hypothesis=None,
                options=None,
                suggest=False,
                state_dir=state_dir,
            )
        )
        self.assertEqual(rc, 0)
        tf = self.tmp / "specs" / "007-TASK-01-do-things.md"
        evidence = verify.read_evidence(tf)
        self.assertIsNotNone(evidence)
        self.assertIn("files", evidence)
        self.assertIn("src.py", evidence["files"])
        self.assertEqual(verify.status(tf), "MET")


class StatusCommandTest(SandboxCase):
    def test_status_on_task_file_prints_derived(self):
        task_file = _task_file(self.tmp)
        verify._write_evidence(task_file, _evidence_for(self.tmp, task_file))
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_status(_ns(task_id=str(task_file), state_dir=self.tmp))
        self.assertEqual(rc, 0)
        self.assertIn("state: MET", buf.getvalue())

    def test_status_without_evidence(self):
        task_file = _task_file(self.tmp)
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_status(_ns(task_id=str(task_file), state_dir=self.tmp))
        self.assertEqual(rc, 0)
        self.assertIn("state: NO-EVIDENCE", buf.getvalue())


class DoctorTest(SandboxCase):
    def setUp(self):
        super().setUp()
        self.spec = _spec_file(self.tmp)
        _task_file(self.tmp)
        fp = verify.command_fingerprint('python -c "print(\'MARKER\')"', "MARKER", str(self.tmp))
        (self.tmp / "specs" / "007-APPROVALS-do-things.json").write_text(
            json.dumps(
                {
                    "spec": "007",
                    "approvals": [
                        {
                            "task": "Task 1",
                            "fingerprint": fp,
                            "command": 'python -c "print(\'MARKER\')"',
                            "expect": "MARKER",
                            "cwd": str(self.tmp),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_doctor_all_pass(self):
        self.assertEqual(verify.doctor(self.spec), [])

    def test_doctor_detects_uncompiled_spec(self):
        self.spec.write_text(
            self.spec.read_text(encoding="utf-8").replace("COMPILED", "DRAFTED"),
            encoding="utf-8",
        )
        gaps = verify.doctor(self.spec)
        self.assertTrue(any(g.startswith("4:") for g in gaps))

    def test_doctor_detects_missing_task_file(self):
        (self.tmp / "specs" / "007-TASK-01-do-things.md").unlink()
        gaps = verify.doctor(self.spec)
        self.assertTrue(any(g.startswith("5:") for g in gaps))

    def test_doctor_detects_unapproved_command(self):
        (self.tmp / "specs" / "007-APPROVALS-do-things.json").write_text(
            json.dumps({"spec": "007", "approvals": []}), encoding="utf-8"
        )
        gaps = verify.doctor(self.spec)
        self.assertTrue(any(g.startswith("7:") for g in gaps))

    def test_doctor_detects_not_compiled(self):
        text = self.spec.read_text(encoding="utf-8")
        self.spec.write_text(text.replace("Status: COMPILED", "Status: DRAFTED"), encoding="utf-8")
        gaps = verify.doctor(self.spec)
        self.assertTrue(any(g.startswith("4:") for g in gaps))


class ReportTest(SandboxCase):
    def test_report_writes_group_report(self):
        spec = _spec_file(self.tmp)
        task_file = _task_file(self.tmp)
        verify._write_evidence(task_file, _evidence_for(self.tmp, task_file))
        path = verify.report(spec)
        self.assertEqual(path.name, "007-REPORT-do-things.md")
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("## Task Status", text)
        self.assertIn("Task 1: MET", text)
        self.assertIn("## Review", text)
        self.assertIn("Task 1: PASS", text)


class ShellCommandTest(SandboxCase):
    """verify.py must shell-execute a command that uses shell syntax (pipes,
    boolean operators, command substitution) instead of a plain argv — a
    command like ``a && b`` or ``test -z \"$(grep ...)\"`` cannot run without a
    shell. Plain argv commands are unchanged."""

    def test_uses_shell_detection(self):
        self.assertTrue(verify.uses_shell("a && b"))
        self.assertTrue(verify.uses_shell("a || b"))
        self.assertTrue(verify.uses_shell("echo hi | grep h"))
        self.assertTrue(verify.uses_shell('test -z "$(grep -rln x docs/)"'))
        self.assertTrue(verify.uses_shell("a; b"))
        self.assertTrue(verify.uses_shell("a `cmd` b"))
        self.assertFalse(verify.uses_shell('python -m unittest discover -s tests'))
        self.assertFalse(verify.uses_shell('echo "hello world"'))

    def test_run_executes_shell_command(self):
        _task_file(self.tmp)
        state_dir = self.tmp / "specs" / "temp"
        # "true && echo SHELLMARKER" needs a shell: as argv, `true && echo`
        # would try to run an executable literally named "&&".
        rc = verify.cmd_run(
            _ns(
                command="true && echo SHELLMARKER",
                task_id="007-Task 1",
                expect="SHELLMARKER",
                lane=None,
                timeout=60,
                hypothesis=None,
                options=None,
                suggest=False,
                state_dir=state_dir,
            )
        )
        self.assertEqual(rc, 0)
        self.assertEqual(verify.status(self.tmp / "specs" / "007-TASK-01-do-things.md"), "MET")

    def test_run_executes_command_substitution(self):
        # The TASK-15 verify shape: a grep whose output feeds a test via a
        # command substitution — only a shell resolves the "$(...)".
        (self.tmp / "docs").mkdir()
        (self.tmp / "docs" / "001-x.md").write_text("plan is real\n", encoding="utf-8")
        cmd = (
            'grep -q "plan" docs/001-x.md && '
            'test -z "$(grep -rln "OLD-STEP" docs/)" && echo REFDOCS-OK'
        )
        state_dir = self.tmp / "specs" / "temp"
        rc = verify.cmd_run(
            _ns(
                command=cmd,
                task_id="007-Task 1",
                expect="REFDOCS-OK",
                lane=None,
                timeout=60,
                hypothesis=None,
                options=None,
                suggest=False,
                state_dir=state_dir,
            )
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
