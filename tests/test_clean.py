"""Unit tests for the task-cleaner engine (clean.py).

Covers spec 002 TASK-12: the new scratchpad scope. The scratchpad now holds
ONLY draft-stage scratch (draft-plan.md, active-task.md, flow diagrams) -
per-task evidence lives in the task files under specs/, the gate log lives in
the spec's `Gates:` section, and approvals are a per-spec file committed with the spec group. So
the default purge preserves only `.gitignore` (gate-log.md / verify-state.json
/ approvals.json are retired as scratch concepts).

Each test uses a self-contained git sandbox (its own AGENTS.md); the CLI
subprocess runs with cwd inside the sandbox so clean.find_root()
(CWD-first, M2) resolves to the sandbox, not the engine's own repo.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "skills" / "dev-agent" / "runtime" / "devagent"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
ENGINE = RUNTIME / "clean.py"

_spec = importlib.util.spec_from_file_location("clean", ENGINE)
assert _spec is not None and _spec.loader is not None
clean_mod = importlib.util.module_from_spec(_spec)
sys.modules["clean"] = clean_mod
_spec.loader.exec_module(clean_mod)


def _sandbox(tmp: Path) -> Path:
    """A self-contained repo with its own AGENTS.md (the find_root marker)."""
    (tmp / "AGENTS.md").write_text("# Test\n", encoding="utf-8")
    specs = tmp / "specs"
    specs.mkdir()
    (specs / "temp").mkdir()
    # Durable group files that must NEVER be touched by a specs/temp purge.
    (specs / "009-SPEC-do-things.md").write_text("# spec\n", encoding="utf-8")
    (specs / "009-TASK-01-do-things.md").write_text("# task\n", encoding="utf-8")
    (specs / "009-APPROVALS-do-things.json").write_text("{}", encoding="utf-8")
    (tmp / "BACKLOG.md").write_text("# backlog\n", encoding="utf-8")
    (tmp / "docs").mkdir()
    (tmp / "docs" / "lifecycle.md").write_text("# lifecycle\n", encoding="utf-8")
    return tmp


def _fill(temp: Path, names: list[str]) -> None:
    for name in names:
        (temp / name).write_text("scratch: " + name + "\n", encoding="utf-8")


class CleanScopeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="clean-sb-"))
        (self._tmp / "specs" / "temp").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _purge(self, temp: Path, preserve: list[str], dry_run: bool):
        return clean_mod.clean(temp, preserve, dry_run)

    def test_default_preserves_only_gitignore(self):
        temp = self._tmp / "specs" / "temp"
        _fill(
            temp,
            ["draft-plan.md", "active-task.md", "flow.md", ".gitignore", "gate-log.md"],
        )
        purged, preserved = self._purge(temp, [".gitignore"], dry_run=False)
        self.assertEqual(preserved, [".gitignore"])
        self.assertEqual(
            sorted(purged),
            ["active-task.md", "draft-plan.md", "flow.md", "gate-log.md"],
        )
        # gate-log.md is retired as a scratch concept: it is purged, not preserved.
        self.assertFalse((temp / "gate-log.md").exists())
        self.assertTrue((temp / ".gitignore").exists())

    def test_retired_scratch_concepts_are_purged(self):
        temp = self._tmp / "specs" / "temp"
        _fill(temp, ["gate-log.md", "verify-state.json", "approvals.json"])
        purged, _ = self._purge(temp, [".gitignore"], dry_run=False)
        self.assertEqual(
            sorted(purged), ["approvals.json", "gate-log.md", "verify-state.json"]
        )

    def test_purge_all_with_empty_preserve(self):
        temp = self._tmp / "specs" / "temp"
        _fill(temp, ["draft-plan.md", ".gitignore"])
        purged, preserved = self._purge(temp, [], dry_run=False)
        self.assertEqual(preserved, [])
        self.assertEqual(purged, [".gitignore", "draft-plan.md"])
        self.assertEqual(list(temp.iterdir()), [])

    def test_dry_run_deletes_nothing(self):
        temp = self._tmp / "specs" / "temp"
        _fill(temp, ["draft-plan.md", ".gitignore"])
        purged, preserved = self._purge(temp, [".gitignore"], dry_run=True)
        self.assertEqual(purged, ["draft-plan.md"])
        self.assertEqual(preserved, [".gitignore"])
        # nothing deleted
        self.assertTrue((temp / "draft-plan.md").exists())
        self.assertTrue((temp / ".gitignore").exists())

    def test_pure_function_signature(self):
        """clean(temp_dir, preserve, dry_run) -> (purged, preserved) per the contract."""
        temp = self._tmp / "specs" / "temp"
        _fill(temp, ["a.md", ".gitignore"])
        result = clean_mod.clean(temp, [".gitignore"], dry_run=False)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        purged, preserved = result
        self.assertIsInstance(purged, list)
        self.assertIsInstance(preserved, list)
        self.assertEqual(purged, ["a.md"])
        self.assertEqual(preserved, [".gitignore"])

    def test_removes_subdirectories(self):
        temp = self._tmp / "specs" / "temp"
        sub = temp / "work"
        sub.mkdir()
        (sub / "nested.md").write_text("x\n", encoding="utf-8")
        _fill(temp, ["draft-plan.md", ".gitignore"])
        purged, _ = self._purge(temp, [".gitignore"], dry_run=False)
        self.assertIn("work", purged)
        self.assertFalse(sub.exists())


class ScratchpadGuardTest(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="clean-guard-"))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_refuses_repo_root(self):
        root = self._tmp
        with self.assertRaises(SystemExit):
            clean_mod.assert_scratchpad(root, root)

    def test_refuses_above_root(self):
        root = self._tmp / "repo"
        root.mkdir()
        with self.assertRaises(SystemExit):
            clean_mod.assert_scratchpad(self._tmp, root)

    def test_allows_inside_scratchpad(self):
        root = self._tmp / "repo"
        root.mkdir()
        target = root / "specs" / "temp"
        # No SystemExit when the target is a scratchpad inside the repo.
        clean_mod.assert_scratchpad(target, root)

    def test_cli_refuses_root_target(self):
        """The CLI exits non-zero when --temp-dir points at the repo root."""
        sandbox = self._tmp / "repo"
        sandbox.mkdir()
        (sandbox / "AGENTS.md").write_text("# Test\n", encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(ENGINE),
                "clean",
                "--temp-dir",
                str(sandbox),
            ],
            capture_output=True,
            text=True,
            cwd=sandbox,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("refusing to purge", proc.stdout + proc.stderr)


class CliTest(unittest.TestCase):
    """Run the engine as a subprocess against a sandbox scratchpad."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="clean-cli-"))
        _sandbox(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ENGINE), *args],
            capture_output=True,
            text=True,
            cwd=self._tmp,
            check=False,
        )

    def test_clean_reports_purged_preserved(self):
        temp = self._tmp / "specs" / "temp"
        _fill(temp, ["draft-plan.md", "active-task.md", ".gitignore"])
        proc = self._cli("clean", "--temp-dir", str(temp))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("purged: 2, preserved: 1", proc.stdout)
        self.assertFalse((temp / "draft-plan.md").exists())
        self.assertTrue((temp / ".gitignore").exists())
        # group files are untouched
        self.assertTrue((self._tmp / "specs" / "009-SPEC-do-things.md").exists())
        self.assertTrue((self._tmp / "specs" / "009-TASK-01-do-things.md").exists())
        self.assertTrue((self._tmp / "BACKLOG.md").exists())
        self.assertTrue((self._tmp / "docs" / "lifecycle.md").exists())

    def test_status_is_read_only(self):
        temp = self._tmp / "specs" / "temp"
        _fill(temp, ["draft-plan.md", ".gitignore"])
        proc = self._cli("status", "--temp-dir", str(temp))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("would purge 1", proc.stdout)
        self.assertIn("would preserve 1", proc.stdout)
        # read-only: nothing deleted
        self.assertTrue((temp / "draft-plan.md").exists())

    def test_cli_dry_run(self):
        temp = self._tmp / "specs" / "temp"
        _fill(temp, ["draft-plan.md", ".gitignore"])
        proc = self._cli("clean", "--dry-run", "--temp-dir", str(temp))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("would purge 1", proc.stdout)
        self.assertTrue((temp / "draft-plan.md").exists())


if __name__ == "__main__":
    unittest.main()
