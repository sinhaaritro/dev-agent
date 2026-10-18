"""Unit tests for the bootstrap engine (bootstrap.py).

Covers a fresh install, idempotent re-run, the `.gitignore` append-not-clobber
rule, the overwrite of a divergent file, dry-run reporting, the self-bootstrap
refusal, and the missing-target error.

The engine copies the real seed files from its own `reference/` folder, so each
test installs into a throwaway temp directory (outside the framework's source
tree) via the script's `--target` contract.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / ".agents" / "skills" / "bootstrap" / "scripts" / "bootstrap.py"
REFERENCE = REPO / ".agents" / "skills" / "bootstrap" / "reference"

SEED_FILES = (
    "AGENTS.md",
    ".gitignore",
    ".agents/rules/system.md",
    ".agents/agents/coder.md",
    ".cursorrules",
    ".windsurfrules",
)


class BootstrapBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.target = Path(self._tmp.name)

    def run_bootstrap(self, target=None, *extra):
        target = self.target if target is None else target
        return subprocess.run(
            [sys.executable, str(ENGINE), "--target", str(target), *extra],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )


class DryRunTest(BootstrapBase):
    def test_dry_run_reports_new_and_writes_nothing(self):
        proc = self.run_bootstrap(None, "--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("new: AGENTS.md", proc.stdout)
        self.assertIn("new: .agents/rules/system.md", proc.stdout)
        self.assertFalse((self.target / "AGENTS.md").exists())


class InstallTest(BootstrapBase):
    def test_install_creates_every_seed_file(self):
        proc = self.run_bootstrap()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(
            "bootstrap complete: 6 installed, 0 updated, 0 unchanged", proc.stdout
        )
        for rel in SEED_FILES:
            self.assertTrue((self.target / rel).is_file(), rel)
        self.assertEqual(
            (self.target / "AGENTS.md").read_bytes(),
            (REFERENCE / "AGENTS.md").read_bytes(),
        )

    def test_second_run_is_idempotent(self):
        self.run_bootstrap()
        proc = self.run_bootstrap()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(
            "bootstrap complete: 0 installed, 0 updated, 6 unchanged", proc.stdout
        )


class GitignoreTest(BootstrapBase):
    def test_existing_gitignore_is_appended_not_clobbered(self):
        (self.target / ".gitignore").write_text("custom/\n", encoding="utf-8")
        proc = self.run_bootstrap()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("appended: .gitignore", proc.stdout)
        text = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("custom/", text)  # target's own ignore preserved
        seed = (REFERENCE / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("specs/temp", text)  # seed patterns merged in
        self.assertIn("specs/temp", seed)
        self.assertIn("5 installed, 1 updated, 0 unchanged", proc.stdout)

    def test_rerun_does_not_duplicate_gitignore_patterns(self):
        self.run_bootstrap()
        before = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.run_bootstrap()
        self.assertEqual(
            (self.target / ".gitignore").read_text(encoding="utf-8"), before
        )


class OverwriteTest(BootstrapBase):
    def test_divergent_file_is_overwritten(self):
        (self.target / "AGENTS.md").write_text("# Old contract\n", encoding="utf-8")
        proc = self.run_bootstrap()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("updated: AGENTS.md", proc.stdout)
        self.assertEqual(
            (self.target / "AGENTS.md").read_bytes(),
            (REFERENCE / "AGENTS.md").read_bytes(),
        )


class RefusalTest(BootstrapBase):
    def test_self_bootstrap_is_refused(self):
        proc = self.run_bootstrap(REPO)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing to bootstrap", proc.stdout + proc.stderr)

    def test_missing_target_is_an_error(self):
        missing = self.target / "does-not-exist"
        proc = self.run_bootstrap(missing)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not a directory", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
