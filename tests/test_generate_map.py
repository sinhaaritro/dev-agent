"""Unit tests for the map-generator engine (generate_map.py).

Covers the snapshot-hash freshness check (content-based, mtime-independent),
index rebuild vs. fresh no-op, force rebuild, the rendered MAP.md content
(active condition, source link), and ASCII sanitization.

The engine resolves its repo root from its own script location, so each test
patches `generate_map.find_root` to a throwaway sandbox.
"""

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / ".agents" / "skills" / "map-generator" / "scripts" / "generate_map.py"

_spec = importlib.util.spec_from_file_location("generate_map", ENGINE)
assert _spec is not None and _spec.loader is not None
gen = importlib.util.module_from_spec(_spec)
sys.modules["generate_map"] = gen
_spec.loader.exec_module(gen)


class MapBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "AGENTS.md").write_text("# Test\n", encoding="utf-8")

    def add_skill(self, name, *, scope=None, tags=(), description="desc"):
        d = self.root / ".agents" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        lines = ["---", f"name: {name}", f"description: {description}"]
        if tags:
            lines.append("tags:")
            lines.extend(f"  - {t}" for t in tags)
        if scope:
            lines.append(f"scope: {scope}")
        lines += ["---", "", "# Skill", ""]
        (d / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
        return d / "SKILL.md"

    def run_main(self, *argv):
        buf = io.StringIO()
        with (
            mock.patch.object(gen, "find_root", return_value=self.root),
            mock.patch.object(sys, "argv", ["generate_map.py", *argv]),
            contextlib.redirect_stdout(buf),
        ):
            code = gen.main()
        return code, buf.getvalue()

    def map_text(self):
        return (self.root / ".agents" / "MAP.md").read_text(encoding="utf-8")

    def skills(self):
        return gen.scan_skills(self.root)


class SnapshotTest(MapBase):
    def test_snapshot_is_deterministic_and_content_sensitive(self):
        p = self.add_skill("alpha", tags=["x"])
        first = gen.snapshot_of([p])
        self.assertEqual(first, gen.snapshot_of([p]))
        p.write_text(p.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
        self.assertNotEqual(first, gen.snapshot_of([p]))


class FreshnessTest(MapBase):
    def test_missing_map_is_not_fresh(self):
        self.add_skill("alpha")
        self.assertFalse(
            gen.is_fresh(self.root, self.root / ".agents" / "MAP.md", self.skills())
        )

    def test_first_run_regenerates_then_reports_fresh(self):
        self.add_skill("alpha")
        code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("regenerated", out)
        self.assertTrue((self.root / ".agents" / "MAP.md").is_file())
        self.assertTrue(
            gen.is_fresh(self.root, self.root / ".agents" / "MAP.md", self.skills())
        )

        code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("MAP.md is fresh", out)

    def test_mutating_a_skill_invalidates_the_index(self):
        p = self.add_skill("alpha")
        self.run_main()
        p.write_text(p.read_text(encoding="utf-8") + "more\n", encoding="utf-8")
        _, out = self.run_main()
        self.assertIn("regenerated", out)

    def test_mutating_a_persona_invalidates_the_index(self):
        # M1: personas are rendered into MAP.md, so they must feed the snapshot.
        self.add_skill("alpha")
        agents = self.root / ".agents" / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        persona = agents / "coder.md"
        persona.write_text(
            "---\nname: coder\ndescription: d\n---\n# Coder\n", encoding="utf-8"
        )
        self.run_main()
        persona.write_text(
            "---\nname: coder\ndescription: d2\n---\n# Coder\n", encoding="utf-8"
        )
        _, out = self.run_main()
        self.assertIn("regenerated", out)

    def test_unknown_snapshot_line_is_not_fresh(self):
        self.add_skill("alpha")
        map_file = self.root / ".agents" / "MAP.md"
        map_file.parent.mkdir(parents=True, exist_ok=True)
        map_file.write_text("- Snapshot: deadbeef\n", encoding="utf-8")
        self.assertFalse(gen.is_fresh(self.root, map_file, self.skills()))

    def test_force_regenerates_even_when_fresh(self):
        self.add_skill("alpha")
        self.run_main()
        _, out = self.run_main("--force")
        self.assertIn("regenerated", out)


class MapContentTest(MapBase):
    def test_rows_show_active_condition_and_source_link(self):
        self.add_skill("always-skill", scope="always")
        self.add_skill("ondemand-skill", tags=["triage", "lane"])
        _, _ = self.run_main()
        text = self.map_text()
        self.assertIn("**always-skill**", text)
        self.assertIn("*Always active*", text)
        self.assertIn("**ondemand-skill**", text)
        self.assertIn("*Use when: `triage`, `lane`*", text)
        self.assertIn("(.agents/skills/always-skill/SKILL.md)", text)

    def test_output_is_ascii_only(self):
        self.add_skill("alpha", description="dash \u2014 and emoji \U0001f600 end")
        self.run_main()
        text = self.map_text()
        self.assertTrue(all(ord(ch) < 128 for ch in text), "MAP.md must be ASCII-only")
        self.assertIn("dash - and emoji", text)


class ParseFrontMatterTest(MapBase):
    def test_parses_scalars_and_dash_lists(self):
        fields = gen.parse_front_matter(
            "---\nname: alpha\ndescription: does things\ntags:\n  - one\n  - two\n---\n# x\n"
        )
        self.assertEqual(fields["name"], "alpha")
        self.assertEqual(fields["description"], "does things")
        self.assertEqual(fields["tags"], ["one", "two"])

    def test_sanitize_ascii_maps_punctuation(self):
        self.assertEqual(gen.sanitize_ascii("a \u2014 b \u2192 c"), "a - b -> c")


if __name__ == "__main__":
    unittest.main()
