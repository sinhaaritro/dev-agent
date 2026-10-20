"""Regression suite for the sync-docs subcommand of the map-generator engine.

Pins the AI topic index contract: `sync-docs` scans `docs/` for topic docs
(one `.md` file or one folder per subsystem), reserves the generated
`_topics.md`, the landing `README.md`, and underscore-prefixed names, and
rebuilds `docs/_topics.md` with one block per topic carrying path, covers
(frontmatter tags), and either sections (flat file) or nested files
(folder). `--check` reports whether the on-disk index is fresh.

Each test builds a sandbox repo under ``tempfile.TemporaryDirectory`` and
drives the engine as a subprocess, exactly as dev-agent-framework.md invokes it.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "dev-agent"
    / "runtime"
    / "devagent"
    / "main.py"
)


def run(args, cwd):
    return subprocess.run(
        [sys.executable, str(ENGINE), "map"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


class SyncDocsTests(unittest.TestCase):
    def test_flat_topic_file_produces_entry_with_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "auth.md").write_text(
                "---\n"
                "tags: [auth, session]\n"
                "---\n"
                "\n"
                "# Auth\n"
                "\n"
                "## Current State\n"
                "\n"
                "State text.\n"
                "\n"
                "## Decision Log\n"
                "\n"
                "### AUTH-D01\n"
                "\n"
                "A decision.\n"
                "\n"
                "## Session Flow\n"
                "\n"
                "Flow text.\n",
                encoding="utf-8",
            )
            result = run(["sync-docs", "--root", str(root)], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = (docs / "_topics.md").read_text(encoding="utf-8")
            self.assertIn("## auth", out)
            self.assertIn("  path: docs/auth.md", out)
            self.assertIn("  covers: auth, session", out)
            self.assertIn("  sections:", out)
            self.assertIn("    - Session Flow", out)
            # the contract sections and decision IDs are not routing topics
            self.assertNotIn("Current State", out)
            self.assertNotIn("Decision Log", out)
            self.assertNotIn("AUTH-D01", out)

    def test_heading_fallback_excludes_decision_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "auth.md").write_text(
                "---\ntags: [auth]\n---\n\n"
                "# Auth\n\n"
                "## Current State\n\n"
                "### Session Flow\n\n"
                "Text.\n\n"
                "## Decision Log\n\n"
                "### AUTH-D01\n\n"
                "A decision.\n",
                encoding="utf-8",
            )
            result = run(["sync-docs", "--root", str(root)], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = (docs / "_topics.md").read_text(encoding="utf-8")
            self.assertIn("    - Session Flow", out)
            self.assertNotIn("AUTH-D01", out)

    def test_topic_folder_lists_subfiles_with_covers_and_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "docs" / "storage"
            folder.mkdir(parents=True)
            (folder / "core.md").write_text(
                "---\ntags: [storage, core]\n---\n\n# Storage Core\n\n## Schema\n\nx\n",
                encoding="utf-8",
            )
            (folder / "backups.md").write_text(
                "---\ntags: [storage, backups]\n---\n\n# Storage Backups\n",
                encoding="utf-8",
            )
            result = run(["sync-docs", "--root", str(root)], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = (root / "docs" / "_topics.md").read_text(encoding="utf-8")
            self.assertIn("## storage", out)
            self.assertIn("  path: docs/storage/", out)
            covers_line = next(l for l in out.splitlines() if "covers:" in l)
            for tag in ("storage", "core", "backups"):
                self.assertIn(tag, covers_line)
            self.assertIn("  files:", out)
            # nested files show their full repo-relative path, then detail
            self.assertIn("    - docs/storage/core.md", out)
            self.assertIn("      covers: storage, core", out)
            self.assertIn("      sections:", out)
            self.assertIn("        - Schema", out)
            self.assertIn("    - docs/storage/backups.md", out)
            self.assertIn("      covers: storage, backups", out)

    def test_reserved_names_are_not_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True)
            (docs / "overview.md").write_text(
                "---\ntags: [framework]\n---\n\n# Framework Overview\n",
                encoding="utf-8",
            )
            (docs / "README.md").write_text("# Landing\n", encoding="utf-8")
            (docs / "_hidden.md").write_text("secret\n", encoding="utf-8")
            (docs / "auth.md").write_text(
                "---\ntags: [auth]\n---\n\n# Auth\n", encoding="utf-8"
            )
            result = run(["sync-docs", "--root", str(root)], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = (docs / "_topics.md").read_text(encoding="utf-8")
            self.assertIn("## overview.md", out)
            self.assertIn("## auth.md", out)
            self.assertNotIn("## README.md", out)
            self.assertNotIn("## _hidden.md", out)
            # the index must not list itself
            self.assertNotIn("## _topics.md", out)

    def test_check_clean_then_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "auth.md").write_text(
                "---\ntags: [auth]\n---\n\n# Auth\n", encoding="utf-8"
            )
            run(["sync-docs", "--root", str(root)], root)
            clean = run(["sync-docs", "--check", "--root", str(root)], root)
            self.assertEqual(clean.returncode, 0, clean.stdout)
            self.assertIn("is fresh", clean.stdout)
            (docs / "auth.md").write_text(
                "---\ntags: [auth, sessions]\n---\n\n# Auth\n", encoding="utf-8"
            )
            stale = run(["sync-docs", "--check", "--root", str(root)], root)
            self.assertEqual(stale.returncode, 1, stale.stdout)
            self.assertIn("is stale", stale.stdout)

    def test_check_reports_missing_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            result = run(["sync-docs", "--check", "--root", str(root)], root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("is stale", result.stdout)

    def test_empty_docs_still_writes_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            result = run(["sync-docs", "--root", str(root)], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = (root / "docs" / "_topics.md").read_text(encoding="utf-8")
            self.assertIn("# Topic Index (`_topics.md`)", out)
            self.assertIn("Auto-generated by `sync-docs`", out)


if __name__ == "__main__":
    unittest.main()
