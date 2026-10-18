"""Deterministic tests for the meta suite runner (tools/suite_report.py).

No agent and no recursion: the runner is invoked as a subprocess against a
throwaway tests directory whose modules use the `suitecase_` prefix, so the real
`tests/` tree is never discovered from inside a test.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "tools" / "suite_report.py"

_spec = importlib.util.spec_from_file_location("suite_report", ENGINE)
assert _spec is not None and _spec.loader is not None
suite_report = importlib.util.module_from_spec(_spec)
sys.modules["suite_report"] = suite_report
_spec.loader.exec_module(suite_report)

PASS_MODULE = '''"""Fixture: one passing test."""
import unittest


class PassTest(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(True)
'''

FAIL_MODULE = '''"""Fixture: one failing test."""
import unittest


class FailTest(unittest.TestCase):
    def test_bad(self):
        self.assertEqual(1, 2)
'''

SKIP_MODULE = '''"""Fixture: one skipped test."""
import unittest


class SkipTest(unittest.TestCase):
    @unittest.skip("fixture")
    def test_skip(self):
        pass
'''

SAME_ID_FAILING_MODULE = '''"""Fixture: same test id as PASS_MODULE, now failing."""
import unittest


class PassTest(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(1, 2)
'''

EXTRA_MODULE = '''"""Fixture: a second passing module."""
import unittest


class ExtraTest(unittest.TestCase):
    def test_extra(self):
        self.assertTrue(True)
'''


class DiffBaselineTest(unittest.TestCase):
    def test_identical_maps_have_no_drift(self):
        baseline = {"a.A.test_one": "pass", "a.A.test_two": "fail"}
        diff = suite_report.diff_baseline(baseline, dict(baseline))
        self.assertEqual(diff, {"added": {}, "removed": {}, "changed": {}})
        self.assertFalse(suite_report.has_drift(diff))

    def test_buckets_are_split(self):
        baseline = {
            "a.A.test_keep": "pass",
            "a.A.test_gone": "pass",
            "a.A.test_flip": "pass",
        }
        current = {
            "a.A.test_keep": "pass",
            "a.A.test_flip": "fail",
            "a.A.test_new": "skip",
        }
        diff = suite_report.diff_baseline(baseline, current)
        self.assertEqual(diff["added"], {"a.A.test_new": "skip"})
        self.assertEqual(diff["removed"], {"a.A.test_gone": "pass"})
        self.assertEqual(diff["changed"], {"a.A.test_flip": {"from": "pass", "to": "fail"}})
        self.assertTrue(suite_report.has_drift(diff))

    def test_report_names_every_delta(self):
        diff = {
            "added": {"a.A.test_new": "pass"},
            "removed": {"a.A.test_gone": "pass"},
            "changed": {"a.A.test_flip": {"from": "pass", "to": "error"}},
        }
        report = suite_report.format_report(diff, total=3)
        self.assertIn("added:   a.A.test_new (pass)", report)
        self.assertIn("removed: a.A.test_gone (baseline pass)", report)
        self.assertIn("changed: a.A.test_flip: pass -> error", report)
        self.assertIn("summary: 1 added, 1 removed, 1 changed", report)

    def test_clean_report_says_no_drift(self):
        report = suite_report.format_report(
            {"added": {}, "removed": {}, "changed": {}}, total=7
        )
        self.assertIn("no drift: 7 tests match the baseline", report)


class BaselineFileTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_write_then_load_roundtrips_sorted(self):
        path = self.root / "nested" / ".suite-baseline.json"
        outcomes = {"b.B.test_two": "skip", "a.A.test_one": "pass"}
        suite_report.write_baseline(path, outcomes)

        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(list(data["tests"]), sorted(outcomes))
        self.assertIn("generated", data)
        self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

        self.assertEqual(suite_report.load_baseline(path), dict(sorted(outcomes.items())))

    def test_unknown_status_is_rejected(self):
        path = self.root / "bad.json"
        path.write_text(json.dumps({"tests": {"a.A.test": "exploded"}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            suite_report.load_baseline(path)

    def test_wrong_shape_is_rejected(self):
        path = self.root / "bad.json"
        path.write_text(json.dumps({"tests": ["not", "a", "map"]}), encoding="utf-8")
        with self.assertRaises(TypeError):
            suite_report.load_baseline(path)

    def test_missing_baseline_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            suite_report.load_baseline(self.root / "absent.json")


class SuiteRunnerCliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.baseline = self.root / ".suite-baseline.json"

    def write_case(self, stem: str, text: str) -> Path:
        path = self.root / f"suitecase_{stem}.py"
        path.write_text(text, encoding="utf-8")
        return path

    def run_report(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(ENGINE),
                "--tests-dir",
                str(self.root),
                "--pattern",
                "suitecase_*.py",
                "--baseline",
                str(self.baseline),
                "--quiet",
                *extra,
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def seed_baseline(self, *texts: str) -> None:
        for index, text in enumerate(texts):
            self.write_case(f"seed{index}", text)
        proc = self.run_report("--update")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_update_records_pass_fail_and_skip(self):
        self.write_case("pass", PASS_MODULE)
        self.write_case("fail", FAIL_MODULE)
        self.write_case("skip", SKIP_MODULE)

        proc = self.run_report("--update")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        data = json.loads(self.baseline.read_text(encoding="utf-8"))
        self.assertEqual(
            data["tests"],
            {
                "suitecase_fail.FailTest.test_bad": "fail",
                "suitecase_pass.PassTest.test_ok": "pass",
                "suitecase_skip.SkipTest.test_skip": "skip",
            },
        )

    def test_rerun_without_changes_exits_zero(self):
        self.seed_baseline(PASS_MODULE)
        proc = self.run_report()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("no drift: 1 tests match the baseline", proc.stdout)

    def test_added_test_is_reported_and_exits_one(self):
        self.seed_baseline(PASS_MODULE)
        self.write_case("extra", EXTRA_MODULE)

        proc = self.run_report()
        self.assertEqual(proc.returncode, suite_report.EXIT_DRIFT, proc.stdout + proc.stderr)
        self.assertIn("added:   suitecase_extra.ExtraTest.test_extra (pass)", proc.stdout)

    def test_removed_test_is_reported_and_exits_one(self):
        self.seed_baseline(PASS_MODULE, EXTRA_MODULE)
        (self.root / "suitecase_seed1.py").unlink()

        proc = self.run_report()
        self.assertEqual(proc.returncode, suite_report.EXIT_DRIFT, proc.stdout + proc.stderr)
        self.assertIn(
            "removed: suitecase_seed1.ExtraTest.test_extra (baseline pass)", proc.stdout
        )

    def test_changed_status_is_reported_and_exits_one(self):
        self.seed_baseline(PASS_MODULE)
        self.write_case("seed0", SAME_ID_FAILING_MODULE)  # same id, now failing

        proc = self.run_report()
        self.assertEqual(proc.returncode, suite_report.EXIT_DRIFT, proc.stdout + proc.stderr)
        self.assertIn(
            "changed: suitecase_seed0.PassTest.test_ok: pass -> fail", proc.stdout
        )

    def test_missing_baseline_exits_two_with_hint(self):
        self.write_case("pass", PASS_MODULE)
        proc = self.run_report()
        self.assertEqual(proc.returncode, suite_report.EXIT_ERROR, proc.stdout + proc.stderr)
        self.assertIn("--update", proc.stderr)

    def test_missing_tests_dir_exits_two(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ENGINE),
                "--tests-dir",
                str(self.root / "nope"),
                "--baseline",
                str(self.baseline),
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(proc.returncode, suite_report.EXIT_ERROR, proc.stdout + proc.stderr)
        self.assertIn("tests directory not found", proc.stderr)


if __name__ == "__main__":
    unittest.main()
