"""Contract tests for the vendored skill-creator scripts used by the harness.

Only the harness-agnostic, stdlib-only parts are exercised here:
parse_skill_md, aggregate_benchmark, and the static review viewer. The
Claude-specific trigger-eval scripts are intentionally out of scope.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_CREATOR = REPO / ".agents" / "skills" / "skill-creator"
UTILS = SKILL_CREATOR / "scripts" / "utils.py"
BENCH = SKILL_CREATOR / "scripts" / "aggregate_benchmark.py"
VIEWER = SKILL_CREATOR / "eval-viewer" / "generate_review.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


utils = load("creator_utils", UTILS)
bench = load("creator_bench", BENCH)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    write(path, json.dumps(data, indent=2) + "\n")


def grading(pass_rate: float, passed: int) -> dict:
    return {
        "expectations": [
            {"text": "output exists", "passed": True, "evidence": "out.md"}
        ],
        "summary": {
            "pass_rate": pass_rate,
            "passed": passed,
            "failed": 2 - passed,
            "total": 2,
        },
    }


class ParseSkillMdTest(unittest.TestCase):
    def test_reads_name_and_description(self):
        with tempfile.TemporaryDirectory(prefix="creator-parse-") as tmp:
            skill = Path(tmp) / "heading-index"
            write(
                skill / "SKILL.md",
                "---\nname: heading-index\ndescription: Index headings.\n---\n\n# Skill\n",
            )
            name, description, content = utils.parse_skill_md(skill)
            self.assertEqual(name, "heading-index")
            self.assertEqual(description, "Index headings.")
            self.assertIn("# Skill", content)


class AggregateBenchmarkTest(unittest.TestCase):
    def test_builds_with_skill_and_baseline_summary(self):
        with tempfile.TemporaryDirectory(prefix="creator-bench-") as tmp:
            iteration = Path(tmp) / "iteration-1"
            eval_dir = iteration / "eval-0-example"
            write_json(eval_dir / "eval_metadata.json", {"eval_id": 0})
            for config, rate, passed in (
                ("with_skill", 1.0, 2),
                ("without_skill", 0.5, 1),
            ):
                run = eval_dir / config / "run-1"
                write_json(run / "grading.json", grading(rate, passed))
                write_json(
                    run / "timing.json",
                    {"total_duration_seconds": 1.5, "total_tokens": 10},
                )
            result = bench.generate_benchmark(iteration, "heading-index", "")
            summary = result["run_summary"]
            self.assertIn("with_skill", summary)
            self.assertIn("without_skill", summary)
            self.assertIn("delta", summary)
            self.assertEqual(summary["with_skill"]["pass_rate"]["mean"], 1.0)
            self.assertEqual(summary["without_skill"]["pass_rate"]["mean"], 0.5)


class StaticReviewTest(unittest.TestCase):
    def test_viewer_writes_html_with_prompt(self):
        with tempfile.TemporaryDirectory(prefix="creator-review-") as tmp:
            iteration = Path(tmp) / "iteration-1"
            eval_dir = iteration / "eval-0-example"
            write_json(
                eval_dir / "eval_metadata.json",
                {
                    "eval_id": 0,
                    "eval_name": "example",
                    "prompt": "do the task",
                    "assertions": [],
                },
            )
            for config in ("with_skill", "without_skill"):
                run = eval_dir / config / "run-1"
                write(run / "outputs" / "out.md", "# output\n")
                write_json(run / "grading.json", grading(1.0, 2))
                shutil_copy = eval_dir / "eval_metadata.json"
                write(
                    run / "eval_metadata.json",
                    shutil_copy.read_text(encoding="utf-8"),
                )
            html = Path(tmp) / "review.html"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(VIEWER),
                    str(iteration),
                    "--skill-name",
                    "heading-index",
                    "--static",
                    str(html),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            output = html.read_text(encoding="utf-8")
            self.assertIn("heading-index", output)
            self.assertIn("do the task", output)


if __name__ == "__main__":
    unittest.main()
