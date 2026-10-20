"""Regression suite for area-scoped AGENTS.md commands and doctor precondition 10.

A mixed-stack project groups its canonical commands under ``### <area>``
headings, each with an optional ``- Skills:`` line. The verify engine must
report commands per area, refuse an area that declares no Build/Test/Lint
command, and keep ``doctor`` honest about the generated docs topic index.
"""

import argparse
import importlib.util
import json
import os
import subprocess
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
ENGINE = RUNTIME / "verify.py"

_spec = importlib.util.spec_from_file_location("verify_areas", ENGINE)
assert _spec is not None and _spec.loader is not None
verify = importlib.util.module_from_spec(_spec)
sys.modules["verify_areas"] = verify
_spec.loader.exec_module(verify)

MULTI_AREA = """# Test

## Commands

### astro-site
- Build: npm run build
- Test: npm run test
- Skills: astro-framework, shadcn

### python-scripts
- Build: python -m compileall -q scripts
- Test: python -m unittest discover -s scripts
- Lint: python -m ruff check scripts
"""

FLAT = """# Test

## Commands

- Build: python -m compileall .
- Test: python -m unittest
- Lint: true
"""


def _sandbox(tmp: Path, agents: str = MULTI_AREA) -> Path:
    (tmp / "AGENTS.md").write_text(agents, encoding="utf-8")
    (tmp / "specs").mkdir()
    (tmp / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", "init"], cwd=tmp, check=True
    )
    return tmp


def _task_file(tmp: Path) -> Path:
    path = tmp / "specs" / "007-TASK-01-do-things.md"
    path.write_text(
        "# TASK 007-01 - do things\n\n"
        "## Role & rules\nImplement only this task.\n\n"
        "## Project overview\nA sandbox.\n\n"
        "## Task\nDo things.\n\n"
        '### Progress\n- [x] read every skill under "Skills to use"\n- [ ] do it\n\n'
        "## Owns\n- `src.py`\n\n"
        "## Reads / Context (read-only)\n- none\n\n"
        "## Skills to use\n- verification-runner\n\n"
        "## Verification\n```bash\npython -c \"print('MARKER')\"\n```\n"
        "**Expect:** `MARKER`\n",
        encoding="utf-8",
    )
    return path


def _spec_file(tmp: Path) -> Path:
    path = tmp / "specs" / "007-SPEC-do-things.md"
    path.write_text(
        "# 007: Do things\n\n"
        "Status: COMPILED | Date: 2026-09-26\n\n"
        "## 1. Goal\nDo things.\n\n"
        "## 5. Tasks & Outcomes\n\n"
        "### Task 1: do things\n"
        "- Depends On: None\n"
        "- Verify: `python -c \"print('MARKER')\"`\n"
        "- Expect: MARKER\n",
        encoding="utf-8",
    )
    return path


def _ns(**kwargs):
    return argparse.Namespace(**kwargs)


class ParseAreasTest(unittest.TestCase):
    def test_multi_area_parses_commands_and_skills(self):
        from common.project import parse_command_areas

        areas = parse_command_areas(MULTI_AREA)
        self.assertEqual(list(areas), ["astro-site", "python-scripts"])
        self.assertEqual(
            areas["astro-site"]["commands"],
            [("Build", "npm run build"), ("Test", "npm run test")],
        )
        self.assertEqual(areas["astro-site"]["skills"], ["astro-framework", "shadcn"])
        self.assertEqual(areas["python-scripts"]["skills"], [])
        self.assertEqual(len(areas["python-scripts"]["commands"]), 3)

    def test_flat_block_is_one_default_area(self):
        from common.project import parse_command_areas

        areas = parse_command_areas(FLAT)
        self.assertEqual(list(areas), ["default"])
        self.assertEqual(len(areas["default"]["commands"]), 3)

    def test_placeholder_commands_are_skipped(self):
        from common.project import parse_command_areas

        areas = parse_command_areas("## Commands\n\n- Build: <command>\n- Test: true\n")
        self.assertEqual(areas["default"]["commands"], [("Test", "true")])


class EngineAreasTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = _sandbox(Path(self._tmp.name))
        self._orig_cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._orig_cwd)

    def test_canonical_areas_and_flat_compatibility_view(self):
        areas = verify._canonical_command_areas(self.root)
        self.assertIn("astro-site", areas)
        flat = verify._canonical_command_list(self.root)
        self.assertIn(("Build", "npm run build"), flat)
        self.assertIn(("Lint", "python -m ruff check scripts"), flat)

    def test_canonical_commands_requires_each_area_to_declare_one(self):
        ok, detail = verify._canonical_commands(self.root)
        self.assertTrue(ok, detail)
        agents = self.root / "AGENTS.md"
        agents.write_text(
            MULTI_AREA.replace(
                "### python-scripts\n"
                "- Build: python -m compileall -q scripts\n"
                "- Test: python -m unittest discover -s scripts\n"
                "- Lint: python -m ruff check scripts\n",
                "### python-scripts\n- Skills: some-skill\n",
            ),
            encoding="utf-8",
        )
        ok, detail = verify._canonical_commands(self.root)
        self.assertFalse(ok)
        self.assertIn("python-scripts", detail)

    def test_suggest_prints_grouped_areas(self):
        buf = StringIO()
        with redirect_stdout(buf):
            rc = verify.cmd_run(_ns(command=None, suggest=True, state_dir=self.root))
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[astro-site]", out)
        self.assertIn("Build: npm run build", out)
        self.assertIn("[python-scripts]", out)


class DoctorDocsIndexTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = _sandbox(Path(self._tmp.name), FLAT)
        self.spec = _spec_file(self.root)
        _task_file(self.root)
        fp = verify.command_fingerprint(
            "python -c \"print('MARKER')\"", "MARKER", verify.APPROVAL_CWD
        )
        (self.root / "specs" / "007-APPROVALS-do-things.json").write_text(
            json.dumps(
                {
                    "spec": "007",
                    "approvals": [
                        {
                            "task": "Task 1",
                            "fingerprint": fp,
                            "command": "python -c \"print('MARKER')\"",
                            "expect": "MARKER",
                            "cwd": verify.APPROVAL_CWD,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self._orig_cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._orig_cwd)

    def test_no_docs_dir_skips_precondition(self):
        self.assertEqual(verify.doctor(self.spec), [])

    def test_fresh_index_passes(self):
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "overview.md").write_text(
            "---\ntags: [framework]\n---\n\n# Overview\n", encoding="utf-8"
        )
        from mapgen import sync_docs

        sync_docs(self.root)
        self.assertEqual(verify.doctor(self.spec), [])

    def test_stale_index_reports_precondition_10(self):
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "overview.md").write_text(
            "---\ntags: [framework]\n---\n\n# Overview\n", encoding="utf-8"
        )
        from mapgen import sync_docs

        sync_docs(self.root)
        (docs / "overview.md").write_text(
            "---\ntags: [framework, new]\n---\n\n# Overview\n", encoding="utf-8"
        )
        gaps = verify.doctor(self.spec)
        self.assertTrue(any(g.startswith("10:") for g in gaps), gaps)
        self.assertIn("sync-docs", " ".join(gaps))


if __name__ == "__main__":
    unittest.main()
