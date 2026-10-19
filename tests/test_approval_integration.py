"""C1 integration: compile-time pre-approvals satisfy verify.py.

`promote_spec.compile_spec()` writes `specs/NNN-APPROVALS-<slug>.json`. That
companion must (a) use the same sha256 fingerprint as verify.py's
`command_fingerprint`, and (b) be honored by `verify.py doctor` and
`verify.py run --lane A` with no separate manual `approve`.

The unit suites used to pin the two formats independently (plain text at
compile, sha256 at verify), so both stayed green while the seam was broken.
This test exercises the whole compile -> doctor -> run path end to end.
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_ENGINE = (
    ROOT / ".agents" / "skills" / "spec-builder" / "scripts" / "promote_spec.py"
)
VERIFY_ENGINE = (
    ROOT / ".agents" / "skills" / "verification-runner" / "scripts" / "verify.py"
)

RUN_COMMAND = "python -c \"print('MARKER')\""

SPEC_TEXT = """\
---
tags: [sandbox, approval]
---

# 007: Approval Sandbox

Status: DRAFTED | Date: 2026-10-19

## 1. Goal & Context

Sandbox for the compile -> doctor -> run approval path.

## 4. Affected Files & Contracts

- [MODIFY] src.py

## 5. Tasks & Outcomes

### Task 1: do things
- Target Files: [MODIFY] src.py
- Depends On: None
- Verify: `python -c "print('MARKER')"`
- Expect: MARKER
"""


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Unique module names so loading here never clobbers the sibling suites.
promote_spec = _load("_approval_test_promote_spec", SPEC_ENGINE)
verify = _load("_approval_test_verify", VERIFY_ENGINE)


class CompileRunApprovalTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self._orig_cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, self._orig_cwd)

        (self.tmp / "AGENTS.md").write_text(
            "# Test\n\n## Commands\n\n"
            "- Build: python -m compileall .\n"
            "- Test: python -m unittest\n"
            "- Lint: true\n",
            encoding="utf-8",
        )
        (self.tmp / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.tmp / "specs").mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.tmp, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.t"], cwd=self.tmp, check=True
        )
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp, check=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-q", "-m", "init"],
            cwd=self.tmp,
            check=True,
        )

        self.spec = self.tmp / "specs" / "007-SPEC-approval-sandbox.md"
        self.spec.write_text(SPEC_TEXT, encoding="utf-8")
        self.approvals = self.tmp / "specs" / "007-APPROVALS-approval-sandbox.json"

    def _compile(self):
        promote_spec.compile_spec(self.spec)

    def test_compile_writes_verify_compatible_fingerprint(self):
        self._compile()
        entry = json.loads(self.approvals.read_text(encoding="utf-8"))["approvals"][0]
        # A sha256 approval key (not the old plain command|expect|cwd string) ...
        self.assertRegex(entry["fingerprint"], r"^[0-9a-f]{64}$")
        # ... that verify.py computes identically for the same inputs (C1).
        self.assertEqual(
            entry["fingerprint"],
            verify.command_fingerprint(entry["command"], entry["expect"], entry["cwd"]),
        )
        # The human-readable companion fields survive (what a person reads).
        self.assertEqual(entry["command"], RUN_COMMAND)
        self.assertEqual(entry["expect"], "MARKER")

    def test_compile_writes_portable_repo_relative_cwd(self):
        self._compile()
        raw = self.approvals.read_text(encoding="utf-8")
        entry = json.loads(raw)["approvals"][0]
        # H5: the fingerprint's cwd term is the repo root repo-relative
        # ('.'), never a machine-absolute path, so the committed companion
        # is portable across clones and operating systems.
        self.assertEqual(entry["cwd"], ".")
        self.assertNotIn(str(self.tmp), raw)

    def test_doctor_precondition_7_accepts_compile_preapproval(self):
        self._compile()
        gaps = verify.doctor(self.spec)
        self.assertEqual([g for g in gaps if g.startswith("7:")], [], gaps)

    def test_run_lane_a_accepts_compile_preapproval(self):
        self._compile()
        rc = verify.cmd_run(
            argparse.Namespace(
                command=RUN_COMMAND,
                task_id="007-Task 1",
                expect="MARKER",
                lane="A",
                timeout=60,
                hypothesis=None,
                options=None,
                suggest=False,
                state_dir=self.tmp / "specs" / "temp",
            )
        )
        self.assertEqual(rc, 0)
