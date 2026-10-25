"""U2.4 - the one-way `specs/` rule (promote_spec.py specs-lint).

`specs/` is disposable: docs, code, and config never reference into it, so
deleting the folder breaks nothing. A `specs/` file may link *out* to docs or
source. These tests exercise both directions plus the skip list.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "skills" / "dev-agent" / "runtime" / "devagent"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
ENGINE = RUNTIME / "specs.py"
MAIN = RUNTIME / "main.py"

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

    def run_lint(self, env=None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(MAIN),
                "spec",
                "specs-lint",
                "--root",
                str(self.root),
            ],
            cwd=REPO,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )


class InboundReferenceTest(SpecsLintBase):
    def test_docs_reference_fails(self):
        write(
            self.root / "docs" / "guide.md", "# Guide\n\nSee `specs/001-SPEC-x.md`.\n"
        )

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
        write(
            self.root / ".agents" / "skills" / "x" / "SKILL.md",
            "see specs/001-SPEC-x.md\n",
        )
        write(
            self.root / "node_modules" / "pkg" / "README.md",
            "see specs/001-SPEC-x.md\n",
        )
        self.assertEqual(promote_spec.scan_specs_references(self.root), [])

    def test_non_text_files_are_skipped(self):
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "logo.png").write_bytes(b"\x89PNG specs/001-SPEC-x.md")
        self.assertEqual(promote_spec.scan_specs_references(self.root), [])

    def test_gitignored_tree_is_skipped(self):
        write(self.root / ".gitignore", "generated/" + "\n")
        write(self.root / "generated" / "out.html", "see specs/001-SPEC-x.md" + "\n")
        self.assertEqual(promote_spec.scan_specs_references(self.root), [])


class FrameworkRepoExemptionTest(SpecsLintBase):
    """H6: the framework repo is the product - it is exempt from its own
    one-way gate, while consumer repos stay strict."""

    def _make_framework_repo(self):
        write(
            self.root / "skills" / "dev-agent" / "runtime" / "devagent" / "__init__.py",
            "" + "\n",
        )
        write(self.root / "skills" / "demo" / "SKILL.md", "# Demo" + "\n")
        write(self.root / "docs" / "guide.md", "See specs/001-SPEC-x.md." + "\n")

    def test_framework_repo_is_exempt(self):
        self._make_framework_repo()
        self.assertTrue(promote_spec.is_framework_repo(self.root))
        # scan_specs_references still reports the reference ...
        self.assertEqual(len(promote_spec.scan_specs_references(self.root)), 1)
        # ... but the gate exempts the product repo.
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("skipped", proc.stdout)

    def test_consumer_repo_is_not_exempt(self):
        # A consumer that keeps a top-level skills/ tree is still strict: only
        # the source runtime marks the framework checkout.
        write(self.root / "skills" / "installed" / "SKILL.md", "# Installed" + "\n")
        write(self.root / "docs" / "guide.md", "See specs/001-SPEC-x.md." + "\n")
        self.assertFalse(promote_spec.is_framework_repo(self.root))
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)


class DanglingFrameworkRefTest(SpecsLintBase):
    """References to the framework's own spec/ADR IDs are dangling in consumers."""

    def test_spec_id_in_docs_fails(self):
        write(self.root / "docs" / "guide.md", "See spec 002, section 2.1.\n")
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("framework-ref", proc.stdout)
        self.assertIn("spec 002", proc.stdout)

    def test_adr_id_in_source_fails(self):
        write(self.root / "src" / "app.py", "# see ADR-001\n")
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("framework-ref", proc.stdout)

    def test_workflow_specs_path_is_not_a_dangling_ref(self):
        write(
            self.root / ".agents" / "skills" / "spec-builder" / "SKILL.md",
            "Write the draft to specs/temp/draft-plan.md.\n",
        )
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_installed_runtime_is_scanned(self):
        write(
            self.root / ".agents" / "scripts" / "devagent" / "engine.py",
            "# Canonical statuses (spec 002)\n",
        )
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("framework-ref", proc.stdout)

    def test_vendored_skill_creator_is_skipped(self):
        write(
            self.root / ".agents" / "skills" / "skill-creator" / "notes.md",
            "ADR-001\n",
        )
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_framework_repo_scans_only_shipped_skills(self):
        write(
            self.root / "skills" / "dev-agent" / "runtime" / "devagent" / "__init__.py",
            "",
        )
        write(self.root / "docs" / "guide.md", "See spec 002.\n")
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        write(self.root / "skills" / "demo" / "SKILL.md", "See spec 002.\n")
        proc = self.run_lint()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("framework-ref", proc.stdout)


class ShippedProductTest(unittest.TestCase):
    """The product must pass the gate it ships: no dangling refs under skills/."""

    def test_shipped_skills_have_no_dangling_refs(self):
        hits = promote_spec.scan_dangling_refs(REPO / "skills")
        self.assertEqual(
            hits,
            [],
            "shipped files reference framework spec/decision IDs:\n"
            + "\n".join(f"{rel}:{lineno}: {line}" for rel, lineno, line in hits),
        )
        self.assertEqual(promote_spec.dangling_refs_for(REPO), [])


class EncodingGuardTest(SpecsLintBase):
    def test_non_utf8_console_does_not_crash(self):
        write(
            self.root / "docs" / "guide.md",
            "See specs/001-SPEC-x.md \u2192 done" + "\n",
        )
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        proc = self.run_lint(env=env)
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("UnicodeEncodeError", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


class Section5OptionalFieldsTest(unittest.TestCase):
    """New §5 fields (Area, Skills, Contract Changes, Callers, Compatibility)."""

    def parse(self, body: str):
        from common.specparse import parse_tasks

        return parse_tasks(body)

    def test_optional_fields_parse_into_structured_values(self):
        tasks = self.parse(
            "### Task 1: add the chart\n"
            "- Target Files: [MODIFY] src/chart.py\n"
            "- Area: astro-site\n"
            "- Skills: astro-framework, `shadcn`\n"
            "- Contract Changes: src/api/chart.py\n"
            "- Callers: src/pages/index.astro, src/pages/map.astro\n"
            "- Compatibility: breaking\n"
            "- Depends On: None\n"
            "- Verify: `python -m unittest`\n"
            '- Expect: "OK"\n'
        )
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task["area"], "astro-site")
        self.assertEqual(task["skills"], ["astro-framework", "shadcn"])
        self.assertEqual(task["contract_changes"], "src/api/chart.py")
        self.assertEqual(
            task["callers"], ["src/pages/index.astro", "src/pages/map.astro"]
        )
        self.assertEqual(task["compatibility"], "breaking")
        # the legacy fields still parse unchanged
        self.assertEqual(task["depends_on"], "None")
        self.assertEqual(task["verify"], "`python -m unittest`")
        self.assertEqual(task["expect"], '"OK"')

    def test_missing_optional_fields_default_to_empty(self):
        tasks = self.parse(
            "### Task 1: plain\n"
            "- Target Files: [NEW] src/a.py\n"
            "- Depends On: None\n"
            "- Verify: `true`\n"
            '- Expect: "ok"\n'
        )
        task = tasks[0]
        self.assertEqual(task["area"], "")
        self.assertEqual(task["skills"], [])
        self.assertEqual(task["contract_changes"], "")
        self.assertEqual(task["callers"], [])
        self.assertEqual(task["compatibility"], "")


if __name__ == "__main__":
    unittest.main()
