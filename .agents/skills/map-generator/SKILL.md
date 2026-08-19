---
name: map-generator
description: Index sync - checks timestamp freshness and rebuilds .agents/MAP.md when skills or rules change. Use when starting a session, adding/removing/editing skills, or verifying the skill index.
tags:
  - map
  - index
  - skill discovery
  - synchronize
metadata:
  version: 1.1.0
  author: AI Agent
---

# Map Generator

## Overview

You keep `.agents/MAP.md` current — the single table-format index of all skills. Run before relying on the index (at session start per system.md step 1, and after any skill change). Never match against a stale index.

## When to Use

- At session start, before any prompt is triaged (system.md step 1).
- After creating, editing, or deleting anything under `.agents/skills/`.
- Whenever `.agents/MAP.md` is suspected stale or hand-edited.

## Instructions

1. Engine: `.agents/skills/map-generator/scripts/generate_map.py`.
2. Run it (one-time setup: `uv venv` in the repo root):
   `python .agents/skills/map-generator/scripts/generate_map.py`
3. Interpret the output exactly:
   - `MAP.md is fresh` — index is current; proceed with the existing MAP.md.
   - `regenerated` — index was rebuilt; **re-read** `.agents/MAP.md` before matching anything against it.
4. `--force` rebuilds unconditionally:
   `python .agents/skills/map-generator/scripts/generate_map.py --force`
   (Use after manual MAP.md edits — which are forbidden; the file is auto-generated.)

## Output Format

MAP.md is a flat table-format index — all skills treated as equal:

- Auto-generated banner with a `> [!NOTE]` warning, generated timestamp, and snapshot hash.
- `## Skills & Instructions` table: `Skill | Description | Active Condition | Source File`, one row per SKILL.md under `.agents/skills/`, sorted by name.
- `## Personas & Roles` table emitted only when `.agents/personas/` exists (per-project extensibility).
- Active Condition derives from frontmatter: `scope: always` → `*Always active*`; otherwise `*Use when: <tags>*` from the `tags` field.

The output is **ASCII-only by design**: the engine maps common Unicode punctuation (em/en dashes, smart quotes, ellipsis, arrows) to ASCII and drops emoji, keeping the index clean in Windows-1252-viewing renderers. Frontmatter follows the canonical SKILL.md contract: required `name`, `description`, `tags`, and a nested `metadata` block (`version`, `author`); optional `scope: always` (on-demand is the default); `requires` for personas; `trigger_tags` is a legacy fallback for `tags`.

## Freshness Check

Freshness is the **snapshot hash**: the engine recomputes a content hash over every SKILL.md and compares it to the `Snapshot:` line. A mismatch means a skill changed (or appeared) and triggers a rebuild. This is mtime-independent — it catches skills copied in with old timestamps (git restore, worktree checkout, clock skew) that a pure timestamp check would miss. Without a `Snapshot:` line (pre-snapshot index), the engine falls back to mtime comparison.

## Notes

- Never write MAP.md when fresh — the no-arg run stays idempotent (second run: `MAP.md is fresh`).
- The engine is stdlib-only Python; no third-party imports without a spec update.
- Fix wrong index metadata by editing the skill's SKILL.md frontmatter and regenerating — never hand-edit MAP.md.
- Emitted output stays ASCII-safe; non-ASCII frontmatter text is sanitized on output.
