"""Unit tests for the optional Vetting gate receipt (spec vetting)."""

import importlib.util
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "skills" / "dev-agent" / "runtime" / "devagent"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
ENGINE = RUNTIME / "specs.py"

_spec = importlib.util.spec_from_file_location("promote_spec", ENGINE)
assert _spec is not None and _spec.loader is not None
promote_spec = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("promote_spec", promote_spec)
_spec.loader.exec_module(promote_spec)


DRAFT = """---
tags: [sandbox]
vetting: on
---

# [SPEC-ID]: Vetting sandbox

Status: DRAFTED

## 1. Goal & Context

x

## 5. Tasks & Outcomes

### Task 1: do it
- Target Files: [MODIFY] src/x.py
- Depends On: None
- Verify: `pytest -q`
- Expect: "OK"

## 6. Gates

_(empty)_
"""


class VettingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.draft = Path(self._tmp.name) / "draft-plan.md"
        self.draft.write_text(DRAFT, encoding="utf-8")

    def run_vetting(self, **kwargs):
        args = Namespace(
            draft=self.draft,
            verdict=kwargs.get("verdict"),
            accept=kwargs.get("accept", False),
            note=kwargs.get("note", ""),
        )
        return promote_spec.cmd_vetting(args)

    def text(self):
        return self.draft.read_text(encoding="utf-8")

    def test_off_is_a_noop(self):
        self.draft.write_text(
            DRAFT.replace("vetting: on", "vetting: off"), encoding="utf-8"
        )
        before = self.text()
        self.assertEqual(self.run_vetting(verdict="block"), 0)
        self.assertEqual(self.text(), before)
        self.assertNotIn("### Vetting", self.text())

    def test_pass_records_without_changing_status(self):
        self.assertEqual(self.run_vetting(verdict="pass", note="no issues"), 0)
        text = self.text()
        self.assertIn("### Vetting", text)
        self.assertIn("- Verdict: pass", text)
        self.assertIn("- Note: no issues", text)
        self.assertIn("Status: DRAFTED", text)

    def test_block_sets_plan_revision_required(self):
        self.assertEqual(self.run_vetting(verdict="block", note="missing rollback"), 0)
        text = self.text()
        self.assertIn("- Verdict: block", text)
        self.assertIn("Status: PLAN_REVISION_REQUIRED", text)

    def test_third_block_reaches_the_cap_and_stays_plan_revision(self):
        for _ in range(3):
            self.assertEqual(self.run_vetting(verdict="block", note="again"), 0)
        self.assertEqual(self.text().count("- Verdict: block"), 3)
        self.assertIn("Status: PLAN_REVISION_REQUIRED", self.text())

    def test_pass_closes_a_blocked_revision_loop(self):
        self.run_vetting(verdict="block", note="issue")
        self.assertEqual(self.run_vetting(verdict="pass", note="fixed"), 0)
        text = self.text()
        self.assertIn("- Verdict: pass", text)
        self.assertIn("Status: DRAFTED", text)

    def test_accept_returns_a_blocked_draft_to_drafted(self):
        self.run_vetting(verdict="block", note="issue")
        self.assertEqual(self.run_vetting(accept=True, note="human override"), 0)
        text = self.text()
        self.assertIn("- Verdict: pass", text)
        self.assertIn("- Accepted: human override", text)
        self.assertIn("Status: DRAFTED", text)

    def test_creates_the_gates_section_when_missing(self):
        self.draft.write_text(DRAFT.split("## 6. Gates")[0], encoding="utf-8")
        self.assertEqual(self.run_vetting(verdict="pass"), 0)
        self.assertIn("## 6. Gates", self.text())

    def test_requires_a_verdict_or_accept(self):
        self.assertEqual(self.run_vetting(), 2)

    def test_missing_draft_is_a_named_error(self):
        args = Namespace(
            draft=Path(self._tmp.name) / "missing.md",
            verdict="pass",
            accept=False,
            note="",
        )
        self.assertEqual(promote_spec.cmd_vetting(args), 1)


if __name__ == "__main__":
    unittest.main()
