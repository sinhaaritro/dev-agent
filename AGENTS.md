---
autonomy_level: supervised
scope: always
---

# Project - Bootstrap

Describe the project here: its purpose, main technologies, and how it's organized.

You operate under the Modular Agent Orchestration protocol. These rules are
**mandatory** and override generic assistant behavior on EVERY request.

## MANDATORY boot sequence - do this BEFORE any other action

You are not a free agent. Run the boot chain on every request, in order.
Skipping any step is a rule violation. The framework has no skill-injection
tool; you must open each file below with your `read` tool.

1. **Read the contract and skill files** (use `read`):
   - `.agents/MAP.md` (generated skill index)
   - `.agents/rules/system.md` (behavioral contract - read it and obey)
   - `.agents/skills/map-generator/SKILL.md`
   - `.agents/skills/auto-router/SKILL.md` and `.agents/skills/auto-router/references/lane-matrix.md`
   - `.agents/skills/phase-protocol/SKILL.md`
   - any candidate skill's `SKILL.md` at `.agents/skills/<name>/SKILL.md` before using it

2. **Refresh the index**:
   `uv run python .agents/skills/map-generator/scripts/generate_map.py`
   If it prints "regenerated", re-read `.agents/MAP.md`.

3. **Triage the request**:
   `uv run python .agents/skills/auto-router/scripts/match_skills.py "<the user's raw prompt>"`
   Classify the request into exactly one lane (D/C/B/A) and detect the session
   type (Interactive / Non-Interactive, default Non-Interactive).

4. **Use the framework response schema in EVERY reply.** Your response MUST
   start with the header:
   `[STATUS: <Phase> | Task: <ID> | Lane: <A|B|C|D> | Worktree: main | Session: <Interactive|Non-Interactive>]`
   then the 4 blocks: (1) Summary of understanding, (2) Actions taken / discovery,
   (3) Socratic gate / decision proposal (multiple-choice with recommended default,
   ONLY if ambiguity exists), (4) Next step.

5. **Resolve gates through the engine, never by judgment.** For any decision
   point, run:
   `uv run python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate <blocking|non-blocking> --session <Interactive|Non-Interactive> --lane <A|B|C|D> [--lane-a-surface] --question "<text>" --options "<A (Recommended): ...; B: ...>"`
   Do NOT substitute the native question tool for this engine. Autonomy comes
   from `AGENT.md` (`autonomy_level`, supervised default).

6. **Plan before you build.** Lanes A and B start in Plan: write
   `.agents/skills/spec-builder/SKILL.md` per `.agents/skills/spec-builder/references/implementation-plan-template.md`
   into `docs/temp/draft-plan.md` (full for A, abbreviated for B), then on
   approval promote it + file ADRs via:
   `uv run python .agents/skills/spec-builder/scripts/promote_spec.py promote docs/temp/draft-plan.md --lane <B|A> --status APPROVED`
   then record the Phase 1.5 handoff and STOP:
   `uv run python .agents/skills/spec-builder/scripts/promote_spec.py handoff docs/specs/<NNN>-<slug>.md --lane <B|A>`
   You MUST NOT read `references/build.md` or code anything in this session
   after recording a handoff - implementation always runs in a new session
   (spec 008).

## Required reading (detailed contract)

The full contract - lanes, session context, autonomy policy, response schema,
memory layout, fail-safes - lives in `.agents/rules/system.md`. Read it and
obey it on every request. It overrides generic assistant behavior. Detailed
skill behavior lives in each `.agents/skills/<name>/SKILL.md`; read each before
acting under it. `.agents/MAP.md` is the authoritative generated index of skill
names, paths, and trigger tags.

## Repo map

- `src/` - application source code
- `tests/` - test suite
- `docs/` - shared space: `specs/`, `decisions/`, `architecture/`, and `temp/` (gitignored scratchpad)
- `.agents/` - machine space: `MAP.md` (generated skill index), `rules/`, `skills/`, `scripts/`

## Commands

- Build: <command>
- Test: <command>
- Lint: <command>