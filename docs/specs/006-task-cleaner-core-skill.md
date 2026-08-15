# 006: task-cleaner — Sixth Core Skill (Scratchpad Garbage Collector)

Status: APPROVED | Phase: 2-Build | Author: AI Agent | Date: 2026-08-15

> **Derived from:** `docs/architecture/000-modular-agent-orchestration-v7.md` (master reference, approved, verbatim; §5.6: purge `docs/temp/` scratchpad upon human acceptance, preserve unreviewed `gate-log.md`; §10 memory lifecycle: "TASK CLEANER - Purges docs/temp/* (Preserves gate-log.md)"; §13 task garbage collection; §2 directory map: `docs/temp/` holds `active-task.md`, `draft-plan.md`, `escalation.md`, `gate-log.md`, `handoff-payload.md` and its own `.gitignore`), `AGENT.md` (`autonomy_level: supervised`), `.agents/rules/system.md` (behavioral contract, accepted; §3: `docs/temp/gate-log.md` is append-only and never purged until a human reviews it; §4 names "scratchpad purging in `task-cleaner`"), `docs/specs/005-verification-runner-core-skill.md` (D1: `docs/temp/verify-state.json` is "purged by task-cleaner on acceptance"), and `.agents/skills/phase-protocol/references/review.md` (§4.2: "Call `task-cleaner` when the human accepts the task (purges `docs/temp/` scratchpad; preserves unreviewed `gate-log.md`)"). Together these form the cleanup contract: the scratchpad is ephemeral by design (gitignored), and `gate-log.md` is the one append-only audit file that survives until a human explicitly clears it.
> **Supersedes:** the untracked scaffold `.agents/skills/task-cleaner/` (legacy frontmatter violating the 001 D4 contract - `type: core`, `trigger_tags`, no `version`/`author`, and a corrupted non-ASCII em-dash `�?` in the description; flat numbered sections; no engine). phase-protocol `review.md` already delegates cleanup to this skill — this spec makes that forward contract real.
> This spec designed the framework's sixth core skill in full - scratchpad purge engine with a gate-log preservation guarantee, SKILL.md doc, and the system.md boot-chain edit. **Implemented and verified on 2026-08-15 (all §5 checks green).**

## 1. Goal & Context

The Modular Agent Orchestration framework requires a garbage-collection skill (000 §5.6) that purges the ephemeral `docs/temp/` scratchpad when a human accepts a task or confirms completion (usually at the end of Phase 3 Review, per phase-protocol `review.md` §4.2), resetting it for the next session while **never purging `docs/temp/gate-log.md` until a human explicitly reviews and clears it** (000 §3.4.2: "this file is never purged by task-cleaner until a human explicitly reviews it"; system.md §3). The scratchpad's contents are canonical per 000 §2: `active-task.md`, `draft-plan.md`, `escalation.md`, `gate-log.md`, `handoff-payload.md`, plus the `.gitignore` that makes the whole directory ephemeral — and per-session add-ons such as `verify-state.json` (005 D1) and ad-hoc scratch files/directories. Promoted artifacts (`docs/specs/*`, `docs/decisions/*`, `docs/architecture/*`) are persistent and must never be touched.

The current `.agents/skills/task-cleaner/` scaffold is untracked and stale: its frontmatter uses legacy fields (`type: core`, `trigger_tags`, no `version`/`author`) violating the 001 D4 frontmatter contract, its description contains a corrupted em-dash (`�?`) that `map-generator` would sanitize, and its purge rules are judgment, not mechanics — a safety gap because "never purge gate-log.md" is exactly the kind of guardrail that gets violated in a hurry, and a hand-rolled `Remove-Item` sweep gives no audit of what was purged vs. preserved. It is replaced in place by this spec's design.

## 2. Architectural Decisions & Trade-offs

