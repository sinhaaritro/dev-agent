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
from argparse import Namespace
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
            self.assertTrue(case.steps, f"{name}: needs at least one step")
            self.assertTrue(case.given.strip(), f"{name}: needs a 'given'")
            self.assertTrue(case.when.strip(), f"{name}: needs a 'when'")
            for step in case.steps:
                self.assertTrue(step.id, f"{name}: step needs an id")
                self.assertTrue(
                    step.prompt.strip(), f"{name}[{step.id}]: needs a prompt"
                )
                self.assertTrue(step.given.strip(), f"{name}[{step.id}]: needs a given")
                self.assertTrue(step.when.strip(), f"{name}[{step.id}]: needs a when")
                self.assertTrue(step.expectations, f"{name}[{step.id}]: needs a 'then'")
                self.assertTrue(
                    step.expected_artifacts, f"{name}[{step.id}]: needs artifacts"
                )
                for artifact in step.expected_artifacts:
                    behavior_eval.parse_artifact(artifact)  # raises on malformed specs
            profile = FIXTURES / "profiles" / case.profile / "repo"
            self.assertTrue(profile.is_dir(), f"{name}: missing profile {case.profile}")
            for step in case.setup:
                self.assertTrue(
                    step == "bootstrap" or step == "map" or step.startswith("skills:"),
                    f"{name}: unknown setup step {step!r}",
                )

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


class FixtureCatalogTest(unittest.TestCase):
    """Cases own prompts; named fixtures own the repo state + setup."""

    def test_every_referenced_fixture_exists(self):
        for name in behavior_eval.list_cases(FIXTURES):
            case = behavior_eval.Case.load(FIXTURES, name)
            if not case.fixture:
                continue
            meta = behavior_eval.load_fixture(FIXTURES, case.fixture)
            self.assertEqual(meta["profile"], case.profile)
            self.assertTrue(
                behavior_eval.fixture_dir(FIXTURES, case.fixture).is_dir(),
                f"{name}: missing fixture {case.fixture}",
            )

    def test_a_fixture_has_one_profile_and_setup(self):
        groups: dict[str, set[tuple[str, tuple[str, ...]]]] = {}
        for name in behavior_eval.list_cases(FIXTURES):
            case = behavior_eval.Case.load(FIXTURES, name)
            if case.fixture:
                groups.setdefault(case.fixture, set()).add(
                    (case.profile, tuple(case.setup))
                )
        for fixture, states in groups.items():
            self.assertEqual(len(states), 1, f"{fixture}: {states}")

    def test_bootstrapped_fixture_is_shared_by_several_cases(self):
        shared = [
            name
            for name in behavior_eval.list_cases(FIXTURES)
            if behavior_eval.Case.load(FIXTURES, name).fixture == "bootstrapped"
        ]
        self.assertGreaterEqual(len(shared), 4, shared)

    def test_coverage_covers_every_test_plan_id(self):
        catalog, covered, _extras = behavior_eval.catalog_coverage(FIXTURES)
        plan_ids = {entry["id"] for _, entries in catalog for entry in entries}
        self.assertEqual(len(plan_ids), 38)
        self.assertEqual(sorted(plan_ids - set(covered)), [])
        self.assertEqual(sorted(set(covered) - plan_ids), [])

    def test_catalog_ids_are_unique_across_cases(self):
        seen: dict[str, str] = {}
        for name in behavior_eval.list_cases(FIXTURES):
            case = behavior_eval.Case.load(FIXTURES, name)
            for step in case.steps:
                if not step.case_id:
                    continue
                self.assertNotIn(
                    step.case_id,
                    seen,
                    f"{step.case_id} also in {seen.get(step.case_id)}",
                )
                seen[step.case_id] = name


class PreparedFixtureTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def test_prepare_fixture_cache_runs_setup_once_per_fixture(self):
        cases = [
            behavior_eval.Case.load(FIXTURES, name)
            for name in (
                "b2-1-four-lanes",
                "b2-2-surface-outranks-count",
                "b3-1-session-default-non-interactive",
                "b4-1-compile-then-stop",
            )
        ]
        calls: list[tuple[str, str]] = []
        original = behavior_eval.prepare_config

        def fake(case, config, dest, old_skills_dir=None):
            calls.append((case.name, config))
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "repo").mkdir(exist_ok=True)
            return []

        behavior_eval.prepare_config = fake
        try:
            cache, _notes = behavior_eval.prepare_fixture_cache(
                cases, ("new_skill",), self.workspace / "cache"
            )
        finally:
            behavior_eval.prepare_config = original
        self.assertEqual(set(cache), {"bootstrapped", "spec-builder"})
        self.assertEqual(len(calls), 2)

    def test_init_run_copies_a_prepared_fixture(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        prepared = self.workspace / "prep"
        behavior_eval.prepare_config(case, "new_skill", prepared)
        run, _notes = behavior_eval.init_run(
            case,
            "prepared-run",
            self.workspace,
            prepared={"new_skill": prepared},
        )
        self.assertTrue((run / "repo" / "AGENTS.md").is_file())
        self.assertTrue(
            (run / "repo" / ".agents" / "skills" / "auto-router" / "SKILL.md").is_file()
        )


class MultiStepTest(unittest.TestCase):
    """A scenario: one repo per config, M independent prompts, N checks each."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def scenario(self):
        return behavior_eval.Case(
            name="scene",
            profile="bootstrapped-node",
            setup=[],
            steps=[
                behavior_eval.Step(
                    id="one",
                    prompt="first",
                    expectations=["e1"],
                    expected_artifacts=["contains:run:transcript.md:alpha"],
                ),
                behavior_eval.Step(
                    id="two",
                    prompt="second",
                    expectations=["e2"],
                    expected_artifacts=["exists:repo:src/new.js"],
                ),
            ],
            legacy=False,
        )

    def load_case(self, data):
        fixtures = self.workspace / "fixtures"
        write(fixtures / "cases" / "x" / "case.json", json.dumps(data))
        return behavior_eval.Case.load(fixtures, "x")

    def test_flat_case_normalizes_to_one_legacy_step(self):
        legacy = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        self.assertTrue(legacy.legacy)
        self.assertEqual(len(legacy.steps), 1)
        self.assertEqual(legacy.steps[0].prompt, legacy.prompt)

    def test_scenario_loads_steps_without_legacy_layout(self):
        scenario = self.load_case(
            {
                "name": "scene",
                "profile": "bootstrapped-node",
                "steps": [
                    {
                        "id": "one",
                        "case_id": "B9.9",
                        "title": "First",
                        "prompt": "first",
                        "expected_artifacts": ["exists:repo:x"],
                    },
                    {
                        "id": "two",
                        "prompt": "second",
                        "expected_artifacts": ["exists:repo:y"],
                    },
                ],
            }
        )
        self.assertFalse(scenario.legacy)
        self.assertEqual(len(scenario.steps), 2)
        self.assertEqual(scenario.steps[0].id, "one")
        self.assertEqual(scenario.steps[0].label, "B9.9 First")
        self.assertTrue(all(step.expected_artifacts for step in scenario.steps))

    def test_prompt_and_steps_together_are_rejected(self):
        with self.assertRaises(SystemExit):
            self.load_case(
                {
                    "name": "x",
                    "profile": "bootstrapped-node",
                    "prompt": "flat",
                    "steps": [
                        {
                            "id": "a",
                            "prompt": "p",
                            "expected_artifacts": ["exists:repo:x"],
                        }
                    ],
                }
            )

    def test_step_without_artifacts_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.load_case(
                {
                    "name": "x",
                    "profile": "bootstrapped-node",
                    "steps": [{"id": "a", "prompt": "p"}],
                }
            )

    def test_duplicate_step_ids_are_rejected(self):
        with self.assertRaises(SystemExit):
            self.load_case(
                {
                    "name": "x",
                    "profile": "bootstrapped-node",
                    "steps": [
                        {
                            "id": "a",
                            "prompt": "p",
                            "expected_artifacts": ["exists:repo:x"],
                        },
                        {
                            "id": "a",
                            "prompt": "q",
                            "expected_artifacts": ["exists:repo:y"],
                        },
                    ],
                }
            )

    def test_check_config_grades_each_step(self):
        case = self.scenario()
        run = self.workspace / "run"
        (run / "repo").mkdir(parents=True)
        write(run / "steps" / "1-one" / "transcript.md", "alpha\n")
        write(run / "steps" / "1-one" / "repo" / "keep.txt", "x\n")
        write(run / "steps" / "2-two" / "transcript.md", "beta\n")
        write(run / "steps" / "2-two" / "repo" / "src" / "new.js", "x\n")

        result = behavior_eval.check_config(case, run, "new_skill")
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["steps"]), 2)
        self.assertTrue((run / "result.json").is_file())
        self.assertTrue((run / "steps" / "1-one" / "result.json").is_file())
        self.assertTrue((run / "steps" / "1-one" / "grading.json").is_file())
        self.assertTrue((run / "steps" / "2-two" / "grading.json").is_file())

    def test_a_failing_step_fails_the_config(self):
        case = self.scenario()
        run = self.workspace / "run"
        (run / "repo").mkdir(parents=True)
        write(run / "steps" / "1-one" / "transcript.md", "alpha\n")
        write(run / "steps" / "1-one" / "repo" / "keep.txt", "x\n")
        write(run / "steps" / "2-two" / "transcript.md", "beta\n")
        write(run / "steps" / "2-two" / "repo" / "other.txt", "x\n")  # no src/new.js

        result = behavior_eval.check_config(case, run, "new_skill")
        self.assertFalse(result["passed"])
        self.assertFalse(result["steps"][1]["passed"])

    def test_review_units_expand_to_one_page_per_step(self):
        case = self.scenario()
        base = self.workspace / "cfg"
        units = behavior_eval.review_units(case, "new_skill", base)
        self.assertEqual(
            [unit[0].name for unit in units],
            ["scene#one", "scene#two"],
        )
        self.assertEqual(units[0][2], base / "steps" / "1-one")
        self.assertEqual(units[0][0].prompt, case.steps[0].prompt)

    def test_review_units_use_test_plan_labels(self):
        case = self.load_case(
            {
                "name": "scene",
                "profile": "bootstrapped-node",
                "steps": [
                    {
                        "id": "compile-then-stop",
                        "case_id": "B4.1",
                        "title": "Compile then stop",
                        "prompt": "compile",
                        "expected_artifacts": ["exists:repo:x"],
                    }
                ],
            }
        )
        base = self.workspace / "cfg"
        units = behavior_eval.review_units(case, "new_skill", base)
        self.assertEqual([unit[0].name for unit in units], ["B4.1 Compile then stop"])

    def test_legacy_review_units_are_single(self):
        case = behavior_eval.Case.load(FIXTURES, "b2-1-four-lanes")
        base = self.workspace / "cfg"
        units = behavior_eval.review_units(case, "new_skill", base)
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0][0].name, "B2.1 Four canonical lanes")
        self.assertEqual(units[0][2], base)

    def test_reset_restores_the_pristine_repo(self):
        base = self.workspace / "cfg"
        write(base / "repo" / "keep.txt", "pristine\n")
        behavior_eval.snapshot_base_repo(base)
        write(base / "repo" / "junk.txt", "left behind\n")
        behavior_eval.reset_working_repo(base)
        self.assertTrue((base / "repo" / "keep.txt").is_file())
        self.assertFalse((base / "repo" / "junk.txt").exists())


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
        self.assertTrue(
            (repo / ".agents" / "rules" / "dev-agent-framework.md").is_file()
        )
        self.assertTrue(
            (repo / ".agents" / "skills" / "auto-router" / "SKILL.md").is_file()
        )
        self.assertTrue(
            any(
                note.endswith("bootstrap: installed AGENTS.md + .agents/rules/")
                for note in notes
            ),
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
        ok, _ = behavior_eval.check_artifact(
            self.run, "contains:run:transcript.md:[STATUS:"
        )
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
        for bad in (
            "nope:repo:x",
            "exists:",
            "contains:repo:docs/flow.md",
            "exists:repo:",
        ):
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
            '{"type":"text","part":{"text":' + json.dumps(mojibake) + "}}\n"
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

        template = json.loads(
            (run / "feedback-template.json").read_text(encoding="utf-8")
        )
        ids = [item["run_id"] for item in template["reviews"]]
        self.assertIn(
            "iteration-1-eval-0-B2.1 Four canonical lanes-new_skill-run-1", ids
        )
        self.assertIn(
            "iteration-1-eval-0-B2.1 Four canonical lanes-without_skill-run-1", ids
        )

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
                        {
                            "run_id": "new_skill",
                            "feedback": "the header lane was wrong",
                        },
                        {"run_id": "without_skill", "feedback": ""},
                    ],
                }
            ),
        )
        rc = behavior_eval.main(
            [
                "feedback",
                "--case",
                case.name,
                "--run-id",
                "rev",
                "--workspace-root",
                str(self.workspace),
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
                "--case",
                case.name,
                "--run-id",
                "rev",
                "--workspace-root",
                str(self.workspace),
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
        self.assertIn(
            "OLD AUTO-ROUTER", (dest / "auto-router" / "SKILL.md").read_text()
        )

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

        template = json.loads(
            (out / "feedback-template.json").read_text(encoding="utf-8")
        )
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
                    "reviews": [
                        {"run_id": "r1", "feedback": "tighten the lane example"}
                    ],
                }
            ),
        )
        rc = behavior_eval.main(["feedback", "--run-dir", str(out)])
        self.assertEqual(rc, 0)
        digest = (out / "feedback-digest.md").read_text(encoding="utf-8")
        self.assertIn("auto-router", digest)
        self.assertIn("tighten the lane example", digest)


class AcceptedBaselineTest(unittest.TestCase):
    """Phase 2: accept a checked run, then detect skill/fixture drift offline."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)
        self.fixtures = self.workspace / "fixtures"

    def make_case(self, prompt: str = "do the thing"):
        case_dir = self.fixtures / "cases" / "case-x"
        write(
            case_dir / "case.json",
            json.dumps(
                {
                    "name": "case-x",
                    "profile": "bootstrapped-node",
                    "setup": [],
                    "prompt": prompt,
                    "expectations": ["creates x"],
                    "expected_artifacts": ["exists:repo:x"],
                }
            ),
        )
        return behavior_eval.Case.load(self.fixtures, "case-x")

    def seed_run(self, case) -> Path:
        run = self.workspace / "runs" / case.name / "run-1"
        write(run / "repo" / "x", "hello\n")
        write(run / "transcript.md", "done\n")
        return run

    def test_no_baseline_has_no_checks(self):
        case = self.make_case()
        self.assertIsNone(behavior_eval.load_baseline(case))
        self.assertEqual(behavior_eval.baseline_checks(case), [])

    def test_accept_records_a_passing_run(self):
        case = self.make_case()
        run = self.seed_run(case)
        behavior_eval.check_config(case, run, "new_skill")
        path = behavior_eval.accept_run(case, run, configs=("new_skill",))
        self.assertTrue(path.is_file())
        self.assertEqual(path, behavior_eval.baseline_path(case))
        baseline = behavior_eval.load_baseline(case)
        self.assertEqual(baseline["case"], "case-x")
        self.assertEqual(baseline["summary"]["pass_rate"], 1.0)
        self.assertIn("skills_sha256", baseline)
        self.assertTrue(all(c["ok"] for c in behavior_eval.baseline_checks(case)))

    def test_accept_refuses_a_failing_run_without_force(self):
        case = self.make_case()
        run = self.workspace / "runs" / case.name / "run-1"
        (run / "repo").mkdir(parents=True)  # x missing -> artifact FAILs
        behavior_eval.check_config(case, run, "new_skill")
        with self.assertRaises(SystemExit):
            behavior_eval.accept_run(case, run, configs=("new_skill",))
        path = behavior_eval.accept_run(case, run, configs=("new_skill",), force=True)
        self.assertTrue(path.is_file())

    def test_fixture_change_shows_as_drift(self):
        case = self.make_case()
        run = self.seed_run(case)
        behavior_eval.check_config(case, run, "new_skill")
        behavior_eval.accept_run(case, run, configs=("new_skill",))
        self.make_case(prompt="do a DIFFERENT thing")
        reloaded = behavior_eval.Case.load(self.fixtures, "case-x")
        drift = {c["name"]: c["ok"] for c in behavior_eval.baseline_checks(reloaded)}
        self.assertFalse(drift["baseline: case fixture unchanged"])
        self.assertTrue(drift["baseline: skills under test unchanged"])

    def test_tree_sha_ignores_line_endings(self):
        a = self.workspace / "a"
        b = self.workspace / "b"
        (a).mkdir(parents=True)
        (b).mkdir(parents=True)
        (a / "f.txt").write_bytes(b"one\ntwo\n")
        (b / "f.txt").write_bytes(b"one\r\ntwo\r\n")
        self.assertEqual(behavior_eval._tree_sha(a), behavior_eval._tree_sha(b))

    def test_baseline_command_reports_drift(self):
        case = self.make_case()
        run = self.seed_run(case)
        behavior_eval.check_config(case, run, "new_skill")
        behavior_eval.accept_run(case, run, configs=("new_skill",))
        args = Namespace(skill=None, strict=False)
        self.assertEqual(behavior_eval.cmd_baseline(args, self.fixtures), 0)
        self.make_case(prompt="changed fixture")
        self.assertEqual(behavior_eval.cmd_baseline(args, self.fixtures), 1)

    def test_baseline_strict_requires_a_baseline(self):
        self.make_case()
        self.assertEqual(
            behavior_eval.cmd_baseline(
                Namespace(skill=None, strict=True), self.fixtures
            ),
            1,
        )
        self.assertEqual(
            behavior_eval.cmd_baseline(
                Namespace(skill=None, strict=False), self.fixtures
            ),
            0,
        )


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

    def test_baseline_reports_cases_offline(self):
        proc = self.run_cli("baseline")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("b2-1-four-lanes", proc.stdout)
        self.assertIn("cases:", proc.stdout)

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
        self.assertIn("PASS case B2.1 Four canonical lanes", check.stdout)
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
