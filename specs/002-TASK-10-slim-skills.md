# TASK 002-10 — slim `.agents` skills (detail moved to `docs/`)

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Cut the `.agents/{rules,skills}` files down to the operational minimum (context budget): keep
the triggers, the exact commands, and the guardrails; replace long explanation with a short
pointer to the matching `docs/` topic. Target: `phase-protocol/SKILL.md` under ~120 lines, same
discipline for the other SKILL.md files. Do not lose any normative rule — move it to docs,
don't delete it.

### Progress
- [x] pick the long prose blocks in each SKILL.md
- [x] move them to the right docs/ topic; leave a one-line pointer
- [x] verify every pointer target exists
- [x] keep frontmatter `name`/`description`/`tags` intact

## Owns
- `.agents/skills/phase-protocol/SKILL.md`
- `.agents/skills/auto-router/SKILL.md`
- `.agents/skills/spec-builder/SKILL.md`
- `.agents/skills/verification-runner/SKILL.md`
- `.agents/skills/task-cleaner/SKILL.md`
- `.agents/rules/system.md`

## Reads / Context (read-only)
- `docs/lifecycle.md`
- `docs/task-files.md`
- `docs/verification.md`
- `docs/run-contract.md`
- `docs/branching.md`

## Skills to use
- map-generator

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'test "$(wc -l < .agents/skills/phase-protocol/SKILL.md)" -lt 120 && echo LEAN-OK'
```
**Expect:** `LEAN-OK`
