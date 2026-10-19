"""Invariant: nothing in the workspace can leak to users.

The skills CLI discovers BOTH `skills/` and `.agents/skills/`. So every
`SKILL.md` under `.agents/skills/` must carry `metadata.internal: true`, or that
skill would be offered to users. Those folders are repo-only tooling
(`author-skill`, vendored `skill-creator`) - the framework's own dogfood mirror
was removed, so this guards the tools that remain.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORK_SKILLS = REPO / ".agents" / "skills"


class NoLeakTest(unittest.TestCase):
    def test_every_workspace_skill_is_internal(self):
        offenders = []
        if WORK_SKILLS.is_dir():
            for skill in sorted(WORK_SKILLS.iterdir()):
                manifest = skill / "SKILL.md"
                if not manifest.is_file():
                    continue
                if "internal: true" not in manifest.read_text(encoding="utf-8"):
                    offenders.append(skill.name)
        self.assertEqual(
            offenders,
            [],
            f"workspace skills missing 'metadata.internal: true' (they would ship): {offenders!r}",
        )

    def test_workspace_is_nonempty(self):
        # A silently empty/renamed workspace would make the check above vacuous.
        skills = (
            [d for d in WORK_SKILLS.iterdir() if (d / "SKILL.md").is_file()]
            if WORK_SKILLS.is_dir()
            else []
        )
        self.assertGreater(len(skills), 0, "no skills found under .agents/skills/")


if __name__ == "__main__":
    unittest.main()
