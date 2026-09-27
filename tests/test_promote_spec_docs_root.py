"""Regression suite for issue #4: repo-root TOC materialization.

Pins the repo-root contract of the spec-builder engine: the engine scans the
repository root (``<root>/specs`` + ``<root>/docs``), writes the specs-only
index to ``specs/README.md`` (and never creates or writes ``docs/README.md``),
and never clobbers the project's root ``README.md``.

Each test builds a sandbox repo under ``tempfile.TemporaryDirectory``
(an ``AGENTS.md`` marker plus a root ``README.md`` with known content)
and drives the engine as a subprocess, exactly as system.md invokes it.
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


def run(args, cwd):
    return subprocess.run(
        [sys.executable, str(ENGINE)] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def make_sandbox(tmp: Path) -> None:
    (tmp / "AGENTS.md").write_text("# sandbox project\n", encoding="utf-8")
    (tmp / "README.md").write_text(ROOT_README, encoding="utf-8")


class SandboxTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="docs-root-regression-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        make_sandbox(self.root)
        (self.root / ".gitignore").write_text("# sandbox\n", encoding="utf-8")

    def assert_root_readme_untouched(self, extra_note=""):
        self.assertEqual(
            (self.root / "README.md").read_text(encoding="utf-8"),
            ROOT_README,
            "root README.md was clobbered" + extra_note,
        )

    def assert_indexes_written(self):
        self.assertTrue(
            (self.root / "specs" / "README.md").is_file(),
            "specs/README.md was not written",
        )
        self.assertFalse(
            (self.root / "docs" / "README.md").is_file(),
            "docs/README.md must not be created by the engine",
        )


class TestBTocRepoRoot(SandboxTestCase):
    """1.1b: toc --root <repo-root> writes specs/README.md only, not docs/README.md."""

    def test_toc_repo_root_writes_index_readmes(self):
        (self.root / "docs").mkdir()
        (self.root / "docs" / "001-framework-overview.md").write_text(
            "---\ntags: [framework]\n---\n\n# 001: Framework Overview\n",
            encoding="utf-8",
        )
        (self.root / "specs").mkdir()
        (self.root / "specs" / "001-sandbox-feature.md").write_text(
            "---\ntags: [sandbox]\n---\n\n# 001: Sandbox Feature\n\nStatus: APPROVED\n",
            encoding="utf-8",
        )
        result = run(["toc", "--root", str(self.root)], cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_root_readme_untouched(extra_note=" after toc --root <repo-root>")
        self.assert_indexes_written()
        specs_readme = (self.root / "specs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("001-sandbox-feature.md", specs_readme,
                      "specs index was not written to specs/README.md")


if __name__ == "__main__":
    unittest.main()
