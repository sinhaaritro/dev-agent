"""Unit tests for the dev-agent installer (bootstrap.py).

Covers the `setup` install (seeds + runtime + manifest), idempotent re-run, the
`.gitignore` append-not-clobber rule, overwriting a divergent seed, dry-run
reporting, the `--check` / `--update` drift contract, the never-downgrade guard,
the self-bootstrap refusal, the missing-target error, atomic staging (a leftover
`.devagent.tmp/` and a detectable interrupted install), and the opt-in
`--skills` delegation (descriptor resolution and the graceful no-`npx` path).

The engine copies the real seed files from its own `reference/` folder and the
bundled `runtime/`, so each test installs into a throwaway temp directory
(outside the framework's source tree) via the script's `--target` contract.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "dev-agent"
ENGINE = SKILL / "scripts" / "bootstrap.py"
REFERENCE = SKILL / "reference"
RUNTIME_SRC = SKILL / "runtime" / "devagent"

_BOOTSTRAP_SPEC = importlib.util.spec_from_file_location("bootstrap_under_test", ENGINE)
assert _BOOTSTRAP_SPEC is not None and _BOOTSTRAP_SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(_BOOTSTRAP_SPEC)
sys.modules["bootstrap_under_test"] = bootstrap
_BOOTSTRAP_SPEC.loader.exec_module(bootstrap)

SEED_FILES = (
    "AGENTS.md",
    ".gitignore",
    ".agents/rules/dev-agent-framework.md",
    ".agents/agents/coder.md",
    ".cursorrules",
    ".windsurfrules",
)
MANIFEST_REL = ".agents/.devagent.json"
RUNTIME_MAIN_REL = ".agents/scripts/devagent/main.py"


def runtime_count() -> int:
    count = 0
    for path in RUNTIME_SRC.rglob("*"):
        if path.is_dir():
            continue
        parts = path.relative_to(RUNTIME_SRC).parts
        if "__pycache__" in parts or path.suffix == ".pyc":
            continue
        count += 1
    return count


class BootstrapBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.target = Path(self._tmp.name)

    def run_bootstrap(self, *args):
        return subprocess.run(
            [sys.executable, str(ENGINE), *args],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def setup_target(self, *extra):
        args = ["setup", "--target", str(self.target)]
        if "--skills" not in extra:
            args += ["--skills", "none"]  # keep subprocess tests off the network
        return self.run_bootstrap(*args, *extra)

    def check_target(self):
        return self.run_bootstrap("--check", "--target", str(self.target))


class DryRunTest(BootstrapBase):
    def test_dry_run_reports_new_and_writes_nothing(self):
        proc = self.setup_target("--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("new: AGENTS.md", proc.stdout)
        self.assertIn("new: .agents/rules/dev-agent-framework.md", proc.stdout)
        self.assertIn("installed: .agents/scripts/devagent/main.py", proc.stdout)
        self.assertFalse((self.target / "AGENTS.md").exists())
        self.assertFalse((self.target / MANIFEST_REL).exists())


class InstallTest(BootstrapBase):
    def test_install_creates_every_seed_file(self):
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for rel in SEED_FILES:
            self.assertTrue((self.target / rel).is_file(), rel)
        # AGENTS.md carries the template inside a marker-managed block.
        agents = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("<!-- dev-agent:begin -->", agents)
        self.assertIn("<!-- dev-agent:end -->", agents)
        self.assertIn(
            (REFERENCE / "AGENTS.md").read_text(encoding="utf-8").strip(), agents
        )

    def test_install_writes_runtime_and_manifest(self):
        self.setup_target()
        self.assertTrue((self.target / RUNTIME_MAIN_REL).is_file())
        manifest = json.loads((self.target / MANIFEST_REL).read_text(encoding="utf-8"))
        self.assertEqual(manifest["framework"], "dev-agent")
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["runtime_version"], "0.1.0")
        self.assertEqual(len(manifest["files"]), runtime_count())
        self.assertIn("devagent/main.py", manifest["files"])

    def test_success_summary_counts_every_file(self):
        total = len(SEED_FILES) + runtime_count() + 1  # seeds + runtime + manifest
        proc = self.setup_target()
        self.assertIn(
            f"dev-agent setup complete: {total} installed, 0 updated, 0 unchanged",
            proc.stdout,
        )

    def test_second_run_is_idempotent(self):
        self.setup_target()
        total = len(SEED_FILES) + runtime_count() + 1
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(
            f"dev-agent setup complete: 0 installed, 0 updated, {total} unchanged",
            proc.stdout,
        )


class GitignoreTest(BootstrapBase):
    def test_existing_gitignore_is_appended_not_clobbered(self):
        (self.target / ".gitignore").write_text("custom/\n", encoding="utf-8")
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("appended: .gitignore", proc.stdout)
        text = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("custom/", text)
        self.assertIn("specs/temp", text)

    def test_rerun_does_not_duplicate_gitignore_patterns(self):
        self.setup_target()
        before = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.setup_target()
        self.assertEqual(
            (self.target / ".gitignore").read_text(encoding="utf-8"), before
        )


class AgentsMergeTest(BootstrapBase):
    def test_existing_agents_md_is_merged_not_overwritten(self):
        (self.target / "AGENTS.md").write_text(
            "# Astro notes\n\nRun `npm run dev`.\n", encoding="utf-8"
        )
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("appended: AGENTS.md", proc.stdout)
        text = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# Astro notes", text)
        self.assertIn("Run `npm run dev`.", text)
        self.assertIn("Read `.agents/rules/dev-agent-framework.md`", text)
        self.assertEqual(text.count("<!-- dev-agent:begin -->"), 1)

    def test_rerun_does_not_duplicate_the_block(self):
        (self.target / "AGENTS.md").write_text("# Astro notes\n", encoding="utf-8")
        self.setup_target()
        before = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("unchanged: AGENTS.md", proc.stdout)
        self.assertEqual(
            (self.target / "AGENTS.md").read_text(encoding="utf-8"), before
        )

    def test_managed_block_is_replaced_in_place(self):
        self.setup_target()
        text = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        stale = text.replace(
            "Read `.agents/rules/dev-agent-framework.md`", "STALE EDIT"
        )
        (self.target / "AGENTS.md").write_text(stale, encoding="utf-8")
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("updated: AGENTS.md", proc.stdout)
        after = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("STALE EDIT", after)
        self.assertEqual(after.count("<!-- dev-agent:begin -->"), 1)

    def test_divergent_non_agents_seed_is_still_overwritten(self):
        (self.target / ".cursorrules").write_text("old rules\n", encoding="utf-8")
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("updated: .cursorrules", proc.stdout)
        self.assertEqual(
            (self.target / ".cursorrules").read_bytes(),
            (REFERENCE / ".cursorrules").read_bytes(),
        )


class RefusalTest(BootstrapBase):
    def test_self_bootstrap_is_refused(self):
        proc = self.run_bootstrap("setup", "--target", str(REPO))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing to bootstrap", proc.stdout + proc.stderr)

    def test_project_install_is_not_mistaken_for_the_source_tree(self):
        # A consumer repo keeps its own AGENTS.md (some tools generate one) and a
        # skills lock recording the install; neither is evidence that the repo is
        # the framework source, so setup must proceed.
        consumer = self.target
        installed = consumer / ".agents" / "skills" / "dev-agent"
        shutil.copytree(
            SKILL, installed, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
        (consumer / "AGENTS.md").write_text("# My project\n", encoding="utf-8")
        (consumer / "skills-lock.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "skills": {
                        "dev-agent": {
                            "source": "github/sinhaaritro/dev-agent",
                            "skillPath": "skills/dev-agent/SKILL.md",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(installed / "scripts" / "bootstrap.py"),
                "setup",
                "--target",
                str(consumer),
                "--skills",
                "none",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("refusing to bootstrap", proc.stdout + proc.stderr)
        agents = (consumer / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# My project", agents)
        self.assertIn("Read `.agents/rules/dev-agent-framework.md`", agents)
        self.assertTrue((consumer / MANIFEST_REL).is_file())

    def test_catalog_without_the_framework_grouping_is_not_refused(self):
        # A repo can publish its own skills.sh.json catalog; only one that groups
        # dev-agent is the framework's source tree.
        consumer = self.target
        (consumer / "skills.sh.json").write_text(
            json.dumps(
                {
                    "groupings": [
                        {"title": "Web", "skills": ["astro", "tailwind"]},
                    ]
                }
            ),
            encoding="utf-8",
        )
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("refusing to bootstrap", proc.stdout + proc.stderr)

    def test_missing_target_is_an_error(self):
        missing = self.target / "does-not-exist"
        proc = self.run_bootstrap("setup", "--target", str(missing))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not a directory", proc.stdout + proc.stderr)

    def test_downgrade_is_refused(self):
        manifest = {
            "schema": 1,
            "framework": "dev-agent",
            "runtime_version": "99.0.0",
            "files": {},
        }
        (self.target / ".agents").mkdir()
        (self.target / MANIFEST_REL).write_text(json.dumps(manifest), encoding="utf-8")
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("refusing to downgrade", proc.stdout + proc.stderr)


class CheckTest(BootstrapBase):
    def test_check_is_clean_after_setup(self):
        self.setup_target()
        proc = self.check_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("dev-agent check: clean", proc.stdout)

    def test_check_reports_missing_when_not_set_up(self):
        proc = self.check_target()
        self.assertEqual(proc.returncode, 1)
        self.assertIn(f"missing: {MANIFEST_REL}", proc.stdout)

    def test_check_reports_modified_runtime(self):
        self.setup_target()
        (self.target / RUNTIME_MAIN_REL).write_text("# tampered\n", encoding="utf-8")
        proc = self.check_target()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("modified: devagent/main.py", proc.stdout)


class UpdateTest(BootstrapBase):
    def test_update_repairs_and_backs_up_modified_file(self):
        self.setup_target()
        original = (self.target / RUNTIME_MAIN_REL).read_bytes()
        (self.target / RUNTIME_MAIN_REL).write_text("# tampered\n", encoding="utf-8")
        proc = self.run_bootstrap("--update", "--target", str(self.target))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("updated: .agents/scripts/devagent/main.py", proc.stdout)
        backup = self.target / (RUNTIME_MAIN_REL + ".bak")
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_text(encoding="utf-8"), "# tampered\n")
        self.assertEqual((self.target / RUNTIME_MAIN_REL).read_bytes(), original)
        self.assertEqual(self.check_target().returncode, 0)


class AtomicityTest(BootstrapBase):
    def test_leftover_staging_dir_is_replaced(self):
        stage = self.target / ".agents" / "scripts" / ".devagent.tmp"
        stage.mkdir(parents=True)
        (stage / "junk.txt").write_text("leftover\n", encoding="utf-8")
        proc = self.setup_target()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(stage.exists(), "staging dir must be consumed by the rename")
        self.assertTrue((self.target / RUNTIME_MAIN_REL).is_file())

    def test_interrupted_install_is_detectable(self):
        # The manifest is written last, so a crash before the rename (or a manual
        # wipe) leaves it behind while the runtime is gone - and `--check` sees it.
        self.setup_target()
        shutil.rmtree(self.target / ".agents" / "scripts" / "devagent")
        proc = self.check_target()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("missing: devagent/main.py", proc.stdout)


class SkillsDescriptorTest(BootstrapBase):
    def test_descriptor_names_the_six_wrappers(self):
        descriptor = bootstrap._read_descriptor(SKILL)
        self.assertEqual(descriptor["source"], "github/sinhaaritro/dev-agent")
        mandatory = descriptor["mandatory"]
        self.assertEqual(len(mandatory), 6)
        for name in mandatory:
            self.assertTrue((REPO / "skills" / name / "SKILL.md").is_file(), name)

    def test_resolve_skill_names_specs(self):
        descriptor = {"mandatory": ["a", "b"], "optional": ["c"]}
        self.assertEqual(
            bootstrap._resolve_skill_names("mandatory", descriptor), ["a", "b"]
        )
        self.assertEqual(bootstrap._resolve_skill_names(None, descriptor), ["a", "b"])
        self.assertEqual(
            bootstrap._resolve_skill_names("all", descriptor), ["a", "b", "c"]
        )
        # The flag adds optional skills; the mandatory set is always included.
        self.assertEqual(
            bootstrap._resolve_skill_names("x, y ", descriptor), ["a", "b", "x", "y"]
        )
        self.assertEqual(bootstrap._resolve_skill_names("none", descriptor), [])

    def test_missing_descriptor_is_an_error(self):
        args = argparse.Namespace(skills="mandatory", scope="project", agent=None)
        # self.target has no skills.json descriptor
        code = bootstrap._install_skills(self.target, args, self.target)
        self.assertEqual(code, 1)

    def test_no_npx_is_a_noop(self):
        args = argparse.Namespace(skills="mandatory", scope="project", agent=None)
        with mock.patch.object(bootstrap.shutil, "which", return_value=None):
            code = bootstrap._install_skills(SKILL, args, self.target)
        self.assertEqual(code, 0)

    def test_no_npx_prints_the_manual_command(self):
        args = argparse.Namespace(skills="all", scope="global", agent="opencode")
        out = io.StringIO()
        with (
            mock.patch.object(bootstrap.shutil, "which", return_value=None),
            contextlib.redirect_stdout(out),
        ):
            code = bootstrap._install_skills(SKILL, args, self.target)
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("npx not found", text)
        self.assertIn("--skill auto-router", text)
        self.assertIn("-g", text)
        self.assertIn("-a opencode", text)


if __name__ == "__main__":
    unittest.main()
