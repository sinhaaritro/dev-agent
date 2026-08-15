---
name: map-generator
description: Index sync - checks timestamp freshness and rebuilds .agents/MAP.md when skills or rules change. Use when starting a session, adding/removing/editing skills, or verifying the skill index.
version: 1.1.0
author: AI Agent
tags:
  - map
  - index
  - skill discovery
  - synchronize
scope: on-demand
---

# Map Generator

## Overview

You keep `.agents/MAP.md` current - the single table-format index of all skills in this repository. Run before relying on the index (at session start per system.md section 2 step 1, and after any skill addition, modification, or removal). Never match against a stale index.

## When to Use

- At session start, before any prompt is triaged (system.md section 2 step 1).
- After creating, editing, or deleting any file under `.agents/skills/`.
- Whenever `.agents/MAP.md` is suspected to be stale or was accidentally hand-edited.

## Instructions

1. Locate the engine: `.agents/skills/map-generator/scripts/generate_map.py`.
2. Run it with the repository's venv (one-time setup: `uv venv` in the repo root):
   `uv run python .agents/skills/map-generator/scripts/generate_map.py`
3. Interpret the output exactly:
   - `MAP.md is fresh` - index is current; proceed with the existing `.agents/MAP.md`.
   - `regenerated` - the index was rebuilt; **re-read** `.agents/MAP.md` before matching anything against it.
4. `--force` rebuilds unconditionally:
   `uv run python .agents/skills/map-generator/scripts/generate_map.py --force`
   (Use after manual `MAP.md` edits - which are forbidden anyway; the file is auto-generated.)

## Output Format

`.agents/MAP.md` is a flat table-format index - all skills are treated as equal:

- Auto-generated banner with a `> [!NOTE]` warning, generated timestamp, and snapshot hash.
- `## Skills & Instructions` table with columns `Skill | Description | Active Condition | Source File`, one row per SKILL.md under `.agents/skills/`, sorted by skill name.
- `## Personas & Roles` table emitted only when a `.agents/personas/` folder exists (per-project extensibility).
- Active Condition is derived from frontmatter: `scope: always` -> `*Always active*`; otherwise `*Use when: <tags>*` from the `tags` field.

The output is **ASCII-only by design**: the engine maps common Unicode punctuation (em/en dashes, smart quotes, ellipsis, arrows) to ASCII equivalents and drops emoji. This keeps the index rendering clean in viewers that default to Windows-1252. Frontmatter is still parsed per the standard SKILL.md format (`name`, `description`, `version`, `author`, `tags`, `requires`); `scope` is the only custom extension field. `trigger_tags` is accepted as a legacy fallback for `tags`.

## Freshness Check

Freshness is decided by the **snapshot hash**: the engine recomputes a content hash over every SKILL.md and compares it to the `Snapshot:` line stored in `MAP.md`. A mismatch means a skill changed (or a new one appeared) and the index is rebuilt. This is mtime-independent - it catches skills copied in with old timestamps (git restore, worktree checkout, clock skew) that a pure timestamp check would silently miss. If the index predates snapshot support (no `Snapshot:` line), the engine falls back to mtime comparison.

## Notes

- Never write `MAP.md` when it is fresh - the no-arg run must stay idempotent (second run reports `MAP.md is fresh`).
- The engine is stdlib-only Python; do not introduce third-party imports without updating the spec.
- To fix wrong metadata in the index, edit the skill's SKILL.md frontmatter and regenerate - never edit `MAP.md` by hand.
- Keep emitted output ASCII-safe; if the source frontmatter contains non-ASCII text the engine sanitizes it on output.