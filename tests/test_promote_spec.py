"""Unit tests for the spec-builder engine (promote_spec.py).

Covers the new-template `check` gate (spec 002, TASK-01): the accepted
section set (0-8), the new section-5 task shape (Task -> Depends On +
Verify/Expect pair), the Verify/Expect static-oracle lint, and the
canonical Status: receipt set.
"""

import importlib.util
import os
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
    fd, name = tempfile.mkstemp(suffix=".md", prefix="draft-")
    os.close(fd)
    path = Path(name)
    path.write_text(body, encoding="utf-8")
    return path


class TestNewTemplateCheck(unittest.TestCase):
    """check_draft() against the new 0-8 section set and section-5 task shape."""

    def test_lane_a_full_template_passes(self):
        draft = write_draft(lane_a_draft())
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, missing, violations = promote_spec.check_draft(draft, "A")
        self.assertTrue(passed, f"missing={missing!r} violations={violations!r}")
        self.assertEqual(missing, [])
        self.assertEqual(violations, [])

    def test_lane_b_sections_pass(self):
        draft = write_draft(lane_b_draft())
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, missing, violations = promote_spec.check_draft(draft, "B")
        self.assertTrue(passed, f"missing={missing!r} violations={violations!r}")

    def test_lane_a_missing_sections_reported(self):
        text = lane_a_draft()
        for n in (2, 3, 6, 7, 8):
            lines = []
            skip = False
            for line in text.splitlines():
                if re.match(rf"^##\s+{n}\.", line.strip()):
                    skip = True
                    continue
                if line.strip().startswith("## "):
                    skip = False
                if not skip:
                    lines.append(line)
            draft = write_draft("\n".join(lines))
            self.addCleanup(draft.unlink, missing_ok=True)
            passed, missing, _ = promote_spec.check_draft(draft, "A")
            self.assertFalse(passed)
            self.assertIn(n, missing)

    def test_no_tasks_rejected(self):
        text = lane_a_draft()
        start = text.index("### Task 1:")
        end = text.index("## 6. Gates")
        draft = write_draft(text[:start] + text[end:])
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("no '### Task N:' blocks" in v for v in violations))

    def test_missing_depends_on(self):
        text = lane_a_draft().replace("- Depends On: None\n", "", 1)
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("'Depends On:'" in v for v in violations))

    def test_missing_verify(self):
        text = lane_a_draft().replace("- Verify: `python -m unittest tests.test_sandbox -v`\n", "", 1)
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("'Verify:'" in v for v in violations))

    def test_missing_expect(self):
        text = lane_a_draft().replace("- Expect: \"OK\"\n", "", 1)
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
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
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("no-op" in v for v in violations))

    def test_whole_command_expect_rejected(self):
        text = lane_a_draft().replace(
            '- Expect: "OK"',
            '- Expect: "python -m unittest tests.test_sandbox -v"',
            1,
        )
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("whole 'Verify:'" in v for v in violations))

    def test_expect_marker_in_command_allowed(self):
        # A marker the command itself emits (grep -o) is a valid oracle, so a
        # marker appearing as a substring of the Verify command is allowed.
        text = lane_a_draft().replace(
            "- Verify: `python -m unittest tests.test_sandbox -v`\n- Expect: \"OK\"",
            "- Verify: `grep -o SB-MARKER src/sandbox.py | tail -1`\n- Expect: \"SB-MARKER\"",
            1,
        )
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertTrue(passed, violations)

    def test_lane_b_bad_depends_on(self):
        text = lane_b_draft().replace("- Depends On: None", "- Depends On: bogus")
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "B")
        self.assertFalse(passed)
        self.assertTrue(any("Task N" in v for v in violations))


