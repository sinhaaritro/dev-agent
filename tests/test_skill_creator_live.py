"""Live skill-creator eval, gated by SKILL_EVAL=1.

This drives OpenCode end-to-end and therefore costs time and tokens. It is
skipped by default so `python -m unittest discover -s tests` stays fast.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "tools" / "skill_eval.py"
CASES = REPO / "tests" / "fixtures" / "skill-creator" / "cases"


@unittest.skipUnless(
    os.environ.get("SKILL_EVAL") == "1",
    "live agent eval; set SKILL_EVAL=1 to run",
)
@unittest.skipUnless(shutil.which("opencode"), "opencode not on PATH")
class LiveSkillCreatorTest(unittest.TestCase):
    def test_create_case_end_to_end(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-live-") as tmp:
            workspace = Path(tmp) / "workspaces"
            base = [
                sys.executable,
                str(ENGINE),
                "--workspace-root",
                str(workspace),
                "--fixtures-root",
                str(CASES),
            ]
            run_id = "live"
            run = subprocess.run(
                base
                + [
                    "run",
                    "--case",
                    "create-headings-skill",
                    "--run-id",
                    run_id,
                    "--timeout",
                    "600",
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            check = subprocess.run(
                base
                + [
                    "check",
                    "--case",
                    "create-headings-skill",
                    "--run-id",
                    run_id,
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)


if __name__ == "__main__":
    unittest.main()
