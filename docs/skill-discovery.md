---
tags: [discovery, indexing, map, skills, recall]
---

# Skill Discovery & Indexing

How the framework finds and loads skills: the generated `MAP.md` index, snapshot-hash freshness, and the two-stage recall that turns a prompt into candidate skills.

## Current State

### The index: `.agents/MAP.md`

`MAP.md` is the single table-format index of all skills. It is **generated, never hand-edited**, and not part of the committed tree — it exists on disk after the first `generate_map.py` run and is rebuilt whenever its freshness check fails.

Format (engine output, ASCII-only by design):

```text
# Workspace Agent Map (`MAP.md`)

> [!NOTE]
> This file is auto-generated ... Do not modify this file manually ...

- Generated: 2026-08-22T15:00:46Z
- Snapshot: 1fdd8835

## Skills & Instructions

| Skill | Description | Active Condition | Source File |
| :--- | :--- | :--- | :--- |
| **auto-router** | Intent triage ... | *Always active* | [auto-router/SKILL.md](...) |
...
```

- One row per `SKILL.md` under `.agents/skills/`, sorted by name.
- `Active Condition` derives from frontmatter: `scope: always` → `*Always active*`; otherwise `*Use when: <tags>*` from the `tags` field.
- A `## Personas & Roles` table is emitted only if `.agents/agents/` exists (per-project extensibility; not present in this repo).
- Output is sanitized to ASCII (em/en dashes, smart quotes, ellipsis, arrows mapped; emoji dropped) so the index renders cleanly in Windows-1252 viewers.

### Freshness: snapshot hash, not timestamps

An earlier design compared timestamps; the implementation uses a **content snapshot hash**:

1. The engine recomputes a content hash over every `SKILL.md`.
2. It compares against the `Snapshot:` line in the existing `MAP.md`.
3. Mismatch → rebuild and print `regenerated`; match → print `MAP.md is fresh` and touch nothing.

The hash is mtime-independent: it catches skills copied in with old timestamps (git restore, worktree checkout, clock skew) that a pure mtime check would miss. Without a `Snapshot:` line (pre-snapshot index), the engine falls back to mtime comparison.

Engine: `python .agents/skills/map-generator/scripts/generate_map.py` (`--force` rebuilds unconditionally — use only after an accidental manual edit, which is forbidden).

### Why MAP.md gates everything

`dev-agent-framework.md` step 1 runs the freshness check **before** any prompt is processed, and auto-router instruction 3 re-reads `MAP.md` whenever `regenerated` was reported. The rule is absolute: never match skills against a stale index. A missing or stale `MAP.md` is a boot-chain violation, not a degraded mode.

### Recall stage 1: `match_skills.py`

After triage, auto-router runs the recall engine on the raw prompt:

```text
python .agents/skills/auto-router/scripts/match_skills.py "<prompt>"
```

Mechanics:

- **Ranking:** MAP.md rows are scored by tag hits first, then description hits (4-character prefix matching), and printed with a `Match:` column explaining each hit (e.g. `Match: tag: test; desc: prompt`).
- **Refusal to run cold:** if `MAP.md` is missing or stale, the engine prints `run map-generator first` and exits — it will not score against a stale index.
- **Output is candidates only.** The engine can never exclude a skill: a skill with zero literal hits can still apply. That is recall stage 2.

Example (prompt `test prompt`):

```text
candidates for: test prompt
(candidates only - re-read .agents/MAP.md when candidates look thin)
1. spec-builder         Match: tag: prompt; desc: prompt
2. verification-runner  Match: tag: test; desc: test
3. task-cleaner         Match: desc: prompt
```

### Recall stage 2: judgment (agent)

Stage 2 is the agent's judgment over stage 1's output:

- Thin or zero candidates → re-read the full `MAP.md` and match by semantic relation.
- Absence from the engine's list is never proof a skill does not apply.
- The selected skills are then loaded by opening their `SKILL.md` (and its `references/`) with the read tool — there is no harness skill-injection mechanism; loading is disk-read, which is what keeps the framework harness-agnostic.

### Adding a new skill (dynamic discovery)

1. Drop a folder: `.agents/skills/<name>/SKILL.md` with canonical frontmatter (`name`, `description`, `tags`; optional `scope: always`; `trigger_tags` is a legacy fallback for `tags`).
2. Next session start, `generate_map.py` detects the hash mismatch and prints `regenerated`; the new row appears in `MAP.md`.
3. `match_skills.py` can now score the new skill. No router, rulebook, or other file is edited — zero hardcoding of skill names anywhere.

To change a skill's indexed metadata, edit its `SKILL.md` frontmatter and let the engine regenerate — never hand-edit `MAP.md`.

## Decision Log

No subsystem-specific decisions are recorded in this doc; it describes the current indexing and recall mechanics. See `overview.md` for the framework overview and `routing.md` for how recall feeds lane triage.
