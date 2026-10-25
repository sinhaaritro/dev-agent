"""Unit tests for the spec-builder engine (promote_spec.py).

Covers the new-template `check` gate (spec 002, TASK-01): the accepted
section set (0-8), the new section-5 task shape (Task -> Depends On +
Verify/Expect pair), the Verify/Expect static-oracle lint, and the
canonical Status: receipt set.
"""

import argparse
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "skills" / "dev-agent" / "runtime" / "devagent"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
ENGINE = RUNTIME / "specs.py"

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
        text = lane_a_draft().replace(
            "- Verify: `python -m unittest tests.test_sandbox -v`\n", "", 1
        )
        draft = write_draft(text)
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("'Verify:'" in v for v in violations))

    def test_missing_expect(self):
        text = lane_a_draft().replace('- Expect: "OK"\n', "", 1)
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
            '- Verify: `python -m unittest tests.test_sandbox -v`\n- Expect: "OK"',
            '- Verify: `grep -o SB-MARKER src/sandbox.py | tail -1`\n- Expect: "SB-MARKER"',
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
            self.assertEqual(
                promote_spec.validate_task_file(f.read_text(encoding="utf-8")), []
            )
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

    def test_compile_scrubs_spec_refs_from_task_overview(self):
        text = self.spec.read_text(encoding="utf-8").replace(
            "Sandbox group for the compile/purge/sync/accept subcommands.",
            "Builds on spec 004 and the specs/004-SPEC-sandbox.md contract, see ADR-001.",
        )
        self.spec.write_text(text, encoding="utf-8")
        promote_spec.compile_spec(self.spec, self.root)
        task = next((self.root / "specs").glob("009-TASK-01-*.md"))
        body = task.read_text(encoding="utf-8")
        self.assertIn("an earlier spec", body)
        self.assertIn("an earlier decision", body)
        self.assertIn("the spec workspace", body)
        self.assertNotRegex(body, promote_spec.DANGLING_REF_RE.pattern)
        self.assertNotRegex(body, promote_spec.SPECS_REF_RE.pattern)
        # the spec itself keeps its own wording (it lives under specs/)
        self.assertIn("spec 004", self.spec.read_text(encoding="utf-8"))

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
                + promote_spec.TOC_START
                + "\n"
                + promote_spec.TOC_END
                + "\n",
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
        report = self.root / "specs" / "009-REPORT-sandbox-group.md"
        report.write_text("# REPORT - 009\n\nReview: PASS\n", encoding="utf-8")
        promote_spec.accept_spec(self.spec, self.root)
        text = self.spec.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^Status:\s*COMPLETED")
        self.assertRegex(text, r"(?m)^Done: \d{4}-\d{2}-\d{2}\s*$")

    def test_accept_requires_reviewed(self):
        self.spec.write_text(
            "---\ntags: [sandbox]\n---\n\n# 009: Sandbox Group\n\nStatus: BUILT\n",
            encoding="utf-8",
        )
        report = self.root / "specs" / "009-REPORT-sandbox-group.md"
        report.write_text("# REPORT - 009\n\nReview: PASS\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            promote_spec.accept_spec(self.spec, self.root)
        self.assertIn("REVIEWED", str(ctx.exception))

    def test_accept_requires_green_report(self):
        self.spec.write_text(
            "---\ntags: [sandbox]\n---\n\n# 009: Sandbox Group\n\nStatus: REVIEWED\n",
            encoding="utf-8",
        )
        with self.assertRaises(SystemExit) as ctx:
            promote_spec.accept_spec(self.spec, self.root)
        self.assertIn("NNN-REPORT", str(ctx.exception))

    def test_accept_rejects_failed_report(self):
        self.spec.write_text(
            "---\ntags: [sandbox]\n---\n\n# 009: Sandbox Group\n\nStatus: REVIEWED\n",
            encoding="utf-8",
        )
        report = self.root / "specs" / "009-REPORT-sandbox-group.md"
        report.write_text(
            "# REPORT - 009\n\nReview: FAIL (not MET)\n", encoding="utf-8"
        )
        with self.assertRaises(SystemExit) as ctx:
            promote_spec.accept_spec(self.spec, self.root)
        self.assertIn("green NNN-REPORT", str(ctx.exception))


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
        text = lane_a_draft().replace(
            "- Target Files: [MODIFY] src/sandbox.py\n", "", 1
        )
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
            "- Verify: `python -m unittest tests.test_sandbox -v`\n"
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
        self.assertIn(
            promote_spec.normalize_status("APPROVED"), promote_spec.CANONICAL_STATUSES
        )
        self.assertIn(
            promote_spec.normalize_status("PROVISIONAL").split()[0],
            promote_spec.CANONICAL_STATUSES,
        )
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


class TaskSlugTest(unittest.TestCase):
    def test_long_title_truncates_without_trailing_hyphen(self):
        # m5: truncation must not leave a dangling hyphen.
        text = "### Task 1: strip generated blocks from docs readme machinery\n"
        slug = promote_spec._slug_from_title_or_name("007-SPEC-x.md", text)
        self.assertTrue(slug)
        self.assertLessEqual(len(slug), 40)
        self.assertFalse(slug.endswith("-"))

    def test_short_title_is_kept_whole(self):
        text = "### Task 2: wire sandbox into the app\n"
        self.assertEqual(
            promote_spec._slug_from_title_or_name("007-SPEC-x.md", text),
            "wire-sandbox-into-the-app",
        )


class PromotionIdentityTest(unittest.TestCase):
    """A repeat promotion of the same plan is refused (title is the identity)."""

    def test_duplicate_title_is_found_across_id_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs = Path(tmp)
            existing = specs / "001-SPEC-cache-layer.md"
            existing.write_text(
                "# 001-SPEC: Cache Layer\n\nStatus: COMPILED\n", encoding="utf-8"
            )
            for draft_title in (
                "# [SPEC-ID]: Cache Layer",
                "# 042: cache layer",
                "# 001-SPEC:   Cache   Layer",
            ):
                self.assertEqual(
                    promote_spec.find_existing_by_title(specs, draft_title),
                    existing,
                    draft_title,
                )
            self.assertIsNone(
                promote_spec.find_existing_by_title(specs, "# [SPEC-ID]: Other Plan")
            )

    def test_draft_without_tags_fails_the_check_gate(self):
        body = lane_b_draft()
        body = body.split("---\n", 2)[2]
        draft = write_draft(body)
        self.addCleanup(draft.unlink, missing_ok=True)
        violations = promote_spec._draft_tag_violations(draft)
        self.assertTrue(any("missing 'tags:'" in v for v in violations), violations)


class LaneADependsOnTest(unittest.TestCase):
    def test_lane_a_rejects_prose_depends_on(self):
        draft = write_draft(
            lane_a_draft().replace("Depends On: Task 1", "Depends On: after task 1")
        )
        self.addCleanup(draft.unlink, missing_ok=True)
        passed, _missing, violations = promote_spec.check_draft(draft, "A")
        self.assertFalse(passed)
        self.assertTrue(any("Depends On" in v for v in violations), violations)


class BacktickExpectTest(unittest.TestCase):
    def test_compile_normalizes_backtick_expect_in_approvals(self):
        import hashlib
        import json

        with tempfile.TemporaryDirectory(prefix="backtick-") as tmp:
            root = Path(tmp)
            spec = make_group_sandbox(root)
            spec.write_text(
                spec.read_text(encoding="utf-8").replace(
                    '- Expect: "SB-PASS"', "- Expect: `SB-PASS`"
                ),
                encoding="utf-8",
            )
            promote_spec.compile_spec(spec, root)
            data = json.loads(
                (root / "specs" / "009-APPROVALS-sandbox-group.json").read_text(
                    encoding="utf-8"
                )
            )
            entry = next(a for a in data["approvals"] if a["task"] == "Task 1")
            self.assertEqual(entry["expect"], "SB-PASS")
            payload = f"{entry['command']}|SB-PASS|."
            self.assertEqual(
                entry["fingerprint"],
                hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            )


class CompileCheckGateTest(unittest.TestCase):
    def test_compile_refuses_a_noop_verify_and_writes_nothing(self):
        with tempfile.TemporaryDirectory(prefix="compile-check-") as tmp:
            root = Path(tmp)
            spec = make_group_sandbox(root)
            spec.write_text(
                spec.read_text(encoding="utf-8").replace(
                    "- Verify: `python -m unittest tests.test_sandbox -v`",
                    "- Verify: `true`",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                promote_spec.compile_spec(spec, root)
            self.assertEqual(list((root / "specs").glob("009-TASK-*")), [])


class TagScopeTest(unittest.TestCase):
    def test_tag_lint_requires_tags_on_specs_and_topic_docs(self):
        docs = {
            "specs": [{"name": "001-SPEC-x.md", "text": "# x", "tags": []}],
            "topics": [{"name": "auth.md", "text": "# auth", "tags": []}],
        }
        violations = promote_spec._tag_lint(docs)
        self.assertTrue(
            any("specs/001-SPEC-x.md: missing" in v for v in violations), violations
        )
        self.assertTrue(
            any("docs/auth.md: missing" in v for v in violations), violations
        )

    def test_topic_docs_are_not_required_to_carry_tags_in_specs_folder(self):
        docs = {
            "specs": [{"name": "001-TASK-01-x.md", "text": "# t", "tags": []}],
            "topics": [],
        }
        self.assertEqual(promote_spec._tag_lint(docs), [])

    def test_tag_lint_scans_folder_style_topics(self):
        with tempfile.TemporaryDirectory(prefix="tag-folder-") as tmp:
            root = Path(tmp)
            topic = root / "docs" / "auth" / "core.md"
            topic.parent.mkdir(parents=True)
            topic.write_text("# Auth core\n", encoding="utf-8")
            docs = promote_spec._scan_docs(root)
            violations = promote_spec._tag_lint(docs)
            self.assertTrue(
                any("docs/auth/core.md: missing" in v for v in violations), violations
            )

    def test_tag_rename_reaches_topic_docs(self):
        with tempfile.TemporaryDirectory(prefix="tag-rename-") as tmp:
            root = Path(tmp)
            topic = root / "docs" / "auth.md"
            topic.parent.mkdir(parents=True)
            topic.write_text(
                "---\ntags: [auth, cookies]\n---\n\n# Auth\n", encoding="utf-8"
            )
            rc = promote_spec._tag_rename(
                argparse.Namespace(root=root, old="cookies", new="sessions")
            )
            self.assertEqual(rc, 0)
            text = topic.read_text(encoding="utf-8")
            self.assertIn("sessions", text)
            self.assertNotIn("cookies", text)


class TaskContractRenderTest(unittest.TestCase):
    """C2/D10: rendered task files carry the real skills and the read item."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="contract-render-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.spec = make_group_sandbox(self.root)

    def add_skill(self, name: str) -> None:
        d = self.root / ".agents" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\ntags:\n  - x\n---\n", encoding="utf-8"
        )

    def task_text(self, num: int) -> str:
        files = sorted((self.root / "specs").glob(f"009-TASK-{num:02d}-*"))
        self.assertEqual(len(files), 1)
        return files[0].read_text(encoding="utf-8")

    def test_renders_declared_skill_with_its_path_and_read_item(self):
        self.add_skill("astro-framework")
        text = self.spec.read_text(encoding="utf-8").replace(
            "- Target Files: [MODIFY] src/sandbox.py\n- Depends On: None\n",
            "- Target Files: [MODIFY] src/sandbox.py\n"
            "- Depends On: None\n"
            "- Skills: astro-framework\n",
        )
        self.spec.write_text(text, encoding="utf-8")
        promote_spec.compile_spec(self.spec, self.root)
        rendered = self.task_text(1)
        self.assertIn(
            "- astro-framework (.agents/skills/astro-framework/SKILL.md)", rendered
        )
        self.assertIn('- [ ] read every skill under "Skills to use"', rendered)
        # the old hardcoded spec-builder skill is gone
        self.assertNotIn("spec-builder", rendered)
        self.assertNotIn("## Upstream interfaces", rendered)
        # Task 2 declares no skills -> no Skills section, no read item
        other = self.task_text(2)
        self.assertNotIn("## Skills to use", other)
        self.assertNotIn("read every skill", other)

    def test_area_skills_are_inherited(self):
        self.add_skill("astro-framework")
        (self.root / "AGENTS.md").write_text(
            "## Commands\n\n"
            "### astro-site\n"
            "- Build: npm run build\n"
            "- Test: npm test\n"
            "- Skills: astro-framework\n\n"
            "### python-scripts\n"
            "- Build: python -m compileall .\n"
            "- Test: python -m unittest\n",
            encoding="utf-8",
        )
        text = (
            self.spec.read_text(encoding="utf-8")
            .replace(
                "- Target Files: [MODIFY] src/sandbox.py\n- Depends On: None\n",
                "- Target Files: [MODIFY] src/sandbox.py\n"
                "- Depends On: None\n"
                "- Area: astro-site\n",
            )
            .replace(
                "- Target Files: [NEW] src/app.py\n- Depends On: Task 1\n",
                "- Target Files: [NEW] src/app.py\n"
                "- Depends On: Task 1\n"
                "- Area: python-scripts\n",
            )
        )
        self.spec.write_text(text, encoding="utf-8")
        promote_spec.compile_spec(self.spec, self.root)
        self.assertIn(
            "astro-framework (.agents/skills/astro-framework/SKILL.md)",
            self.task_text(1),
        )
        self.assertNotIn("## Skills to use", self.task_text(2))

    def test_compile_refuses_an_unresolvable_skill(self):
        text = self.spec.read_text(encoding="utf-8").replace(
            "- Target Files: [MODIFY] src/sandbox.py\n- Depends On: None\n",
            "- Target Files: [MODIFY] src/sandbox.py\n"
            "- Depends On: None\n"
            "- Skills: missing-skill\n",
        )
        self.spec.write_text(text, encoding="utf-8")
        buf = StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit):
            promote_spec.compile_spec(self.spec, self.root)
        self.assertIn("missing-skill", buf.getvalue())
        self.assertFalse(list((self.root / "specs").glob("009-TASK-*")))


class TaskLintTest(unittest.TestCase):
    """Area and contract-closure lints fail the check gate."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="task-lint-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.spec = make_group_sandbox(self.root)
        (self.root / "AGENTS.md").write_text(
            "## Commands\n\n"
            "### astro-site\n- Build: npm run build\n- Test: npm test\n\n"
            "### python-scripts\n- Build: python -m compileall .\n"
            "- Test: python -m unittest\n",
            encoding="utf-8",
        )

    def test_multi_area_project_requires_area_per_task(self):
        passed, _, violations = promote_spec.check_draft(self.spec, "A", self.root)
        self.assertFalse(passed)
        self.assertTrue(any("missing 'Area:'" in v for v in violations), violations)

    def test_unknown_area_is_rejected(self):
        text = self.spec.read_text(encoding="utf-8").replace(
            "- Target Files: [MODIFY] src/sandbox.py\n- Depends On: None\n",
            "- Target Files: [MODIFY] src/sandbox.py\n"
            "- Depends On: None\n"
            "- Area: nowhere\n",
        )
        self.spec.write_text(text, encoding="utf-8")
        _, _, violations = promote_spec.check_draft(self.spec, "A", self.root)
        self.assertTrue(
            any("unknown 'Area:' 'nowhere'" in v for v in violations), violations
        )

    def test_contract_change_requires_every_caller_owned(self):
        text = (
            self.spec.read_text(encoding="utf-8")
            .replace(
                "- Target Files: [MODIFY] src/sandbox.py\n- Depends On: None\n",
                "- Target Files: [MODIFY] src/sandbox.py\n"
                "- Depends On: None\n"
                "- Area: python-scripts\n"
                "- Contract Changes: src/sandbox.py\n"
                "- Callers: src/app.py\n",
            )
            .replace(
                "- Target Files: [NEW] src/app.py\n- Depends On: Task 1\n",
                "- Target Files: [NEW] src/app.py\n"
                "- Depends On: Task 1\n"
                "- Area: python-scripts\n",
            )
        )
        self.spec.write_text(text, encoding="utf-8")
        _, _, violations = promote_spec.check_draft(self.spec, "A", self.root)
        self.assertTrue(
            any(
                "caller 'src/app.py' is not in this task's Target Files" in v
                for v in violations
            ),
            violations,
        )

    def test_shim_compatibility_waives_caller_closure(self):
        text = (
            self.spec.read_text(encoding="utf-8")
            .replace(
                "- Target Files: [MODIFY] src/sandbox.py\n- Depends On: None\n",
                "- Target Files: [MODIFY] src/sandbox.py\n"
                "- Depends On: None\n"
                "- Area: python-scripts\n"
                "- Contract Changes: src/sandbox.py\n"
                "- Compatibility: shim\n",
            )
            .replace(
                "- Target Files: [NEW] src/app.py\n- Depends On: Task 1\n",
                "- Target Files: [NEW] src/app.py\n"
                "- Depends On: Task 1\n"
                "- Area: python-scripts\n",
            )
        )
        self.spec.write_text(text, encoding="utf-8")
        passed, _, violations = promote_spec.check_draft(self.spec, "A", self.root)
        self.assertTrue(passed, violations)


class SpecsIndexFilterTest(unittest.TestCase):
    """specs/README.md indexes groups only (SPEC/REPORT/ESCALATION)."""

    def test_task_files_and_approvals_are_not_indexed(self):
        with tempfile.TemporaryDirectory(prefix="toc-filter-") as tmp:
            root = Path(tmp)
            specs = root / "specs"
            specs.mkdir()
            (root / "AGENTS.md").write_text("# a\n", encoding="utf-8")
            for name in (
                "001-SPEC-alpha.md",
                "001-TASK-01-alpha.md",
                "001-APPROVALS-alpha.json",
                "001-REPORT-alpha.md",
                "001-ESCALATION-alpha.md",
                "002-A01.md",
                "002-SPEC-beta.md",
            ):
                (specs / name).write_text(
                    "# " + name + "\n\nStatus: DRAFTED\n", encoding="utf-8"
                )
            promote_spec.sync_specs_readme(root)
            readme = (specs / "README.md").read_text(encoding="utf-8")
            self.assertIn("001-SPEC-alpha.md", readme)
            self.assertIn("001-REPORT-alpha.md", readme)
            self.assertIn("001-ESCALATION-alpha.md", readme)
            self.assertIn("002-A01.md", readme)
            self.assertIn("002-SPEC-beta.md", readme)
            self.assertNotIn("001-TASK-01-alpha.md", readme)
            self.assertNotIn("001-APPROVALS-alpha.json", readme)
            # within one NNN: SPEC -> REPORT -> ESCALATION
            spec_pos = readme.index("001-SPEC-alpha.md")
            report_pos = readme.index("001-REPORT-alpha.md")
            escal_pos = readme.index("001-ESCALATION-alpha.md")
            self.assertLess(spec_pos, report_pos)
            self.assertLess(report_pos, escal_pos)
            # a sub-ID sorts before its parent NNN's named companions
            self.assertLess(
                readme.index("002-A01.md"), readme.index("002-SPEC-beta.md")
            )


if __name__ == "__main__":
    unittest.main()
