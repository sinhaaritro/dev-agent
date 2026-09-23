"""Regression suite for the sync-docs subcommand of the map-generator engine.

Pins the AI topic index contract: `sync-docs` scans `docs/` for topic docs
(one `.md` file or one folder per subsystem), skips ONLY the generated
`_topics.md` itself (reference series, README, and other files all index),
and rebuilds `docs/_topics.md` with one section per topic carrying path,
covers (frontmatter tags), and either sections (flat file) or files (folder).

Each test builds a sandbox repo under ``tempfile.TemporaryDirectory`` and
drives the engine as a subprocess, exactly as system.md invokes it.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = (
    Path(__file__).resolve().parent.parent
    / ".agents" / "skills" / "map-generator" / "scripts" / "generate_map.py"
)


def run(args, cwd):
    return subprocess.run(
        [sys.executable, str(ENGINE)] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
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
                "A decision.\n",
                encoding="utf-8",
            )
            result = run(["sync-docs", "--root", str(root)], root)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = (docs / "_topics.md").read_text(encoding="utf-8")
            self.assertIn("## auth", out)
            self.assertIn("path: docs/auth.md", out)
            self.assertIn("covers: auth, session", out)
            self.assertIn("sections:", out)
            self.assertIn("- Current State", out)
            self.assertIn("- Decision Log", out)

    def test_topic_folder_lists_subfiles_with_covers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "docs" / "storage"
            folder.mkdir(parents=True)
            (folder / "core.md").write_text(
                "---\ntags: [storage, core]\n---\n\n# Storage Core\n",
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
            self.assertIn("path: docs/storage/", out)
            covers_line = next(l for l in out.splitlines() if "covers:" in l)
            for tag in ("storage", "core", "backups"):
                self.assertIn(tag, covers_line)
            self.assertIn("files:", out)
            self.assertIn("- core.md: storage, core", out)
            self.assertIn("- backups.md: storage, backups", out)

    def test_only_topics_md_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True)
            # the reference series, the landing README, and other underscore
            # files are all legitimate topics now - the ONLY thing skipped is
            # the generated _topics.md itself
            (docs / "001-framework-overview.md").write_text(
                "---\ntags: [framework]\n---\n\n# 001: Framework Overview\n",
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
            self.assertIn("## 001-framework-overview.md", out)
            self.assertIn("## README.md", out)
            self.assertIn("## _hidden.md", out)
            self.assertIn("## auth.md", out)
            # the index must not list itself
            self.assertNotIn("## _topics.md", out)

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
