# TASK 002-11 — bootstrap reference seeds match the new framework

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Update the bootstrap seed files so a freshly bootstrapped project gets the new framework:
`.agents/skills/bootstrap/reference/AGENTS.md`, `reference/rules/system.md`,
`reference/.cursorrules`, `reference/.windsurfrules`, `reference/.gitignore`. They must carry
the canonical phases, the single `Status:` model, the run contract, and the never-merge-main
guardrail — and seed `.agents/agents/coder.md` (from task 04).

### Progress
- [x] apply the T5 phase/status renames to every reference file
- [x] add the run contract + guardrail (T6/T7) to reference/rules/system.md
- [x] ensure .gitignore covers `specs/temp` and `MAP.md`
- [x] confirm no `Phase:` remains in reference/

## Owns
- `.agents/skills/bootstrap/reference/AGENTS.md`
- `.agents/skills/bootstrap/reference/rules/system.md`
- `.agents/skills/bootstrap/reference/.cursorrules`
- `.agents/skills/bootstrap/reference/.windsurfrules`
- `.agents/skills/bootstrap/reference/.gitignore`

## Reads / Context (read-only)
- `.agents/rules/system.md`
- `.agents/skills/auto-router/references/lane-matrix.md`
- `specs/002-SPEC-subagent-task-files-full-plan.md`

## Skills to use
- bootstrap

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'test -z "$(grep -rn "Phase:" .agents/skills/bootstrap/reference)" && grep -qi "never merge" .agents/skills/bootstrap/reference/rules/system.md && echo BOOTSTRAP-OK'
```
**Expect:** `BOOTSTRAP-OK`
