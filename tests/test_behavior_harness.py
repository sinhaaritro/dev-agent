"""Deterministic tests for the behavior harness (tools/behavior_eval.py).

No agent runs: these cover the case catalog contract, the real install path
(`bootstrap` + local skill copy), the profile/overlay seeding, the artifact DSL,
and the offline `init`/`check` CLI.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "tools" / "behavior_eval.py"
FIXTURES = REPO / "tests" / "fixtures" / "behavior"

_spec = importlib.util.spec_from_file_location("behavior_eval", ENGINE)
assert _spec is not None and _spec.loader is not None
behavior_eval = importlib.util.module_from_spec(_spec)
sys.modules["behavior_eval"] = behavior_eval
_spec.loader.exec_module(behavior_eval)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CaseCatalogTest(unittest.TestCase):
    def test_every_case_loads_and_is_well_formed(self):
        names = behavior_eval.list_cases(FIXTURES)
        self.assertTrue(names, "no behavior cases found")
        self.assertEqual(len(names), 38, "case count drifted from the test plan")
        for name in names:
            case = behavior_eval.Case.load(FIXTURES, name)
            self.assertEqual(case.name, name)
            self.assertEqual(case.layer, "behavior")
            self.assertTrue(case.prompt.strip(), name)
            self.assertTrue(case.expectations, f"{name}: needs expectations")
            self.assertTrue(case.expected_artifacts, f"{name}: needs artifacts")
            profile = FIXTURES / "profiles" / case.profile / "repo"
            self.assertTrue(profile.is_dir(), f"{name}: missing profile {case.profile}")
            for step in case.setup:
                self.assertTrue(
                    step == "bootstrap" or step == "map" or step.startswith("skills:"),
                    f"{name}: unknown setup step {step!r}",
                )
            for artifact in case.expected_artifacts:
                behavior_eval.parse_artifact(artifact)  # raises on malformed specs

    def test_case_names_are_unique(self):
        names = behavior_eval.list_cases(FIXTURES)
        self.assertEqual(len(names), len(set(names)))

    def test_every_setup_skill_exists_in_skills_dir(self):
        for name in behavior_eval.list_cases(FIXTURES):
            case = behavior_eval.Case.load(FIXTURES, name)
            for step in case.setup:
                if step.startswith("skills:"):
                    for skill in step.split(":", 1)[1].split(","):
                        self.assertTrue(
                            (REPO / "skills" / skill.strip()).is_dir(),
                            f"{name}: unknown skill {skill}",
                        )


class InitRunTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def test_init_installs_framework_via_real_setup_path(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        run, notes = behavior_eval.init_run(case, "run-1", self.workspace)

        repo = run / "repo"
        self.assertTrue((repo / "package.json").is_file())  # profile seeded
        self.assertTrue((repo / "AGENTS.md").is_file())  # bootstrap ran
        self.assertTrue((repo / ".agents" / "rules" / "system.md").is_file())
        self.assertTrue(
            (repo / ".agents" / "skills" / "auto-router" / "SKILL.md").is_file()
        )
        self.assertIn("bootstrap: installed AGENTS.md + .agents/rules/", notes)

        meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["case"], "b2-1-four-lanes")
        self.assertEqual(meta["run_id"], "run-1")

    def test_init_refuses_existing_run_without_force(self):
        case = behavior_eval.Case.load(FIXTURES, "b8-3-bootstrap-confirms-policy")
        behavior_eval.init_run(case, "dupe", self.workspace)
        with self.assertRaises(SystemExit):
            behavior_eval.init_run(case, "dupe", self.workspace)

    def test_force_re_seeds_cleanly(self):
        case = behavior_eval.Case.load(FIXTURES, "b8-3-bootstrap-confirms-policy")
        run, _ = behavior_eval.init_run(case, "dupe", self.workspace)
        write(run / "stale.txt", "stale")
        rerun, _ = behavior_eval.init_run(case, "dupe", self.workspace, force=True)
        self.assertFalse((rerun / "stale.txt").exists())

    def test_case_repo_is_an_overlay_on_the_profile(self):
        case = behavior_eval.Case.load(FIXTURES, "b4-2-run-refused-not-compiled")
        run, _ = behavior_eval.init_run(case, "overlay", self.workspace)
        repo = run / "repo"
        self.assertTrue((repo / "package.json").is_file())
        self.assertTrue((repo / "specs" / "001-SPEC-cache.md").is_file())

    def test_setup_empty_skips_bootstrap(self):
        case = behavior_eval.Case.load(FIXTURES, "b8-3-bootstrap-confirms-policy")
        run, notes = behavior_eval.init_run(case, "raw", self.workspace)
        self.assertEqual(notes, [])
        self.assertFalse((run / "repo" / "AGENTS.md").exists())


class ArtifactDslTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run = Path(self._tmp.name)
        write(self.run / "repo" / "src" / "app.js", "module.exports = {};\n")
        write(self.run / "repo" / "docs" / "flow.md", "Flow doc, no plan pointers.\n")
        write(self.run / "transcript.md", "[STATUS: COMPLETED | Lane: D]\n")

    def test_exists_glob_and_scope(self):
        ok, _ = behavior_eval.check_artifact(self.run, "exists:repo:src/*.js")
        self.assertTrue(ok)
        ok, _ = behavior_eval.check_artifact(self.run, "exists:run:transcript.md")
        self.assertTrue(ok)
        ok, _ = behavior_eval.check_artifact(self.run, "exists:repo:specs/")
        self.assertFalse(ok)

    def test_missing(self):
        ok, _ = behavior_eval.check_artifact(self.run, "missing:repo:specs/")
        self.assertTrue(ok)

    def test_contains_and_not_contains(self):
        ok, _ = behavior_eval.check_artifact(self.run, "contains:run:transcript.md:[STATUS:")
        self.assertTrue(ok)
        ok, _ = behavior_eval.check_artifact(
            self.run, "not-contains:repo:docs/flow.md:specs/"
        )
        self.assertTrue(ok)
        ok, _ = behavior_eval.check_artifact(
            self.run, "contains:repo:docs/flow.md:specs/"
        )
        self.assertFalse(ok)

    def test_missing_file_fails_contains(self):
        ok, detail = behavior_eval.check_artifact(
            self.run, "contains:repo:docs/absent.md:x"
        )
        self.assertFalse(ok)
        self.assertIn("file not found", detail)

    def test_malformed_artifacts_raise(self):
        for bad in ("nope:repo:x", "exists:", "contains:repo:docs/flow.md", "exists:repo:"):
            with self.assertRaises(ValueError, msg=bad):
                behavior_eval.parse_artifact(bad)

    def test_check_run_writes_result_json(self):
        case = behavior_eval.Case(
            name="synthetic",
            profile="bootstrapped-node",
            prompt="p",
            expected_artifacts=[
                "contains:run:transcript.md:Lane: D",
                "missing:repo:specs/",
            ],
        )
        result = behavior_eval.check_run(case, self.run)
        self.assertTrue(result["passed"])
        written = json.loads((self.run / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(written["case"], "synthetic")
        self.assertTrue(written["passed"])

    def test_check_run_fails_when_any_artifact_fails(self):
        case = behavior_eval.Case(
            name="synthetic",
            profile="bootstrapped-node",
            prompt="p",
            expected_artifacts=["exists:repo:specs/"],
        )
        self.assertFalse(behavior_eval.check_run(case, self.run)["passed"])


class CliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ENGINE), *args],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_list_prints_cases(self):
        proc = self.run_cli("list")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("b2-1-four-lanes", proc.stdout)

    def test_init_then_check_offline(self):
        init = self.run_cli(
            "init",
            "--case",
            "b2-1-four-lanes",
            "--run-id",
            "cli-run",
            "--workspace-root",
            str(self.workspace),
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        run = self.workspace / "b2-1-four-lanes" / "cli-run"
        self.assertTrue((run / "repo" / "AGENTS.md").is_file())

        # No agent ran, so the case must fail; the mechanics must not.
        check = self.run_cli(
            "check",
            "--case",
            "b2-1-four-lanes",
            "--run-id",
            "cli-run",
            "--workspace-root",
            str(self.workspace),
        )
        self.assertEqual(check.returncode, 1, check.stdout + check.stderr)
        self.assertIn("FAIL", check.stdout)

        write(run / "transcript.md", "[STATUS: COMPLETED | Lane: D]\n")
        check = self.run_cli(
            "check",
            "--case",
            "b2-1-four-lanes",
            "--run-id",
            "cli-run",
            "--workspace-root",
            str(self.workspace),
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("PASS case b2-1-four-lanes", check.stdout)

    def test_check_on_missing_run_exits_two(self):
        proc = self.run_cli(
            "check",
            "--case",
            "b2-1-four-lanes",
            "--run-id",
            "absent",
            "--workspace-root",
            str(self.workspace),
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_run_requires_run_id(self):
        proc = self.run_cli("run", "--case", "b2-1-four-lanes")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("--run-id", proc.stderr)


if __name__ == "__main__":
    unittest.main()
