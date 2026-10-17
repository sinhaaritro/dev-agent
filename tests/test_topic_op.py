"""Regression suite for the engine's Topic-Based ADR `topic` operation.

Pins the topic contract: one doc per subsystem directly under docs/ with a
'## Current State' + '## Decision Log' (ID subheadings), topic-global
<TOPIC>-D<nn> IDs scanned across all folder sub-files, revision by
supersede (never delete+recreate, never reuse an ID, Current State updated
in place), and cross-topic revisions linked by Affects (primary) + Ref
(reciprocal) heading anchors.

Each test builds a sandbox repo under ``tempfile.TemporaryDirectory`` (an
``AGENTS.md`` marker) and drives the engine as a subprocess, exactly as
system.md invokes it.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = (
    Path(__file__).resolve().parent.parent
    / ".agents" / "skills" / "spec-builder" / "scripts" / "promote_spec.py"
)

ROOT_README = "# Sandbox Project\n\nKnown root README content for the regression suite.\n"

DRAFT_PLAN = """---
tags: [sandbox]
---

# [SPEC-ID]: Sandbox Feature

Status: DRAFT

## 1. Goal & Context

Goal text.

## 2. Design & Trade-offs

Design text.

## 3. Risks & Open Questions

Risk text.

## 4. Affected Files & Contracts

- Deleted: none

## 5. Task DAG

### Task 1: Sandbox

- Target Files: [NEW] src/sandbox.py
- Depends On: None
- Subtasks:
  - [ ] 1.1 Build it.
    - Input: goal
    - Output: artifact
    - Verify: test -f src/sandbox.py
    - Expect: file present

## 6. Verification Commands

- Test Command: python -m unittest

## 7. Rollback Strategy

