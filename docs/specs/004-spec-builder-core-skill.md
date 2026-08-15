# 004: spec-builder — Fourth Core Skill (Spec Lifecycle & Promotion Engine)

Status: APPROVED | Phase: 2-Build | Author: AI Agent | Date: 2026-08-15

> **Derived from:** `docs/architecture/000-modular-agent-orchestration-v7.md` (master reference, approved, verbatim; §§5, 7, 10: templates, promotion pipeline, memory lifecycle), `AGENT.md` (`autonomy_level: supervised`), `.agents/rules/system.md` (behavioral contract, accepted; §2 step 4 is spec-builder's boot position), and `docs/specs/003-phase-protocol-core-skill.md` (D4: references name this skill's template path as a forward contract).
> **Supersedes:** the untracked scaffold `.agents/skills/spec-builder/` (legacy frontmatter violating the 001 D4 contract; flat numbered sections; no engine). The phase-protocol references (`plan.md`, lane-matrix) already point at `.agents/skills/spec-builder/references/implementation-plan-template.md` — this spec makes that forward contract real.
> This spec designed the framework's fourth core skill in full - draft validation and promotion engine, SKILL.md doc, reference alignment, and the system.md boot-chain edit. **Implemented and verified on 2026-08-15 (all §5 checks green).**

## 1. Goal & Context

The Modular Agent Orchestration framework requires a spec lifecycle skill (000 §5.4, §7) that drafts implementation plans in `docs/temp/draft-plan.md` under enforced templates (Lane B: sections 1, 3, 4; Lane A: full six-section template), maintains real-time TODO checkboxes during Build, and promotes approved drafts to `docs/specs/<NNN>-<feature-slug>.md` on human acceptance (000 §10 promotion pipeline). Per `.agents/rules/system.md` §2, every request is processed in order: map-generator freshness gate → auto-router triage → phase-protocol governance → **step 4: on-demand skills** — spec-builder is the first on-demand skill in that step, loaded whenever a lane's plan must be drafted (Lanes B and A, per phase-protocol `plan.md`) or a spec promoted (Review phase, per phase-protocol `review.md`). phase-protocol's references already treat this skill as a forward contract: `plan.md` §2 mandates its template path and `review.md` §3 delegates promotion to it.

The current `.agents/skills/spec-builder/` scaffold is untracked and stale: its frontmatter uses legacy fields (`type: core`, `trigger_tags`, no `version`/`author`) violating the frontmatter contract fixed by 001 D4; its body is organized as flat numbered sections rather than the standard structure fixed by 002's committed SKILL.md; and its numbering ("Check existing files for the next number") is judgment, not mechanics — a safety gap because a wrong NNN can silently overwrite a committed spec. It is replaced in place by this spec's design.

## 2. Architectural Decisions & Trade-offs

**D1. `promote_spec.py` engine — check and promote modes.** The skill owns an assist engine: `.agents/skills/spec-builder/scripts/promote_spec.py` (skill-local scripts per 001 D1's structural rule; stdlib-only Python, styled after `generate_map.py` / `match_skills.py` / `resolve_gate.py`; `find_root` via the `AGENT.md` marker). Two modes:
- **check**: `promote_spec.py check <draft> --lane <B|A>` — parses the `## N.` section headings and validates presence of the lane's required sections (B: 1, 3, 4; A: 1-6); prints missing sections, exit 1 on any absence, exit 0 when complete. This enforces 000 §7's "identical formatting across all sessions" mechanically during Plan.
- **promote**: `promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL> [--dry-run] [--slug <override>] [--specs-dir <dir>]` — validates the draft for its lane, computes the next spec number by scanning the specs directory for the max `\d{3}-` prefix + 1 (zero-padded, sequential per scaffold §4), derives the slug from the draft title (`# [SPEC-ID]: Title` -> `title`; lowercase, non-alphanumerics to hyphens, collapsed), writes the promoted file with the `Status:` line replaced by the requested value (`PROVISIONAL` renders as `PROVISIONAL - AUTONOMOUS DEFAULT`, ASCII), refuses on duplicates — an existing spec whose first `# ` title matches the draft's (the title is the plan's identity; a repeat promotion must be refused even though the sequential number is new) or an exact path collision — and prints `promoted: docs/specs/004-<slug>.md`. Files are read BOM-tolerantly (`utf-8-sig`) so drafts written by Windows editors never degrade the slug. `--specs-dir` overrides the target directory for testing (verification and evals never touch the real `docs/specs/`); `--dry-run` prints the target path without writing. Trade-off: an engine on a judgment-y workflow — justified because numbering is the one silent-corruption risk (a wrong NNN overwrites a committed spec), duplicate promotion is the quiet-clutter risk, and template enforcement is mechanically checkable; the rest of the lifecycle (what the plan says) stays the agent's.

