# 001: map-generator — First Core Skill (Skill-Local Index Engine)

Status: APPROVED | Phase: 2-Build | Author: AI Agent | Date: 2026-08-15

> **Derived from:** `docs/architecture/000-modular-agent-orchestration-v7.md` (master reference, approved, verbatim), `AGENT.md`, and `.agents/rules/system.md` (behavioral contract, accepted).
> **Supersedes:** `docs/specs/001-core-skill-refinement.md` (multi-skill pass design; replaced by this single-skill spec).
> This spec designs the framework's first core skill in full — engine, SKILL.md doc, and MAP.md output contract. It is the design record; **no code changes have been made yet.**

## 1. Goal & Context

The Modular Agent Orchestration framework requires a Dynamic Map Generator (000 §11): an engine that scans skill folders, verifies index freshness by timestamp, and compiles `.agents/MAP.md` — the single discovery surface every session consults before any prompt processing (system.md §2 step 1). No skill or MAP.md exists in committed history yet, so **map-generator is the first skill to build**: it is the bootstrap dependency for auto-router (the next skill) and the freshness gate that opens every session. This spec designs the whole skill.

## 2. Architectural Decisions & Trade-offs

**D1. Skill-local scripts (structural rule).** The engine lives inside the skill folder: `.agents/skills/map-generator/scripts/generate_map.py`. Each core skill owns its scripts, making skill folders self-contained and portable (drop-in, no shared-scripts coupling). Trade-off: `system.md` §2 step 1's engine path must be repointed — a one-line edit, and the only modification to the accepted behavioral contract; the top-level `.agents/scripts/` is not used for skill engines.

**D2. mtime-based freshness (000 §11).** A no-arg run compares the newest modification time across `AGENT.md`, `.agents/rules/*.md`, and `.agents/skills/*/**` against `.agents/MAP.md`. If the index is up to date, print `MAP.md is fresh` and exit 0; otherwise rebuild and print `regenerated`. `--force` skips the comparison and rebuilds unconditionally. These two strings match system.md §2 step 1's contract verbatim ("if it reports 'regenerated', re-read the index"). Trade-off: mtime comparison is exactly what 000 §11 specifies and is cheap; clock skew is the only edge case, and exit-0 freshness is the safe failure.

**D3. MAP.md format is a contract, defined here.** Since nothing is committed, this spec fixes the output format that auto-router (skill #2) will parse: auto-generated banner (warning + engine path + generated timestamp + snapshot hash), then sections — **Always-loaded** (`scope: always`), **Situational Rules** (`scope: on-demand`), **Core System Skills**, **Optional Extension Skills**, and a loading-semantics footer. The snapshot hash (over scanned front-matter) gives readers a cheap change signal.

**D4. Zero-hardcoding classification.** The engine never hardcodes skill names. Core vs. optional comes from each SKILL.md front-matter field (`type: core | optional`); unknown/missing `type` defaults to `optional` (fail-safe — never over-privilege). Trade-off: classification lives in each skill's own metadata instead of one central list; misdeclaration is caught at review. This preserves 000 §6's zero-hardcoding principle inside the index engine itself.

**D5. Scope field drives load classes.** `scope: always` (front-matter) lands in Always-loaded; `scope: on-demand` (default) lands in the situational/skills sections. Defaults follow system.md §1: always for `.agents/rules/`, on-demand for `.agents/skills/`. Rules and AGENT.md are indexed alongside skills so the index is the authoritative list of both load classes (system.md §1).

## 3. Affected Files & Scope

- Created: `.agents/skills/map-generator/scripts/generate_map.py` — engine (scan, front-matter parse, classify, emit MAP.md; freshness + `--force` modes)
- Created: `.agents/skills/map-generator/SKILL.md` — skill doc (front-matter + run contract)
- Modified: `.agents/rules/system.md` — §2 step 1 engine path repoint
- Generated: `.agents/MAP.md` — engine output; committed as the discovery index
- Created: `docs/specs/001-map-generator-core-skill.md` — this spec
- Deleted: `docs/specs/001-core-skill-refinement.md` — superseded by this spec
- Untouched: `AGENT.md`, `docs/architecture/000-modular-agent-orchestration-v7.md`, `docs/temp/`

## 4. Actionable TODO Checklist

- [ ] Step 1: Create `.agents/skills/map-generator/scripts/generate_map.py` — scan `AGENT.md`, `.agents/rules/*.md`, `.agents/skills/*/SKILL.md`; parse YAML front-matter (`name`, `type`, `scope`, `trigger_tags`, `description`); classify core/optional per D4; compute snapshot hash; emit MAP.md per the D3 format (banner, timestamp, hash, sections, footer).
- [ ] Step 2: Implement freshness mode — no-arg run compares newest scanned mtime against MAP.md (D2); print `MAP.md is fresh` + exit 0, or rebuild + print `regenerated`.
- [ ] Step 3: Implement `--force` — unconditional rebuild, print `regenerated`.
- [ ] Step 4: Update `.agents/rules/system.md` §2 step 1 — repoint engine path to `.agents/skills/map-generator/scripts/generate_map.py`.
- [ ] Step 5: Create `.agents/skills/map-generator/SKILL.md` — front-matter (`name: map-generator`, `type: skill`, `scope: on-demand`, `trigger_tags: [map, index, skill discovery, synchronize]`, description); body: purpose (000 §11), both run modes, freshness strings, "never match against a stale index" rule, engine ownership note.
- [ ] Step 6: Run the engine twice — first `regenerated`, second `MAP.md is fresh`.
- [ ] Step 7: Verify MAP.md content — banner + timestamp + hash; Always-loaded lists `AGENT.md` and the system rule; Core System Skills lists map-generator with tags; Optional Extension Skills placeholder present; loading-semantics footer present.
- [ ] Step 8: Confirm `git status --short` shows only the intended files (§3).

## 5. Verification Commands

- `python .agents/skills/map-generator/scripts/generate_map.py` — twice: `regenerated`, then `MAP.md is fresh` (idempotency)
- `python .agents/skills/map-generator/scripts/generate_map.py --force` — rebuilds regardless of freshness
- Visual: `.agents/MAP.md` sections per D3; `system.md` §2 step 1 path equals engine path
- `git status --short` shows only §3 files; no stale `.agents/scripts/` references remain

## 6. Rollback Strategy

- Delete `.agents/skills/map-generator/` (SKILL.md + `scripts/`).
- `git checkout .agents/rules/system.md` reverts the one-line path edit.
- Delete generated `.agents/MAP.md`.
- The superseded `001-core-skill-refinement.md` was uncommitted (untracked) — no git copy exists; recreate from session history only if ever needed. This spec is the replacement design record.