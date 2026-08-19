# 003: phase-protocol — Third Core Skill (Meta-Skill: Phases, Gates & Autonomy Engine)

Status: APPROVED | Phase: 2-Build | Author: AI Agent | Date: 2026-08-15

> **Derived from:** `docs/architecture/000-modular-agent-orchestration-v7.md` (master reference, approved, verbatim; §§3, 5, 9: Socratic gate, session detection, autonomy policy, response schema, phase references, circuit breakers), `AGENTS.md` (`autonomy_level: supervised`), and `.agents/rules/system.md` (behavioral contract, accepted; §1 always-loaded set, §2 step 3 is phase-protocol's boot position).
> **Supersedes:** the untracked scaffold `.agents/skills/phase-protocol/` (legacy frontmatter violating the 001 D4 contract; flat section structure; no engine). `docs/specs/002-auto-router-core-skill.md` D4 defined the handoff verdict phase-protocol consumes; this spec is the receiving-side design.
> This spec designed the framework's third core skill in full - gate-resolution engine, SKILL.md doc, reference alignment, and the system.md boot-chain edit. **Implemented and verified on 2026-08-15 (all §5 checks green).**

## 1. Goal & Context

The Modular Agent Orchestration framework requires a process-governance meta-skill (000 §5) that drives the SDLC phases (Plan → Build → Review), enforces tool permissions, resolves Socratic gates, applies the autonomy policy, and emits the `[STATUS: ...]` 5-tag header with the 4-Block response schema. Per `.agents/rules/system.md` §2, every request is processed in order: **step 1** map-generator freshness gate (built and committed) → **step 2** auto-router (built and committed, `4eadd54`) → **step 3** phase-protocol → **step 4** on-demand skills. Auto-router's D4 handoff contract (Lane/Session/candidates/escalation flag) names phase-protocol as its sole consumer, and system.md §1 already lists phase-protocol in the always-loaded set — it is the final mandatory link in the boot chain, after which on-demand skills (spec-builder, verification-runner, task-cleaner) can be routed to.

The current `.agents/skills/phase-protocol/` scaffold is untracked and stale: its frontmatter uses legacy fields (`type: core`, `trigger_tags`, no `version`/`author`) that violate the frontmatter contract fixed by spec 001 D4; its body is organized as flat numbered sections rather than the standard structure fixed by spec 002's committed SKILL.md; and its autonomy policy is pure judgment with no mechanical, testable core — a safety gap given the policy gates the security-relevant fail-closed matrix (000 §3.4). It is replaced in place by this spec's design.

## 2. Architectural Decisions & Trade-offs

**D1. Gate-resolution engine — `resolve_gate.py` (human-approved).** The skill owns an assist engine: `.agents/skills/phase-protocol/scripts/resolve_gate.py` (skill-local scripts per 001 D1's structural rule; stdlib-only Python, styled after `generate_map.py` and `match_skills.py`; `find_root` via the `AGENTS.md` marker). It is a deterministic decision machine over the autonomy matrix — (gate: blocking|non-blocking) × (session: interactive|non-interactive) × (lane A/B/C/D) × (autonomy: supervised|autonomous):

| Gate | Session | Autonomy | Outcome | Exit |
| :--- | :--- | :--- | :--- | :--- |
| non-blocking | any | any | Proceed; state the default | 0 |
| blocking | interactive | any | Halt; await human answer | 1 |
| blocking | non-interactive | supervised | **Fail closed** — write `docs/temp/escalation.md`, never gate-log | 2 |
| blocking | non-interactive | autonomous + `--lane-a-surface` | **Always fail closed** (000 §3.4.3: schema/auth/public-API never autonomous) | 2 |
| blocking | non-interactive | autonomous, no Lane-A surface | Resolve to the Recommended Option; append verbatim entry to `docs/temp/gate-log.md` | 0 |

Autonomy defaults to the `autonomy_level` frontmatter in `AGENTS.md` (no hardcoding); `--autonomy` overrides for testing. Gate-log entries follow the fixed format already declared in `docs/temp/gate-log.md` (question, options, choice made, autonomy mode, provisional-spec tag) and are **append-only — the engine never truncates or purges** (000 §9, system.md §3). Fail-closed writes follow the fixed `docs/temp/escalation.md` format (pending question with guided options, lane, session). Trade-off: a script on a meta-skill 000 describes as checklist-driven — justified because the matrix is the framework's safety-critical core; a mechanical engine makes every outcome testable (mirroring 002's §5 verification style) and fixes the audit-trail format machine-verifiably instead of by LLM judgment. `--autonomy autonomous` resolution on Lane A surfaces is unreachable regardless of flags — the exception is encoded, not advisory.

**D2. Frontmatter contract compliance.** The new `SKILL.md` follows the standard frontmatter fixed by 001 D4: `name: phase-protocol`, `description` (ASCII-safe, one sentence), `version: 1.0.0`, `author: AI Agent`, `tags` (phase, plan, build, review, gate, autonomy, response, socratic), custom `scope: always`. Legacy `type: core` and `trigger_tags` are dropped. Consequence: `map-generator` renders phase-protocol's Active Condition as `*Always active*` in `MAP.md`, matching system.md §1's always-loaded set — unchanged from today, but now contract-compliant.

**D3. SKILL.md restructured to the standard format.** The scaffold's flat numbered sections (1. Phase routing, 2. Socratic inquiry gate, 3. Autonomy policy, 4. Response schema) reorganize into the structure fixed by auto-router's committed SKILL.md: **Overview** (process-governance meta-skill; mandatory step 3 of the boot chain), **When to Use** (every session — `scope: always`; every phase transition; every gate), **Instructions** (1. route the phase from the auto-router verdict and load `references/<phase>.md` at phase start, completing a phase only when its checklist is green; 2. enforce tool posture per phase — read-only in Plan/Review, lane-scoped edits in Build; 3. resolve every gate through the engine — blocking vs non-blocking classification per 000 §3.1, engine invocation per D6, non-blocking gates state the default and proceed in both session types; 4. emit the 5-tag header + 4 blocks in every response), **Output Contract** (the `[STATUS: Phase | Task | Lane | Worktree | Session]` header with the 4 blocks — SUMMARY OF UNDERSTANDING / ACTIONS TAKEN / SOCRATIC GATE / NEXT STEP — as the schema every skill inherits; `Worktree: main` unless a worktree is active), **Notes** (owns gates/autonomy/response schema exclusively; never re-triages the lane; gate-log is append-only and never purged). Trade-off: one restructure pass vs. preserving scaffold prose — the scaffold's checklists survive in the references; only the skill contract reorganizes.

**D4. References aligned, four kept.** `references/plan.md`, `build.md`, `review.md` are load-bearing (000 §5.1 explicitly names them) and `harness.md` stays situational (000 §12). Edits: `plan.md` gains the exact spec-builder template path (`.agents/skills/spec-builder/references/implementation-plan-template.md` — a forward contract, matching lane-matrix's precedent for the not-yet-built spec-builder skill); all three checklists route gate resolution through the engine rather than bare judgment; `build.md`'s 3-retry → circuit-breaker escalation path is verified against 000 §9 (max 3 consecutive attempts, escalation.md + revert + handoff, delegating execution to `verification-runner`); `review.md`'s promotion/ADR/cleanup steps are confirmed as forward contracts to spec-builder and task-cleaner. Trade-off: minimal edits to working checklists vs. a full rewrite — the scaffold prose is sound; only gate resolution and the template path change.

**D5. Consumes the auto-router verdict (002 D4, receiving side).** Phase-protocol consumes auto-router's output — Lane (A/B/C/D) and Session (Interactive/Non-Interactive) into the `[STATUS: ...]` header, candidate skills into step 4's on-demand loading, and the optional escalation flag as an announce-only upward re-route: when execution reveals a higher-lane criterion, phase-protocol continues under the announced lane with the same phase machinery (re-plan under the new lane's artifact requirements) — it never re-triages the lane itself, never asks permission to escalate, and never silently de-escalates (000 §4). Trade-off: strict separation keeps each skill's authority legible (gates/autonomy/response schema are exclusively phase-protocol's domain, per 002 D4); the cost is that every escalation re-emits the verdict through the header.

**D6. system.md §2 step 3 edit.** Step 3 gains the engine invocation line, mirroring step 2's edit pattern: gates resolve via `python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate <blocking|non-blocking> --session <Interactive|Non-Interactive> --lane <A|B|C|D> [--lane-a-surface] --question "<text>" --options "<A: ...; B: ...>"` (autonomy read from AGENTS.md; append-only gate-log; fail-closed writes escalation.md). §3's gate-log guardrail wording is aligned with the append-only engine behavior. Trade-off: one more explicit path in the behavioral contract — consistent with the step-2 precedent and keeps the engine invocation discoverable.

## 3. Affected Files & Scope

- Overwritten in place: `.agents/skills/phase-protocol/SKILL.md` — skill doc (frontmatter per D2 + standard body per D3; overwrites the untracked scaffold in place, no git delete needed)
- Created: `.agents/skills/phase-protocol/scripts/resolve_gate.py` — gate-resolution & autonomy engine (D1)
- Modified: `.agents/skills/phase-protocol/references/plan.md` — template path + engine-based gate resolution (D4)
- Modified: `.agents/skills/phase-protocol/references/build.md` — engine-based gate resolution + circuit-breaker cross-check (D4)
- Modified: `.agents/skills/phase-protocol/references/review.md` — engine-based gate resolution + forward contracts (D4)
- Modified: `.agents/skills/phase-protocol/references/harness.md` — unchanged semantics; posture aligned (D4)
- Modified: `.agents/rules/system.md` — §2 step 3: engine invocation + §3 gate-log wording (D6)
- Generated: `.agents/MAP.md` — regenerated (row unchanged `*Always active*`; snapshot hash changes; index already committed)
- Created: `docs/specs/003-phase-protocol-core-skill.md` — this spec
- Untouched: `AGENTS.md`, `docs/architecture/000-modular-agent-orchestration-v7.md`, `docs/specs/001-map-generator-core-skill.md`, `docs/specs/002-auto-router-core-skill.md`, `.agents/skills/map-generator/`, `.agents/skills/auto-router/`, `docs/temp/`

## 4. Actionable TODO Checklist

- [x] Step 1: Create `.agents/skills/phase-protocol/scripts/resolve_gate.py` — stdlib-only; `find_root` via the `AGENTS.md` marker; args `--gate`, `--session`, `--lane`, `--autonomy` (default: parse `autonomy_level` from AGENTS.md frontmatter), `--lane-a-surface`, `--question`, `--options`; the five-row decision matrix per D1 (Lane-A exception encoded, not advisory); append-only gate-log entry per the fixed `docs/temp/gate-log.md` format; fail-closed escalation per the fixed `docs/temp/escalation.md` format; ASCII-only output; exit codes 0 (proceed/resolved), 1 (halt), 2 (fail-closed).
- [x] Step 2: Create `.agents/skills/phase-protocol/SKILL.md` — frontmatter per D2 (no `type:`/`trigger_tags`); body per the standard structure (Overview, When to Use, Instructions, Output Contract, Notes) per D3.
- [x] Step 3: Update `.agents/skills/phase-protocol/references/plan.md`, `build.md`, `review.md`, `harness.md` per D4.
- [x] Step 4: Update `.agents/rules/system.md` §2 step 3 (engine invocation) and §3 (gate-log append-only wording) per D6.
- [x] Step 5: Regenerate `.agents/MAP.md` via `map-generator` (first `regenerated`, second `MAP.md is fresh`); verify the phase-protocol row shows Active Condition `*Always active*`.
- [x] Step 6: Verify engine behavior per §5 — all five matrix rows, append-only gate-log, ASCII output; confirm `git status --short` shows only §3 files (scaffold overwritten in place, untracked — no git delete entries).

## 5. Verification Commands

- Interactive blocking: `python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate blocking --session interactive --lane A --question "adopt Postgres? " --options "A (Recommended): Postgres; B: MySQL"` → prints HALT, exit 1, no files written.
- Non-interactive supervised fail-closed: `python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate blocking --session non-interactive --lane B --question "..." --options "A: x; B: y"` (no `--autonomy`; AGENTS.md `supervised`) → exit 2, `docs/temp/escalation.md` written, `gate-log.md` untouched.
- Lane-A exception (000 §3.4.3): `... --gate blocking --session non-interactive --lane A --autonomy autonomous --lane-a-surface ...` → exit 2 even under autonomous — the exception is encoded.
- Autonomous resolution: `... --gate blocking --session non-interactive --lane B --autonomy autonomous --question "which cache?" --options "A (Recommended): redis; B: memcached"` → exit 0, prints RESOLVED, `docs/temp/gate-log.md` appended with the verbatim entry (question, options, choice, autonomy mode, provisional tag).
- Non-blocking (both sessions): `... --gate non-blocking --session interactive --lane C ...` and `... --gate non-blocking --session non-interactive --lane C ...` → exit 0, no files written.
- Append-only: run the autonomous case twice → two `## Entry` blocks, previous entries intact (never truncated).
- Matrix edge: `--lane-a-surface` without `--autonomy autonomous` (supervised) → exit 2, fail-closed as expected.
- MAP.md idempotency: `python .agents/skills/map-generator/scripts/generate_map.py` twice — `regenerated`, then `MAP.md is fresh`; phase-protocol row reads `*Always active*`.
- Visual: header format check — every planned response carries the 5-tag `[STATUS: ...]` header; output is ASCII-only; `system.md` §2 step 3 includes the engine path.
- Cross-check (002 §5 already proven): `python .agents/skills/auto-router/scripts/match_skills.py "phases gate the workflow"` → phase-protocol surfaces via description hits, confirming the boot-chain handoff still resolves.
- `git status --short` shows only §3 files.

## 6. Rollback Strategy

- Delete `.agents/skills/phase-protocol/scripts/` (`resolve_gate.py`).
- `git checkout .agents/rules/system.md` reverts the §2 step 3 and §3 edits.
- `git checkout .agents/MAP.md` restores the committed index; it is regenerable by the map-generator engine at any time.
- Delete `docs/specs/003-phase-protocol-core-skill.md`.
- The superseded scaffold was uncommitted (untracked) — no git copy exists; its checklist content is fully covered by 000 §§3–5/9 and this spec, so recreation from history is unnecessary.
- `docs/temp/gate-log.md` is preserve-only by contract (never purged until human review); `docs/temp/escalation.md` is gitignored ephemeral state.