**D2. Frontmatter contract compliance.** The new `SKILL.md` follows the standard frontmatter fixed by 001 D4: `name: spec-builder`, `description` (ASCII-safe, one sentence), `version: 1.0.0`, `author: AI Agent`, `tags` (spec, plan draft, promote, implementation plan, template), custom `scope: on-demand`. Legacy `type: core` and `trigger_tags` are dropped. Consequence: `map-generator` renders spec-builder's Active Condition as `*Use when: spec, plan draft, promote, implementation plan, template*` — unchanged from today, but now contract-compliant.

**D3. SKILL.md restructured to the standard format.** The scaffold's flat numbered sections (1. Drafting, 2. TODO discipline, 3. Promotion, 4. Naming & numbering, 5. Guardrails) reorganize into the structure fixed by auto-router's committed SKILL.md: **Overview** (owns plan drafting + spec promotion; templates in `references/` are the single source of format truth; mandatory step 4 of the boot chain when a lane requires planning artifacts), **When to Use** (Lanes B/A planning per phase-protocol `plan.md`; Review promotion per `review.md`; any "draft a plan" / "promote a spec" request), **Instructions** (1. draft per lane into the running `docs/temp/draft-plan.md` - one plan file per task, never multiple; 2. validate with `check` before presenting the plan; 3. maintain TODO checkboxes in real time per `references/todo-checklist-format.md` - `[x]` only after local verification; 4. promote only on human acceptance, or a compliant autonomous resolution per phase-protocol, via `promote` with the correct `--status`; 5. Lane A architectural decisions (database, auth, public API) also produce an ADR at `docs/decisions/adr-<NNN>-<topic>.md` in Review), **Output Contract** (the draft at `docs/temp/draft-plan.md` during Plan; the promoted `docs/specs/<NNN>-<slug>.md` path + status during Review), **Notes** (never promote without the gate; numbering is engine-derived, never hand-written; protected files never touched while drafting; `--specs-dir` is for tests only, real promotions target `docs/specs/`). Trade-off: one restructure pass vs. preserving scaffold prose - the scaffold's guardrails survive; only the contract reorganizes and the mechanics move to the engine.

**D4. Numbering is engine-derived, never hardcoded.** The next spec number is computed by scanning the target specs directory (max `\d{3}-` prefix + 1), not guessed from memory or "check existing files" judgment. The slug derives from the draft's own title so the promoted file always matches its plan. Trade-off: the engine must read the directory on every promote - trivial cost, and it makes collisions structurally impossible rather than merely unlikely.

**D5. The acceptance gate is the caller's, the engine is mechanics only.** `promote` takes `--status` as an explicit argument: `APPROVED` (human acceptance) or `PROVISIONAL` (compliant autonomous resolution per phase-protocol, rendering `PROVISIONAL - AUTONOMOUS DEFAULT` until a human clears it, 000 §3.4.3). The engine never decides whether the gate passed - the agent asserts it through the status argument, keeping the separation of authority legible (gates/autonomy are phase-protocol's domain per 002 D4; the promotion mechanics are spec-builder's). Trade-off: an agent could pass the wrong status deliberately; that is a policy violation, not an engine failure - the audit trail (gate-log.md) records which status was lawful.

**D6. system.md §2 step 4 edit.** Step 4 gains the engine invocation lines, mirroring steps 2/3's edit pattern: drafts validate via `uv run python .agents/skills/spec-builder/scripts/promote_spec.py check <draft> --lane <B|A>`; promotions run via `promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL>`. The step's stale `trigger_tags` wording is corrected to `tags` (the frontmatter contract fixed by 001 D4) with the example skills unchanged. Trade-off: one more explicit path in the behavioral contract - consistent with the step-2/3 precedent.

## 3. Affected Files & Scope

- Overwritten in place: `.agents/skills/spec-builder/SKILL.md` — skill doc (frontmatter per D2 + standard body per D3; overwrites the untracked scaffold in place, no git delete needed)
- Created: `.agents/skills/spec-builder/scripts/promote_spec.py` — check/promote engine (D1)
- Modified: `.agents/skills/spec-builder/references/implementation-plan-template.md` — template stays the format truth; usage line aligned with the engine (check/promote paths) (D1/D3)
- Modified: `.agents/skills/spec-builder/references/todo-checklist-format.md` — unchanged semantics; ASCII punctuation normalized (D3)
- Modified: `.agents/rules/system.md` — §2 step 4: engine invocation + `tags` wording (D6)
- Generated: `.agents/MAP.md` — regenerated (row unchanged `*Use when: ...*`; snapshot hash changes; index already committed)
- Created: `docs/specs/004-spec-builder-core-skill.md` — this spec
- Untouched: `AGENT.md`, `docs/architecture/000-modular-agent-orchestration-v7.md`, `docs/specs/001/002/003`, `.agents/skills/map-generator|auto-router|phase-protocol/`, `docs/temp/`

