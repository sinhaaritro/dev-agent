"""U2.4 - the one-way `specs/` rule (promote_spec.py specs-lint).

`specs/` is disposable: docs, code, and config never reference into it, so
deleting the folder breaks nothing. A `specs/` file may link *out* to docs or
source. These tests exercise both directions plus the skip list.
"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / ".agents" / "skills" / "spec-builder" / "scripts" / "promote_spec.py"

_spec = importlib.util.spec_from_file_location("promote_spec", ENGINE)
assert _spec is not None and _spec.loader is not None
promote_spec = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("promote_spec", promote_spec)
_spec.loader.exec_module(promote_spec)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class SpecsLintBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        write(self.root / "AGENTS.md", "# AGENTS\n")

    def run_lint(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(ENGINE),
                "specs-lint",
                "--root",
                str(self.root),
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )


class InboundReferenceTest(SpecsLintBase):
    def test_docs_reference_fails(self):
        write(self.root / "docs" / "guide.md", "# Guide\n\nSee `specs/001-SPEC-x.md`.\n")

        hits = promote_spec.scan_specs_references(self.root)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], "docs/guide.md")
        self.assertEqual(hits[0][1], 3)

        proc = self.run_lint()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("specs-ref: docs/guide.md:3:", proc.stdout)
        self.assertIn("1 reference(s) into specs/", proc.stdout)

    def test_source_reference_fails(self):
        write(self.root / "src" / "app.py", "# see specs/002-SPEC-y.md\nprint('hi')\n")

        proc = self.run_lint()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("specs-ref: src/app.py:1:", proc.stdout)

    def test_link_into_specs_dir_also_fails(self):
        write(
            self.root / "docs" / "link.md",
            "[plan](../specs/003-SPEC-z.md)\n",
        )
        hits = promote_spec.scan_specs_references(self.root)
        self.assertEqual([h[0] for h in hits], ["docs/link.md"])


class AllowedDirectionTest(SpecsLintBase):
    def test_specs_file_linking_out_passes(self):
        write(self.root / "docs" / "guide.md", "# Guide\n\nClean.\n")
        write(self.root / "src" / "app.py", "print('hi')\n")
        write(
            self.root / "specs" / "001-SPEC-x.md",
            "# Spec\n\nImplements docs/guide.md and src/app.py.\n",
        )

        self.assertEqual(promote_spec.scan_specs_references(self.root), [])

        proc = self.run_lint()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("specs-ref: ok", proc.stdout)

    def test_clean_tree_passes(self):
        write(self.root / "docs" / "guide.md", "# Guide\n")
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_specs_folder_absence_is_fine(self):
        self.assertFalse((self.root / "specs").exists())
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class NoiseTest(SpecsLintBase):
    def test_prefixed_names_are_not_specs_refs(self):
        write(self.root / "docs" / "names.md", "myspecs/foo\nsub-specs/bar\n")
        self.assertEqual(promote_spec.scan_specs_references(self.root), [])

    def test_vendored_and_ignored_trees_are_skipped(self):
        write(self.root / ".agents" / "skills" / "x" / "SKILL.md", "see specs/001-SPEC-x.md\n")
        write(self.root / "node_modules" / "pkg" / "README.md", "see specs/001-SPEC-x.md\n")
        self.assertEqual(promote_spec.scan_specs_references(self.root), [])

    def test_non_text_files_are_skipped(self):
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "logo.png").write_bytes(b"\x89PNG specs/001-SPEC-x.md")
        self.assertEqual(promote_spec.scan_specs_references(self.root), [])


if __name__ == "__main__":
    unittest.main()
