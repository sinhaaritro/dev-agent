"""Unit tests for the spec-builder engine (promote_spec.py).

Covers the new-template `check` gate (spec 002, TASK-01): the accepted
section set (0-8), the new section-5 task shape (Task -> Depends On +
Verify/Expect pair), the Verify/Expect static-oracle lint, and the
canonical Status: receipt set.
"""

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = (
    Path(__file__).resolve().parent.parent
    / ".agents" / "skills" / "spec-builder" / "scripts" / "promote_spec.py"
)

_spec = importlib.util.spec_from_file_location("promote_spec", ENGINE)
assert _spec is not None and _spec.loader is not None
promote_spec = importlib.util.module_from_spec(_spec)
sys.modules["promote_spec"] = promote_spec
_spec.loader.exec_module(promote_spec)


def lane_a_draft() -> str:
    return """---
tags: [sandbox, new-template]
---

# [SPEC-ID]: Sandbox Feature

Status: DRAFTED | Date: 2026-09-26

## 1. Goal & Context

Sandbox plan for the new-template check gate.

## 2. The Change

- One coherent change.

## 3. Risks & Open Questions

None.

## 4. Affected Files & Contracts

- Modified: none

## 5. Tasks & Outcomes

### Task 1: implement the sandbox behavior
- Target Files: [MODIFY] src/sandbox.py
- Depends On: None
- Verify: `python -m unittest tests.test_sandbox -v`
- Expect: "OK"

### Task 2: wire the sandbox into the app
- Target Files: [MODIFY] src/app.py
- Depends On: Task 1
- Verify: `python -m unittest tests.test_sandbox -v`
- Expect: "OK"

## 6. Gates

_(empty)_

## 7. Verification Commands

- Build Command: `python -m compileall -q .`

## 8. Rollback Strategy

Revert in reverse task order.
"""


def lane_b_draft() -> str:
    return """---
tags: [sandbox, lane-b]
---

# [SPEC-ID]: Sandbox Lane B

Status: DRAFTED | Date: 2026-09-26

## 1. Goal & Context

Lane B sandbox plan.

## 4. Affected Files & Contracts

- Modified: none

## 5. Tasks & Outcomes

### Task 1: single degenerate task
- Target Files: [MODIFY] src/foo.py
- Depends On: None
- Verify: `python -m unittest tests.test_sandbox -v`
- Expect: "OK"
"""


def write_draft(body: str) -> Path:
    path = Path(tempfile.mkstemp(suffix=".md", prefix="draft-")[1])
    path.write_text(body, encoding="utf-8")
    return path


class TestNewTemplateCheck(unittest.TestCase):
    """check_draft() against the new 0-8 section set and section-5 task shape."""

    def test_lane_a_full_template_passes(self):
        draft = write_draft(lane_a_draft())
        self.addCleanup(draft.unlink)
        passed, missing, violations = promote_spec.check_draft(draft, "A")
        self.assertTrue(passed, "missing=%r violations=%r" % (missing, violations))
        self.assertEqual(missing, [])
        self.assertEqual(violations, [])

    def test_lane_b_sections_pass(self):
        draft = write_draft(lane_b_draft())
        self.addCleanup(draft.unlink)
        passed, missing, violations = promote_spec.check_draft(draft, "B")
        self.assertTrue(passed, "missing=%r violations=%r" % (missing, violations))

    def test_lane_a_missing_sections_reported(self):
        text = lane_a_draft()
        for n in (2, 3, 6, 7, 8):
            lines = []
            skip = False
            for line in text.splitlines():
                if re.match(r"^##\s+%d\." % n, line.strip()):
                    skip = True
                    continue
                if line.strip().startswith("## "):
                    skip = False
                if not skip:
                    lines.append(line)
            draft = write_draft("\n".join(lines))
            self.addCleanup(draft.unlink)
            passed, missing, _ = promote_spec.check_draft(draft, "A")
            self.assertFalse(passed)
            self.assertIn(n, missing)

    def test_no_tasks_rejected(self):
        text = lane_a_draft()
        start = text.index("### Task 1:")
        end = text.index("## 6. Gates")
        draft = write_draft(text[:start] + text[end:])
        self.addCleanup(draft.unlink)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("no '### Task N:' blocks" in v for v in violations))

    def test_missing_depends_on(self):
        text = lane_a_draft().replace("- Depends On: None\n", "", 1)
        draft = write_draft(text)
        self.addCleanup(draft.unlink)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("'Depends On:'" in v for v in violations))

    def test_missing_verify(self):
        text = lane_a_draft().replace("- Verify: `python -m unittest tests.test_sandbox -v`\n", "", 1)
        draft = write_draft(text)
        self.addCleanup(draft.unlink)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("'Verify:'" in v for v in violations))

    def test_missing_expect(self):
        text = lane_a_draft().replace("- Expect: \"OK\"\n", "", 1)
        draft = write_draft(text)
        self.addCleanup(draft.unlink)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("'Expect:'" in v for v in violations))

    def test_noop_verify_rejected(self):
        text = lane_a_draft().replace(
            "- Verify: `python -m unittest tests.test_sandbox -v`",
            "- Verify: `true`",
            1,
        )
        draft = write_draft(text)
        self.addCleanup(draft.unlink)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("no-op" in v for v in violations))

    def test_expect_in_verify_rejected(self):
        text = lane_a_draft().replace(
            '- Expect: "OK"', '- Expect: "unittest"', 1
        )
        draft = write_draft(text)
        self.addCleanup(draft.unlink)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("substring" in v for v in violations))

    def test_lane_b_bad_depends_on(self):
        text = lane_b_draft().replace("- Depends On: None", "- Depends On: bogus")
        draft = write_draft(text)
        self.addCleanup(draft.unlink)
        passed, _, violations = promote_spec.check_draft(draft, "B")
        self.assertFalse(passed)
        self.assertTrue(any("Task N" in v for v in violations))


