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

VERIFY_SCRIPT = (
    REPO / ".agents" / "skills" / "verification-runner" / "scripts" / "verify.py"
)


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
        "- Verify: `python -c \"print('MARKER')\"`\n"
        "- Expect: MARKER\n",
        encoding="utf-8",
    )
    return path


def _spec_with_outcomes(tmp: Path) -> Path:
    """Like _spec_file, but section 5 declares an Outcomes table: R1 is
    delivered by Task 1, R2 by no task — the fixture for the H4 observations."""
    path = tmp / "specs" / "007-SPEC-do-things.md"
    path.write_text(
        "# 007: Do things\n\n"
        "Status: COMPILED | Date: 2026-09-26\n\n"
        "## 1. Goal\nDo things.\n\n"
        "## 5. Tasks & Outcomes\n\n"
        "**Outcomes:**\n\n"
        "| ID | Outcome (what the user gets) |\n"
        "|----|------------------------------|\n"
        "| R1 | the thing works |\n"
        "| R2 | the other thing works |\n\n"
        "### Task 1: do things\n"
        "- Depends On: None\n"
        "- Outcomes: R1\n"
        "- Verify: `python -c \"print('MARKER')\"`\n"
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
                command="python -c \"print('MARKER')\"",
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


class ReferenceResolutionTest(SandboxCase):
    """H3: --spec/--task accept a spec/task id, file name, relative path, or
    absolute path (not just a concrete path)."""

    def setUp(self):
        super().setUp()
        self.spec = _spec_file(self.tmp)
        self.task_file = _task_file(self.tmp)
        verify._write_evidence(self.task_file, _evidence_for(self.tmp, self.task_file))

    def test_spec_forms(self):
        for raw in (
            "007",
            "7",
            "007-SPEC-do-things.md",
            "specs/007-SPEC-do-things.md",
            str(self.spec),
        ):
            path, err = verify.resolve_spec(raw, self.tmp)
            self.assertEqual(err, "", raw)
            self.assertEqual(path, self.spec.resolve(), raw)

    def test_spec_unknown_is_a_clear_error(self):
        path, err = verify.resolve_spec("999", self.tmp)
        self.assertIsNone(path)
        self.assertIn("no spec matches", err)

    def test_task_forms(self):
        for raw in (
            "007-Task 1",
            "007-01",
            "Task 1",
            "007-TASK-01-do-things.md",
            "specs/007-TASK-01-do-things.md",
            str(self.task_file),
        ):
            path, err = verify.resolve_task(raw, self.tmp)
            self.assertEqual(err, "", raw)
            self.assertEqual(path, self.task_file.resolve(), raw)

    def test_bare_task_ambiguous_across_specs(self):
        (self.tmp / "specs" / "002-SPEC-other.md").write_text(
            "# 002: Other\n\nStatus: COMPILED\n", encoding="utf-8"
        )
        (self.tmp / "specs" / "002-TASK-01-other.md").write_text(
            "# TASK 002-01 - other\n", encoding="utf-8"
        )
        path, err = verify.resolve_task("Task 1", self.tmp)
        self.assertIsNone(path)
        self.assertIn("ambiguous", err)

    def test_status_derives_from_task_id(self):
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_status(_ns(task_id="007-Task 1", state_dir=self.tmp))
        self.assertEqual(rc, 0)
        self.assertIn("state: MET", buf.getvalue())

    def test_status_spec_disambiguates_bare_id(self):
        (self.tmp / "specs" / "002-SPEC-other.md").write_text(
            "# 002: Other\n\nStatus: COMPILED\n", encoding="utf-8"
        )
        (self.tmp / "specs" / "002-TASK-01-other.md").write_text(
            "# TASK 002-01 - other\n", encoding="utf-8"
        )
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_status(
                _ns(task_id="Task 1", spec="007", state_dir=self.tmp)
            )
        self.assertEqual(rc, 0)
        self.assertIn("state: MET", buf.getvalue())

    def test_doctor_accepts_spec_number(self):
        buf = StringIO()
        with redirect_stdout(buf):
            verify.cmd_doctor(_ns(spec="007"))
        self.assertNotIn("cannot read spec", buf.getvalue())

    def test_report_accepts_spec_id_without_a_stray_file(self):
        verify._set_spec_status(self.spec, "BUILT")
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_report(_ns(spec="007"))
        self.assertEqual(rc, 0)
        self.assertTrue((self.tmp / "specs" / "007-REPORT-do-things.md").is_file())
        self.assertFalse((self.tmp / "007-REPORT-spec.md").exists())


class DoctorTest(SandboxCase):
    def setUp(self):
        super().setUp()
        self.spec = _spec_file(self.tmp)
        _task_file(self.tmp)
        fp = verify.command_fingerprint(
            "python -c \"print('MARKER')\"", "MARKER", str(self.tmp)
        )
        (self.tmp / "specs" / "007-APPROVALS-do-things.json").write_text(
            json.dumps(
                {
                    "spec": "007",
                    "approvals": [
                        {
                            "task": "Task 1",
                            "fingerprint": fp,
                            "command": "python -c \"print('MARKER')\"",
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
        self.spec.write_text(
            text.replace("Status: COMPILED", "Status: DRAFTED"), encoding="utf-8"
        )
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


class OutcomeObservationTest(SandboxCase):
    """H4: report() emits one R# observation per declared outcome, and a
    missing observation fails review (exit 1, no advance to REVIEWED)."""

    def setUp(self):
        super().setUp()
        self.spec = _spec_with_outcomes(self.tmp)
        task_file = _task_file(self.tmp)
        verify._write_evidence(task_file, _evidence_for(self.tmp, task_file))

    def test_one_observation_line_per_r(self):
        path = verify.report(self.spec)
        text = path.read_text(encoding="utf-8")
        self.assertIn("## Outcomes", text)
        self.assertIn("- R1: observed (Task 1)", text)
        self.assertIn("- R2: MISSING (no delivering task)", text)
        self.assertIn("Review: FAIL", text)

    def test_missing_observation_fails_review(self):
        verify._set_spec_status(self.spec, "BUILT")
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_report(_ns(spec=self.spec))
        self.assertEqual(rc, 1)
        self.assertIn("R2", buf.getvalue())
        # a failed review leaves the spec where it was
        self.assertEqual(verify._status_token(self.spec), "BUILT")

    def test_all_observed_passes_review(self):
        text = self.spec.read_text(encoding="utf-8").replace(
            "| R2 | the other thing works |\n", ""
        )
        self.spec.write_text(text, encoding="utf-8")
        verify._set_spec_status(self.spec, "BUILT")
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_report(_ns(spec=self.spec))
        self.assertEqual(rc, 0)
        self.assertEqual(verify._status_token(self.spec), "REVIEWED")
        report = self.tmp / "specs" / "007-REPORT-do-things.md"
        report_text = report.read_text(encoding="utf-8")
        self.assertIn("- R1: observed (Task 1)", report_text)
        self.assertIn("Review: PASS", report_text)


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
        self.assertFalse(verify.uses_shell("python -m unittest discover -s tests"))
        self.assertFalse(verify.uses_shell('echo "hello world"'))

    def test_run_executes_shell_command(self):
        _task_file(self.tmp)
        state_dir = self.tmp / "specs" / "temp"
        # "echo A && echo SHELLMARKER" needs a shell: as argv, `echo A && echo`
        # would try to run an executable literally named "&&". The command is
        # portable across POSIX shells and Windows cmd.
        rc = verify.cmd_run(
            _ns(
                command="echo A && echo SHELLMARKER",
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
        self.assertEqual(
            verify.status(self.tmp / "specs" / "007-TASK-01-do-things.md"), "MET"
        )

    @unittest.skipUnless(os.name == "posix", "POSIX shell command substitution")
    def test_run_executes_command_substitution(self):
        # The TASK-15 verify shape: a grep whose output feeds a test via a
        # command substitution — only a POSIX shell resolves the "$(...)".
        (self.tmp / "docs").mkdir()
        (self.tmp / "docs" / "001-x.md").write_text("plan is real\n", encoding="utf-8")
        cmd = (
            'grep -q "plan" docs/note.md && '
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


class EscalationRecordTest(SandboxCase):
    """C3: the circuit-breaker escalation is a durable, per-spec record."""

    def _fail_once(self, task_id="007-Task 1", state_dir=None):
        return verify.cmd_run(
            _ns(
                command='python -c "raise SystemExit(1)"',
                task_id=task_id,
                expect=None,
                lane=None,
                timeout=60,
                hypothesis=None,
                options=None,
                suggest=False,
                state_dir=state_dir or (self.tmp / "specs" / "temp"),
            )
        )

    def test_circuit_breaker_writes_durable_record_and_stamps_spec(self):
        _spec_file(self.tmp)
        _task_file(self.tmp)
        self.assertEqual(self._fail_once(), 1)
        self.assertEqual(self._fail_once(), 1)
        self.assertEqual(self._fail_once(), 2)  # third consecutive failure trips
        esc = self.tmp / "specs" / "007-ESCALATION-do-things.md"
        self.assertTrue(esc.is_file(), "durable escalation was not written")
        text = esc.read_text(encoding="utf-8")
        self.assertIn("# ESCALATION - 007-Task 1", text)
        self.assertIn("Spec: 007-SPEC-do-things.md", text)
        self.assertIn("never reverts", text)
        self.assertNotIn("revert broken dirty edits", text)
        # a known spec group never uses the ephemeral scratchpad copy
        self.assertFalse((self.tmp / "specs" / "temp" / "escalation.md").is_file())
        # the spec is parked ESCALATED
        spec_text = (self.tmp / "specs" / "007-SPEC-do-things.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Status: ESCALATED", spec_text)

    def test_no_spec_group_falls_back_to_scratchpad(self):
        _task_file(self.tmp)
        state_dir = self.tmp / "specs" / "temp"
        self.assertEqual(self._fail_once(task_id="ad-hoc", state_dir=state_dir), 1)
        self.assertEqual(self._fail_once(task_id="ad-hoc", state_dir=state_dir), 1)
        self.assertEqual(self._fail_once(task_id="ad-hoc", state_dir=state_dir), 2)
        self.assertTrue((state_dir / "escalation.md").is_file())
        self.assertFalse(list((self.tmp / "specs").glob("*-ESCALATION-*.md")))

    def test_escalate_rewrites_durable_record(self):
        _spec_file(self.tmp)
        state_dir = self.tmp / "specs" / "temp"
        for _ in range(3):
            self._fail_once(state_dir=state_dir)
        durable = self.tmp / "specs" / "007-ESCALATION-do-things.md"
        durable.unlink()
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_escalate(
                _ns(
                    task_id="007-Task 1",
                    hypothesis="try a lock",
                    options="A (Recommended): lock; B: queue",
                    state_dir=state_dir,
                )
            )
        self.assertEqual(rc, 0)
        self.assertTrue(durable.is_file())
        text = durable.read_text(encoding="utf-8")
        self.assertIn("try a lock", text)
        self.assertIn("lock", text)


class StatusAdvanceTest(SandboxCase):
    """C4: verify.py owns the build/review status receipts."""

    def setUp(self):
        super().setUp()
        self.spec = _spec_file(self.tmp)
        _task_file(self.tmp)

    def _pass(self, task_id="007-Task 1"):
        return verify.cmd_run(
            _ns(
                command="python -c \"print('MARKER')\"",
                task_id=task_id,
                expect="MARKER",
                lane=None,
                timeout=60,
                hypothesis=None,
                options=None,
                suggest=False,
                state_dir=self.tmp / "specs" / "temp",
            )
        )

    def test_single_task_pass_sets_built(self):
        self.assertEqual(self._pass(), 0)
        self.assertEqual(verify._status_token(self.spec), "BUILT")

    def test_incomplete_spec_stays_building(self):
        self.spec.write_text(
            self.spec.read_text(encoding="utf-8")
            + "\n### Task 2: more\n- Depends On: Task 1\n"
            + "- Verify: `python -c \"print('MARKER')\"`\n- Expect: MARKER\n",
            encoding="utf-8",
        )
        self.assertEqual(self._pass(), 0)
        self.assertEqual(verify._status_token(self.spec), "BUILDING")

    def test_report_advances_built_to_reviewed(self):
        self.assertEqual(self._pass(), 0)
        buf = StringIO()
        with redirect_stdout(buf):
            verify.cmd_report(_ns(spec=self.spec))
        self.assertEqual(verify._status_token(self.spec), "REVIEWED")
        # the report is written after the advance, so its Status: line matches
        report = self.tmp / "specs" / "007-REPORT-do-things.md"
        self.assertIn("Status: REVIEWED", report.read_text(encoding="utf-8"))

    def test_doctor_accepts_building(self):
        verify._set_spec_status(self.spec, "BUILDING")
        gaps = verify.doctor(self.spec)
        self.assertFalse(any(g.startswith("4:") for g in gaps))


class BranchPossibleTest(unittest.TestCase):
    """H7: doctor's branch precondition accepts 'main' or 'master'."""

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git not available")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=str(self.tmp),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            errors="replace",
        )

    def _init_repo(self, branch):
        if self._git("init", "-b", branch).returncode != 0:
            self._git("init")
            self._git("symbolic-ref", "HEAD", f"refs/heads/{branch}")
        self._git(
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=test",
            "commit",
            "--allow-empty",
            "-m",
            "init",
        )

    def test_master_default_is_accepted(self):
        self._init_repo("master")
        ok, detail = verify._branch_possible(self.tmp)
        self.assertTrue(ok, detail)

    def test_main_default_is_accepted(self):
        self._init_repo("main")
        ok, detail = verify._branch_possible(self.tmp)
        self.assertTrue(ok, detail)

    def test_non_repo_is_rejected(self):
        ok, _detail = verify._branch_possible(self.tmp)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
