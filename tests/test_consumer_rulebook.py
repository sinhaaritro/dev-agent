"""U2.6 - the shipped consumer rulebook carries the new guardrails.

The dev-agent seed at `skills/dev-agent/reference/rules/dev-agent-framework.md` is what
installs into *other* repos, so the `specs/` one-way rule and the plan-time
gate labels must live there, not only in this repo's own `.agents/` copy.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHIPPED_RULES = (
    REPO / "skills" / "dev-agent" / "reference" / "rules" / "dev-agent-framework.md"
)


class ConsumerRulebookTest(unittest.TestCase):
    def setUp(self):
        self.text = SHIPPED_RULES.read_text(encoding="utf-8")

    def test_shipped_rules_file_exists(self):
        self.assertTrue(SHIPPED_RULES.is_file(), SHIPPED_RULES)

    def test_specs_folder_is_disposable_and_one_way(self):
        self.assertIn("`specs/` is disposable", self.text)
        self.assertIn("one-way", self.text)
        self.assertIn("deleting the whole folder breaks nothing", self.text)

    def test_specs_lint_command_is_named(self):
        self.assertIn("main.py spec specs-lint", self.text)

    def test_gate_type_is_visible_at_plan_time(self):
        self.assertIn("Gate type is visible at plan time", self.text)
        self.assertIn("`blocking` / `non-blocking` label", self.text)

    def test_directional_allowance_is_stated(self):
        self.assertIn("may link out to `docs/` or source", self.text)


if __name__ == "__main__":
    unittest.main()