**D1. `clean.py` engine — purge mechanics with a preservation guarantee.** The skill owns an assist engine: `.agents/skills/task-cleaner/scripts/clean.py` (skill-local scripts per 001 D1; stdlib-only Python, styled after `verify.py` / `promote_spec.py`; `find_root` via the `AGENT.md` marker). Two modes:
- **clean**: `clean.py clean [--dry-run] [--preserve <list>] [--temp-dir <dir>]` — deletes every file and subdirectory inside the scratchpad **except** the preserved basenames; default preserve list is `gate-log.md,.gitignore` (the audit file and the file that makes the directory ephemeral are both non-negotiable by default). `--preserve ""` is the explicit override that allows purging everything, including a gate-log a human has reviewed and cleared. `--dry-run` lists what would be purged and preserved without deleting anything. Prints a report: `purged: <N>, preserved: <M>`. Refuses to run against the repo root or any path above it (the target must be a real scratchpad, never a parent directory).
- **status**: `clean.py status [--temp-dir <dir>]` — lists the scratchpad's contents with would-purge/would-preserve classification and the current preserve list; read-only, exit 0.
Trade-off: an engine on a deletion task — justified because deletion is irreversible, the gate-log preservation is the framework's audit-trail guarantee (000 §3.4.2, system.md §3), and a report of exactly what was purged vs. preserved is what makes cleanup reviewable. The engine never decides whether the task is accepted — the agent calls it when the acceptance gate has passed (review.md §4.2).

**D2. Purge scope is the whole scratchpad, nothing else.** The engine clears all contents of `docs/temp/` (files and subdirectories, including per-session workspaces and `verify-state.json`) except the preserved list. It never touches `docs/specs/`, `docs/decisions/`, `docs/architecture/`, or anything outside the scratchpad — the target directory is bounded, and a path equal to the repo root (or above) is refused. Trade-off: aggressive scope (everything ephemeral goes) vs. selective file lists — justified because the directory is gitignored by design (000 §2: "Ephemeral session state... keeping git commit history clean"); a selective purge would leave stragglers that defeat the reset purpose, and promoted artifacts live outside the scratchpad by construction.

**D3. `gate-log.md` is preserved by default and purged only on explicit override.** The preserve list defaults to `gate-log.md,.gitignore`; `--preserve ""` explicitly surrenders the audit file. The distinction matters: an agent that hand-deletes a gate-log is a policy violation with no audit trail, while an agent that passes `--preserve ""` is executing a reviewed-and-cleared state (000 §3.4.2). Trade-off: the override is a bypass by design — justified because the guardrail's purpose is to prevent *accidental* destruction; a human-cleared gate-log must be purgable, and the explicit flag makes the act legible in the shell history and the cleanup report.

**D4. No stub restoration in the engine.** The scaffold's rule 4 ("Restore the template stubs for the purged files... if stubs are missing, note it in the summary") refers to a framework Phase-1 skeleton that does not exist in this repository. The engine does not invent formats; the SKILL.md instructs the agent to note stub absence in the cleanup summary instead. Trade-off: no stub regeneration vs. the scaffold's aspiration — justified by the scaffold's own fallback ("note it in the summary instead of inventing new formats"); the next task's Plan phase creates its scratchpad files fresh (spec-builder drafts into `docs/temp/draft-plan.md` on demand).

**D5. system.md §2 step 4 edit.** Step 4 gains the engine invocation line, mirroring the spec-builder/verification-runner edit pattern: cleanup runs via `uv run python .agents/skills/task-cleaner/scripts/clean.py clean` (gate-log.md preserved by default; `--preserve ""` only after human review clears it). Trade-off: one more explicit path in the behavioral contract — consistent with the step-2/3/4 precedent; this closes the boot chain's on-demand set (spec-builder, verification-runner, task-cleaner).

## 3. Affected Files & Scope

