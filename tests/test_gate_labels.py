"""U2.5 - gate type visible at spec creation (section-6 decision labels).

Every planned decision in a Lane-A plan is a `- **D<n> ...` bullet that carries
a `blocking` / `non-blocking` label, so the human chooses before build and the
build never reopens a settled menu.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNTIME = REPO / "skills" / "dev-agent" / "runtime" / "devagent"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
ENGINE = RUNTIME / "specs.py"

_spec = importlib.util.spec_from_file_location("promote_spec", ENGINE)
assert _spec is not None and _spec.loader is not None
promote_spec = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("promote_spec", promote_spec)
_spec.loader.exec_module(promote_spec)

GATES_EMPTY = "## 6. Gates\n\n_(empty)_\n"
GATES_UNLABELED = (
    "## 6. Gates\n\n"
    "- **D1 Choose a database** — options: Postgres (Recommended); SQLite\n"
)
GATES_BLOCKING = (
    "## 6. Gates\n\n"
    "- **D1 Choose a database** — options: Postgres (Recommended); SQLite; **blocking**\n"
)
GATES_NON_BLOCKING = (
    "## 6. Gates\n\n"
    "- **D1 Choose a log format** — options: JSON (Recommended); text; **non-blocking** (default: JSON)\n"
)
GATES_LOG_ENTRY = (
    "## 6. Gates\n\n- Vetting: pass (2026-10-18) — plan reviewed, no blocking issues\n"
)


def lane_a_draft(gates: str) -> str:
    return f"""---
tags: [sandbox, gate-labels]
---

# [SPEC-ID]: Gate Label Sandbox

Status: DRAFTED | Date: 2026-10-18

## 1. Goal & Context

Sandbox plan for the section-6 label lint.

## 2. The Change

- One coherent change.

## 3. Risks & Open Questions

None.

## 4. Affected Files & Contracts

- Modified: none

## 5. Tasks & Outcomes

### Task 1: implement the sandbox behavior
- Target Files: [MODIFY] src/sandbox.py
- Depends On: None
- Verify: `python -m unittest tests.test_sandbox -v`
- Expect: "OK"

{gates}
## 7. Verification Commands

- Build Command: `python -m compileall -q .`

## 8. Rollback Strategy

Revert in reverse task order.
"""


class GateLabelLintTest(unittest.TestCase):
    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def check(self, body: str) -> tuple[bool, list[int], list[str]]:
        draft = self.dir / "draft.md"
        draft.write_text(body, encoding="utf-8")
        return promote_spec.check_draft(draft, "A")

    def test_unlabeled_decision_fails(self):
        passed, missing, violations = self.check(lane_a_draft(GATES_UNLABELED))
        self.assertFalse(passed)
        self.assertEqual(missing, [])
        self.assertTrue(
            any("D1" in v and "blocking/non-blocking label" in v for v in violations),
            violations,
        )

    def test_blocking_label_passes(self):
        passed, missing, violations = self.check(lane_a_draft(GATES_BLOCKING))
        self.assertTrue(passed, (missing, violations))
        self.assertEqual(violations, [])

    def test_non_blocking_label_passes(self):
        passed, missing, violations = self.check(lane_a_draft(GATES_NON_BLOCKING))
        self.assertTrue(passed, (missing, violations))
        self.assertEqual(violations, [])

    def test_empty_gates_section_still_passes(self):
        passed, missing, violations = self.check(lane_a_draft(GATES_EMPTY))
        self.assertTrue(passed, (missing, violations))

    def test_gate_log_entries_are_not_decisions(self):
        passed, missing, violations = self.check(lane_a_draft(GATES_LOG_ENTRY))
        self.assertTrue(passed, (missing, violations))

    def test_multiple_decisions_each_need_a_label(self):
        gates = (
            "## 6. Gates\n\n"
            "- **D1 Choose a database** — options: Postgres; SQLite; **blocking**\n"
            "- **D2 Choose a log format** — options: JSON; text\n"
        )
        passed, _, violations = self.check(lane_a_draft(gates))
        self.assertFalse(passed)
        self.assertEqual(len(violations), 1)
        self.assertIn("D2", violations[0])

    def test_lane_b_is_not_checked_for_section_six(self):
        body = """---
tags: [sandbox, lane-b]
---

# [SPEC-ID]: Lane B Gate Sandbox

Status: DRAFTED | Date: 2026-10-18

## 1. Goal & Context

Lane B sandbox.

## 4. Affected Files & Contracts

- Modified: none

## 5. Tasks & Outcomes

### Task 1: single degenerate task
- Target Files: [MODIFY] src/foo.py
- Depends On: None
- Verify: `python -m unittest tests.test_sandbox -v`
- Expect: "OK"

## 6. Gates

- **D1 Unlabeled but Lane B**
"""
        draft = self.dir / "draft-b.md"
        draft.write_text(body, encoding="utf-8")
        passed, missing, violations = promote_spec.check_draft(draft, "B")
        self.assertTrue(passed, (missing, violations))
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
