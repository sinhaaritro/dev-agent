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
        self.assertEqual(len(names), 39, "case count drifted from the test plan")
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
        self.assertTrue(
            any(note.endswith("bootstrap: installed AGENTS.md + .agents/rules/") for note in notes),
            notes,
        )

        meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["case"], "b2-1-four-lanes")
        self.assertEqual(meta["run_id"], "run-1")
        self.assertEqual(meta["configs"], ["new_skill"])

    def test_without_skill_config_is_the_raw_repo(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        run, _ = behavior_eval.init_run(
            case, "both-run", self.workspace, configs=("with_skill", "without_skill")
        )
        self.assertTrue((run / "repo" / "AGENTS.md").is_file())
        bare = run / "without_skill" / "repo"
        self.assertTrue((bare / "package.json").is_file())
        self.assertFalse((bare / "AGENTS.md").exists())
        self.assertFalse((bare / ".agents").exists())

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
        case = behavior_eval.Case(
            name="raw", profile="bootstrapped-node", prompt="p", setup=[]
        )
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

    def test_regex_matches_and_not_matches(self):
        ok, _ = behavior_eval.check_artifact(
            self.run, "matches:run:transcript.md:Lane: (C|D)"
        )
        self.assertTrue(ok)
        ok, _ = behavior_eval.check_artifact(
            self.run, "matches:run:transcript.md:Lane: (A|B)"
        )
        self.assertFalse(ok)
        ok, _ = behavior_eval.check_artifact(
            self.run, "not-matches:run:transcript.md:Lane: (A|B)"
        )
        self.assertTrue(ok)

    def test_bad_regex_fails_the_check(self):
        ok, detail = behavior_eval.check_artifact(
            self.run, "matches:run:transcript.md:Lane: ("
        )
        self.assertFalse(ok)
        self.assertIn("bad regex", detail)

    def test_describe_artifact_is_human_readable(self):
        self.assertEqual(
            behavior_eval.describe_artifact("contains:run:transcript.md:Lane: D"),
            "the agent's answer contains 'Lane: D'",
        )
        self.assertEqual(
            behavior_eval.describe_artifact("missing:repo:specs/"),
            "the repo has no path matching `specs/`",
        )
        self.assertEqual(
            behavior_eval.describe_artifact("not-contains:repo:docs/flow.md:specs/"),
            "the repo does not contain 'specs/' in `docs/flow.md`",
        )
        self.assertEqual(
            behavior_eval.describe_artifact("matches:run:transcript.md:Lane: (A|B)"),
            "the agent's answer matches /Lane: (A|B)/",
        )
        self.assertEqual(
            behavior_eval.describe_artifact("exists:repo:src/*.js"),
            "the repo has a path matching `src/*.js`",
        )

    def test_case_assertion_labels_override_the_default_wording(self):
        case = behavior_eval.Case(
            name="synthetic",
            profile="bootstrapped-node",
            prompt="p",
            expected_artifacts=["exists:repo:x"],
            assertion_labels={"exists:repo:x": "x was created"},
        )
        self.assertEqual(case.assertion_labels["exists:repo:x"], "x was created")

    def test_extract_repairs_mojibake_and_skips_tool_events(self):
        # "gate — halt\nstep → done" read as cp1252, JSON-escaped in the stream.
        original = "gate \u2014 halt\nstep \u2192 done"
        mojibake = original.encode("utf-8").decode("cp1252")
        jsonl = (
            '{"type":"tool_use","part":{"text":"ignored"}}\n'
            '{"type":"text","part":{"text":'
            + json.dumps(mojibake)
            + "}}\n"
        )
        text = behavior_eval.extract_assistant_text(jsonl)
        self.assertEqual(text, original)

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


class ReviewAndFeedbackTest(unittest.TestCase):
    """The skill-creator review loop: grading.json -> review.html -> feedback."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def seed_run(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        run, _ = behavior_eval.init_run(
            case, "rev", self.workspace, configs=("new_skill", "without_skill")
        )
        write(run / "transcript.md", "[STATUS: COMPLETED | Lane: D]\n")
        write(run / "outputs" / "answer.md", "Framework answer\n")
        write(run / "without_skill" / "transcript.md", "Just an answer.\n")
        write(run / "without_skill" / "outputs" / "answer.md", "Baseline answer\n")
        return case, run

    def test_grading_uses_viewer_contract(self):
        case, run = self.seed_run()
        result = behavior_eval.check_config(case, run, "new_skill")
        self.assertTrue(result["passed"])

        grading = json.loads((run / "grading.json").read_text(encoding="utf-8"))
        self.assertTrue(grading["expectations"])
        for item in grading["expectations"]:
            self.assertEqual(set(item), {"text", "passed", "evidence"})
            self.assertNotIn(item["text"], case.expected_artifacts)
            self.assertIn("(check: ", item["evidence"])
        self.assertEqual(grading["summary"]["total"], len(case.expected_artifacts))
        self.assertEqual(grading["summary"]["pass_rate"], 1.0)

    def test_review_html_and_feedback_template(self):
        case, run = self.seed_run()
        behavior_eval.check_config(case, run, "new_skill")
        behavior_eval.check_config(case, run, "without_skill")

        html = behavior_eval.build_review(case, run)
        self.assertIsNotNone(html, "review generation failed")
        self.assertTrue(html.is_file())
        body = html.read_text(encoding="utf-8")
        self.assertIn("Submit All Reviews", body)
        self.assertIn("Framework answer", body)
        self.assertIn("Baseline answer", body)

        template = json.loads((run / "feedback-template.json").read_text(encoding="utf-8"))
        ids = [item["run_id"] for item in template["reviews"]]
        self.assertIn("iteration-1-eval-0-b2-1-four-lanes-new_skill-run-1", ids)
        self.assertIn("iteration-1-eval-0-b2-1-four-lanes-without_skill-run-1", ids)

        preview = behavior_eval.trusted_preview(f"{case.name}-{run.name}", html)
        self.addCleanup(preview.unlink, missing_ok=True)
        self.assertEqual(preview.parent, REPO / ".behavior-review")
        self.assertIn("Submit All Reviews", preview.read_text(encoding="utf-8"))

    def test_feedback_digest_from_download(self):
        case, run = self.seed_run()
        write(
            run / "feedback.json",
            json.dumps(
                {
                    "status": "complete",
                    "reviews": [
                        {"run_id": "new_skill", "feedback": "the header lane was wrong"},
                        {"run_id": "without_skill", "feedback": ""},
                    ],
                }
            ),
        )
        rc = behavior_eval.main(
            [
                "feedback",
                "--case", case.name,
                "--run-id", "rev",
                "--workspace-root", str(self.workspace),
            ]
        )
        self.assertEqual(rc, 0)
        digest = (run / "feedback-digest.md").read_text(encoding="utf-8")
        self.assertIn("the header lane was wrong", digest)
        self.assertNotIn("## without_skill", digest)

    def test_missing_feedback_is_a_named_error(self):
        case, _run = self.seed_run()
        rc = behavior_eval.main(
            [
                "feedback",
                "--case", case.name,
                "--run-id", "rev",
                "--workspace-root", str(self.workspace),
            ]
        )
        self.assertEqual(rc, 2)


class ConfigAndBaselineTest(unittest.TestCase):
    """new_skill vs old_skill: aliases + previous-version staging."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def test_with_skill_is_an_alias_for_new_skill(self):
        run = Path("run")
        self.assertEqual(behavior_eval.canonical_config("with_skill"), "new_skill")
        self.assertEqual(behavior_eval.config_path(run, "with_skill"), run)
        self.assertEqual(behavior_eval.config_path(run, "old_skill"), run / "old_skill")
        self.assertEqual(
            behavior_eval.select_configs("compare"), ("new_skill", "old_skill")
        )

    def test_old_skill_is_exported_from_git_head(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        dest = self.workspace / "old"
        behavior_eval.materialize_old_skills(case, dest)
        for skill in ("auto-router", "phase-protocol"):
            self.assertTrue((dest / skill / "SKILL.md").is_file(), skill)

    def test_old_skills_dir_wins_when_given(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        snapshot = self.workspace / "snapshot"
        write(snapshot / "auto-router" / "SKILL.md", "OLD AUTO-ROUTER\n")
        write(snapshot / "phase-protocol" / "SKILL.md", "OLD PHASE\n")

        dest = self.workspace / "old"
        behavior_eval.materialize_old_skills(case, dest, snapshot)
        self.assertIn("OLD AUTO-ROUTER", (dest / "auto-router" / "SKILL.md").read_text())

    def test_init_installs_the_old_version(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        run, _ = behavior_eval.init_run(
            case, "old-run", self.workspace, configs=("old_skill",)
        )
        installed = run / "old_skill" / "repo" / ".agents" / "skills" / "auto-router"
        self.assertTrue((installed / "SKILL.md").is_file())
        self.assertFalse((run / "old_skill" / "_old_skills").exists())


class BatchReviewTest(unittest.TestCase):
    """One review page for many predefined prompts + the Benchmark summary."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def entry(self, name: str, config: str):
        case = behavior_eval.Case(
            name=name,
            profile="bootstrapped-node",
            prompt=f"prompt for {name}",
            expected_artifacts=["exists:repo:x"],
        )
        base = self.workspace / f"{name}-{config}"
        write(base / "outputs" / "answer.md", f"answer for {name} {config}\n")
        write(
            base / "grading.json",
            json.dumps(
                {
                    "expectations": [
                        {"text": "exists:repo:x", "passed": True, "evidence": "ok"}
                    ],
                    "summary": {
                        "pass_rate": 1.0,
                        "passed": 1,
                        "failed": 0,
                        "total": 1,
                    },
                }
            ),
        )
        return (case, config, base)

    def test_many_prompts_many_configs_one_review(self):
        entries = [
            self.entry("case-a", "new_skill"),
            self.entry("case-a", "old_skill"),
            self.entry("case-b", "new_skill"),
            self.entry("case-b", "old_skill"),
        ]
        out = self.workspace / "batch"
        html = behavior_eval.render_review(
            entries, out, label="batch-x", skill_name="auto-router"
        )
        self.assertIsNotNone(html, "review generation failed")
        self.assertTrue(html.is_file())

        template = json.loads((out / "feedback-template.json").read_text(encoding="utf-8"))
        ids = [item["run_id"] for item in template["reviews"]]
        self.assertEqual(len(ids), 4)
        self.assertIn("iteration-1-eval-0-case-a-new_skill-run-1", ids)
        self.assertIn("iteration-1-eval-0-case-a-old_skill-run-1", ids)
        self.assertIn("iteration-1-eval-1-case-b-old_skill-run-1", ids)

        benchmark = out / "review" / "iteration-1" / "benchmark.json"
        self.assertTrue(benchmark.is_file(), "benchmark summary missing")
        summary = json.loads(benchmark.read_text(encoding="utf-8"))
        self.assertIn("run_summary", summary)

        preview = behavior_eval.trusted_preview("batch-x", html)
        self.addCleanup(preview.unlink, missing_ok=True)
        self.assertTrue(preview.is_file())

    def test_feedback_accepts_a_batch_run_dir(self):
        out = self.workspace / "batch-y"
        write(out / "batch.json", json.dumps({"skills": ["auto-router"]}))
        write(
            out / "feedback.json",
            json.dumps(
                {
                    "status": "complete",
                    "reviews": [{"run_id": "r1", "feedback": "tighten the lane example"}],
                }
            ),
        )
        rc = behavior_eval.main(["feedback", "--run-dir", str(out)])
        self.assertEqual(rc, 0)
        digest = (out / "feedback-digest.md").read_text(encoding="utf-8")
        self.assertIn("auto-router", digest)
        self.assertIn("tighten the lane example", digest)


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
        self.assertIn("review:", check.stdout)
        self.assertTrue((run / "review.html").is_file())

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
