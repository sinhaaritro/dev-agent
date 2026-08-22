tags: [auto-router, core-skill, lane-taxonomy, triage]

# 002: auto-router — Second Core Skill (Intent Triage & Lane Taxonomy Engine)

Status: APPROVED | Phase: 2-Build | Date: 2026-08-15

Superseded (SKILL.md format): the frontmatter shape prescribed in this spec's unchecked TODOs (flat `version:`/`author:`/`scope:` fields) was replaced by the minimal nested-`metadata` contract in spec 009 (adjudicated 2026-08-19); the current live files under `.agents/skills/` are the implementation truth.

> **Derived from:** `docs/architecture/000-modular-agent-orchestration-v7.md` (master reference, approved, verbatim; §§3-6: lanes, session detection, escalation, dynamic skill discovery), `AGENTS.md` (`autonomy_level: supervised`), and `.agents/rules/system.md` (behavioral contract, accepted; §2 step 2 is auto-router's boot position).
> **Supersedes:** the untracked scaffold `.agents/skills/auto-router/SKILL.md` (stale frontmatter and engine path; see §1). `docs/specs/001-map-generator-core-skill.md` named auto-router as "the next skill" after map-generator; this spec is that design.
> This spec designs the framework's second core skill in full — decision matrix, assist engine, SKILL.md doc, and the phase-protocol handoff contract. It is the design record; **no code changes have been made yet.**

## 1. Goal & Context

The Modular Agent Orchestration framework requires an intent triage engine (000 §4) that classifies every incoming prompt into exactly one of four Execution Lanes (D/C/B/A), detects the session type (Interactive vs. Non-Interactive), monitors scope escalation, and matches skills dynamically via `.agents/MAP.md` (000 §6) with zero hardcoding. Per `.agents/rules/system.md` §2, every request is processed in this order: **step 1** map-generator freshness gate (built and committed, `b1dbf8a`) → **step 2** auto-router → **step 3** phase-protocol → **step 4** on-demand skills. Auto-router is `scope: always` (system.md §1), so it loads at every session start — it is the critical next step in the boot chain, and its dependency (a generated, fresh `MAP.md`) is now satisfied.

The current `.agents/skills/auto-router/SKILL.md` scaffold is untracked and stale: its frontmatter uses legacy fields (`type: core`, `trigger_tags`) that violate the frontmatter contract fixed by spec 001 D4; §5 references the obsolete engine path `.agents/scripts/generate_map.py` (repointed to `.agents/skills/map-generator/scripts/generate_map.py` in 001); and it lacks `version`/`author`. It is replaced in place by this spec's design.

## 2. Architectural Decisions & Trade-offs

**D1. Two-stage recall engine — assist, never filter.** The skill owns an assist engine: `.agents/skills/auto-router/scripts/match_skills.py` (skill-local scripts per 001 D1's structural rule; stdlib-only Python, styled after `generate_map.py`). Stage 1 is mechanical: the engine reads `.agents/MAP.md` (the discovery surface, 000 §6 — never a hardcoded list), tokenizes the prompt (lowercase, strip non-alphanumerics, drop stopwords), and per row computes two hit sets: **tag hits** (prompt tokens overlapping the row's `tags`) and **description hits** (prompt tokens overlapping the description column, matched with 4-character prefix matching so `scratch` hits `scratchpad`). Rows print ranked — tag hits first, then description hits — with a `Match:` column showing exactly which tokens hit (`tag: promote, spec` / `desc: scratchpad`). With 20 skills, tag hits may surface ~10; description hits rescue a further subset mechanically; the rest stay silent. Zero hits prints `no candidates — review full index manually` (exit 0 — advisory, never an error). Stage 2 is judgment: the engine output is **candidates only and can never exclude** — the agent must still re-read the full `MAP.md` when candidates are thin, and may select a skill with zero literal hits if the prompt semantically relates to its description. This two-stage design answers the recall question directly: a description read can select skills that tag matching missed, both mechanically (word overlap) and by judgment (semantic relation). Trade-off: literal matching is naive and will miss synonyms; the candidate-only contract makes that harmless — the engine exists to speed recall, not to bound it. If `MAP.md` is missing entirely, the engine exits 1 with `run map-generator first` (system.md §2 step 1 ordering is enforced, not duplicated).

**D2. Decision procedure in `references/lane-matrix.md`.** The lane table (D/C/B/A criteria, docs artifacts, Socratic gates, verification), the four escalation rules (000 §4: announce-only upward escalation, human-confirmed de-escalation, ambiguous → higher lane, Lane D never auto-escalates with request splitting), and session detection (Interactive if a human can plausibly respond this turn; default Non-Interactive) live in a dedicated reference file, mirroring phase-protocol's `references/` pattern. `SKILL.md` stays lean and loads the matrix at every triage. Trade-off: one extra file vs. a bloated SKILL.md; the matrix is the single source of truth for lane criteria and can be extended with worked examples without touching the skill contract.

**D3. Frontmatter contract compliance.** The new `SKILL.md` follows the standard frontmatter fixed by 001 D4: `name: auto-router`, `description` (ASCII-safe, one sentence), `version: 1.0.0`, `author: AI Agent`, `tags` (triage, lane, escalation, session, routing), custom `scope: always`. Legacy `type: core` and `trigger_tags` are dropped. Consequence: `map-generator` renders auto-router's Active Condition as `*Always active*` in `MAP.md`, matching system.md §1's always-loaded set.

**D4. Handoff contract to phase-protocol — no gate authority.** Auto-router's output is a routing verdict, not a decision: it emits **Lane** (A/B/C/D), **Session** (Interactive/Non-Interactive), **candidate skills**, and an optional **escalation flag**. Phase-protocol consumes these into the `[STATUS: ... | Lane: X | Session: Y]` header and its phase routing (phase-protocol §4). Socratic gates (blocking/non-blocking), the autonomy policy, and the 4-Block response schema are exclusively phase-protocol's domain — auto-router never halts for a gate and never applies autonomy policy. Mid-flight re-triage: if execution reveals a higher-lane criterion, auto-router re-runs classification, **announces** the upward escalation (never asks permission, never silently de-escalates), and phase-protocol continues under the new lane. Trade-off: strict separation keeps each skill's authority legible; the cost is that the verdict must be re-emitted through the header on every escalation.

**D5. Zero hardcoding, verifiably.** The engine reads `MAP.md` only; no skill name appears in `SKILL.md` or the engine beyond auto-router's own identity. This is *testable*: modify any skill's `tags`, regenerate `MAP.md`, and the engine's output for that skill changes without the engine source being touched. This mirrors 001's snapshot-freshness verification style and proves 000 §6's "zero hardcoding" claim mechanically.

**D6. Commit `.agents/MAP.md` with this task.** Spec 001 §3 declared the generated index "committed as the discovery index", but commit `b1dbf8a` omitted it — `MAP.md` is still untracked. This task regenerates and commits it. Rationale: the index is the single discovery surface every session consults (000 §6); versioning it gives a stable baseline on fresh checkouts and diff visibility when skills change. Trade-off: generated files can cause merge noise; the map-generator idempotency rule (never write when fresh) limits this to actual skill changes.

## 3. Affected Files & Scope

- Created: `.agents/skills/auto-router/SKILL.md` — skill doc (frontmatter per D3 + triage contract; overwrites the untracked scaffold in place, no git delete needed)
- Created: `.agents/skills/auto-router/references/lane-matrix.md` — lane table, escalation rules, session detection, worked examples (D2)
- Created: `.agents/skills/auto-router/scripts/match_skills.py` — two-stage recall engine (D1)
- Modified: `.agents/rules/system.md` — §2 step 2: add engine invocation path + candidates-only semantics
- Generated: `.agents/MAP.md` — regenerated and **committed** with this task (D6; fixes 001 §3 leftover)
- Created: `docs/specs/002-auto-router-core-skill.md` — this spec
- Untouched: `AGENTS.md`, `docs/architecture/000-modular-agent-orchestration-v7.md`, `docs/specs/001-map-generator-core-skill.md`, `.agents/skills/map-generator/`, `docs/temp/`

## 4. Actionable TODO Checklist

- [ ] Step 1: Create `.agents/skills/auto-router/references/lane-matrix.md` — the four-lane table (Lane | Name | Scope Criteria | Docs Artifact | Socratic Gate | Verification) per 000 §4 verbatim semantics; top-down classification order (non-mutating → D; single-file <30-line diff without schema/API/auth/deps → C; 2-5 files without Lane-A surface → B; else → A); the four escalation rules; session detection with Non-Interactive default; worked examples (000 §4's four + ambiguous cases: a docs-only multi-file edit, "explain, then fix" request split, mid-flight escalation from C to B).
- [ ] Step 2: Create `.agents/skills/auto-router/scripts/match_skills.py` — stdlib-only; `find_root` via the `AGENTS.md` marker (mirror `generate_map.py`); read `.agents/MAP.md`; tokenize the prompt (lowercase, non-alphanumerics stripped, stopword list); per row compute tag hits and description hits (4-char prefix matching); print ranked candidates with a `Match:` column showing hit tokens; `no candidates — review full index manually` when nothing hits; missing `MAP.md` → exit 1 with `run map-generator first`; ASCII-only output (reuse 001's sanitize approach); exit 0 on success.
- [ ] Step 3: Create `.agents/skills/auto-router/SKILL.md` — frontmatter per D3 (`name`, ASCII `description`, `version: 1.0.0`, `author: AI Agent`, `tags`, `scope: always`; no `type:`/`trigger_tags`); body per the standard structure: Overview (initial gatekeeper, runs at system.md §2 step 2), When to Use (every session start, every prompt, mid-flight re-triage), Instructions (1. classify via `references/lane-matrix.md`; 2. detect session; 3. run the engine + Stage-2 judgment — candidates can never exclude; 4. hand off the verdict), Output contract (Lane/Session/candidates/escalation flag → `[STATUS: ...]` header, phase-protocol owns gates and response schema), Notes (no gate authority; re-read `MAP.md` when map-generator reports `regenerated`; never hardcode skill names).
- [ ] Step 4: Update `.agents/rules/system.md` §2 step 2 — add the engine invocation (`python .agents/skills/auto-router/scripts/match_skills.py "<prompt>"`) with the candidates-only caveat, alongside the existing lane/session/escalation line.
- [ ] Step 5: Regenerate `.agents/MAP.md` via `map-generator` (first run reports `regenerated`); verify the auto-router row shows Active Condition `*Always active*`; second run reports `MAP.md is fresh`.
- [ ] Step 6: Commit `.agents/MAP.md` with this task (D6 — 001 §3 declared it committed but it remains untracked).
- [ ] Step 7: Verify engine behavior per §5 — lane-sensitive prompts surface expected skills; the description-rescue case (e.g. "purge temp scratch files" hits task-cleaner via description, and "phases gate the workflow" hits phase-protocol with no tag hits at all); the no-hardcode test (add a tag to a skill's SKILL.md → regenerate MAP.md → engine output changes, engine source untouched → revert).
- [ ] Step 8: Confirm `git status --short` shows only §3 files; the scaffold was overwritten in place (untracked — no git delete entries).

## 5. Verification Commands

- `python .agents/skills/auto-router/scripts/match_skills.py "how do I promote a spec to docs/specs"` → spec-builder surfaces via tag hits (`promote`, `spec`).
- `python .agents/skills/auto-router/scripts/match_skills.py "the build keeps failing, retry three times then escalate"` → verification-runner surfaces (`build`, `retry`; `escalation` tag via 4-char prefix match on `escalate`).
- `python .agents/skills/auto-router/scripts/match_skills.py "purge the temp scratchpad after acceptance"` → task-cleaner surfaces via tags (`purge`, `acceptance`) and description (`scratchpad`).
- Description-rescue case: `python .agents/skills/auto-router/scripts/match_skills.py "phases gate the workflow"` → phase-protocol surfaces via description hits only (no tags on the row) — proves the recall path beyond tag matching.
- No-hardcode test: add a tag (e.g. `cache`) to a skill's SKILL.md → `python .agents/skills/map-generator/scripts/generate_map.py --force` → re-run the engine with a prompt using that word → the skill now surfaces; revert the tag, regenerate, confirm the original output.
- Idempotency: run `map-generator` twice — first `regenerated`, then `MAP.md is fresh`.
- Visual: `.agents/MAP.md` auto-router row reads `*Always active*`; candidates output is ASCII-only; `system.md` §2 step 2 includes the engine path.
- `git status --short` shows only §3 files; no stale `.agents/scripts/` references remain.

## 6. Rollback Strategy

- Delete `.agents/skills/auto-router/` (`SKILL.md`, `references/lane-matrix.md`, `scripts/match_skills.py`).
- `git checkout .agents/rules/system.md` reverts the §2 step 2 edit.
- Delete `docs/specs/002-auto-router-core-skill.md`.
- `.agents/MAP.md`: `git checkout .agents/MAP.md` restores the committed index; it is regenerable by the map-generator engine at any time.
- The superseded scaffold was uncommitted (untracked) — no git copy exists; its lane/escalation/session content is fully covered by 000 §§3-6 and this spec, so recreation from history is unnecessary.