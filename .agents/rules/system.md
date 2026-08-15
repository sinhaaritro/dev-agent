---
name: system
type: rules
scope: always
---

# SYSTEM — BEHAVIORAL CONTRACT

You are an AI software development agent under the Modular Agent Orchestration protocol (Spec V7). These rules are mandatory and override generic assistant behavior — when anything conflicts with this file, this file wins.

## 1. Loading semantics

Read **`scope: always`** files at session start; they are the baseline for every request. Load **`scope: on-demand`** files only when their trigger tags or context matches. Default when the tag is missing: always for `.agents/rules/`, on-demand for `.agents/skills/`. The always-loaded set consists of `AGENT.md`, `.agents/rules/*`, and any skill declared `scope: always` — currently `auto-router` and `phase-protocol`. Check `.agents/MAP.md` for the authoritative generated list of skills (all skills are treated as equal in the index; `scope` only marks load behavior).

## 2. On every request, in this order

1. Verify `.agents/MAP.md` is fresh via `map-generator`: run `.agents/skills/map-generator/scripts/generate_map.py` — if it reports "regenerated", re-read the index. Never match against a stale index.
2. Run `auto-router` (scope: always) first: classify into a lane (D/C/B/A), detect the session type, apply escalation rules. Run its recall engine with the raw prompt — `uv run python .agents/skills/auto-router/scripts/match_skills.py "<prompt>"` — and treat the output as candidates only, never a filter: re-read `.agents/MAP.md` when candidates are thin, and a skill with zero literal hits can still apply.
3. Follow `phase-protocol` (scope: always): phases Plan → Build → Review, Socratic gates, autonomy policy, and the 4-Block response schema with the `[STATUS: ...]` header. Resolve every gate through its engine — `uv run python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate <blocking|non-blocking> --session <Interactive|Non-Interactive> --lane <A|B|C|D> [--lane-a-surface] --question "<text>" --options "<A (Recommended): ...; B: ...>"` — autonomy is read from `AGENT.md` (`autonomy_level`, supervised default); exit 0 = proceed/resolved (gate-log.md appended when autonomous), 1 = halt for human answer, 2 = fail-closed (escalation.md written, no changes). Never resolve a blocking gate by judgment alone.
4. Load and obey any other skill whose `tags` match (e.g. `spec-builder`, `verification-runner`, `task-cleaner`). When `spec-builder` is active, its engine owns the plan mechanics: validate drafts via `uv run python .agents/skills/spec-builder/scripts/promote_spec.py check <draft> --lane <B|A>`; promote approved plans via `uv run python .agents/skills/spec-builder/scripts/promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL>` (the gate is asserted by the status argument, never bypassed). When `verification-runner` is active, verification runs through its ledger and circuit breaker: `uv run python .agents/skills/verification-runner/scripts/verify.py run --command "<cmd>" --task <task-id>` (exit 0 = green, counter reset; 1 = failed, retry remaining; 2 = circuit breaker tripped at 3 consecutive failures - escalation.md written, halt; 3 = command source unresolved - detect the framework or ask); the counter lives in `docs/temp/verify-state.json`, never hand-tracked. When `task-cleaner` is active, cleanup runs through its engine: `uv run python .agents/skills/task-cleaner/scripts/clean.py clean` (purges the `docs/temp/` scratchpad on human acceptance; `gate-log.md` and `.gitignore` preserved by default; `--preserve ""` only after a human explicitly reviews and clears the gate-log — never hand-delete it).
5. No matching skill → baseline behavior: plan in `docs/temp/draft-plan.md`, build, verify, promote only on human acceptance.

## 3. Guardrails — never violate, regardless of skills loaded

- Never modify or delete `.env*` files, credentials/keys/certificates, lockfiles (unless executing approved dependency commands), or `docs/decisions/*` without explicit human confirmation.
- Never commit `docs/temp/` contents; `docs/temp/gate-log.md` is append-only and never purged until a human reviews it.

## 4. Delegation

Detailed behavior lives in the skills: lanes & escalation in `auto-router`, phases/gates/response schema/autonomy in `phase-protocol`, verification & circuit breaker in `verification-runner`, plan drafting & promotion in `spec-builder`, scratchpad purging in `task-cleaner`. If a skill is missing or unloaded, fall back to `docs/architecture/000-modular-agent-orchestration-v7.md` sections 3–5.