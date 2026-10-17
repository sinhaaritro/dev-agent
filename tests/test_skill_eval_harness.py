"""Deterministic tests for the skill-creator eval harness (tools/skill_eval.py).

These do not call an agent. They cover the canonical workspace, case seeding,
layout normalization, structural checks, and golden acceptance.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "tools" / "skill_eval.py"
CASES = REPO / "tests" / "fixtures" / "skill-creator" / "cases"

_spec = importlib.util.spec_from_file_location("skill_eval", ENGINE)
assert _spec is not None and _spec.loader is not None
skill_eval = importlib.util.module_from_spec(_spec)
sys.modules["skill_eval"] = skill_eval
_spec.loader.exec_module(skill_eval)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    write(path, json.dumps(data, indent=2) + "\n")


def grading(pass_rate: float = 1.0) -> dict:
    return {
        "expectations": [
            {"text": "the output exists", "passed": True, "evidence": "out.md"}
        ],
        "summary": {"pass_rate": pass_rate, "passed": 1, "failed": 0, "total": 1},
    }


def make_eval_tree(run_dir: Path, config: str = "with_skill") -> Path:
    eval_dir = run_dir / "iteration-1" / "eval-0-example"
    write_json(
        eval_dir / "eval_metadata.json",
        {
            "eval_id": 0,
            "eval_name": "example",
            "prompt": "do the task",
            "assertions": [],
        },
    )
    for name in ("with_skill", "without_skill"):
        run1 = eval_dir / name / "run-1"
        write(run1 / "outputs" / "out.md", "# output\n")
        write_json(run1 / "grading.json", grading(1.0 if name == "with_skill" else 0.5))
    return eval_dir


class CliParserTest(unittest.TestCase):
    def test_each_subcommand_builds(self):
        parser = skill_eval.build_parser()
        init_args = parser.parse_args(["init", "--case", "x"])
        self.assertEqual(init_args.case, "x")
        check_args = parser.parse_args(["check", "--case", "x", "--run-id", "r"])
        self.assertEqual(check_args.run_id, "r")
        accept_args = parser.parse_args(["accept", "--case", "x", "--run-id", "r"])
        self.assertEqual(accept_args.case, "x")
        iterate_args = parser.parse_args(
            ["iterate", "--case", "x", "--run-id", "r", "--iteration", "2"]
        )
        self.assertEqual(iterate_args.iteration, 2)
        self.assertEqual(parser.parse_args(["list"]).command, "list")


class IterationTest(unittest.TestCase):
    def test_next_iteration(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-iter-") as tmp:
            run_dir = Path(tmp)
            self.assertEqual(skill_eval.next_iteration(run_dir), 1)
            (run_dir / "iteration-1").mkdir()
            self.assertEqual(skill_eval.next_iteration(run_dir), 2)
            (run_dir / "iteration-3").mkdir()
            self.assertEqual(skill_eval.next_iteration(run_dir), 4)

    def test_prompt_names_feedback_and_previous(self):
        case = skill_eval.Case.load(CASES, "create-headings-skill")
        with tempfile.TemporaryDirectory(prefix="skill-eval-prompt-") as tmp:
            run_dir = Path(tmp)
            prompt = skill_eval.iteration_prompt(
                case, run_dir, 2, run_dir / "feedback.json"
            )
            self.assertIn("iteration 2", prompt)
            self.assertIn("feedback.json", prompt)
            self.assertIn("iteration-1", prompt)


class CaseLoadTest(unittest.TestCase):
    def test_create_case_loads(self):
        case = skill_eval.Case.load(CASES, "create-headings-skill")
        self.assertEqual(case.mode, "create")
        self.assertEqual(case.skill_name, "heading-index")
        self.assertTrue(case.prompt)
        self.assertIsNone(case.baseline)

    def test_improve_case_loads(self):
        case = skill_eval.Case.load(CASES, "improve-existing-skill")
        self.assertEqual(case.mode, "improve")
        self.assertEqual(case.baseline, "skills/heading-index")


class InitTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="skill-eval-init-")
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name) / "workspaces"

    def test_create_layout(self):
        case = skill_eval.Case.load(CASES, "create-headings-skill")
        run_dir = skill_eval.init_run(REPO, case, "run-1", self.workspace, CASES)
        self.assertTrue((run_dir / "sandbox" / "AGENTS.md").is_file())
        self.assertIn(
            "Skill-creator eval override",
            (run_dir / "sandbox" / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertTrue(
            (
                run_dir
                / "sandbox"
                / ".agents"
                / "skills"
                / "skill-creator"
                / "SKILL.md"
            ).is_file()
        )
        self.assertTrue((run_dir / "skill").is_dir())
        self.assertTrue((run_dir / "evals").is_dir())
        meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["case"], "create-headings-skill")
        self.assertEqual(meta["prompt_sha256"], skill_eval.sha256_text(case.prompt))
        self.assertTrue(meta["input_tree_hash"])

    def test_improve_copies_baseline(self):
        case = skill_eval.Case.load(CASES, "improve-existing-skill")
        run_dir = skill_eval.init_run(REPO, case, "run-1", self.workspace, CASES)
        self.assertTrue((run_dir / "skill" / "SKILL.md").is_file())
        self.assertTrue((run_dir / "skill-snapshot" / "SKILL.md").is_file())
        self.assertIn(
            "heading-index",
            (run_dir / "skill" / "SKILL.md").read_text(encoding="utf-8"),
        )

    def test_refuses_existing_run_without_force(self):
        case = skill_eval.Case.load(CASES, "create-headings-skill")
        skill_eval.init_run(REPO, case, "run-1", self.workspace, CASES)
        with self.assertRaises(SystemExit):
            skill_eval.init_run(REPO, case, "run-1", self.workspace, CASES)


class NormalizeLayoutTest(unittest.TestCase):
    def test_moves_legacy_outputs_into_run_one(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-layout-") as tmp:
            run_dir = Path(tmp)
            eval_dir = run_dir / "iteration-1" / "eval-0-example"
            write_json(
                eval_dir / "eval_metadata.json",
                {"eval_id": 0, "prompt": "do the task"},
            )
            write(eval_dir / "with_skill" / "outputs" / "out.md", "x\n")
            write_json(eval_dir / "with_skill" / "grading.json", grading())
            changes = skill_eval.normalize_layout(run_dir)
            self.assertTrue(changes)
            self.assertTrue(
                (eval_dir / "with_skill" / "run-1" / "outputs" / "out.md").is_file()
            )
            self.assertTrue(
                (eval_dir / "with_skill" / "run-1" / "grading.json").is_file()
            )
            self.assertTrue(
                (eval_dir / "with_skill" / "run-1" / "eval_metadata.json").is_file()
            )


class StructuralCheckTest(unittest.TestCase):
    def test_valid_tree_passes(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-check-") as tmp:
            run_dir = Path(tmp)
            write(
                run_dir / "skill" / "SKILL.md",
                "---\nname: heading-index\ndescription: Index headings.\n---\n",
            )
            write_json(
                run_dir / "evals" / "evals.json",
                {
                    "skill_name": "heading-index",
                    "evals": [
                        {"id": 1, "prompt": "index a.md", "expected_output": "a list"}
                    ],
                },
            )
            make_eval_tree(run_dir)
            skill_eval.normalize_layout(run_dir)
            case = skill_eval.Case.load(CASES, "create-headings-skill")
            checks = skill_eval.structural_checks(run_dir, case)
            failed = [c for c in checks if not c["ok"]]
            self.assertEqual(failed, [])

    def test_empty_tree_fails(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-empty-") as tmp:
            case = skill_eval.Case.load(CASES, "create-headings-skill")
            checks = skill_eval.structural_checks(Path(tmp), case)
            self.assertTrue(any(not c["ok"] for c in checks))


class ScriptCheckTest(unittest.TestCase):
    def test_benchmark_and_review_are_generated(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-scripts-") as tmp:
            run_dir = Path(tmp)
            write(
                run_dir / "skill" / "SKILL.md",
                "---\nname: heading-index\ndescription: Index headings.\n---\n",
            )
            write_json(
                run_dir / "evals" / "evals.json",
                {
                    "skill_name": "heading-index",
                    "evals": [
                        {"id": 1, "prompt": "index a.md", "expected_output": "a list"}
                    ],
                },
            )
            make_eval_tree(run_dir)
            skill_eval.normalize_layout(run_dir)
            case = skill_eval.Case.load(CASES, "create-headings-skill")
            checks = skill_eval.script_checks(REPO, run_dir, case)
            failed = [c for c in checks if not c["ok"]]
            self.assertEqual(failed, [])
            self.assertTrue((run_dir / "iteration-1" / "benchmark.json").is_file())
            self.assertTrue((run_dir / "review.html").is_file())


class AcceptTest(unittest.TestCase):
    def test_accept_writes_golden(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-accept-") as tmp:
            fixtures = Path(tmp) / "cases"
            case_dir = fixtures / "fake-case"
            write_json(
                case_dir / "case.json",
                {
                    "name": "fake-case",
                    "mode": "create",
                    "skill_name": "fake",
                    "prompt": "make a skill",
                },
            )
            workspace = Path(tmp) / "workspaces"
            run_dir = workspace / "skill-creator" / "fake-case" / "run-1"
            write(
                run_dir / "skill" / "SKILL.md", "---\nname: fake\ndescription: x\n---\n"
            )
            write_json(
                run_dir / "evals" / "evals.json", {"skill_name": "fake", "evals": []}
            )
            (run_dir / "iteration-1").mkdir()
            write_json(run_dir / "check.json", {"ok": True, "checks": []})
            write_json(
                run_dir / "run.json", {"prompt_sha256": "abc", "input_tree_hash": "def"}
            )
            args = SimpleNamespace(
                case="fake-case",
                run_id="run-1",
                force=False,
                fixtures_root=fixtures,
                workspace_root=workspace,
            )
            rc = skill_eval.cmd_accept(args, REPO)
            self.assertEqual(rc, 0)
            expected = case_dir / "expected"
            self.assertTrue((expected / "golden.json").is_file())
            self.assertTrue((expected / "skill" / "SKILL.md").is_file())
            self.assertTrue((expected / "manifest.json").is_file())
            case = skill_eval.Case.load(fixtures, "fake-case")
            checks = skill_eval.golden_checks(run_dir, case, fixtures)
            self.assertTrue(all(c["ok"] for c in checks), checks)

    def test_golden_detects_fixture_change(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-golden-") as tmp:
            fixtures = Path(tmp) / "cases"
            case_dir = fixtures / "fake-case"
            write_json(
                case_dir / "case.json",
                {
                    "name": "fake-case",
                    "mode": "create",
                    "skill_name": "fake",
                    "prompt": "make a skill",
                },
            )
            write_json(
                case_dir / "expected" / "golden.json",
                {"input_tree_hash": "old", "prompt_sha256": "old"},
            )
            write(case_dir / "expected" / "skill" / "SKILL.md", "x\n")
            write_json(case_dir / "expected" / "evals.json", {"evals": []})
            run_dir = Path(tmp) / "run"
            write_json(
                run_dir / "run.json",
                {"input_tree_hash": "new", "prompt_sha256": "old"},
            )
            case = skill_eval.Case.load(fixtures, "fake-case")
            checks = skill_eval.golden_checks(run_dir, case, fixtures)
            failed = [c["name"] for c in checks if not c["ok"]]
            self.assertIn("golden: input tree matches", failed)


class TreeHashTest(unittest.TestCase):
    def test_pycache_is_ignored(self):
        with tempfile.TemporaryDirectory(prefix="skill-eval-hash-") as tmp:
            root = Path(tmp)
            write(root / "a.txt", "one\n")
            first = skill_eval.tree_hash(root)
            write(root / "__pycache__" / "x.pyc", "junk")
            self.assertEqual(skill_eval.tree_hash(root), first)


class ParseFrontmatterTest(unittest.TestCase):
    def test_name_and_description(self):
        data = skill_eval.parse_frontmatter(
            "---\nname: heading-index\ndescription: Index headings.\n---\n"
        )
        self.assertEqual(data["name"], "heading-index")
        self.assertEqual(data["description"], "Index headings.")


if __name__ == "__main__":
    unittest.main()