Revert the change.
"""

# the topic lifecycle must not clobber the project's root README
ROOT_GUARD = ("README.md",)


def run(args, cwd):
    return subprocess.run(
        [sys.executable, str(ENGINE)] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def make_sandbox(tmp: Path) -> Path:
    (tmp / "AGENTS.md").write_text("# sandbox project\n", encoding="utf-8")
    return tmp


def seed_topic(path: Path, name: str, entries: list[tuple[str, str]]) -> None:
    """Write a minimal topic doc: frontmatter, state, log with the given entries.

    ``entries`` is a list of (decision_id, title) pairs already carrying a
    Why/Date body so the file is contract-complete.
    """
    ns = name.upper()
    lines = [
        "---",
        f"tags: [{name}]",
        "---",
        "",
        f"# {name.capitalize()}",
        "",
        "## Current State",
        "",
        "Seeded state.",
        "",
        "## Decision Log",
        "",
    ]
    for i, (dec_id, title) in enumerate(entries, start=1):
        assert dec_id.startswith(ns + "-D"), (dec_id, ns)
        lines += [
            f"### {dec_id} - {title}",
            f"- **Date:** 2026-01-0{i}",
            f"- **Why:** Seeded reason {i}.",
            "",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


class TopicOpTests(unittest.TestCase):
    def test_create_folder_topic_allocates_id_across_all_subfiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sandbox(Path(tmp))
            docs = root / "docs"
            folder = docs / "db"
            seed_topic(folder / "core.md", "db", [("DB-D01", "Engine")])
            seed_topic(folder / "gotchas.md", "db", [("DB-D03", "Retries")])

            result = run(
                ["topic", "db", "--file", "core",
                 "--why", "Switch to the new engine", "--title", "New engine",
                 "--docs-dir", str(docs)],
                root,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            core = (folder / "core.md").read_text(encoding="utf-8")
            gotchas = (folder / "gotchas.md").read_text(encoding="utf-8")
            # the ID is topic-global: max across both sub-files is D03, so the
            # new entry is D04 - not D02 (per-file) and not a reused number
            self.assertIn("### DB-D04 - New engine", core)
            self.assertIn("- **Why:** Switch to the new engine", core)
            self.assertIn("### DB-D01 - Engine", core)
            # the other sub-file is untouched
            self.assertIn("### DB-D03 - Retries", gotchas)
            self.assertNotIn("DB-D04", gotchas)

    def test_create_single_file_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sandbox(Path(tmp))
            docs = root / "docs"

            result = run(
                ["topic", "auth",
                 "--why", "Cookies beat JWT for our session model",
                 "--title", "Session cookies over JWT",
                 "--tags", "auth,session",
                 "--docs-dir", str(docs)],
                root,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            self.assertTrue((docs / "auth.md").is_file())
            text = (docs / "auth.md").read_text(encoding="utf-8")
            self.assertIn("tags: [auth, session]", text)
            self.assertIn("## Current State", text)
            self.assertIn("## Decision Log", text)
            self.assertIn("### AUTH-D01 - Session cookies over JWT", text)
            self.assertIn("- **Why:** Cookies beat JWT for our session model", text)

    def test_revision_supersedes_without_reusing_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sandbox(Path(tmp))
            docs = root / "docs"
            seed_topic(
                docs / "file.md", "file",
                [("FILE-D01", "Initial layout"), ("FILE-D02", "Nested")],
            )

            result = run(
                ["topic", "file",
                 "--why", "Flat layout wins", "--title", "Flat layout",
                 "--supersedes", "FILE-D02",
                 "--state", "Flat layout, no nesting.",
                 "--docs-dir", str(docs)],
                root,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            text = (docs / "file.md").read_text(encoding="utf-8")
            # the revision takes the next ID - it never reuses the reversed one
            self.assertIn("### FILE-D03 - Flat layout", text)
            self.assertIn("- **Supersedes:** FILE-D02", text)
            # the reversed entry stays, marked - never deleted
            self.assertIn("### FILE-D02 - Nested (superseded)", text)
            self.assertIn("### FILE-D01 - Initial layout", text)
            # the Current State was updated in place
            self.assertIn("Flat layout, no nesting.", text)
            self.assertNotIn("Seeded state.", text)

    def test_cross_topic_revision_writes_affects_and_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sandbox(Path(tmp))
            docs = root / "docs"
            seed_topic(
                docs / "auth.md", "auth",
                [("AUTH-D01", "JWT bearer"), ("AUTH-D02", "localStorage JWT")],
            )
            seed_topic(docs / "api.md", "api", [("API-D01", "Bearer auth header")])

            result = run(
                ["topic", "auth",
                 "--why", "JWT in localStorage is XSS-exposed",
                 "--title", "Back to session cookies",
                 "--supersedes", "AUTH-D02",
                 "--affects", "api.md#api-auth",
                 "--reciprocal", "api",
                 "--reciprocal-why", "Auth arrives via cookie, not bearer header.",
                 "--docs-dir", str(docs)],
                root,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            auth = (docs / "auth.md").read_text(encoding="utf-8")
            api = (docs / "api.md").read_text(encoding="utf-8")
            # primary: new entry with the one-way Affects pointer
            self.assertIn("### AUTH-D03 - Back to session cookies", auth)
            self.assertIn("- **Affects:** api.md#api-auth", auth)
            # affected topic: its own terse entry pointing back at the primary
            self.assertIn("### API-D02 - Cross-topic: AUTH-D03", api)
            self.assertIn("- **Ref:** auth.md#auth-d03", api)

    def test_topic_full_lifecycle_leaves_root_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sandbox(Path(tmp))
            (root / "README.md").write_text(ROOT_README, encoding="utf-8")
            docs = root / "docs"
            draft = root / "specs" / "temp" / "draft-plan.md"
            draft.parent.mkdir(parents=True)
            draft.write_text(DRAFT_PLAN, encoding="utf-8")
            specs = root / "specs"

            promoted = run(
                ["promote", str(draft), "--lane", "B", "--status", "APPROVED",
                 "--specs-dir", str(specs), "--root", str(root)],
                root,
            )
            self.assertEqual(promoted.returncode, 0, promoted.stdout + promoted.stderr)
            spec = next(specs.glob("0*.md"))

            topic = run(
                ["topic", "sandbox-topic", "--why", "Chose the flat layout",
                 "--docs-dir", str(root)],
                root,
            )
            self.assertEqual(topic.returncode, 0, topic.stdout + topic.stderr)

            # nothing engine-side may clobber the project's root README
            self.assertEqual(
                (root / "README.md").read_text(encoding="utf-8"), ROOT_README,
                "root README was rewritten",
            )
            # the artifacts landed under the sandbox docs root
            self.assertTrue(spec.is_file())
            self.assertTrue((docs / "sandbox-topic.md").is_file())
            self.assertIn(
                "### SANDBOX-TOPIC-D01",
                (docs / "sandbox-topic.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
