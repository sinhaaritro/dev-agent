"""Runtime CLI: dispatch, preflight, and scope-independent discovery.

Every engine is reached through one entry point:

    python .agents/scripts/devagent/main.py <command> [args]

This pins the dispatch contract (help / unknown command / argv hand-through),
the runtime preflight (missing manifest, stale runtime version, current
version), and the CWD-walk-up ``find_runtime`` resolution that makes a globally
installed skill resolve the project it is *run in* rather than its own folder.
"""

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "skills" / "dev-agent" / "runtime" / "devagent"
MAIN = RUNTIME / "main.py"

if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import cli
from common import root as root_mod


def run_main(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MAIN), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class DispatchTest(unittest.TestCase):
    def test_help_lists_every_command(self):
        proc = run_main(REPO, "--help")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for command in cli.COMMANDS:
            self.assertIn(command, proc.stdout)

    def test_no_args_prints_help(self):
        proc = run_main(REPO)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("usage: devagent", proc.stdout)

    def test_unknown_command_exits_2(self):
        proc = run_main(REPO, "frobnicate")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown command", proc.stderr)

    def test_unknown_command_does_not_run_preflight(self):
        # Bad dispatch must fail before any discovery/project probing.
        proc = run_main(REPO, "frobnicate")
        self.assertNotIn("no dev-agent runtime", proc.stderr)

    def test_every_command_module_is_importable(self):
        for command, module_name in cli.COMMANDS.items():
            module = importlib.import_module(module_name)
            self.assertTrue(callable(module.main), command)

    def test_known_command_gets_its_own_argv(self):
        # `verify -h` proves the command token is consumed and the rest is handed
        # to the engine's own argparse, which handles -h itself.
        proc = run_main(REPO, "verify", "-h")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("usage", (proc.stdout + proc.stderr).lower())


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "AGENTS.md").write_text("# project\n", encoding="utf-8")

    def write_manifest(self, version: str) -> None:
        (self.root / ".agents").mkdir(exist_ok=True)
        (self.root / ".agents" / ".devagent.json").write_text(
            json.dumps(
                {"schema": 1, "framework": "dev-agent", "runtime_version": version}
            ),
            encoding="utf-8",
        )

    def test_missing_manifest_exits_2_with_setup_hint(self):
        proc = run_main(self.root, "map")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no dev-agent runtime installed", proc.stderr)
        self.assertIn("setup --target", proc.stderr)

    def test_stale_manifest_exits_2_with_update_hint(self):
        self.write_manifest("0.0.1")
        proc = run_main(self.root, "map")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("out of date", proc.stderr)
        self.assertIn("setup --update", proc.stderr)

    def test_current_manifest_proceeds(self):
        self.write_manifest(cli._runtime_version())
        proc = run_main(self.root, "map")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((self.root / ".agents" / "MAP.md").is_file())


class FindRuntimeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / ".agents").mkdir()
        self.manifest = (self.root / ".agents" / ".devagent.json").resolve()
        self.manifest.write_text("{}\n", encoding="utf-8")

    def test_finds_manifest_walking_up_from_a_nested_cwd(self):
        nested = self.root / "a" / "b" / "c"
        nested.mkdir(parents=True)
        self.assertEqual(root_mod.find_runtime(nested), self.manifest)

    def test_returns_none_when_no_manifest_above(self):
        with tempfile.TemporaryDirectory() as other:
            self.assertIsNone(root_mod.find_runtime(Path(other)))

    def test_start_defaults_to_cwd(self):
        # Discovery follows the CWD, not the running script's location: from the
        # project root the manifest is found with no explicit start.
        previous = os.getcwd()
        os.chdir(self.root)
        try:
            self.assertEqual(root_mod.find_runtime(), self.manifest)
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
