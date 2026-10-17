"""Integration: the shipping CLI offers exactly the `skills/` folders.

Runs the real `npx skills add . --list` against this repo and checks that the
count of discoverable skills equals the number of top-level `skills/` folders -
i.e. the `.agents/skills/` workspace does not leak.

Optional and environment-dependent: skipped when `npx` is missing or the CLI
cannot run (offline / no network). It is the strongest form of the no-leak
guarantee, but test_no_leak.py is the always-on guard.
"""

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
NPX = shutil.which("npx")

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def shipped_names() -> set:
    return {d.name for d in SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()}


def cli_list(internal: bool) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if internal:
        env["INSTALL_INTERNAL_SKILLS"] = "1"
    return subprocess.run(
        [NPX, "--yes", "skills@latest", "add", ".", "--list"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=180,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def found_count(stdout: str):
    match = re.search(r"Found (\d+) skill", ANSI.sub("", stdout))
    return int(match.group(1)) if match else None


@unittest.skipUnless(NPX, "npx not available")
class ShippingSetTest(unittest.TestCase):
    def _list_or_skip(self, internal: bool) -> subprocess.CompletedProcess:
        try:
            result = cli_list(internal)
        except (OSError, subprocess.SubprocessError) as exc:
            self.skipTest(f"skills CLI unavailable: {exc}")
        if result.returncode != 0:
            self.skipTest(f"skills CLI failed (offline?): {ANSI.sub('', result.stderr)[:200]}")
        return result

    def test_default_list_is_exactly_the_product(self):
        shipped = shipped_names()
        text = ANSI.sub("", self._list_or_skip(internal=False).stdout)
        self.assertEqual(found_count(text), len(shipped), text)
        for name in shipped:
            self.assertIn(name, text)

    def test_internal_reveal_adds_more(self):
        shipped = shipped_names()
        text = ANSI.sub("", self._list_or_skip(internal=True).stdout)
        count = found_count(text)
        self.assertIsNotNone(count)
        # revealing internals can only add skills, never remove shipped ones
        self.assertGreaterEqual(count, len(shipped))


if __name__ == "__main__":
    unittest.main()
