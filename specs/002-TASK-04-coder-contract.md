# TASK 002-04 — portable `coder` contract + bootstrap seeding

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Write `.agents/agents/coder.md` — the portable behavioral contract for the coder subagent:
role; input = the task file only; fetch more context on demand; return search/replace blocks
for large files; run the task's listed verification; **never commit, never plan, never expand
scope, never touch files it does not Own**; it is the sole writer of its own task file. Keep
it short; the harness adapter (model binding + permission surface) is per-harness. Then update
`.agents/skills/bootstrap/SKILL.md` to seed `agents/coder.md` + the adapter notes on bootstrap.

### Progress
- [ ] create `.agents/agents/coder.md` with the sections above
- [ ] add the seed step to bootstrap/SKILL.md (and its reference copy if present)
- [ ] note the trivial direct-fix exception (lead may edit directly; recorded `direct`)

## Owns
- `.agents/agents/coder.md`
- `.agents/skills/bootstrap/SKILL.md`

## Reads / Context (read-only)
- `specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md`
- `.agents/skills/phase-protocol/SKILL.md`

## Skills to use
- bootstrap

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'grep -q "never commit" .agents/agents/coder.md && echo CODER-CONTRACT-OK'
```
**Expect:** `CODER-CONTRACT-OK`