class TestCanonicalStatuses(unittest.TestCase):
    """The canonical Status: receipt set (spec 002, §2.1)."""

    def test_canonical_set(self):
        self.assertEqual(
            set(promote_spec.CANONICAL_STATUSES),
            {
                "DRAFTED",
                "COMPILED",
                "BUILDING",
                "BUILT",
                "REVIEWED",
                "COMPLETED",
                "PLAN_REVISION_REQUIRED",
                "REVIEW_REVISION_REQUIRED",
                "ESCALATED",
                "ABORTED",
            },
        )

    def test_old_statuses_absent(self):
        for old in ("DRAFT", "APPROVED", "HANDED-OFF", "PLANNED", "PROVISIONAL"):
            self.assertNotIn(old, promote_spec.CANONICAL_STATUSES)

    def test_status_value_leading_token(self):
        self.assertIn(
            promote_spec.status_value("Status: DRAFTED | Date: 2026-09-26").split()[0],
            promote_spec.CANONICAL_STATUSES,
        )


def spec_group_text() -> str:
    """A promoted NNN-SPEC-<slug>.md body with two §5 tasks (for compile)."""
    return """---
tags: [sandbox, group]
---

# 009: Sandbox Group

Status: APPROVED | Date: 2026-09-26

## 1. Goal & Context

Sandbox group for the compile/purge/sync/accept subcommands.

## 2. The Change

- One coherent change.

## 3. Risks & Open Questions

None.

## 4. Affected Files & Contracts

### [MODIFY] src/sandbox.py

One-line purpose.

- Contract:
  - `run(): None`

### [NEW] src/app.py

One-line purpose.

- Contract:
  - exports `wire()`

## 5. Tasks & Outcomes

### Task 1: implement the sandbox behavior
- Target Files: [MODIFY] src/sandbox.py
- Depends On: None
- Verify: `python -m unittest tests.test_sandbox -v`
- Expect: "SB-PASS"

### Task 2: wire sandbox into the app
- Target Files: [NEW] src/app.py
- Depends On: Task 1
- Verify: `python -m unittest tests.test_sandbox -v`
- Expect: "SB-WIRED"

## 6. Gates

_(empty)_

## 7. Verification Commands

- Build Command: `python -m compileall -q .`

## 8. Rollback Strategy

Revert in reverse task order.
"""


def make_group_sandbox(tmp: Path) -> Path:
    """Build a sandbox repo root with one NNN-SPEC-<slug>.md group."""
    (tmp / "AGENTS.md").write_text("# sandbox\n", encoding="utf-8")
    specs = tmp / "specs"
    specs.mkdir()
    spec = specs / "009-SPEC-sandbox-group.md"
    spec.write_text(spec_group_text(), encoding="utf-8")
    return spec


