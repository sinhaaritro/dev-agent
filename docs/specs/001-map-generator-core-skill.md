tags: [core-skill, index, map-generator, skill-discovery]

# 001: map-generator — First Core Skill (Skill-Local Index Engine)

Status: APPROVED | Phase: 2-Build | Date: 2026-08-15

> **Derived from:** `docs/architecture/000-modular-agent-orchestration-v7.md` (master reference, approved, verbatim), `AGENTS.md`, and `.agents/rules/system.md` (behavioral contract, accepted).
> **Supersedes:** `docs/specs/001-core-skill-refinement.md` (multi-skill pass design; replaced by this single-skill spec).
> This spec designs the framework's first core skill in full — engine, SKILL.md doc, and MAP.md output contract. It is the design record; **no code changes have been made yet.**

## 1. Goal & Context

The Modular Agent Orchestration framework requires a Dynamic Map Generator (000 §11): an engine that scans skill folders, verifies index freshness by timestamp, and compiles `.agents/MAP.md` — the single discovery surface every session consults before any prompt processing (system.md §2 step 1). No skill or MAP.md exists in committed history yet, so **map-generator is the first skill to build**: it is the bootstrap dependency for auto-router (the next skill) and the freshness gate that opens every session. This spec designs the whole skill.

## 2. Architectural Decisions & Trade-offs

**D1. Skill-local scripts (structural rule).** The engine lives inside the skill folder: `.agents/skills/map-generator/scripts/generate_map.py`. Each core skill owns its scripts, making skill folders self-contained and portable (drop-in, no shared-scripts coupling). Trade-off: `system.md` §2 step 1's engine path must be repointed — a one-line edit, and the only modification to the accepted behavioral contract; the top-level `.agents/scripts/` is not used for skill engines.

**D2. Snapshot-hash freshness (000 §11, improved).** A no-arg run recomputes the content hash over every SKILL.md and compares it to the `Snapshot:` line stored in `MAP.md`. Match → print `MAP.md is fresh`, exit 0; mismatch → rebuild, print `regenerated`. `--force` skips the check and rebuilds unconditionally. The two output strings match system.md §2 step 1's contract verbatim ("if it reports 'regenerated', re-read the index"). Trade-off: hashing replaces 000 §11's pure mtime comparison because mtimes are unreliable — skills copied in with old timestamps (git restore, worktree checkout, clock skew) would be silently missed; the hash is content-based and immune. Indexes without a `Snapshot:` line fall back to mtime comparison.

**D3. MAP.md format is a contract, defined here.** Since nothing is committed, this spec fixes the output format: a flat table index where all skills are treated as equal (agent-map.md style) — auto-generated banner with `> [!NOTE]` warning, generated timestamp, and snapshot hash; a `## Skills & Instructions` table (`Skill | Description | Active Condition | Source File`) sorted by skill name; and an optional `## Personas & Roles` table emitted only when a `.agents/personas/` folder exists (per-project extensibility). The output is **ASCII-only by design**: Unicode punctuation (em/en dashes, smart quotes, ellipsis, arrows) maps to ASCII equivalents and emoji is dropped, so the index renders cleanly in viewers that default to Windows-1252. The snapshot hash (over scanned SKILL.md contents) gives readers a cheap change signal.

**D4. Flat model — all skills equal, zero hardcoding.** The engine never hardcodes skill names and makes no core/optional split: every SKILL.md under `.agents/skills/` gets one row. Standard SKILL.md frontmatter (`name`, `description`, `version`, `author`, `tags`, `requires`) is parsed per the Skills Directory format, with `trigger_tags` accepted as a legacy fallback for `tags`. Trade-off: the 000 §5 core/optional catalog is no longer reflected in the index — classification duties move to `scope` (load behavior) and `tags` (routing), keeping the index truthful to disk state.

**D5. Scope drives the Active Condition column.** `scope: always` renders `*Always active*`; on-demand renders `*Use when: <tags>*`. Defaults follow system.md §1: always for `.agents/rules/`, on-demand for `.agents/skills/`. AGENTS.md and rules are no longer indexed — system.md §1 keeps their textual list, and the index is the authoritative generated list of skills only.

## 3. Affected Files & Scope

- Created: `.agents/skills/map-generator/scripts/generate_map.py` — engine (scan, front-matter parse, classify, emit MAP.md; freshness + `--force` modes)
- Created: `.agents/skills/map-generator/SKILL.md` — skill doc (front-matter + run contract)
- Modified: `.agents/rules/system.md` — §1 wording (skills-only index) + §2 step 1 engine path repoint
- Generated: `.agents/MAP.md` — engine output; committed as the discovery index
- Created: `docs/specs/001-map-generator-core-skill.md` — this spec
- Deleted: `docs/specs/001-core-skill-refinement.md` — superseded by this spec
- Untouched: `AGENTS.md`, `docs/architecture/000-modular-agent-orchestration-v7.md`, `docs/temp/`

## 4. Actionable TODO Checklist

- [x] Step 1: Create `.agents/skills/map-generator/scripts/generate_map.py` — scan `.agents/skills/*/SKILL.md`; parse standard front-matter (`name`, `description`, `version`, `author`, `tags`, `requires`, legacy `trigger_tags` fallback, custom `scope`); compute snapshot hash; emit MAP.md per the D3 format (banner, `> [!NOTE]`, timestamp, hash, Skills & Instructions table, optional Personas table).
- [x] Step 2: Implement freshness mode — no-arg run compares the recomputed snapshot hash against the `Snapshot:` line in MAP.md (D2); print `MAP.md is fresh` + exit 0, or rebuild + print `regenerated`; mtime fallback for legacy indexes.
- [x] Step 3: Implement `--force` — unconditional rebuild, print `regenerated`.
- [x] Step 4: Update `.agents/rules/system.md` — §1 wording (index is the generated skill list, all skills equal) + §2 step 1 engine path repoint to `.agents/skills/map-generator/scripts/generate_map.py`.
- [x] Step 5: Create `.agents/skills/map-generator/SKILL.md` — standard front-matter (`name: map-generator`, `description`, `version: 1.0.0`, `author: AI Agent`, `tags`, custom `scope: on-demand`); body per the standard structure (Overview, When to Use, Instructions, Output Format, Notes).
- [x] Step 6: Run the engine twice — first `regenerated`, second `MAP.md is fresh`.
- [x] Step 7: Verify MAP.md content — banner + `> [!NOTE]` + timestamp + hash; `## Skills & Instructions` table lists map-generator with description, Active Condition (`*Use when: map, index, ...*`), and source link; all on-disk skills present as equal rows; output is ASCII-only (no emoji, no Unicode dashes).
- [x] Step 8: Confirm `git status --short` shows only the intended files (§3).

## 5. Verification Commands

- `python .agents/skills/map-generator/scripts/generate_map.py` — twice: `regenerated`, then `MAP.md is fresh` (idempotency)
- `python .agents/skills/map-generator/scripts/generate_map.py --force` — rebuilds regardless of freshness
- Visual: `.agents/MAP.md` renders the table format per D3 (Skill | Description | Active Condition | Source File); `system.md` §1 wording + §2 step 1 path consistent
- `git status --short` shows only §3 files; no stale `.agents/scripts/` references remain

## 6. Rollback Strategy

- Delete `.agents/skills/map-generator/` (SKILL.md + `scripts/`).
- `git checkout .agents/rules/system.md` reverts the one-line path edit.
- Delete generated `.agents/MAP.md`.
- The superseded `001-core-skill-refinement.md` was uncommitted (untracked) — no git copy exists; recreate from session history only if ever needed. This spec is the replacement design record.