- Overwritten in place: `.agents/skills/task-cleaner/SKILL.md` — skill doc (frontmatter per 001 D4 + standard body; overwrites the untracked scaffold in place, no git delete needed; the corrupted `�?` em-dash is fixed to ASCII `-`)
- Created: `.agents/skills/task-cleaner/scripts/clean.py` — clean/status engine (D1–D3)
- Modified: `.agents/rules/system.md` — §2 step 4: task-cleaner engine invocation (D5)
- Generated: `.agents/MAP.md` — regenerated (row `*Use when: <tags>*`; snapshot hash changes; index already committed)
- Created: `docs/specs/006-task-cleaner-core-skill.md` — this spec
- Untouched: `AGENT.md`, `docs/architecture/000-modular-agent-orchestration-v7.md`, `docs/specs/001/002/003/004/005`, `.agents/skills/map-generator|auto-router|phase-protocol|spec-builder|verification-runner/`, `docs/temp/`

## 4. Actionable TODO Checklist

- [x] Step 1: Create `.agents/skills/task-cleaner/scripts/clean.py` — stdlib-only; `find_root` via the `AGENT.md` marker; `clean` mode (whole-scratchpad purge, default preserve `gate-log.md,.gitignore`, `--preserve ""` override, `--dry-run`, refuse root-or-above targets, `purged: N, preserved: M` report, ASCII output); `status` mode (contents + classification); `--temp-dir` override for testing (verification and evals never touch the real `docs/temp/`).
- [x] Step 2: Create `.agents/skills/task-cleaner/SKILL.md` — frontmatter per 001 D4 (no `type:`/`trigger_tags`; ASCII description); body per the standard structure (Overview, When to Use, Instructions, Output Contract, Notes); stub-absence note per D4.
- [x] Step 3: Update `.agents/rules/system.md` §2 step 4 (task-cleaner engine invocation) per D5.
- [x] Step 4: Regenerate `.agents/MAP.md` via `map-generator` (first `regenerated`, second `MAP.md is fresh`); verify the task-cleaner row shows Active Condition `*Use when: <tags>*`.
- [x] Step 5: Verify engine behavior per §5 — default clean preserves gate-log + .gitignore, override purges all, dry-run deletes nothing, status classifies, root-refusal, sandbox isolation; confirm `git status --short` shows only §3 files.

## 5. Verification Commands

All cleans target a sandbox `--temp-dir`; the real `docs/temp/` is never touched by verification.

- Status: `clean.py status --temp-dir <sandbox>` -> lists contents, classifies would-purge vs would-preserve, prints preserve list; exit 0
- Default clean: `clean.py clean --temp-dir <sandbox>` (sandbox seeded with active-task.md, draft-plan.md, verify-state.json, escalation.md, gate-log.md, handoff-payload.md, scratch/) -> exit 0, `purged: 7, preserved: 2`; gate-log.md and .gitignore remain with content intact; everything else gone
- Dry-run: `clean.py clean --dry-run --temp-dir <sandbox>` -> lists the same files without deleting; re-run `status` shows all files still present
- Override: `clean.py clean --preserve "" --temp-dir <sandbox>` -> `purged: 2, preserved: 0`; the scratchpad is empty
- Root refusal: `clean.py clean --temp-dir <repo-root>` -> exit 1, refusal message, nothing deleted
- Missing dir: `clean.py clean --temp-dir <empty-or-missing>` -> exit 0, `purged: 0`
- MAP.md idempotency: `generate_map.py` twice -> `regenerated`, then `MAP.md is fresh`; task-cleaner row `*Use when: ...*`
- Visual: `system.md` §2 step 4 includes the task-cleaner engine path
- `git status --short` shows only §3 files

## 6. Rollback Strategy

- Delete `.agents/skills/task-cleaner/scripts/` (`clean.py`).
- `git checkout .agents/rules/system.md` reverts the §2 step 4 edit.
- `git checkout .agents/MAP.md` restores the committed index; regenerable by map-generator at any time.
- Delete `docs/specs/006-task-cleaner-core-skill.md`.
- The superseded scaffold was uncommitted (untracked) — no git copy exists; its content is fully covered by 000 §§2/5/10/13 and this spec, so recreation from history is unnecessary.
- No verification or eval run ever touches the real `docs/temp/` (sandbox `--temp-dir` only), so no scratchpad state requires rollback; the engine's default preserve list means even a real run keeps `gate-log.md` and `.gitignore`.