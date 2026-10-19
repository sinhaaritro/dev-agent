"""Invariant: shipped skills are self-contained.

Everything under `skills/` is installed into a consumer repository. A consumer
does not have this framework's own `docs/` reference series or `tools/`
engines, so a shipped file that points at them sends the agent to a path that
does not exist on the user's disk. This guard scans the shipped surface and
fails with `file:line` so a stray pointer is caught the moment it is written.

What shipped files MAY reference:
  (a) their own skill package - `references/`, `scripts/`, `reference/`
  (b) consumer artifacts - `specs/...`, `docs/<name>.md`, `docs/_topics.md`,
      `AGENTS.md`
  (c) the consumer install path - `.agents/...` (skills, rules, agents)

What they may NOT reference: this repo's maintainer-only documentation
(`docs/001-*` .. `docs/007-*`, `docs/flow.md`, `docs/lifecycle.md`,
`docs/run-contract.md`, `docs/branching.md`, `docs/task-files.md`,
`docs/verification.md`, `docs/decision-records.md`) or its maintainer engines
(`tools/*.py`). Rationale for those belongs in the framework repo, not in the
product.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHIPPED = REPO / "skills"

# Maintainer-only paths that must never appear in a shipped file.
FORBIDDEN = (
    (
        re.compile(
            r"docs/(?:overview|skill-discovery|routing|lifecycle|decision-records|"
            r"task-files|verification|branching|run-contract|flow)\.md"
        ),
        "framework topic doc",
    ),
    (
        re.compile(r"tools/(?:skill_eval|behavior_eval|suite_report)\.py"),
        "maintainer engine",
    ),
)

# Section that existed only to point at the framework's docs/.
DEAD_SECTION = re.compile(r"^##\s+Deep reference", re.MULTILINE)


def _iter_text_files(root):
    """Yield (path, text) for every UTF-8-decodable file under root."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def find_violations(text):
    """Return [(pattern_label, line_number, line)] for a file's text."""
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern, label in FORBIDDEN:
            if pattern.search(line):
                hits.append((label, number, line.strip()))
    return hits


class ShippingPathsTest(unittest.TestCase):
    def test_shipped_files_reference_no_maintainer_paths(self):
        offenders = []
        scanned = 0
        for path, text in _iter_text_files(SHIPPED):
            scanned += 1
            rel = path.relative_to(REPO).as_posix()
            for label, number, line in find_violations(text):
                offenders.append(f"{rel}:{number}: {label} -> {line}")
        self.assertGreater(
            scanned, 0, "no shipped files scanned - guard would be vacuous"
        )
        self.assertEqual(
            offenders,
            [],
            "shipped files point at maintainer-only paths (a consumer does not have them):\n"
            + "\n".join(offenders),
        )

    def test_no_dead_deep_reference_sections(self):
        offenders = []
        for path, text in _iter_text_files(SHIPPED):
            if path.suffix != ".md":
                continue
            if DEAD_SECTION.search(text):
                offenders.append(path.relative_to(REPO).as_posix())
        self.assertEqual(
            offenders,
            [],
            "shipped markdown still carries a '## Deep reference' context-budget section "
            f"(it only ever pointed at the framework's docs/): {offenders!r}",
        )

    def test_guard_detects_known_violations(self):
        # A guard that silently stopped matching would pass forever; prove it bites.
        cases = {
            "The why lives in `docs/flow.md`.": "framework topic doc",
            "see docs/routing.md": "framework topic doc",
            "run tools/behavior_eval.py": "maintainer engine",
        }
        for line, label in cases.items():
            hits = find_violations(line)
            self.assertEqual(len(hits), 1, f"expected exactly one hit for: {line}")
            self.assertEqual(hits[0][0], label)
            self.assertEqual(hits[0][1], 1)
        # ...and that consumer artifacts are not false positives.
        allowed = [
            "Read `specs/temp/draft-plan.md`.",
            "AI index: `docs/_topics.md`.",
            "Human landing page at `docs/README.md`.",
            "Topic docs live at `docs/<name>.md`.",
            "Install path `.agents/scripts/devagent/main.py`.",
        ]
        for line in allowed:
            self.assertEqual(
                find_violations(line), [], f"false positive on allowed path: {line}"
            )


if __name__ == "__main__":
    unittest.main()