class TestCompilePurgeSyncAccept(unittest.TestCase):
    """TASK-02: the compile / purge / sync / accept subcommands (spec 002)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="group-op-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.spec = make_group_sandbox(self.root)

    def test_validate_task_file_wellformed(self):
        text = (
            "# TASK 009-01 — implement the sandbox behavior\n\n"
            "## Role & rules\nImplement ONLY this task.\n\n"
            "## Project overview\nA sandbox.\n\n"
            "## Task\nImplement it.\n\n"
            "### Progress\n- [ ] implement\n\n"
            "## Owns\n- [MODIFY] src/sandbox.py\n\n"
            "## Reads / Context (read-only)\n- the spec\n\n"
            "## Skills to use\n- spec-builder\n\n"
            "## Upstream interfaces\n```python\ndef f() -> None\n```\n\n"
            "## Verification\n```bash\npython -m unittest tests.test_sandbox -v\n```\n"
            "**Expect:** `SB-PASS`\n"
        )
        self.assertEqual(promote_spec.validate_task_file(text), [])

    def test_validate_task_file_missing_heading(self):
        text = (
            "# TASK 009-01 — t\n\n"
            "## Role & rules\nx\n\n"
            "## Project overview\nx\n\n"
            "## Verification\n```bash\nx\n```\n**Expect:** `y`\n"
        )
        violations = promote_spec.validate_task_file(text)
        self.assertTrue(any("Task" in v for v in violations))
        self.assertTrue(any("Owns" in v for v in violations))

    def test_validate_task_file_verification_without_expect(self):
        text = (
            "# TASK 009-01 — t\n\n"
            "## Role & rules\nx\n\n"
            "## Project overview\nx\n\n"
            "## Task\nt\n\n"
            "### Progress\n- [ ] a\n\n"
            "## Owns\n- x\n\n"
            "## Reads / Context (read-only)\n- x\n\n"
            "## Skills to use\n- x\n\n"
            "## Upstream interfaces\n```python\nx\n```\n\n"
            "## Verification\n```bash\nx\n```\n"
        )
        violations = promote_spec.validate_task_file(text)
        self.assertTrue(any("Expect" in v for v in violations))

    def test_compile_writes_task_files_and_approvals(self):
        written = promote_spec.compile_spec(self.spec, self.root)
        self.assertEqual(len(written), 2)
        for f in written:
            self.assertTrue(f.is_file())
            self.assertEqual(promote_spec.validate_task_file(f.read_text(encoding="utf-8")), [])
        approvals = self.root / "specs" / "009-APPROVALS-sandbox-group.json"
        self.assertTrue(approvals.is_file())
        import json
        data = json.loads(approvals.read_text(encoding="utf-8"))
        self.assertEqual(len(data["approvals"]), 2)
        # fingerprint has no executor field (spec 002 §2.5): command|expect|cwd
        fp = data["approvals"][0]["fingerprint"]
        self.assertEqual(fp.count("|"), 2)
        self.assertNotIn("executor", fp)
        # compile stamps Status: COMPILED on the spec
        text = self.spec.read_text(encoding="utf-8")
        self.assertEqual(promote_spec.status_value(text), "COMPILED")
        self.assertNotIn("Handoff:", text)

    def test_compile_idempotent_compiled_stamp(self):
        promote_spec.compile_spec(self.spec, self.root)
        text_after_first = self.spec.read_text(encoding="utf-8")
        # re-compile should not duplicate the Status: COMPILED stamp
        for f in (self.root / "specs").glob("009-TASK-*"):
            f.unlink()
        promote_spec.compile_spec(self.spec, self.root)
        text_after_second = self.spec.read_text(encoding="utf-8")
        self.assertEqual(text_after_first.count("Status:"), 1)
        self.assertEqual(
            text_after_first.count("COMPILED"),
            text_after_second.count("COMPILED"),
        )

    def test_purge_removes_whole_group(self):
        promote_spec.compile_spec(self.spec, self.root)
        before = {f.name for f in (self.root / "specs").iterdir()}
        self.assertIn("009-SPEC-sandbox-group.md", before)
        self.assertTrue(any(n.startswith("009-TASK-") for n in before))
        self.assertTrue(any(n.startswith("009-APPROVALS-") for n in before))
        promote_spec.purge_spec(self.spec, self.root)
        after = {f.name for f in (self.root / "specs").iterdir()}
        self.assertFalse(any(n.startswith("009-") for n in after), after)

    def test_sync_regenerates_readme_without_deleting(self):
        (self.root / "specs" / "009-SPEC-other.md").write_text(
            "---\ntags: [sandbox]\n---\n\n# 009: Other\n\nStatus: DRAFTED\n",
            encoding="utf-8",
        )
        # ensure a specs/README.md exists with markers
        readme = self.root / "specs" / "README.md"
        if not readme.is_file():
            readme.write_text(
                "# Specs\n\n"
                + promote_spec.TOC_START + "\n" + promote_spec.TOC_END + "\n",
                encoding="utf-8",
            )
        promote_spec.sync_specs_readme(self.root)
        content = readme.read_text(encoding="utf-8")
        self.assertIn("009-SPEC-sandbox-group.md", content)
        self.assertIn("009-SPEC-other.md", content)
        # no deletes
        self.assertTrue(self.spec.is_file())

    def test_accept_stamps_completed(self):
        self.spec.write_text(
            "---\ntags: [sandbox]\n---\n\n# 009: Sandbox Group\n\nStatus: REVIEWED\n",
            encoding="utf-8",
        )
        promote_spec.accept_spec(self.spec, self.root)
        text = self.spec.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^Status:\s*COMPLETED")
        self.assertRegex(text, r"(?m)^Done: \d{4}-\d{2}-\d{2}\s*$")


if __name__ == "__main__":
    unittest.main()