class TestCanonicalStatuses(unittest.TestCase):
    """The canonical Status: receipt set (spec 002, section 2.1)."""

    def test_canonical_set(self):
        self.assertEqual(
            set(promote_spec.CANONICAL_STATUSES),
            {
                "DRAFTED",
                "APPROVED",
                "PROVISIONAL",
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

    def test_status_value_leading_token(self):
        self.assertIn(
            promote_spec.status_value("Status: DRAFTED | Date: 2026-09-26").split()[0],
            promote_spec.CANONICAL_STATUSES,
        )


def spec_group_text() -> str:
    """A promoted NNN-SPEC-<slug>.md body with two section 5 tasks (for compile)."""
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
        # fingerprint is the sha256 approval key shared with verify.py (C1);
        # the command/expect/cwd fields are the human-readable companion copy.
        entry = data["approvals"][0]
        self.assertRegex(entry["fingerprint"], r"^[0-9a-f]{64}$")
        self.assertIn("command", entry)
        self.assertIn("expect", entry)
        self.assertIn("cwd", entry)
        # compile stamps Status: COMPILED on the spec
        text = self.spec.read_text(encoding="utf-8")
        self.assertEqual(promote_spec.status_value(text), "COMPILED")

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


class TestTargetFilesPerTask(unittest.TestCase):
    """C2: Target Files drive per-task Owns and are validated."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="c2-targets-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.spec = make_group_sandbox(self.root)

    @staticmethod
    def _owns(text: str) -> list[str]:
        body = text.split("## Owns", 1)[1].split("\n## ", 1)[0]
        return [ln.strip() for ln in body.splitlines() if ln.strip().startswith("-")]

    def test_check_rejects_missing_target_files(self):
        text = lane_a_draft().replace("- Target Files: [MODIFY] src/sandbox.py\n", "", 1)
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("Target Files" in v for v in violations), violations)

    def test_check_rejects_overlapping_target_files(self):
        text = lane_a_draft().replace(
            "- Target Files: [MODIFY] src/app.py",
            "- Target Files: [MODIFY] src/sandbox.py",
            1,
        )
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("already owned" in v for v in violations), violations)

    def test_compiled_owns_are_per_task(self):
        promote_spec.compile_spec(self.spec, self.root)
        specs = self.root / "specs"
        t1 = next(specs.glob("009-TASK-01-*")).read_text(encoding="utf-8")
        t2 = next(specs.glob("009-TASK-02-*")).read_text(encoding="utf-8")
        self.assertEqual(self._owns(t1), ["- [MODIFY] src/sandbox.py"])
        self.assertEqual(self._owns(t2), ["- [NEW] src/app.py"])

    def test_compile_refuses_missing_target_files(self):
        self.spec.write_text(
            "## 5. Tasks & Outcomes\n\n"
            "### Task 1: x\n"
            "- Depends On: None\n"
            '- Verify: `python -m unittest tests.test_sandbox -v`\n'
            '- Expect: "OK"\n',
            encoding="utf-8",
        )
        with self.assertRaises(SystemExit):
            promote_spec.compile_spec(self.spec, self.root)


class TestStatusTransitions(unittest.TestCase):
    """C4: promote writes canonical receipts; `transition` enforces legal edges."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="transition-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.spec = make_group_sandbox(self.root)  # Status: APPROVED

    def test_promote_writes_a_canonical_status(self):
        self.assertIn(promote_spec.normalize_status("APPROVED"),
                      promote_spec.CANONICAL_STATUSES)
        self.assertIn(promote_spec.normalize_status("PROVISIONAL").split()[0],
                      promote_spec.CANONICAL_STATUSES)
        token = promote_spec.status_token(self.spec.read_text(encoding="utf-8"))
        self.assertIn(token, promote_spec.CANONICAL_STATUSES)

    def test_transition_legal_edge(self):
        promote_spec.transition_spec(self.spec, "COMPILED", self.root)
        self.assertEqual(
            promote_spec.status_token(self.spec.read_text(encoding="utf-8")),
            "COMPILED",
        )

    def test_transition_illegal_edge_refused(self):
        with self.assertRaises(SystemExit):
            promote_spec.transition_spec(self.spec, "REVIEWED", self.root)

    def test_transition_non_canonical_refused(self):
        with self.assertRaises(SystemExit):
            promote_spec.transition_spec(self.spec, "DONE", self.root)

    def test_check_rejects_non_canonical_status(self):
        path = write_draft(lane_b_draft().replace("Status: DRAFTED", "Status: DONE"))
        self.addCleanup(path.unlink)
        passed, _missing, violations = promote_spec.check_draft(path, "B")
        self.assertFalse(passed)
        self.assertTrue(any("canonical" in v for v in violations))


class TestSpecsReadmeScaffold(unittest.TestCase):
    """H2: the fresh specs/README scaffold names NNN-SPEC-<slug>.md, no dead block."""

    def test_stub_names_the_canonical_spec_filename(self):
        stub = promote_spec._specs_readme_stub()
        self.assertIn("NNN-SPEC-<slug>.md", stub)
        self.assertNotIn("feature-slug", stub)
        self.assertNotIn("TAG-INDEX", stub)


if __name__ == "__main__":
    unittest.main()
