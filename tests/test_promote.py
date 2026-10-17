"""Tests for the promote engine (tools/promote.py).

Pure-function unit tests plus subprocess integration tests against a sandbox
repo, mirroring the sandbox style used by test_verify.py.

Covers: the internal-flag injection (merge with an existing `metadata:` block),
line-ending normalisation, the derived-file set, and the CLI modes
(apply / --dry-run / --check) including drift, removal, the unmanaged-folder
passthrough, and the collision guard.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "tools" / "promote.py"

_spec = importlib.util.spec_from_file_location("promote", ENGINE)
assert _spec is not None and _spec.loader is not None
promote = importlib.util.module_from_spec(_spec)
sys.modules["promote"] = promote
_spec.loader.exec_module(promote)


SKILL_STUB = """---
name: {name}
description: sandbox skill {name}
metadata:
  version: 1.0.0
  author: Tester
---

# {name}
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def make_sandbox() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="promote-sandbox-"))
    root = tmp / "repo"
    (root / "tools").mkdir(parents=True)
    write(root / "AGENTS.md", "# sandbox\n")
    shutil.copy2(ENGINE, root / "tools" / "promote.py")
    return root


def add_skill(root: Path, name: str) -> Path:
    skill = root / "skills" / name
    write(skill / "SKILL.md", SKILL_STUB.format(name=name))
    return skill


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "tools" / "promote.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


class InjectInternalTest(unittest.TestCase):
    def test_merges_into_existing_metadata(self):
        out = promote.inject_internal(SKILL_STUB.format(name="foo"))
        self.assertIn("  internal: true", out)
        self.assertIn("  version: 1.0.0", out)
        self.assertIn("  author: Tester", out)
        self.assertEqual(out.count("internal: true"), 1)

    def test_creates_metadata_block_when_absent(self):
        text = "---\nname: foo\ndescription: bar\n---\n\n# foo\n"
        out = promote.inject_internal(text)
        self.assertIn("metadata:", out)
        self.assertIn("  internal: true", out)

    def test_is_idempotent(self):
        once = promote.inject_internal(SKILL_STUB.format(name="foo"))
        self.assertEqual(promote.inject_internal(once), once)

    def test_missing_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            promote.inject_internal("no frontmatter here\n")


class NormalizeBytesTest(unittest.TestCase):
    def test_crlf_and_cr_to_lf(self):
        self.assertEqual(promote.normalize_bytes(b"a\r\nb\rc\n"), b"a\nb\nc\n")

    def test_binary_passthrough(self):
        data = b"\x00\x01\x02\xff\xfe"
        self.assertEqual(promote.normalize_bytes(data), data)


class ExpectedFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="promote-src-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_skill_md_transformed_others_normalized(self):
        skill = self.tmp / "foo"
        write(skill / "SKILL.md", SKILL_STUB.format(name="foo"))
        (skill / "scripts").mkdir()
        (skill / "scripts" / "run.py").write_bytes(b"print(1)\r\n")
        out = promote.expected_files(skill)
        self.assertIn("  internal: true", out["SKILL.md"].decode("utf-8"))
        self.assertEqual(out["scripts/run.py"], b"print(1)\n")

    def test_skips_pycache(self):
        skill = self.tmp / "foo"
        write(skill / "SKILL.md", SKILL_STUB.format(name="foo"))
        write(skill / "__pycache__" / "x.pyc", "junk")
        out = promote.expected_files(skill)
        self.assertEqual(list(out.keys()), ["SKILL.md"])


class CliIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.root = make_sandbox()
        self.addCleanup(shutil.rmtree, self.root.parent, ignore_errors=True)

    def test_apply_then_check_clean(self):
        add_skill(self.root, "foo")
        applied = run(self.root, "apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertIn("installed: foo", applied.stdout)

        derived = self.root / ".agents" / "skills" / "foo" / "SKILL.md"
        self.assertTrue(derived.is_file())
        self.assertIn("internal: true", derived.read_text(encoding="utf-8"))

        source = (self.root / "skills" / "foo" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("internal", source)

        manifest = (self.root / ".agents" / ".promoted.json").read_text(encoding="utf-8")
        self.assertIn("foo", manifest)

        checked = run(self.root, "--check")
        self.assertEqual(checked.returncode, 0, checked.stdout)
        self.assertIn("promote: clean", checked.stdout)

    def test_check_detects_drift(self):
        add_skill(self.root, "foo")
        run(self.root, "apply")
        write(self.root / "skills" / "foo" / "SKILL.md", SKILL_STUB.format(name="foo") + "\nedited\n")
        checked = run(self.root, "--check")
        self.assertEqual(checked.returncode, 1)
        self.assertIn("overwrite: foo", checked.stdout)

    def test_dry_run_writes_nothing(self):
        add_skill(self.root, "foo")
        result = run(self.root, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("new: foo", result.stdout)
        self.assertFalse((self.root / ".agents" / "skills" / "foo").exists())
        self.assertFalse((self.root / ".agents" / ".promoted.json").exists())

    def test_removed_source_is_removed(self):
        add_skill(self.root, "foo")
        add_skill(self.root, "bar")
        run(self.root, "apply")
        shutil.rmtree(self.root / "skills" / "bar")
        result = run(self.root, "apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("removed: bar", result.stdout)
        self.assertFalse((self.root / ".agents" / "skills" / "bar").exists())
        manifest = (self.root / ".agents" / ".promoted.json").read_text(encoding="utf-8")
        self.assertNotIn("bar", manifest)

    def test_unmanaged_folder_untouched(self):
        add_skill(self.root, "foo")
        unmanaged = self.root / ".agents" / "skills" / "thirdparty"
        write(unmanaged / "SKILL.md", "---\nname: thirdparty\ndescription: x\n---\n")
        result = run(self.root, "apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (unmanaged / "SKILL.md").read_text(encoding="utf-8"),
            "---\nname: thirdparty\ndescription: x\n---\n",
        )
        manifest = (self.root / ".agents" / ".promoted.json").read_text(encoding="utf-8")
        self.assertNotIn("thirdparty", manifest)

    def test_collision_with_unmanaged_is_refused(self):
        add_skill(self.root, "foo")
        hand = self.root / ".agents" / "skills" / "foo" / "SKILL.md"
        write(hand, "---\nname: foo\ndescription: hand-written\n---\n")
        result = run(self.root, "apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("collision", result.stderr.lower())
        # the hand-written folder is never overwritten
        self.assertIn("hand-written", hand.read_text(encoding="utf-8"))


class LiveRepoTest(unittest.TestCase):
    """The checked-in repo must be in sync (source of truth == mirror)."""

    def test_repo_is_synced(self):
        result = subprocess.run(
            [sys.executable, str(ENGINE), "--check"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
