#!/usr/bin/env python3
"""Meta test runner: snapshot the unit suite and diff it against a baseline.

The unit suite (`tests/test_*.py`) is the contract for the stdlib engines. This
tool answers one question before behavior work starts: *did anything change?*

    python tools/suite_report.py            # run + diff against the baseline
    python tools/suite_report.py --update   # run + rewrite the baseline

It runs the suite in-process with a recording `TestResult`, so every test id is
captured as `pass` / `fail` / `error` / `skip` / `xfail` / `unexpected-pass`.
The result is compared with `tests/.suite-baseline.json` and the delta is
printed as **added / removed / changed**. Exit codes:

    0  no drift (or `--update` wrote the baseline)
    1  unexpected delta (added, removed, or changed test)
    2  usage / missing-baseline error

This tool lives outside `tests/` on purpose: `discover` only collects
`test_*.py` from its start directory, so the runner can never collect itself.

Usage:
    python tools/suite_report.py
    python tools/suite_report.py --update
    python tools/suite_report.py --tests-dir tests --pattern "test_*.py"
"""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TESTS_DIR = "tests"
DEFAULT_PATTERN = "test_*.py"
DEFAULT_BASELINE = Path("tests") / ".suite-baseline.json"

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RecordingResult(unittest.TestResult):
    """A `TestResult` that keeps a deterministic `test id -> status` map."""

    SEVERITY: ClassVar[dict[str, int]] = {
        "pass": 0,
        "skip": 1,
        "xfail": 2,
        "unexpected-pass": 3,
        "fail": 4,
        "error": 5,
    }

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        super().__init__(stream, descriptions, verbosity)
        self.outcomes: dict[str, str] = {}

    def _record(self, test_id: str, status: str) -> None:
        previous = self.outcomes.get(test_id)
        if previous is None or self.SEVERITY[status] >= self.SEVERITY[previous]:
            self.outcomes[test_id] = status

    def addSuccess(self, test):
        self._record(test.id(), "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test.id(), "fail")

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test.id(), "error")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test.id(), "skip")

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._record(test.id(), "xfail")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._record(test.id(), "unexpected-pass")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            status = "fail" if issubclass(err[0], test.failureException) else "error"
            self._record(test.id(), status)


def run_suite(
    tests_dir: Path,
    pattern: str = DEFAULT_PATTERN,
    verbosity: int = 2,
) -> dict[str, str]:
    """Run every test matching `pattern` under `tests_dir`; return id -> status."""
    tests_dir = Path(tests_dir)
    if not tests_dir.is_dir():
        raise FileNotFoundError(f"tests directory not found: {tests_dir}")
    loader = unittest.TestLoader()
    suite = loader.discover(
        str(tests_dir), pattern=pattern, top_level_dir=str(tests_dir)
    )
    runner = unittest.TextTestRunner(
        stream=sys.stderr,
        verbosity=verbosity,
        resultclass=RecordingResult,
    )
    result = runner.run(suite)
    return dict(sorted(result.outcomes.items()))


def diff_baseline(
    baseline: dict[str, str], current: dict[str, str]
) -> dict[str, dict]:
    """Compare two `id -> status` maps; return added / removed / changed buckets."""
    added = {
        test_id: status
        for test_id, status in current.items()
        if test_id not in baseline
    }
    removed = {
        test_id: status
        for test_id, status in baseline.items()
        if test_id not in current
    }
    changed = {
        test_id: {"from": baseline[test_id], "to": current[test_id]}
        for test_id in current
        if test_id in baseline and baseline[test_id] != current[test_id]
    }
    return {"added": added, "removed": removed, "changed": changed}


def has_drift(diff: dict[str, dict]) -> bool:
    return any(diff[key] for key in ("added", "removed", "changed"))


def load_baseline(path: Path) -> dict[str, str]:
    """Read the baseline JSON and return its `tests` map (sorted)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"baseline not found: {path} (run --update to create it)")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable baseline {path}: {exc}") from exc
    tests = data.get("tests")
    if not isinstance(tests, dict):
        raise TypeError(f"baseline {path} has no 'tests' object")
    for test_id, status in tests.items():
        if status not in RecordingResult.SEVERITY:
            raise ValueError(f"baseline {path}: unknown status {status!r} for {test_id}")
    return dict(sorted(tests.items()))


def write_baseline(path: Path, outcomes: dict[str, str]) -> None:
    """Write a deterministic baseline: sorted ids, fixed metadata, trailing newline."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": iso_now(),
        "tests": dict(sorted(outcomes.items())),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def format_report(diff: dict[str, dict], total: int) -> str:
    """Render the delta as added / removed / changed lines plus a summary."""
    lines: list[str] = []
    for test_id, status in sorted(diff["added"].items()):
        lines.append(f"added:   {test_id} ({status})")
    for test_id, status in sorted(diff["removed"].items()):
        lines.append(f"removed: {test_id} (baseline {status})")
    for test_id, change in sorted(diff["changed"].items()):
        lines.append(f"changed: {test_id}: {change['from']} -> {change['to']}")
    if lines:
        counts = (
            f"{len(diff['added'])} added, "
            f"{len(diff['removed'])} removed, "
            f"{len(diff['changed'])} changed"
        )
        lines.append(f"summary: {counts} ({total} tests in this run)")
    else:
        lines.append(f"no drift: {total} tests match the baseline")
    return "\n".join(lines)


def _resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the unit suite and diff it against the golden baseline.",
    )
    parser.add_argument("--tests-dir", default=DEFAULT_TESTS_DIR)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument(
        "--update",
        action="store_true",
        help="write the current outcome map as the new baseline",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the per-test lines from the unittest runner",
    )
    args = parser.parse_args(argv)

    tests_dir = _resolve(args.tests_dir)
    baseline_path = _resolve(args.baseline)

    try:
        outcomes = run_suite(tests_dir, args.pattern, verbosity=0 if args.quiet else 2)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.update:
        write_baseline(baseline_path, outcomes)
        print(f"baseline updated: {baseline_path} ({len(outcomes)} tests)")
        return EXIT_OK

    try:
        baseline = load_baseline(baseline_path)
    except (FileNotFoundError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    diff = diff_baseline(baseline, outcomes)
    print(format_report(diff, len(outcomes)))
    return EXIT_DRIFT if has_drift(diff) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