## 4. Actionable TODO Checklist

- [x] Step 1: Create `.agents/skills/spec-builder/scripts/promote_spec.py` — stdlib-only; `find_root` via the `AGENT.md` marker; `check` mode (parse `## N.` headings, lane-required section sets B:{1,3,4} / A:{1-6}, missing list, exit 1); `promote` mode (check first, next-NNN scan of `--specs-dir` (default `<root>/docs/specs`), slug from title, `--slug` override, Status line replacement with `PROVISIONAL - AUTONOMOUS DEFAULT` expansion, exists-refusal, `--dry-run`, ASCII output); exit codes 0/1.
- [x] Step 2: Create `.agents/skills/spec-builder/SKILL.md` — frontmatter per D2 (no `type:`/`trigger_tags`); body per the standard structure (Overview, When to Use, Instructions, Output Contract, Notes) per D3.
- [x] Step 3: Update `.agents/skills/spec-builder/references/implementation-plan-template.md` and `todo-checklist-format.md` per D1/D3.
- [x] Step 4: Update `.agents/rules/system.md` §2 step 4 (engine invocation + `tags` wording) per D6.
- [x] Step 5: Regenerate `.agents/MAP.md` via `map-generator` (first `regenerated`, second `MAP.md is fresh`); verify the spec-builder row shows Active Condition `*Use when: spec, plan draft, promote, implementation plan, template*`.
- [x] Step 6: Verify engine behavior per §5 — check pass/fail per lane, dry-run numbering, real promote into a `--specs-dir` sandbox (never `docs/specs/`), exists-refusal, sequential numbering, PROVISIONAL status; confirm `git status --short` shows only §3 files.

## 5. Verification Commands

All promotes target a sandbox directory; the real `docs/specs/` is never touched by verification.

- Lane B check pass: `uv run python .agents/skills/spec-builder/scripts/promote_spec.py check <draft-with-1,3,4> --lane B` -> exit 0, `check passed`
- Lane B check fail: same draft missing section 1 -> exit 1, `missing sections: 1`
- Lane A check fail: full-section draft missing 5 and 6 -> exit 1, `missing sections: 5, 6`; with 5/6 present -> exit 0
- Dry-run: `promote <draft> --lane A --status APPROVED --specs-dir <sandbox> --dry-run` -> prints `next: 001` and `target: <sandbox>/001-<slug>.md`, writes nothing
- Real promote into a sandbox with a pre-seeded `003-x.md`: `promote <draft> --lane B --status APPROVED --specs-dir <sandbox>` -> `promoted: <sandbox>/004-<slug>.md`; the file's `Status:` line reads `APPROVED`
- Duplicate refusal: repeating the same promote (same draft title) -> exit 1, `already exists: <sandbox>/004-<slug>.md` — no second numbered copy is created
- PROVISIONAL: `--status PROVISIONAL` on a different draft -> `005-<slug>.md` with header `Status: PROVISIONAL - AUTONOMOUS DEFAULT`; repeating it -> exit 1, `already exists`
- Exists-refusal: promote when the target already exists -> exit 1, `already exists`
- MAP.md idempotency: `generate_map.py` twice -> `regenerated`, then `MAP.md is fresh`; spec-builder row `*Use when: ...*`
- Visual: `system.md` §2 step 4 includes both engine paths and `tags` wording
- `git status --short` shows only §3 files

## 6. Rollback Strategy

- Delete `.agents/skills/spec-builder/scripts/` (`promote_spec.py`).
- `git checkout .agents/rules/system.md` reverts the §2 step 4 edit.
- `git checkout .agents/MAP.md` restores the committed index; regenerable by map-generator at any time.
- Delete `docs/specs/004-spec-builder-core-skill.md`.
- The superseded scaffold was uncommitted (untracked) — no git copy exists; its content is fully covered by 000 §§5/7/10 and this spec, so recreation from history is unnecessary.
- No verification or eval run ever writes into the real `docs/specs/` (sandbox `--specs-dir` only), so no spec files require rollback.